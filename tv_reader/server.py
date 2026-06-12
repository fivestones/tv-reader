from __future__ import annotations

import argparse
import asyncio
import json
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets

from .reader_core import (
    BookLibrary,
    PreloadManager,
    ReaderSession,
    SpreadRenderer,
    default_library_roots,
    json_dumps,
    parse_size,
)


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


class ReaderRuntime:
    def __init__(self, session: ReaderSession, config: dict[str, Any]) -> None:
        self.session = session
        self.config = config
        self.clients: set[Any] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def websocket_handler(self, websocket: Any) -> None:
        self.clients.add(websocket)
        try:
            await websocket.send(self.state_message())
            async for raw in websocket:
                response = self.handle_ws_message(raw)
                await self.broadcast_state(response)
        finally:
            self.clients.discard(websocket)

    def handle_ws_message(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self.session.state()

        message_type = data.get("type")
        width, height = parse_size(data.get("size"))
        if message_type == "command":
            return self.session.command(str(data.get("command", "")), width=width, height=height)
        if message_type == "open":
            return self.session.open_book(str(data.get("book_id", "")), width=width, height=height)
        if message_type == "state":
            return self.session.state(width, height)
        return self.session.state(width, height)

    def state_message(self, state: dict | None = None) -> str:
        return json.dumps({"type": "state", "state": state or self.session.state()}, ensure_ascii=False)

    async def broadcast_state(self, state: dict | None = None) -> None:
        if not self.clients:
            return
        message = self.state_message(state)
        stale = []
        for client in list(self.clients):
            try:
                await client.send(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self.clients.discard(client)

    def notify_state_changed(self, state: dict | None = None) -> None:
        if not self.loop:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast_state(state), self.loop)


class ReaderHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], runtime: ReaderRuntime) -> None:
        super().__init__(address, ReaderHTTPRequestHandler)
        self.runtime = runtime


class ReaderHTTPRequestHandler(BaseHTTPRequestHandler):
    server: ReaderHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        try:
            if parsed.path == "/health":
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/books":
                self.send_json({"books": self.server.runtime.session.list_books()})
                return
            if parsed.path == "/api/state":
                width, height = parse_size(query.get("size", [None])[0])
                self.send_json({"state": self.server.runtime.session.state(width, height)})
                return
            if parsed.path == "/api/config":
                self.send_json({"config": self.server.runtime.config})
                return
            if parsed.path.startswith("/spread/"):
                self.send_spread(parsed.path)
                return
            if parsed.path == "/":
                self.send_redirect("/tv")
                return
            if parsed.path == "/tv":
                self.send_static_file(STATIC_DIR / "tv.html")
                return
            if parsed.path == "/remote":
                self.send_static_file(STATIC_DIR / "remote.html")
                return
            if parsed.path.startswith("/assets/"):
                self.send_static_file(STATIC_DIR / parsed.path.removeprefix("/assets/"))
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            width, height = parse_size(payload.get("size"))
            if parsed.path == "/api/open":
                state = self.server.runtime.session.open_book(
                    str(payload.get("book_id", "")),
                    start_page=int(payload.get("start_page", 0)),
                    width=width,
                    height=height,
                )
                self.server.runtime.notify_state_changed(state)
                self.send_json({"state": state})
                return
            if parsed.path == "/api/command":
                state = self.server.runtime.session.command(
                    str(payload.get("command", "")),
                    width=width,
                    height=height,
                )
                self.server.runtime.notify_state_changed(state)
                self.send_json({"state": state})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def send_spread(self, path: str) -> None:
        parts = path.strip("/").split("/")
        if len(parts) != 4:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        _, book_id, size, filename = parts
        width, height = parse_size(size)
        left_text = filename.split(".", 1)[0]
        data, content_type = self.server.runtime.session.get_spread_bytes(
            book_id,
            int(left_text),
            width,
            height,
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_static_file(self, path: Path) -> None:
        resolved = path.resolve()
        static_root = STATIC_DIR.resolve()
        if not resolved.is_file() or static_root not in resolved.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(resolved.suffix.lower(), "application/octet-stream")
        body = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def send_json(self, data: object, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json_dumps(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_session(args: argparse.Namespace) -> ReaderSession:
    roots = [Path(root) for root in args.library] if args.library else default_library_roots()
    library = BookLibrary(roots)
    renderer = SpreadRenderer(Path(args.cache_dir))
    preload = PreloadManager(renderer)
    return ReaderSession(
        library,
        renderer,
        preload,
        default_width=args.width,
        default_height=args.height,
    )


def start_http_server(runtime: ReaderRuntime, host: str, port: int) -> ReaderHTTPServer:
    server = ReaderHTTPServer((host, port), runtime)
    thread = threading.Thread(target=server.serve_forever, name="reader-http", daemon=True)
    thread.start()
    return server


async def start_websocket_server(runtime: ReaderRuntime, host: str, port: int) -> None:
    runtime.loop = asyncio.get_running_loop()
    async with websockets.serve(runtime.websocket_handler, host, port):
        await asyncio.Future()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tv-reader web server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP and websocket servers.")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP server port.")
    parser.add_argument("--ws-port", type=int, default=55559, help="Websocket server port.")
    parser.add_argument(
        "--library",
        action="append",
        help="Book library root. Defaults to downloads/ or TV_READER_LIBRARY.",
    )
    parser.add_argument("--cache-dir", default="cache/spreads", help="Rendered spread cache directory.")
    parser.add_argument("--width", type=int, default=1920, help="Default rendered spread width.")
    parser.add_argument("--height", type=int, default=1080, help="Default rendered spread height.")
    parser.add_argument(
        "--public-ws-url",
        help="Public websocket URL. Defaults to wss://host/ws on HTTPS or ws://host:ws-port locally.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = build_session(args)
    runtime = ReaderRuntime(
        session,
        {
            "render_size": f"{args.width}x{args.height}",
            "ws_port": args.ws_port,
            "public_ws_url": args.public_ws_url,
        },
    )
    start_http_server(runtime, args.host, args.http_port)

    ip = get_local_ip()
    print("TV reader server is running.")
    print(f"  HTTP:      http://{ip}:{args.http_port}")
    print(f"  WebSocket: ws://{ip}:{args.ws_port}")
    print("  Production reverse proxy target:")
    print(f"    https://reader.example.com -> http://127.0.0.1:{args.http_port}")
    print(f"    wss://reader.example.com/ws -> ws://127.0.0.1:{args.ws_port}")

    asyncio.run(start_websocket_server(runtime, args.host, args.ws_port))


if __name__ == "__main__":
    main()
