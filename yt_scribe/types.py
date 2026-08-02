"""The one value type that crosses stage boundaries."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Video:
    id: str
    url: str
    title: str
    published: datetime
    channel: str
    thumbnail: str | None
