"""Behavioral tests for the hidock_batch.sh transcription pool.

The real script is copied into a temp dir next to stub hidock_pull.py and
transcribe.py, and a stub `uv` sits first on PATH, with HOME pointed at the
temp dir: nothing here touches the real ~/.scribe or a real device.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
BATCH_SCRIPT = SCRIPTS_DIR / "hidock_batch.sh"

STUB_UV = """#!/bin/bash
# uv stub: drop 'run' and its --with flags and the interpreter word, then run the rest.
while [ $# -gt 0 ] && [ "$1" != "run" ]; do shift; done
[ $# -gt 0 ] && shift
while [ $# -gt 0 ] && [ "$1" = "--with" ]; do shift 2; done
[ $# -gt 0 ] && shift
exec python3 "$@"
"""

STUB_PULL = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"

STUB_TRANSCRIBE = '''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
audio = args[0]
out = args[args.index("-o") + 1]
stem = os.path.splitext(os.path.basename(audio))[0]
def log(event):
    with open(os.environ["STUB_TIMELOG"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stem": stem, "event": event, "t": time.time()}) + "\\n")
log("start")
time.sleep(float(os.environ.get("STUB_SLEEP", "0.4")))
if stem == os.environ.get("STUB_FAIL_STEM", ""):
    sys.exit(3)
with open(out, "w", encoding="utf-8") as fh:
    json.dump({"schema": "scribe.transcript/1", "source": "hidock", "turns": []}, fh)
log("end")
'''


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "hidock_batch.sh").write_text(BATCH_SCRIPT.read_text(encoding="utf-8"))
    for name, text in (
        ("hidock_pull.py", STUB_PULL),
        ("transcribe.py", STUB_TRANSCRIBE),
        ("uv", STUB_UV),
    ):
        path = scripts / name
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)
    audio = tmp_path / ".scribe" / "audio"
    audio.mkdir(parents=True)
    (tmp_path / ".scribe" / "transcripts").mkdir()
    return scripts, audio


def _run(scripts: Path, tmp_path: Path, jobs: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": f"{scripts}:{os.environ['PATH']}",
        "STUB_TIMELOG": str(tmp_path / "timelog.jsonl"),
        "STUB_SLEEP": "0.6",
        "STUB_FAIL_STEM": "C",
    }
    return subprocess.run(
        ["bash", str(scripts / "hidock_batch.sh"), "2026-10-01", "0", jobs],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _max_concurrency(timelog: Path) -> int:
    events = [json.loads(line) for line in timelog.read_text().splitlines() if line]
    intervals: dict[str, dict[str, float]] = {}
    for event in events:
        intervals.setdefault(event["stem"], {})[event["event"]] = event["t"]
    spans = [(v["start"], v["end"]) for v in intervals.values() if "end" in v]
    return max((sum(1 for start, end in spans if start <= s < end) for s, _ in spans), default=0)


def test_pool_transcribes_concurrently_and_keeps_failed_mp3(tmp_path: Path) -> None:
    scripts, audio = _setup(tmp_path)
    done = tmp_path / ".scribe" / "transcripts"
    for stem in ("A", "B", "C", "D"):
        (audio / f"{stem}.mp3").write_bytes(b"fake")
    (audio / "skipme.mp3").write_bytes(b"fake")
    (done / "skipme.json").write_text("{}")

    result = _run(scripts, tmp_path, "3")

    assert result.returncode == 1
    for stem in ("A", "B", "D"):
        assert (done / f"{stem}.json").exists()
        assert not (audio / f"{stem}.mp3").exists()
    # The failed file keeps its MP3 for the next run; the others do not block it.
    assert not (done / "C.json").exists()
    assert (audio / "C.mp3").exists()
    # Already-transcribed audio is dropped without a transcribe run.
    assert not (audio / "skipme.mp3").exists()
    assert "=== transcribing skipme ===" not in result.stderr
    assert "=== transcribing A ===" in result.stderr
    assert "=== failed C" in result.stderr
    assert "FAILED" in result.stderr
    assert _max_concurrency(tmp_path / "timelog.jsonl") >= 2


def test_jobs_must_be_a_positive_integer(tmp_path: Path) -> None:
    scripts, audio = _setup(tmp_path)
    (audio / "A.mp3").write_bytes(b"fake")

    result = _run(scripts, tmp_path, "abc")

    assert result.returncode == 2
    assert "jobs" in result.stderr
    assert "=== transcribing" not in result.stderr
    assert (audio / "A.mp3").exists()


def test_jobs_over_the_cap_is_clamped(tmp_path: Path) -> None:
    scripts, audio = _setup(tmp_path)
    (audio / "A.mp3").write_bytes(b"fake")

    result = _run(scripts, tmp_path, "9")

    assert result.returncode == 0
    assert "capping jobs at 4" in result.stderr
    assert (tmp_path / ".scribe" / "transcripts" / "A.json").exists()
