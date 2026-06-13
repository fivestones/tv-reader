from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        values[key] = value
        os.environ.setdefault(key, value)
    return values


def configured_server_url() -> str:
    return normalize_server_url(
        os.environ.get("TV_READER_SERVER_URL")
        or os.environ.get("TV_READER_URL")
        or ""
    )


def normalize_server_url(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"http://{text}"
    parsed = urlparse(text)
    path = parsed.path.rstrip("/")
    if path == "/tv":
        path = ""
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def tv_url(server_url: str) -> str:
    normalized = normalize_server_url(server_url)
    if not normalized:
        return ""
    return f"{normalized}/tv"


def public_ws_url(server_url: str) -> str:
    normalized = normalize_server_url(server_url)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/ws", "", "", ""))
