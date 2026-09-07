#!/usr/bin/env python3
"""Local HTTP server for the offline site - videos play INLINE this way.

YouTube refuses /embed/ requests without a Referer, which every file:// page
is (Error 153). Served over http:// this stops being a problem: click a video
and the YouTube/Vimeo player mounts directly in the page (verified).

Usage:
    python tools/serve.py            # serve cfa_l1_offline_notes_site_2026/ on :8909
    python tools/serve.py --port 9000
"""

import argparse
import socket
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DIR = REPO / "cfa_l1_offline_notes_site_2026"

PORT = 8909


def lan_ip() -> str:
    """Best-effort LAN address for phone access (no traffic is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Serve the CFA offline notes site locally.")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR,
                    help="directory to serve (default: the multi-file site)")
    args = ap.parse_args()

    site_dir = args.dir
    if not (site_dir / "index.html").is_file():
        print(f"error: no index.html in {site_dir}", file=sys.stderr)
        return 1

    handler = lambda *a, **kw: SimpleHTTPRequestHandler(*a, directory=str(site_dir), **kw)
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"serving {site_dir}")
    print(f"  this computer : http://127.0.0.1:{args.port}/")
    print(f"  phone (same WiFi): http://{lan_ip()}:{args.port}/   <- videos play inline here")
    print("  Ctrl+C to stop")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
