# Duration filter — design

Date: 2026-08-04

## Problem

A channel's feed carries whatever the channel publishes, and for several of the
subscribed channels that includes shorts: minute-long fragments that are not
worth reading a transcript of. They are cheap to transcribe and expensive to
have: 85 yt-scribe entries sat unread in the reader, and every fragment among
them is one more line to skip past.

Filtering them out at the reader does not work. Of those 85, only 6 carry
hashtags in the title, and all 6 come from a single channel — a title rule
catches that channel and nothing else. Blocking by channel is wrong in the other
direction: the same channels publish the clips that are worth reading, so the
filter has to distinguish a fragment from a clip, and the only honest signal for
that is how long the video runs.

Neither the feed nor the store carries a duration, so nothing today can tell the
difference.

## Scope

Skip videos shorter than a configured number of seconds, before transcription.

Not in scope:

- Removing shorts already transcribed and stored. They stay, and fall out of the
  feed once 200 newer entries push them past the window.
- Recording a skip. A skipped video is re-probed on every run, which is one
  yt-dlp metadata call of about two seconds. A channel feed holds roughly its
  fifteen most recent videos, so a short stops being re-probed once the channel
  publishes past it.

## Configuration

`min_duration`, in seconds, at the top level of `config.toml` beside `limit`.
Default `0`, which disables the filter.

The default is off on purpose. The filter discards content, and a filter that
discards content should be asked for rather than inherited. `config.example.toml`
ships `min_duration = 180` with a comment, so a new install starts from a working
value while an existing one keeps its behaviour until its config says otherwise.

180 is YouTube's own upper bound for a short.

## Probing

A new module, `yt_scribe/probe.py`:

```python
def probe(url, timeout=120) -> tuple[str, int | None]
```

It returns the live status and the duration in seconds.

`transcribe()` already shells out to `yt-dlp --print %(live_status)s` before
downloading, to avoid starting a download that never ends. That call moves here
and prints both fields, so the number of yt-dlp invocations does not change.

Parsing is a pure function over the printed output, so it can be tested without a
network. The existing `live_status()` parser moves across unchanged — it exists
because yt-dlp prints warnings before the value, and the value is the last line.

A duration that is absent or not a number yields `None`, and a `None` duration is
never skipped. Failing open matters here: an unknown duration is a fact about the
probe, not about the video, and silently dropping a video because a metadata field
was missing would be indistinguishable from the video never having existed.

`transcribe()` loses its probe and its `None` return, and does one thing:
audio to text.

## The run loop

`pending()` currently returns `videos[: config.limit]`. It returns all of them
instead, and `__main__` stops once it has processed `limit` of them:

```
processed = 0
for video in videos:
    if processed >= config.limit:
        break
    live, duration = probe(video.url)
    if live in SKIP_STATUSES:                       # "skipped (live)"
        continue
    if min_duration and duration is not None and duration < min_duration:
        continue                                    # "skipped (short 47s)"
    transcribe -> summarise -> store.save
    processed += 1
```

`processed` counts failures as well as successes. If it counted only successes, a
video that fails every time would make each run walk the entire backlog behind it.

Skips are not counted, so neither a short nor a live stream consumes a slot. Under
the old slicing they did, and because a skip is not recorded, the same short would
have taken a slot on every run forever. That is what makes not recording skips
affordable.

## Failure handling

Unchanged. A probe that raises is caught by the same handler that already wraps
the per-video work: the video counts as failed, nothing is written for it, and the
next run tries again.

## Testing

`tests/test_probe.py`, in the shape of the existing `test_transcribe.py`: the
parser against a normal two-line output, a `NA` duration, output with warning
lines before the values, and empty output.

The run loop gets no test. `__main__` has none today, and adding a harness for it
is a larger change than this one.

## Documentation

README gains `min_duration` where the config is described.
