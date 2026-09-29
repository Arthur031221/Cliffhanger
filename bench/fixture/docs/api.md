# shelf HTTP API

All responses are JSON.

## Endpoints

### GET /books

Returns every book as a list.

### GET /books/{id}

Returns one book, or 404 with `{"error": "not found"}`.

### POST /books

Body: `{"title": str, "author": str, "year": int, "tags": [str]}`. Returns 201 and the new book.

### DELETE /books/{id}

Deletes the book. Returns `{"deleted": id}`, or 404.
