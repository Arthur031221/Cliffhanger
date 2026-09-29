import pytest

from shelf.store import NotFound, Store


def test_add_and_get():
    store = Store()
    book = store.add("Dune", "Frank Herbert", 1965)
    assert store.get(book.id).title == "Dune"


def test_delete_missing():
    with pytest.raises(NotFound):
        Store().delete(99)


def test_by_author():
    store = Store()
    store.add("Emma", "Jane Austen", 1815)
    store.add("Dune", "Frank Herbert", 1965)
    assert [b.title for b in store.by_author("Jane Austen")] == ["Emma"]
