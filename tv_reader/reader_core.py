from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import os
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
from PIL import Image, features


BOOK_EXTENSIONS = {".pdf", ".epub", ".mobi", ".xps", ".cbz"}
DEFAULT_VIEWPORT = (1920, 1080)
DEFAULT_EPUB_FONT_SIZE = 16
MIN_EPUB_FONT_SIZE = 10
MAX_EPUB_FONT_SIZE = 32
REFLOWABLE_EXTENSIONS = {"epub", "mobi"}


def _sha1_short(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def normalize_page(page: int, page_count: int) -> int:
    if page_count <= 0:
        return 0
    return page % page_count


def parse_size(value: str | None, default: tuple[int, int] = DEFAULT_VIEWPORT) -> tuple[int, int]:
    if not value:
        return default
    try:
        width_text, height_text = value.lower().split("x", 1)
        width = max(320, min(3840, int(width_text)))
        height = max(240, min(2160, int(height_text)))
        return width, height
    except (TypeError, ValueError):
        return default


def normalize_page_mode(value: object) -> str:
    return "single" if str(value).strip().lower() in {"single", "single_page", "page"} else "spread"


def normalize_font_size(value: object) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        size = DEFAULT_EPUB_FONT_SIZE
    return max(MIN_EPUB_FONT_SIZE, min(MAX_EPUB_FONT_SIZE, size))


@dataclass(frozen=True)
class BookInfo:
    id: str
    path: Path
    title: str
    extension: str
    size: int
    modified_ns: int
    fingerprint: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "extension": self.extension,
            "size": self.size,
            "modified_ns": self.modified_ns,
            "path": str(self.path),
        }


class BookLibrary:
    def __init__(self, roots: Iterable[Path]) -> None:
        self.roots = [Path(root).expanduser().resolve() for root in roots]
        self._books: dict[str, BookInfo] = {}
        self._lock = threading.RLock()
        self.refresh()

    def refresh(self) -> list[BookInfo]:
        books: dict[str, BookInfo] = {}
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.name.startswith("."):
                    continue
                if path.suffix.lower() not in BOOK_EXTENSIONS:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                absolute = path.resolve()
                book_id = _sha1_short(str(absolute))
                fingerprint = _sha1_short(f"{absolute}:{stat.st_mtime_ns}:{stat.st_size}")
                books[book_id] = BookInfo(
                    id=book_id,
                    path=absolute,
                    title=absolute.stem,
                    extension=absolute.suffix.lower().lstrip("."),
                    size=stat.st_size,
                    modified_ns=stat.st_mtime_ns,
                    fingerprint=fingerprint,
                )
        with self._lock:
            self._books = books
            return sorted(self._books.values(), key=lambda book: book.title.lower())

    def list_books(self) -> list[BookInfo]:
        with self._lock:
            return sorted(self._books.values(), key=lambda book: book.title.lower())

    def get(self, book_id: str) -> BookInfo | None:
        with self._lock:
            return self._books.get(book_id)


