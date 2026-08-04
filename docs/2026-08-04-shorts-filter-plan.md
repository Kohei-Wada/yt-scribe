# Duration filter — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skip videos shorter than a configured number of seconds before they are transcribed.

**Architecture:** The single `yt-dlp` metadata call that `transcribe()` makes today to detect live streams moves into a new `yt_scribe/probe.py` and returns the duration alongside the live status. `__main__` owns both skip decisions, and stops after processing `limit` videos rather than slicing the backlog to `limit` up front, so a skip no longer consumes a slot.

**Tech Stack:** Python 3.11, standard library only, pytest, ruff, mypy, uv.

Spec: `docs/2026-08-04-shorts-filter-design.md`. Branch: `duration-filter`.

## Global Constraints

- Runtime dependencies stay empty. Standard library only — `pyproject.toml` says so on purpose.
- Python 3.11 floor; ruff `target-version = "py311"`, line-length 88, `E501` ignored.
- `make check` (ruff lint + ruff format --check + mypy over `yt_scribe` + pytest) must pass before every commit.
- Commit messages are conventional-commit prefixed: one of `feat fix docs style refactor perf test build ci chore revert`. A commit-msg hook rejects anything else.
- No `Co-Authored-By` trailers.
- `min_duration` is measured in seconds, defaults to `0`, and `0` means the filter is off.

---

### Task 1: Read `min_duration` from the config

**Files:**
- Modify: `yt_scribe/config.py:17-26` (the `Config` dataclass), `yt_scribe/config.py:53-65` (the `load` return)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Config.min_duration: int` — seconds; `0` disables the filter. Task 3 reads it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`. The first assertion goes inside the existing
`test_defaults_are_applied`, next to `assert config.limit == 20`:

```python
    assert config.min_duration == 0
```

And a new test at the end of the file:

```python
def test_min_duration_is_read(tmp_path):
    config = load(write(tmp_path, MINIMAL + "min_duration = 180\n"))
    assert config.min_duration == 180
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'min_duration'`

- [ ] **Step 3: Add the field**

In `yt_scribe/config.py`, add the field to `Config` directly after `limit: int`:

```python
    limit: int
    min_duration: int
```

and add the corresponding line to the `Config(...)` returned by `load`, directly
after `limit=int(raw.get("limit", 20)),`:

```python
    return Config(
        # ...
        limit=int(raw.get("limit", 20)),
        min_duration=int(raw.get("min_duration", 0)),
        # ...
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 5: Document the key in the example config**

In `config.example.toml`, directly after the `limit = 20` block, add:

```toml
# Skip videos shorter than this many seconds, before transcribing them. 180 is
# YouTube's upper bound for a short. Set to 0 to transcribe everything.
min_duration = 180
```

- [ ] **Step 6: Run the whole check and commit**

```bash
make check
git add yt_scribe/config.py tests/test_config.py config.example.toml
git commit -m "feat: read min_duration from the config"
```

---

### Task 2: Move the yt-dlp probe into its own module and have it read the duration

**Files:**
- Create: `yt_scribe/probe.py`
- Create: `tests/test_probe.py`
- Modify: `yt_scribe/transcribe.py:1-27` (drop `SKIP_STATUSES`, `live_status`, and the probe block)
- Delete: `tests/test_transcribe.py` (its three tests move into `tests/test_probe.py`; nothing else in `transcribe.py` is a pure function)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `yt_scribe.probe.SKIP_STATUSES: tuple[str, ...]` — `("is_live", "is_upcoming")`.
  - `yt_scribe.probe.parse(output: str) -> tuple[str, int | None]` — pure; `(live_status, seconds)`.
  - `yt_scribe.probe.probe(url, timeout: int = 120) -> tuple[str, int | None]` — runs yt-dlp, returns `parse` of its stdout.
  - `yt_scribe.transcribe.transcribe(url, whisper_bin, model, device, workdir) -> str` — no longer returns `None`.

  Task 3 imports `probe` and `SKIP_STATUSES` from `yt_scribe.probe`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_probe.py`:

```python
from yt_scribe.probe import parse


def test_reads_both_fields():
    assert parse("not_live\n743\n") == ("not_live", 743)


def test_warnings_come_before_the_values():
    # yt-dlp prints warnings on stdout before what --print asked for; the
    # values are the last two lines.
    assert parse("WARNING: something\nis_live\nNA\n") == ("is_live", None)


def test_unknown_duration_is_none():
    # A live or upcoming video has no duration yet, and yt-dlp prints NA.
    assert parse("is_upcoming\nNA\n") == ("is_upcoming", None)


def test_fractional_duration_is_truncated():
    assert parse("not_live\n61.5\n") == ("not_live", 61)


def test_empty_output_is_unknown():
    assert parse("   \n") == ("unknown", None)


def test_one_line_is_unknown():
    # Fewer lines than fields means the print did not happen as asked; treat it
    # the same as no output rather than reading the duration as a status.
    assert parse("not_live\n") == ("unknown", None)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_probe.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_scribe.probe'`

