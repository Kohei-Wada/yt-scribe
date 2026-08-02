"""Run every stage once, then write the feed."""

import argparse
import os
import sys
import tempfile

from .config import load
from .feed import render
from .serve import serve
from .sources import fetch_channel
from .store import Store
from .summarise import summarise
from .transcribe import transcribe


def pending(config, store):
    """Return the videos still to process and how many channels raised."""
    videos = []
    channel_failures = 0
    for channel_id in config.channels:
        try:
            for video in fetch_channel(channel_id):
                if not store.is_done(video.id):
                    videos.append(video)
        except Exception as exc:
            channel_failures += 1
            print(f"channel {channel_id} failed: {exc}", file=sys.stderr)
    videos.sort(key=lambda v: v.published, reverse=True)
    return videos[: config.limit], channel_failures


def write_feed(path, text):
    # Render first, then swap: a reader must never see a truncated or partial
    # feed, and os.replace is only atomic within one filesystem, so the
    # temporary file lives beside the target.
    directory = os.path.dirname(os.path.abspath(path))
    handle, tmp = tempfile.mkstemp(dir=directory, prefix=".feed-", suffix=".xml")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def process(video, config, store):
    with tempfile.TemporaryDirectory() as workdir:
        text = transcribe(
            video.url, config.whisper_bin, config.whisper_model,
            config.whisper_device, workdir,
        )
    if text is None:
        print(f"skipped (live) {video.id} {video.title}", file=sys.stderr)
        return False
    if not text.strip():
        # whisper-cli can exit 0 with no stdout. Recording it would mark the
        # video done forever with no content, so treat it as a failure.
        raise ValueError("empty transcript")
    summary = None
    if config.summary:
        summary = summarise(
            text, config.summary.endpoint, config.summary.model,
            config.summary.prompt, config.summary.api_key,
        )
    store.save(video, text, summary)
    print(f"done {video.id} {video.title}", file=sys.stderr)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(prog="yt-scribe")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--serve", type=int, metavar="PORT",
                        help="serve the generated feed on this port (binds "
                             "0.0.0.0, reachable from the network) and block")
    args = parser.parse_args()

    config = load(args.config)
    store = Store(config.db)

    videos, channel_failures = pending(config, store)
    print(f"{len(videos)} pending", file=sys.stderr)

    done = failed = 0
    for video in videos:
        try:
            if process(video, config, store):
                done += 1
        except Exception as exc:
            # Left unrecorded on purpose: the next run retries it.
            print(f"failed {video.id} {video.url}: {exc}", file=sys.stderr)
            failed += 1

    write_feed(config.output,
               render(store.entries(), config.feed_title, config.feed_url))
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
