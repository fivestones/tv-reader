# Android TV Web Reader Implementation Plan

## Goal

Make tv-reader usable on Android TV by moving the display surface to a browser
page served from the LAN server and wrapping that page in a small Kotlin Android
TV WebView app. The planned production URL is `https://reader.example.com`.

## Architecture

- Python runs on the LAN server and owns book discovery, book state, PDF
  rendering, spread caching, and websocket state broadcasts.
- Android TV opens `https://reader.example.com/tv` in a fullscreen WebView.
- Phones open `https://reader.example.com/remote` for book selection and page controls.
- Browser clients connect to `/ws`; the server broadcasts state changes and
  accepts commands such as `right`, `left`, `shift`, `beginning`, and `open`.
- Rendered spreads are served as static image responses from `/spread/...`.

## Server Implementation

- Add a new server entrypoint rather than replacing the existing Tkinter
  `app.py` flow immediately.
- Use the standard library HTTP server plus the existing `websockets`
  dependency, keeping installation friction low.
- Discover books from `downloads/` by default, with an environment override for
  additional library roots later.
- Use PyMuPDF to render one two-page spread into a single TV-sized image.
- Cache rendered spreads on disk under `cache/spreads/{book_hash}/{size}/`.
- Keep a small in-memory LRU cache for hot spreads.
- Track a single active reading session initially. Multi-session support can be
  added later if multiple TVs need independent state.

## Preload Strategy

- The active spread is rendered synchronously when requested if needed.
- After opening a book or turning pages, background workers warm:
  - current spread
  - next spread
  - previous spread
  - one additional spread in each direction
- The `/api/state` payload includes URLs for the active spread and preload
  candidates so the TV browser can also warm its image cache.
- Render cache keys include book identity, page number, viewport size, and
  spread mode so stale images are avoided when settings change.

## TV Browser UI

- `/tv` displays the active spread fullscreen on a black background.
- It connects to `/ws`, updates when state changes, and preloads upcoming image
  URLs before swapping.
- It accepts keyboard/D-pad style events:
  - right/space/select: next spread
  - left/backspace: previous spread
  - `s`: shift page alignment
  - `b`: beginning
- It shows a calm waiting/error state when no book is open or the server is
  unreachable.

## Phone Remote UI

- `/remote` lists available books from `/api/books`.
- It can open a book, turn left/right, shift spread alignment, and go to the
  beginning.
- It displays current book title and page progress from websocket state.
- It uses large touch targets and avoids hardcoded hostnames.

## Android TV Kotlin WebView App

- Add a small Gradle/Kotlin project under `android-tv/`.
- The TV activity loads `https://reader.example.com/tv` by default.
- The URL can be overridden at build time with a Gradle property for local
  testing.
- Manifest requirements:
  - `android.permission.INTERNET`
  - `CATEGORY_LEANBACK_LAUNCHER`
  - `android.software.leanback`
  - touchscreen not required
- WebView settings:
  - JavaScript enabled
  - DOM storage enabled
  - media playback without user gesture
  - fullscreen, no overscroll chrome
- Native key handling should forward D-pad left/right/select to JavaScript so
  page turning is reliable even if WebView focus changes.
- Production uses HTTPS. Debug builds may allow HTTP LAN URLs for testing.

## Commit Steps

1. Commit this plan and agent pointer.
2. Commit Python reader core and web server endpoints.
3. Commit TV and phone remote browser UIs.
4. Commit Kotlin Android TV WebView project.
5. Commit README/setup documentation and verification fixes.

## Verification

- Run Python syntax checks for new modules.
- Start the web server locally and exercise `/api/books`, `/api/state`, and a
  spread render against a sample PDF.
- Open `/tv` and `/remote` in a browser when local browser tooling is available.
- Verify Android project structure with static inspection locally; full Gradle
  build requires Android Gradle tooling.

## Implementation Status

Implemented in commits:

- `b13ac4f` adds this plan and `AGENTS.md`.
- `3aca9d2` adds the Python web reader server core, render cache, and preload workers.
- `26e2ded` adds the `/tv` and `/remote` browser interfaces.
- `a04075b` adds the Kotlin Android TV WebView wrapper.

The final docs and verification commit updates README/setup guidance and records
the known local limitation: this workspace does not currently have Gradle or an
Android SDK available for a full Android build.
