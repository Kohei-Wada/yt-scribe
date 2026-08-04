"""One TOML file, validated once at startup."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SummaryConfig:
    endpoint: str
    model: str
    prompt: str
    api_key: str | None


@dataclass(frozen=True)
class Config:
    channels: tuple[str, ...]
    db: str
    output: str
    feed_title: str
    feed_url: str
    limit: int
    min_duration: int
    whisper_bin: str
    whisper_model: str
    whisper_device: str
    summary: SummaryConfig | None


def load(path) -> Config:
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)

    channels = raw.get("channels") or []
    if not channels:
        raise ValueError("config: channels must list at least one channel id")

    whisper = raw.get("whisper") or {}
    if not whisper.get("model"):
        raise ValueError("config: whisper.model is required")

    summary_raw = raw.get("summary")
    summary = None
    if summary_raw:
        for key in ("endpoint", "model", "prompt"):
            if not summary_raw.get(key):
                raise ValueError(f"config: summary.{key} is required")
        summary = SummaryConfig(
            endpoint=summary_raw["endpoint"],
            model=summary_raw["model"],
            prompt=summary_raw["prompt"],
            api_key=summary_raw.get("api_key"),
        )

    return Config(
        channels=tuple(channels),
        db=raw.get("db", "yt-scribe.db"),
        output=raw.get("output", "feed.xml"),
        feed_title=raw.get("feed_title", "yt-scribe"),
        feed_url=raw.get("feed_url", "http://localhost:8110/feed.xml"),
        limit=int(raw.get("limit", 20)),
        min_duration=int(raw.get("min_duration", 0)),
        whisper_bin=whisper.get("bin", "whisper-cli"),
        whisper_model=whisper["model"],
        whisper_device=str(whisper.get("device", "0")),
        summary=summary,
    )
