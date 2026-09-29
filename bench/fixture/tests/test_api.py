from conftest import call, seeded_app


def test_list_books():
    status, body = call(seeded_app(), "GET", "/books")
    assert status == 200 and len(body) == 3


def test_create_book():
    status, body = call(seeded_app(), "POST", "/books", {"title": "Ubik", "author": "Philip K. Dick", "year": 1969})
    assert status == 201 and body["id"] == 4


def test_get_missing():
    status, body = call(seeded_app(), "GET", "/books/42")
    assert status == 404
