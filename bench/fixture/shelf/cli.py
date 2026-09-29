import argparse

from .store import Store


def main(argv=None, store=None, out=print):
    store = store or Store()
    parser = argparse.ArgumentParser(prog="shelf")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("title")
    add.add_argument("author")
    add.add_argument("year", type=int)
    sub.add_parser("list")
    args = parser.parse_args(argv)
    if args.cmd == "add":
        book = store.add(args.title, args.author, args.year)
        out(f"added {book.id}: {book.title}")
    elif args.cmd == "list":
        for book in store.list():
            out(f"{book.id}\t{book.title}\t{book.author}\t{book.year}")
    return 0
