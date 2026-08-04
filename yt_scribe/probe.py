"""What yt-dlp knows about a video before anything is downloaded."""

import subprocess

SKIP_STATUSES = ("is_live", "is_upcoming")


def parse(output: str) -> tuple[str, int | None]:
    # yt-dlp prints warnings before the values, so the fields asked for are the
    # last lines rather than the first.
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return "unknown", None
    status, duration = lines[-2], lines[-1]
    try:
        seconds: int | None = int(float(duration))
    except ValueError:
        # NA, or anything else that is not a number. An unknown duration is a
        # fact about the probe, not about the video, so the caller must not
        # treat it as "too short".
        seconds = None
    return status, seconds


def probe(url: str, timeout: int = 120) -> tuple[str, int | None]:
    # A live stream never finishes downloading, so it would consume the whole
    # download timeout and starve everything behind it. Ask first; this is a
    # metadata call of about two seconds.
    result = subprocess.run(
        [
            "yt-dlp",
            "--no-warnings",
            "--print",
            "%(live_status)s",
            "--print",
            "%(duration)s",
            "--",
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return parse(result.stdout)
