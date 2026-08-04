"""Run every stage once, then write the feed."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from .config import load
from .feed import render
from .probe import SKIP_STATUSES, probe
from .serve import serve
from .sources import fetch_channel
from .store import Store
from .summarise import summarise
from .transcribe import transcribe
from .types import Video


def pending(config, store):
    """Return every video still to process and how many channels raised."""
    videos: list[Video] = []
    channel_failures = 0
    for channel_id in config.channels:
        try:
            videos.extend(
                video
                for video in fetch_channel(channel_id)
                if not store.is_done(video.id)
            )
        except Exception as exc:
            channel_failures += 1
            print(f"channel {channel_id} failed: {exc}", file=sys.stderr)
    videos.sort(key=lambda v: v.published, reverse=True)
    return videos, channel_failures


def write_feed(path, text):
    # Render first, then swap: a reader must never see a truncated or partial
    # feed, and os.replace is only atomic within one filesystem, so the
    # temporary file lives beside the target.
    directory = Path(path).resolve().parent
    handle, tmp_name = tempfile.mkstemp(dir=directory, prefix=".feed-", suffix=".xml")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        # mkstemp makes the file 0600 and Path.replace carries that onto the
        # target, which would break serving the feed with nginx running as
        # another user. Restore what a plain open(..., "w") would have made.
        umask = os.umask(0)
        os.umask(umask)
        tmp.chmod(0o666 & ~umask)
        tmp.replace(path)
    except BaseException:
        tmp.unlink()
        raise


def process(video, config, store):
    with tempfile.TemporaryDirectory() as workdir:
        text = transcribe(
            video.url,
            config.whisper_bin,
            config.whisper_model,
            config.whisper_device,
            workdir,
        )
    if not text.strip():
        # whisper-cli can exit 0 with no stdout. Recording it would mark the
        # video done forever with no content, so treat it as a failure.
        raise ValueError("empty transcript")
    summary = None
    if config.summary:
        summary = summarise(
            text,
            config.summary.endpoint,
            config.summary.model,
            config.summary.prompt,
            config.summary.api_key,
        )
    store.save(video, text, summary)
    print(f"done {video.id} {video.title}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="yt-scribe")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument(
        "--serve",
        type=int,
        metavar="PORT",
        help="serve the generated feed on this port (binds "
        "0.0.0.0, reachable from the network) and block",
    )
    args = parser.parse_args()

    config = load(args.config)
    store = Store(config.db)

    videos, channel_failures = pending(config, store)
    print(f"{len(videos)} pending", file=sys.stderr)

    done = failed = 0
    for video in videos:
        # Counting failures too: a video that fails every time would otherwise
        # make every run walk the entire backlog queued behind it.
        if done + failed >= config.limit:
            break
        try:
            status, duration = probe(video.url)
            if status in SKIP_STATUSES:
                # A stream becomes an ordinary recording once it ends, so it is
                # left unrecorded to be picked up later rather than written off.
                print(f"skipped (live) {video.id} {video.title}", file=sys.stderr)
                continue
            if (
                config.min_duration
                and duration is not None
                and duration < config.min_duration
            ):
                print(
                    f"skipped (short {duration}s) {video.id} {video.title}",
                    file=sys.stderr,
                )
                continue
            process(video, config, store)
            done += 1
        except Exception as exc:
            # Left unrecorded on purpose: the next run retries it.
            print(f"failed {video.id} {video.url}: {exc}", file=sys.stderr)
            failed += 1

    write_feed(
        config.output, render(store.entries(), config.feed_title, config.feed_url)
    )
    print(f"{done} ok, {failed} failed", file=sys.stderr)

    if args.serve:
        print(f"serving {config.output} on :{args.serve}", file=sys.stderr)
        serve(config.output, args.serve)

    # Every channel unreachable is "no network": no work is ever found, so the
    # loop above cannot report it. The timer must see it.
    if channel_failures == len(config.channels):
        print("every channel failed", file=sys.stderr)
        return 1

    # One video failing is ordinary operation. A run that achieved nothing
    # despite having work means something systemic — a missing binary, a dead
    # endpoint, no network — and should be visible to the timer.
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())