- [ ] **Step 3: Write the module**

Create `yt_scribe/probe.py`:

```python
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
```

Two `--print` flags rather than one template with a newline in it: yt-dlp prints
each `--print` on its own line, in the order given, and does not have to be
trusted to expand an escape.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_probe.py -q`
Expected: PASS

- [ ] **Step 5: Strip the probe out of `transcribe.py`**

In `yt_scribe/transcribe.py`, delete `SKIP_STATUSES`, the `live_status`
function, and the probe block with its `return None`, so the file starts:

```python
"""Audio to text, by shelling out to yt-dlp, ffmpeg and whisper.cpp."""

import subprocess
from pathlib import Path


def transcribe(url, whisper_bin, model, device, workdir):
    audio = Path(workdir) / "audio.opus"
    pcm = Path(workdir) / "pcm.wav"
```

Everything from `subprocess.run([ "yt-dlp", "-q", ...` onwards is unchanged.

- [ ] **Step 6: Delete the superseded test file**

```bash
git rm tests/test_transcribe.py
```

Its three cases are covered by `test_empty_output_is_unknown`,
`test_warnings_come_before_the_values`, and `test_reads_both_fields`.

- [ ] **Step 7: Verify the suite still passes**

Run: `uv run pytest -q`
Expected: PASS. `__main__.py` still imports nothing that was removed — it imports
`transcribe`, which still exists; Task 3 updates its use of the return value.

- [ ] **Step 8: Run the whole check and commit**

```bash
make check
git add yt_scribe/probe.py yt_scribe/transcribe.py tests/test_probe.py
git commit -m "refactor: move the yt-dlp probe into its own module"
```

`git rm` in Step 6 already staged the deletion — do not pass
`tests/test_transcribe.py` to `git add`, which would fail on a path that no
longer exists.

---

### Task 3: Skip short videos, and stop skips from consuming the run's budget

**Files:**
- Modify: `yt_scribe/__main__.py:10-17` (imports), `yt_scribe/__main__.py:20-34` (`pending`), `yt_scribe/__main__.py:59-86` (`process`), `yt_scribe/__main__.py:104-116` (the run loop)
- Modify: `README.md`

**Interfaces:**
- Consumes: `Config.min_duration` (Task 1); `probe`, `SKIP_STATUSES` (Task 2).
- Produces: nothing later tasks depend on — this is the last task.

- [ ] **Step 1: Update the imports**

In `yt_scribe/__main__.py`, add the probe import. The import block becomes:

```python
from .config import load
from .feed import render
from .probe import SKIP_STATUSES, probe
from .serve import serve
from .sources import fetch_channel
from .store import Store
from .summarise import summarise
from .transcribe import transcribe
from .types import Video
```

- [ ] **Step 2: Return the whole backlog from `pending`**

Replace the last two lines of `pending`:

```python
    videos.sort(key=lambda v: v.published, reverse=True)
    return videos, channel_failures
```

Update its docstring to match:

```python
    """Return every video still to process and how many channels raised."""
```

- [ ] **Step 3: Take the live check out of `process`**

`process` no longer decides anything — it transcribes, summarises and stores.
Replace the whole function with:

```python
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
```

- [ ] **Step 4: Rewrite the run loop**

In `main`, replace the loop that starts `done = failed = 0` with:

```python
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
```

Skips do not touch `done` or `failed`, so they cost a probe and nothing else.
The `{len(videos)} pending` line above now reports the whole backlog rather than
the capped slice, which is the more useful number.

- [ ] **Step 5: Verify nothing regressed**

Run: `uv run pytest -q`
Expected: PASS

Run: `uv run mypy yt_scribe`
Expected: no errors. `transcribe()` returns `str` now, and `process` no longer
compares it against `None`.

- [ ] **Step 6: Document the option**

`README.md:57` reads:

```markdown
Run it from a timer. Each run picks up new videos, transcribes at most `limit`
of them, and rewrites the feed.
```

Extend that paragraph:

```markdown
Run it from a timer. Each run picks up new videos, transcribes at most `limit`
of them, and rewrites the feed. Videos shorter than `min_duration` seconds are
skipped without being transcribed, which keeps shorts out of the feed; it is off
by default, and 180 is YouTube's upper bound for a short.
```

- [ ] **Step 7: Run the whole check and commit**

```bash
make check
git add yt_scribe/__main__.py README.md
git commit -m "feat: skip videos shorter than min_duration"
```

---

## After the plan

The deployed instance on rtx5090 reads its own `config.toml`, which will not have
`min_duration` and so keeps the filter off. Adding `min_duration = 180` there is a
separate deployment step, not part of this branch.
