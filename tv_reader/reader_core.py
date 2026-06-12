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

    def spread_url(self, book: BookInfo, left_page: int, width: int, height: int) -> str:
        page = max(0, int(left_page))
        return (
            f"/spread/{book.id}/{width}x{height}/{page}.{self.image_format}"
            f"?v={book.fingerprint}"
        )

    def _cache_path(self, book: BookInfo, left_page: int, width: int, height: int) -> Path:
        return (
            self.cache_dir
            / book.id
            / book.fingerprint
            / f"{width}x{height}"
            / f"{left_page}.{self.image_format}"
        )

    def _cache_key(self, book: BookInfo, left_page: int, width: int, height: int) -> str:
        return f"{book.id}:{book.fingerprint}:{width}x{height}:{left_page}:{self.image_format}"

    def get_spread_bytes(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
    ) -> tuple[bytes, str]:
        key = self._cache_key(book, left_page, width, height)
        with self._memory_lock:
            cached = self._memory.get(key)
            if cached is not None:
                self._memory.move_to_end(key)
                return cached, self.content_type

        path = self.ensure_spread(book, left_page, width, height)
        data = path.read_bytes()

        with self._memory_lock:
            self._memory[key] = data
            self._memory.move_to_end(key)
            while len(self._memory) > self.memory_limit:
                self._memory.popitem(last=False)
        return data, self.content_type

    def ensure_spread(self, book: BookInfo, left_page: int, width: int, height: int) -> Path:
        path = self._cache_path(book, left_page, width, height)
        if path.exists():
            return path

        key = self._cache_key(book, left_page, width, height)
        with self._key_locks_lock:
            lock = self._key_locks.setdefault(key, threading.Lock())

        with lock:
            if path.exists():
                return path
            path.parent.mkdir(parents=True, exist_ok=True)
            self._render_spread(book, left_page, width, height, path)
            return path

    def _render_spread(
        self,
        book: BookInfo,
        left_page: int,
        width: int,
        height: int,
        destination: Path,
    ) -> None:
        with fitz.open(book.path) as doc:
            if doc.page_count <= 0:
                raise ValueError(f"{book.path} has no pages")

            left_index = normalize_page(left_page, doc.page_count)
            right_index = normalize_page(left_index + 1, doc.page_count)
            left = doc[left_index]
            right = doc[right_index]
            left_rect = left.rect
            right_rect = right.rect
            scale = min(
                width / max(1.0, left_rect.width + right_rect.width),
                height / max(1.0, max(left_rect.height, right_rect.height)),
            )

            left_image = self._render_page(left, scale)
            right_image = self._render_page(right, scale)

        canvas = Image.new("RGB", (width, height), (0, 0, 0))
        total_width = left_image.width + right_image.width
        start_x = max(0, (width - total_width) // 2)
        left_y = max(0, (height - left_image.height) // 2)
        right_y = max(0, (height - right_image.height) // 2)
        canvas.paste(left_image, (start_x, left_y))
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
    ) -> None:
        for left_page in left_pages:
            key = self.renderer._cache_key(book, left_page, width, height)
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

        with fitz.open(book.path) as doc:
            page_count = doc.page_count
        if page_count <= 0:
            raise ValueError(f"{book.path} has no pages")

        with self._lock:
            self.current_book = book
            self.page_count = page_count
            self.current_left_page = normalize_page(start_page, page_count)
            self.last_error = None
            self.updated_at = time.time()

        size = (width or self.default_width, height or self.default_height)
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

            if normalized in {"right", "next", "arrowright", "select", "space"}:
                self.current_left_page = normalize_page(self.current_left_page + 2, self.page_count)
            elif normalized in {"left", "previous", "prev", "arrowleft", "backspace"}:
                self.current_left_page = normalize_page(self.current_left_page - 2, self.page_count)
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
        if not self.current_book:
            return {
                "status": "idle",
                "message": "Open a book from the remote.",
                "book": None,
                "page_count": 0,
                "current_left_page": 0,
                "right_page": 0,
                "spread_url": None,
                "preload_urls": [],
                "last_error": self.last_error,
                "updated_at": self.updated_at,
            }

        preload_pages = self.preload_pages_locked()
        right_page = normalize_page(self.current_left_page + 1, self.page_count)
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
            ),
            "preload_urls": [
                self.renderer.spread_url(self.current_book, page, width, height)
                for page in preload_pages
            ],
            "last_error": self.last_error,
            "updated_at": self.updated_at,
        }

    def page_label_locked(self) -> str:
        if self.page_count <= 0:
            return "0 / 0"
        right_page = normalize_page(self.current_left_page + 1, self.page_count)
        return f"{self.current_left_page + 1}-{right_page + 1} / {self.page_count}"

    def preload_pages_locked(self) -> list[int]:
        if self.page_count <= 0:
            return []
        pages: list[int] = []
        for offset in (0, 2, -2, 4, -4):
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
        self.preload.preload(book, pages, width or self.default_width, height or self.default_height)

    def get_spread_bytes(
        self,
        book_id: str,
        left_page: int,
        width: int,
        height: int,
    ) -> tuple[bytes, str]:
        book = self.library.get(book_id)
        if not book:
            raise KeyError(f"Unknown book id: {book_id}")
        return self.renderer.get_spread_bytes(book, left_page, width, height)


def json_dumps(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def default_library_roots() -> list[Path]:
    configured = os.environ.get("TV_READER_LIBRARY")
    if configured:
        return [Path(part) for part in configured.split(os.pathsep) if part]
    return [Path("downloads")]
