"""
AutoApply AI — Frontend Local Development Server
=================================================
Serves static frontend assets (HTML, CSS, JS) with proper development headers.
Default host: 127.0.0.1, Default port: 5500.
"""

import http.server
import socketserver
import sys
from pathlib import Path

PORT = 5500
DIRECTORY = Path(__file__).resolve().parent


class FrontendDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Disable caching during development so edits reflect immediately
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


def run(port=PORT, host="127.0.0.1"):
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((host, port), FrontendDevHandler) as httpd:
            print(f"AutoApply AI Frontend server running at http://{host}:{port}/", flush=True)
            print("Connecting to backend at http://127.0.0.1:8000/api", flush=True)
            print("Press Ctrl+C to stop.", flush=True)
            httpd.serve_forever()
    except OSError as e:
        # Windows WSAEADDRINUSE error is 10048
        if getattr(e, "winerror", None) == 10048 or "address already in use" in str(e).lower():
            print(f"Port {port} is in use, falling back to port {port + 1}...", flush=True)
            run(port=port + 1, host=host)
        else:
            raise


if __name__ == "__main__":
    cli_port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    cli_host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    run(port=cli_port, host=cli_host)
