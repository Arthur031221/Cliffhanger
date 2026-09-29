from shelf.cli import main
from shelf.store import Store


def test_add_then_list():
    store, lines = Store(), []
    main(["add", "Dune", "Frank Herbert", "1965"], store=store, out=lines.append)
    main(["list"], store=store, out=lines.append)
    assert lines == ["added 1: Dune", "1\tDune\tFrank Herbert\t1965"]
