# tv-reader

Displays PDF/MOBI books fullscreen on a TV (or any screen) as a two-page spread, like an open book. You control it from your phone via a simple web remote.

Built this to read picture books on the TV with my kids back in 2023. Spruced it up a bit with claude in Feb 2026 when I came across the old code. Intended to run on a Raspberry Pi connected to a TV. Works with PDFs, MOBIs, maybe epubs(?). 

## How it works

- Python app opens a book fullscreen using Tkinter + PyMuPDF
- Runs a websocket server (port 55559) that listens for page turn commands
- Runs a web server (port 8080) that serves a simple remote control page with Right/Left/Shift buttons
- Open the remote on your phone and tap to turn pages

## Setup

You need Python 3 and Tkinter. Tkinter usually comes with Python, but on a Raspberry Pi / Debian you might need:

```
sudo apt install python3-tk
```

Then install the Python dependencies:

```
pip install PyMuPDF Pillow pynput websockets
```

If you want SMB support (pulling books from a network share), also:

```
pip install smbprotocol
```

## Running it

```
python app.py
```

It'll print the remote control URL (something like `http://yourcomputer.local:8080`), then ask you to pick a book. Local PDFs/MOBIs in `downloads/` are listed automatically.

## Controls

- **Right/Left arrows** (keyboard) or **Right/Left buttons** (web remote): turn pages
- **s**: shift page alignment by one (if the spread is off by a page)
- **b**: go back to the beginning

## Notes

- Books get cached in `downloads/` after being pulled from SMB
- Pre-rendered page images go in `pageImages/`
- The web remote auto-detects the host, no hardcoded IPs
- `webapp.py` was an experiment to serve everything via web instead of Tkinter, never finished
