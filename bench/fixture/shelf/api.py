"""WSGI app. Routes:

GET    /books          list books
GET    /books/<id>     one book
POST   /books          create a book from a JSON body
DELETE /books/<id>     delete a book
"""
import json
import re

from .store import NotFound, Store


def _json(start_response, status, body):
    data = json.dumps(body).encode()
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(data)))])
    return [data]


def make_app(store=None):
    store = store or Store()

    def app(environ, start_response):
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")
        if path == "/books" and method == "GET":
            return _json(start_response, "200 OK", [b.to_dict() for b in store.list()])
        if path == "/books" and method == "POST":
            length = int(environ.get("CONTENT_LENGTH") or 0)
            payload = json.loads(environ["wsgi.input"].read(length) or b"{}")
            book = store.add(payload["title"], payload["author"], payload["year"], payload.get("tags"))
            return _json(start_response, "201 Created", book.to_dict())
        match = re.fullmatch(r"/books/(\d+)", path)
        if match:
            book_id = int(match.group(1))
            try:
                if method == "GET":
                    return _json(start_response, "200 OK", store.get(book_id).to_dict())
                if method == "DELETE":
                    store.delete(book_id)
                    return _json(start_response, "200 OK", {"deleted": book_id})
            except NotFound:
                return _json(start_response, "404 Not Found", {"error": "not found"})
        return _json(start_response, "404 Not Found", {"error": "no route"})

    app.store = store
    return app
