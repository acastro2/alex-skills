"""voicememo_transcript.py: read the transcript Apple Voice Memos stores in the .m4a
(`moov/trak/udta/tsrp`, JSON) and write a normal scribe transcript JSON from it."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import scribe_common  # noqa: E402
import voicememo_transcript as vt  # noqa: E402


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def tsrp_payload(words: list[tuple[str, float, float]]) -> bytes:
    runs, table = [], []
    for i, (text, start, end) in enumerate(words):
        runs += [text, i]
        table.append({"timeRange": [start, end]})
    return json.dumps({"locale": {"identifier": "en_US"},
                       "attributedString": {"runs": runs, "attributeTable": table}}).encode()


def make_m4a(path: Path, words: list[tuple[str, float, float]] | None, duration_s: float = 10.0) -> Path:
    # mvhd v0: version/flags, ctime, mtime, timescale, duration, then padding the parser ignores.
    mvhd = box(b"mvhd", struct.pack(">IIIII", 0, 0, 0, 1000, int(duration_s * 1000)) + b"\0" * 80)
    udta = box(b"udta", box(b"tsrp", tsrp_payload(words))) if words is not None else b""
    trak = box(b"trak", box(b"tkhd", b"\0" * 84) + udta)
    path.write_bytes(box(b"ftyp", b"M4A \0\0\0\0") + box(b"moov", mvhd + trak) + box(b"mdat", b"\0" * 32))
    return path


WORDS = [("Hi", 0.0, 0.3), (" team,", 0.3, 0.7), (" quick", 0.8, 1.1), (" update.", 1.1, 1.6),
         ("Next", 5.0, 5.4), (" topic.", 5.4, 6.0)]


def test_read_words_from_tsrp(tmp_path: Path) -> None:
    m4a = make_m4a(tmp_path / "a.m4a", WORDS)
    tsrp = vt.read_tsrp(m4a)
    assert tsrp["locale"]["identifier"] == "en_US"
    words = vt.words(tsrp)
    assert words[0] == {"start": 0.0, "end": 0.3, "text": "Hi"}
    assert words[1]["text"] == "team,"  # leading space stripped
    assert len(words) == 6


def test_no_tsrp_returns_none_and_cli_exits_4(tmp_path: Path, capsys) -> None:
    m4a = make_m4a(tmp_path / "b.m4a", None)
    assert vt.read_tsrp(m4a) is None
    rc = vt.main([str(m4a), "-o", str(tmp_path / "out.json"), "--voicememo-id", "X", "--start", "2026-11-12T15:42:07Z"])
    assert rc == 4
    assert not (tmp_path / "out.json").exists()
    assert "no Apple transcript" in capsys.readouterr().err


def test_cli_writes_scribe_transcript(tmp_path: Path) -> None:
    m4a = make_m4a(tmp_path / "c.m4a", WORDS, duration_s=10.0)
    out = tmp_path / "out.json"
    rc = vt.main([str(m4a), "-o", str(out), "--voicememo-id", "6C80-AB",
                  "--start", "2026-11-12T15:42:07Z", "--title", "Memo"])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["schema"] == scribe_common.SCHEMA_VERSION
    assert data["source"] == "voicememo"
    assert data["title"] == "Memo"
    assert data["start"] == "2026-11-12T15:42:07Z"
    assert data["end"] == "2026-11-12T15:42:17Z"  # start + mvhd duration
    # A 3.4 s pause (1.6 -> 5.0) splits the turns, like whisper's 2 s paragraph gap.
    assert [t["text"] for t in data["turns"]] == ["Hi team, quick update.", "Next topic."]
    assert data["turns"][1]["start"] == 5.0
    assert all(t["speaker"] is None for t in data["turns"])
    assert data["speakers"] == []
    p = data["provenance"]
    assert p["transcript_source"] == "apple"
    assert p["voicememo_id"] == "6C80-AB"
    assert p["word_count"] == 6
    assert p["duration_s"] == 10.0
    assert p["transcript_end_s"] == 6.0
    assert p["coverage"] == 0.6  # last word end / duration: flags a cut-off Apple transcript
    assert p["diarization_status"] == "skipped"
    assert p["audio_sha256"] == hashlib.sha256(m4a.read_bytes()).hexdigest()


def test_live_memo_file_is_not_modified(tmp_path: Path) -> None:
    m4a = make_m4a(tmp_path / "d.m4a", WORDS)
    before = (m4a.read_bytes(), m4a.stat().st_mtime_ns)
    vt.main([str(m4a), "-o", str(tmp_path / "o.json"), "--voicememo-id", "X", "--start", "2026-11-12T15:42:07Z"])
    assert (m4a.read_bytes(), m4a.stat().st_mtime_ns) == before


def test_empty_apple_transcript_falls_back(tmp_path: Path) -> None:
    m4a = make_m4a(tmp_path / "e.m4a", [])  # atom present, Apple has not transcribed yet
    rc = vt.main([str(m4a), "-o", str(tmp_path / "out.json"), "--voicememo-id", "X", "--start", "2026-11-12T15:42:07Z"])
    assert rc == 4
    assert not (tmp_path / "out.json").exists()
