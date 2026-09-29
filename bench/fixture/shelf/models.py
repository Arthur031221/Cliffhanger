from dataclasses import asdict, dataclass, field


@dataclass
class Book:
    id: int
    title: str
    author: str
    year: int
    tags: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
