"""The only state this project owns: one SQLite file."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id         TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    title      TEXT NOT NULL,
    published  TEXT NOT NULL,
    channel    TEXT NOT NULL,
    thumbnail  TEXT,
    transcript TEXT NOT NULL,
    summary    TEXT
);
"""


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def is_done(self, video_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM videos WHERE id = ?", (video_id,)
        ).fetchone()
        return row is not None

    def save(self, video, transcript: str, summary: str | None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO videos"
            " (id, url, title, published, channel, thumbnail, transcript, summary)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                video.id,
                video.url,
                video.title,
                video.published.isoformat(),
                video.channel,
                video.thumbnail,
                transcript,
                summary,
            ),
        )
        self.conn.commit()

    def entries(self, limit: int = 200) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM videos ORDER BY published DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
