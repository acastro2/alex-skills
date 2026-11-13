"""transcribe.hex_asr: scribe's ASR through the running Hex app (Parakeet v3), replacing
mlx-whisper (Alex, 2026-11-13). Hex's CLI returns text only, so the audio is cut into fixed
chunks and each chunk's text gets the chunk's start time. Both seams are faked here: no
ffmpeg, no Hex."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import transcribe  # noqa: E402


class FakeHex:
    """Records every hex command; answers like Hex 3.4.0 does."""

    def __init__(self, texts: dict[str, str], labs_on: bool = False, fail_on: str | None = None,
                 not_running: bool = False):
        self.texts, self.labs_on, self.fail_on, self.not_running = texts, labs_on, fail_on, not_running
        self.calls: list[list[str]] = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        args = cmd[1:]
        if self.not_running:
            return subprocess.CompletedProcess(cmd, 3, "", "hex: Hex isn't running")
        if args[:2] == ["labs", "list"]:
            state = "on" if self.labs_on else "off"
            out = f"transcribe-files               {state}      everyone  Turn a WAV recording into text\n"
            return subprocess.CompletedProcess(cmd, 0, out, "")
        if args[:2] == ["labs", "on"]:
            self.labs_on = True
            return subprocess.CompletedProcess(cmd, 0, "Turned transcribe-files on.\n", "")
        if args[:2] == ["labs", "off"]:
            self.labs_on = False
            return subprocess.CompletedProcess(cmd, 0, "Turned transcribe-files off.\n", "")
        if args[0] == "transcribe":
            name = Path(args[-1]).name
            if name == self.fail_on:
                return subprocess.CompletedProcess(cmd, 1, "", "hex: model failed")
            body = {"version": 1, "status": "ok", "text": self.texts[name]}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(body), "")
        raise AssertionError(f"unexpected hex command {cmd}")


def fake_split(chunks: list[str]):
    def split(audio_path: str, out_dir: str, chunk_seconds: float) -> list[str]:
        assert chunk_seconds == 30
        return [str(Path(out_dir) / c) for c in chunks]
    return split


def test_chunks_become_timed_segments_and_empty_chunks_drop(tmp_path: Path) -> None:
    hexer = FakeHex({"c0000.wav": " Hello team. ", "c0001.wav": "", "c0002.wav": "Next topic."})
    result = transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en",
                                run=hexer, split=fake_split(["c0000.wav", "c0001.wav", "c0002.wav"]))
    assert result["language"] == "en"
    assert result["segments"] == [
        {"id": 0, "start": 0.0, "end": 30.0, "text": "Hello team."},
        {"id": 2, "start": 60.0, "end": 90.0, "text": "Next topic."},
    ]
    transcribe_calls = [c for c in hexer.calls if c[1] == "transcribe"]
    assert transcribe_calls[0][1:5] == ["transcribe", "--json", "--model", "parakeet_v3"]


def test_labs_switch_is_turned_on_then_restored(tmp_path: Path) -> None:
    hexer = FakeHex({"c0000.wav": "Hi."}, labs_on=False)
    transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=hexer, split=fake_split(["c0000.wav"]))
    verbs = [" ".join(c[1:3]) for c in hexer.calls if c[1] == "labs"]
    assert verbs == ["labs list", "labs on", "labs off"]
    assert hexer.labs_on is False


def test_labs_left_on_when_alex_had_it_on(tmp_path: Path) -> None:
    hexer = FakeHex({"c0000.wav": "Hi."}, labs_on=True)
    transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=hexer, split=fake_split(["c0000.wav"]))
    assert [c[2] for c in hexer.calls if c[1] == "labs"] == ["list"]
    assert hexer.labs_on is True


def test_failed_chunk_raises_and_still_restores_labs(tmp_path: Path) -> None:
    hexer = FakeHex({"c0000.wav": "Hi.", "c0001.wav": "x"}, fail_on="c0001.wav")
    with pytest.raises(RuntimeError, match="Hex"):
        transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=hexer,
                           split=fake_split(["c0000.wav", "c0001.wav"]))
    assert hexer.labs_on is False


def test_hex_not_running_says_how_to_fix(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="hex start"):
        transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=FakeHex({}, not_running=True),
                           split=fake_split(["c0000.wav"]))


def test_default_model_is_parakeet_v3() -> None:
    assert transcribe.DEFAULT_MODEL == "parakeet_v3"


def test_no_speech_chunk_is_skipped_not_an_error(tmp_path: Path) -> None:
    """Hex 3.4 exits 4 with {"code": "no-speech"} on a silent or very short chunk (seen on a
    0.3 s tail, 2026-11-13). That is an empty chunk, not a failure."""
    hexer = FakeHex({"c0000.wav": "Hi."})
    real = hexer.__call__

    def run(cmd, **kw):
        if cmd[1] == "transcribe" and Path(cmd[-1]).name == "c0001.wav":
            hexer.calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 4, '{"status":"error","code":"no-speech"}', "")
        return real(cmd, **kw)

    result = transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=run,
                                split=fake_split(["c0000.wav", "c0001.wav"]))
    assert [s["text"] for s in result["segments"]] == ["Hi."]


def test_other_exit_4_still_fails(tmp_path: Path) -> None:
    hexer = FakeHex({})

    def run(cmd, **kw):
        if cmd[1] == "transcribe":
            return subprocess.CompletedProcess(cmd, 4, '{"status":"error","code":"model-missing"}', "")
        return hexer(cmd, **kw)

    with pytest.raises(RuntimeError, match="Hex"):
        transcribe.hex_asr(str(tmp_path / "a.m4a"), "parakeet_v3", "en", run=run, split=fake_split(["c0000.wav"]))
