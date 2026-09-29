import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shelf.api import make_app  # noqa: E402


def call(app, method, path, body=None, query=""):
    data = json.dumps(body).encode() if body is not None else b""
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
               "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
    captured = {}

    def start_response(status, headers):
        captured["status"] = int(status.split()[0])

    body_out = b"".join(app(environ, start_response))
    return captured["status"], json.loads(body_out) if body_out else None


def seeded_app():
    app = make_app()
    app.store.add("Dune", "Frank Herbert", 1965, ["scifi"])
    app.store.add("Emma", "Jane Austen", 1815, ["classic"])
    app.store.add("Persuasion", "Jane Austen", 1817, ["classic"])
    return app
