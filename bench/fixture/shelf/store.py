from .models import Book


class NotFound(KeyError):
    pass


class Store:
    """In-memory book store. Ids are assigned in insertion order, starting at 1."""

    def __init__(self):
        self._books = {}
        self._next_id = 1

    def add(self, title, author, year, tags=None):
        book = Book(id=self._next_id, title=title, author=author, year=year, tags=list(tags or []))
        self._books[book.id] = book
        self._next_id += 1
        return book

    def get(self, book_id):
        try:
            return self._books[book_id]
        except KeyError:
            raise NotFound(book_id) from None

    def list(self):
        return list(self._books.values())

    def delete(self, book_id):
        self.get(book_id)
        del self._books[book_id]

    def by_author(self, author):
        return [b for b in self._books.values() if b.author == author]
