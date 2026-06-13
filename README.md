# tv-reader

Displays PDF/MOBI books fullscreen on a TV (or any screen) as a two-page spread, like an open book. You control it from your phone via a simple web remote.

Built this to read picture books on the TV with my kids back in 2023. Spruced it up a bit with claude in Feb 2026 when I came across the old code. Intended to run on a Raspberry Pi connected to a TV. Works with PDFs, MOBIs, maybe epubs(?). 

## Android TV / web mode

The Android TV path is now browser-first:

- Run the Python web reader on a LAN server.
- Open `/tv` on the TV, or use the Android TV WebView wrapper in `android-tv/`.
- Open `/remote` on a phone to choose books and turn pages.
- The server renders two-page spreads with PyMuPDF, caches them in `cache/spreads/`, and preloads nearby spreads for fluid page turns.

Configure the public server URL in `.env` when the reader is available through
a stable hostname:

```
TV_READER_SERVER_URL=https://reader.example.com
```

Run the web reader locally:

```
python3 web_reader.py --host 0.0.0.0 --http-port 8080 --ws-port 55559
```

Useful URLs:

- TV display: `http://server-ip:8080/tv`
- Phone remote: `http://server-ip:8080/remote`
- Health check: `http://server-ip:8080/health`
- Books API: `http://server-ip:8080/api/books`

For production behind a public hostname, proxy normal HTTP traffic to port
`8080` and websocket traffic at `/ws` to port `55559`. If your public websocket
URL is unusual, pass it explicitly:

```
python3 web_reader.py --public-ws-url wss://reader.example.com/ws
```

Example nginx shape:

```nginx
server {
    server_name reader.example.com;

    location /ws {
        proxy_pass http://127.0.0.1:55559;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }
}
```

The Android TV app reads its default server from `TV_READER_SERVER_URL` in the
repo `.env` file, or you can choose a server from the app settings screen.
Build it from `android-tv/`:

```
./build-tv.sh
```

For local debug builds, override the URL with:

```
./build-tv.sh :app:installDebug -PtvReaderServerUrl=http://192.168.1.50:8080
```

Replace the IP with your LAN server. Debug builds allow cleartext HTTP for local testing; release builds are intended for HTTPS.

## How it works

Legacy desktop/Raspberry Pi mode:

- `app.py` opens a book fullscreen using Tkinter + PyMuPDF.
- It runs a websocket server (port `55559`) for page turn commands.
- It runs a web server (port `8080`) for the simple phone remote.

Android TV / browser mode:

- `web_reader.py` runs the HTTP API, websocket server, spread renderer, and preload cache.
- `/tv` displays the active spread fullscreen.
- `/remote` lets a phone choose books and send page commands.
- Settings can switch between two-page spreads and single-page view. EPUB font
  size is shared across TV and remote controls.

The older Tkinter app still lives in `app.py`. The Android TV path uses `web_reader.py` plus the web UI in `web/`.

## Setup

You need Python 3. For legacy Tkinter mode, Tkinter usually comes with Python,
but on a Raspberry Pi / Debian you might need:

```
sudo apt install python3-tk
```

Then install the Python dependencies:

```
pip install -r requirements.txt
```

If you want SMB support (pulling books from a network share), also:

```
pip install smbprotocol
```

## Running Legacy Mode

```
python app.py
```

It'll print the remote control URL (something like `http://yourcomputer.local:8080`), then ask you to pick a book. Local PDFs/MOBIs in `downloads/` are listed automatically.

## Controls

- **Right/Left arrows** (keyboard) or **Right/Left buttons** (web remote): turn pages
- **s**: shift page alignment by one (if the spread is off by a page)
- **b**: go back to the beginning
- **Back/Menu** in the Android TV app: open settings

## Notes

- Books get cached in `downloads/` after being pulled from SMB
- Old pre-rendered page images go in `pageImages/`
- Web-reader spread caches go in `cache/spreads/`
- The web remote auto-detects the host, no hardcoded IPs
- `webapp.py` was an early experiment; the implemented web reader is now `web_reader.py`
