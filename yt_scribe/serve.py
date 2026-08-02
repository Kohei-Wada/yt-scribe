"""A one-file HTTP server, for users without a web server already running."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve(path: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        # A client that connects and sends nothing must not hold the server.
        timeout = 30

        def do_GET(self):
            try:
                with Path(path).open("rb") as handle:
                    body = handle.read()
            except FileNotFoundError:
                self.send_error(404, "feed not generated yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/atom+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