class SpreadRenderer:
    def __init__(
        self,
        cache_dir: Path,
        *,
        memory_limit: int = 16,
        image_quality: int = 88,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_limit = memory_limit
        self.image_quality = image_quality
        self.image_format = "webp" if features.check("webp") else "jpg"
        self.content_type = mimetypes.types_map.get(f".{self.image_format}", "image/jpeg")
        if self.image_format == "webp":
            self.content_type = "image/webp"
        self._memory: OrderedDict[str, bytes] = OrderedDict()
        self._memory_lock = threading.RLock()
        self._key_locks: dict[str, threading.Lock] = {}
        self._key_locks_lock = threading.Lock()

    def spread_url(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> str:
        page = max(0, int(left_page))
        variant = self._variant(page_mode, epub_font_size)
        return (
            f"/spread/{book.id}/{width}x{height}/{variant}/{page}.{self.image_format}"
            f"?v={book.fingerprint}"
        )

    def _cache_path(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> Path:
        return (
            self.cache_dir
            / book.id
            / book.fingerprint
            / f"{width}x{height}"
            / self._variant(page_mode, epub_font_size)
            / f"{left_page}.{self.image_format}"
        )

    def _cache_key(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> str:
        variant = self._variant(page_mode, epub_font_size)
        return f"{book.id}:{book.fingerprint}:{width}x{height}:{variant}:{left_page}:{self.image_format}"

    @staticmethod
    def _variant(page_mode: str, epub_font_size: int) -> str:
        return f"{normalize_page_mode(page_mode)}-font-{normalize_font_size(epub_font_size)}"

    def page_count(self, book: BookInfo, width: int, height: int, epub_font_size: int) -> int:
        with fitz.open(book.path) as doc:
            self._layout_document(doc, book, width, height, epub_font_size)
            return doc.page_count

    def get_spread_bytes(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> tuple[bytes, str]:
        key = self._cache_key(book, left_page, width, height, page_mode, epub_font_size)
        with self._memory_lock:
            cached = self._memory.get(key)
            if cached is not None:
                self._memory.move_to_end(key)
                return cached, self.content_type

        path = self.ensure_spread(book, left_page, width, height, page_mode, epub_font_size)
        data = path.read_bytes()

        with self._memory_lock:
            self._memory[key] = data
            self._memory.move_to_end(key)
            while len(self._memory) > self.memory_limit:
                self._memory.popitem(last=False)
        return data, self.content_type

    def ensure_spread(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> Path:
        path = self._cache_path(book, left_page, width, height, page_mode, epub_font_size)
        if path.exists():
            return path

        key = self._cache_key(book, left_page, width, height, page_mode, epub_font_size)
        with self._key_locks_lock:
            lock = self._key_locks.setdefault(key, threading.Lock())

        with lock:
            if path.exists():
                return path
            path.parent.mkdir(parents=True, exist_ok=True)
            self._render_spread(book, left_page, width, height, page_mode, epub_font_size, path)
            return path

    def _render_spread(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
        destination: Path,
    ) -> None:
        with fitz.open(book.path) as doc:
            self._layout_document(doc, book, width, height, epub_font_size)
            if doc.page_count <= 0:
                raise ValueError(f"{book.path} has no pages")

            left_index = normalize_page(left_page, doc.page_count)
            left = doc[left_index]
            left_rect = left.rect
            if normalize_page_mode(page_mode) == "single":
                scale = min(
                    width / max(1.0, left_rect.width),
                    height / max(1.0, left_rect.height),
                )
                left_image = self._render_page(left, scale)
                right_image = None
            else:
                right_index = normalize_page(left_index + 1, doc.page_count)
                right = doc[right_index]
                right_rect = right.rect
                scale = min(
                    width / max(1.0, left_rect.width + right_rect.width),
                    height / max(1.0, max(left_rect.height, right_rect.height)),
                )
                left_image = self._render_page(left, scale)
                right_image = self._render_page(right, scale)

        canvas = Image.new("RGB", (width, height), (0, 0, 0))
        total_width = left_image.width + (right_image.width if right_image else 0)
        start_x = max(0, (width - total_width) // 2)
        left_y = max(0, (height - left_image.height) // 2)
        canvas.paste(left_image, (start_x, left_y))
        if right_image:
            right_y = max(0, (height - right_image.height) // 2)
            canvas.paste(right_image, (start_x + left_image.width, right_y))

        temp = destination.with_name(f"{destination.name}.{threading.get_ident()}.tmp")
        if self.image_format == "webp":
            canvas.save(temp, format="WEBP", quality=self.image_quality, method=4)
        else:
            canvas.save(temp, format="JPEG", quality=self.image_quality, optimize=True)
        temp.replace(destination)

    @staticmethod
    def _render_page(page: fitz.Page, scale: float) -> Image.Image:
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        return image.convert("RGB")

    @staticmethod
    def _layout_document(doc: fitz.Document, book: BookInfo, width: int, height: int, epub_font_size: int) -> None:
        if book.extension in REFLOWABLE_EXTENSIONS and hasattr(doc, "layout"):
            doc.layout(width=width, height=height, fontsize=normalize_font_size(epub_font_size))


class PreloadManager:
    def __init__(self, renderer: SpreadRenderer, max_workers: int = 2) -> None:
        self.renderer = renderer
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="spread")
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def preload(
        self,
        book: BookInfo,
        left_pages: Iterable[int],
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> None:
        for left_page in left_pages:
            key = self.renderer._cache_key(book, left_page, width, height, page_mode, epub_font_size)
            with self._lock:
                if key in self._pending:
                    continue
                self._pending.add(key)
            future = self.executor.submit(
                self.renderer.ensure_spread,
                book,
                left_page,
                width,
                height,
                page_mode,
                epub_font_size,
            )
            future.add_done_callback(lambda _future, cache_key=key: self._clear(cache_key))

    def _clear(self, key: str) -> None:
        with self._lock:
            self._pending.discard(key)


class ReaderSession:
    def __init__(
        self,
        library: BookLibrary,
        renderer: SpreadRenderer,
        preload: PreloadManager,
        *,
        default_width: int = DEFAULT_VIEWPORT[0],
        default_height: int = DEFAULT_VIEWPORT[1],
    ) -> None:
        self.library = library
        self.renderer = renderer
        self.preload = preload
        self.default_width = default_width
        self.default_height = default_height
        self._lock = threading.RLock()
        self.current_book: BookInfo | None = None
        self.page_count = 0
        self.current_left_page = 0
        self.page_mode = "spread"
        self.epub_font_size = DEFAULT_EPUB_FONT_SIZE
        self.last_error: str | None = None
        self.updated_at = time.time()

    def list_books(self) -> list[dict]:
        return [book.to_dict() for book in self.library.refresh()]

    def open_book(
        self,
        book_id: str,
        *,
        start_page: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> dict:
        book = self.library.get(book_id)
        if not book:
            raise KeyError(f"Unknown book id: {book_id}")

        size = (width or self.default_width, height or self.default_height)
        page_count = self.renderer.page_count(book, size[0], size[1], self.epub_font_size)
        if page_count <= 0:
            raise ValueError(f"{book.path} has no pages")

        with self._lock:
            self.current_book = book
            self.page_count = page_count
            self.current_left_page = normalize_page(start_page, page_count)
            self.last_error = None
            self.updated_at = time.time()

        self.schedule_preload(*size)
        return self.state(*size)

    def command(
        self,
        command: str,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> dict:
        normalized = command.strip().lower()
        with self._lock:
            if not self.current_book or self.page_count <= 0:
                self.last_error = "No book is open."
                return self.state_locked(width or self.default_width, height or self.default_height)

            stride = self.page_stride_locked()
            if normalized in {"right", "next", "arrowright", "select", "space"}:
                self.current_left_page = normalize_page(self.current_left_page + stride, self.page_count)
            elif normalized in {"left", "previous", "prev", "arrowleft", "backspace"}:
                self.current_left_page = normalize_page(self.current_left_page - stride, self.page_count)
            elif normalized in {"s", "shift"}:
                self.current_left_page = normalize_page(self.current_left_page + 1, self.page_count)
            elif normalized in {"b", "beginning", "home"}:
                self.current_left_page = 0
            else:
                self.last_error = f"Unknown command: {command}"
                return self.state_locked(width or self.default_width, height or self.default_height)

            self.last_error = None
            self.updated_at = time.time()

        size = (width or self.default_width, height or self.default_height)
        self.schedule_preload(*size)
        return self.state(*size)

    def state(self, width: int | None = None, height: int | None = None) -> dict:
        with self._lock:
            return self.state_locked(width or self.default_width, height or self.default_height)

    def state_locked(self, width: int, height: int) -> dict:
        settings = self.settings_locked()
        if not self.current_book:
            return {
                "status": "idle",
                "message": "Open a book from the remote.",
                "book": None,
                "page_count": 0,
                "current_left_page": 0,
                "right_page": None,
                "spread_url": None,
                "preload_urls": [],
                "settings": settings,
                "last_error": self.last_error,
                "updated_at": self.updated_at,
            }

        preload_pages = self.preload_pages_locked()
        right_page = (
            None
            if self.page_mode == "single"
            else normalize_page(self.current_left_page + 1, self.page_count)
        )
        return {
            "status": "ready",
            "book": self.current_book.to_dict(),
            "page_count": self.page_count,
            "current_left_page": self.current_left_page,
            "right_page": right_page,
            "page_label": self.page_label_locked(),
            "spread_url": self.renderer.spread_url(
                self.current_book,
                self.current_left_page,
                width,
                height,
                self.page_mode,
                self.epub_font_size,
            ),
            "preload_urls": [
                self.renderer.spread_url(
                    self.current_book,
                    page,
                    width,
                    height,
                    self.page_mode,
                    self.epub_font_size,
                )
                for page in preload_pages
            ],
            "settings": settings,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
        }

    def page_label_locked(self) -> str:
        if self.page_count <= 0:
            return "0 / 0"
        if self.page_mode == "single":
            return f"{self.current_left_page + 1} / {self.page_count}"
        right_page = normalize_page(self.current_left_page + 1, self.page_count)
        return f"{self.current_left_page + 1}-{right_page + 1} / {self.page_count}"

    def page_stride_locked(self) -> int:
        return 1 if self.page_mode == "single" else 2

    def settings_locked(self) -> dict:
        return {
            "page_mode": self.page_mode,
            "single_page": self.page_mode == "single",
            "epub_font_size": self.epub_font_size,
            "epub_font_size_min": MIN_EPUB_FONT_SIZE,
            "epub_font_size_max": MAX_EPUB_FONT_SIZE,
        }

    def settings(self) -> dict:
        with self._lock:
            return self.settings_locked()

    def update_settings(
        self,
        changes: dict,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> dict:
        if not isinstance(changes, dict):
            changes = {}
        size = (width or self.default_width, height or self.default_height)
        with self._lock:
            if "single_page" in changes:
                self.page_mode = "single" if bool(changes["single_page"]) else "spread"
            if "page_mode" in changes:
                self.page_mode = normalize_page_mode(changes["page_mode"])
            if "epub_font_size" in changes:
                self.epub_font_size = normalize_font_size(changes["epub_font_size"])
            book = self.current_book

        if book:
            page_count = self.renderer.page_count(book, size[0], size[1], self.epub_font_size)
            with self._lock:
                self.page_count = page_count
                self.current_left_page = normalize_page(self.current_left_page, page_count)
                self.last_error = None
                self.updated_at = time.time()
        else:
            with self._lock:
                self.updated_at = time.time()

        self.schedule_preload(*size)
        return self.state(*size)

    def preload_pages_locked(self) -> list[int]:
        if self.page_count <= 0:
            return []
        pages: list[int] = []
        stride = self.page_stride_locked()
        for offset in (0, stride, -stride, stride * 2, -stride * 2):
            page = normalize_page(self.current_left_page + offset, self.page_count)
            if page not in pages:
                pages.append(page)
        return pages

    def schedule_preload(self, width: int | None = None, height: int | None = None) -> None:
        with self._lock:
            if not self.current_book or self.page_count <= 0:
                return
            book = self.current_book
            pages = self.preload_pages_locked()
            page_mode = self.page_mode
            epub_font_size = self.epub_font_size
        self.preload.preload(
            book,
            pages,
            width or self.default_width,
            height or self.default_height,
            page_mode,
            epub_font_size,
        )

    def get_spread_bytes(
        self,
        book_id: str,
        left_page: int,
        width: int,
        height: int,
        page_mode: str,
        epub_font_size: int,
    ) -> tuple[bytes, str]:
        book = self.library.get(book_id)
        if not book:
            raise KeyError(f"Unknown book id: {book_id}")
        return self.renderer.get_spread_bytes(book, left_page, width, height, page_mode, epub_font_size)


def json_dumps(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def default_library_roots() -> list[Path]:
    configured = os.environ.get("TV_READER_LIBRARY")
    if configured:
        return [Path(part) for part in configured.split(os.pathsep) if part]
    return [Path("downloads")]
