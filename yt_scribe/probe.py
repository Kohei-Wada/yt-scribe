"""What yt-dlp knows about a video before anything is downloaded."""

import subprocess

SKIP_STATUSES = ("is_live", "is_upcoming")

# A stream whose start time has passed but which is not playing yet makes the
# extractor error out instead of printing a status, so the run below exits
# non-zero and parse() never sees "is_upcoming". Observed on a channel that
# scheduled a stream: the same video failed every night until it went live.
NOT_YET_LIVE = ("This live event will begin", "Premieres in")


def not_yet_live(stderr: str) -> bool:
    return any(marker in stderr for marker in NOT_YET_LIVE)


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
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        if not_yet_live(result.stderr):
            return "is_upcoming", None
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )
    return parse(result.stdout)
