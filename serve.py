"""Loopback HTTP entry point for the replay and its browser UI."""
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from demo import run

ROOT = Path(__file__).resolve().parent
FIXTURE = json.loads((ROOT / "fixture.json").read_text(encoding="utf-8"))
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/ui.js": ("ui.js", "text/javascript; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json_reply(self, code, value):
        self.reply(code, "application/json; charset=utf-8", json.dumps(value).encode())

    def do_GET(self):
        target = urlsplit(self.path)
        if target.path in STATIC:
            name, mime = STATIC[target.path]
            self.reply(200, mime, (ROOT / name).read_bytes())
            return
        if target.path != "/api/replay":
            self.json_reply(404, {"error": "Unknown route"})
            return
        try:
            params = parse_qs(target.query, keep_blank_values=True, max_num_fields=12)
            if any(len(values) != 1 for values in params.values()):
                raise ValueError("Use each setting only once.")
            result = run(FIXTURE, {key: values[0] for key, values in params.items()})
        except ValueError as error:
            self.json_reply(400, {"error": str(error)})
            return
        self.json_reply(200, result)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    options = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", options.port), Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
