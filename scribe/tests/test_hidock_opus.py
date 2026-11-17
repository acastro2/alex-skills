"""HiDock firmware now records Ogg Opus (16 kb/s), not MP3 (96 kb/s).

Seen 2026-11-16: Rec34 and Rec35 start with b"OggS"; ffprobe reads Rec35 as
2006.58 s while the 96 kb/s size estimate says 347 s. Sync must accept Ogg,
write it as .ogg, and apply --min-seconds to the real duration, not the MP3
size estimate.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import hidock_pull as hp  # noqa: E402
from test_hidock_pull import FakeTransport, _factory, file_list_bytes  # noqa: E402,F401

PRE_SKIP = 312


def _ogg_page(granule: int, payload: bytes, seq: int, header_type: int = 0) -> bytes:
    segs = []
    remaining = len(payload)
    while remaining >= 255:
        segs.append(255)
        remaining -= 255
    segs.append(remaining)
    header = b"OggS" + bytes([0, header_type]) + struct.pack("<qIII", granule, 1, seq, 0)
    return header + bytes([len(segs)]) + bytes(segs) + payload


def _opus_bytes(duration_s: float, size: int) -> bytes:
    head = b"OpusHead" + bytes([1, 1]) + struct.pack("<HIhB", PRE_SKIP, 16000, 0, 0)
    first = _ogg_page(0, head, 0, header_type=2)
    granule = int(duration_s * 48000) + PRE_SKIP
    middle = _ogg_page(48000, b"\x00" * 10, 1)
    final = _ogg_page(granule, b"", 2)
    filler = b"\x00" * (size - len(first) - len(middle) - len(final))
    assert filler, "size too small for the synthetic pages"
    # The filler sits between pages, so the real granule must come from the
    # LAST OggS page, found by scanning backwards.
    return first + middle + filler + final


def test_opus_bytes_helper_produces_exact_size():
    data = _opus_bytes(1000.0, 2276652)
    assert len(data) == 2276652
    assert data[:4] == b"OggS"


def test_audio_format_recognizes_mp3_ogg_and_rejects_other_bytes():
    assert hp.audio_format(b"\xff\xfb\x90\x00rest") == "mp3"
    assert hp.audio_format(b"ID3\x03\x00\x00\x00") == "mp3"
    assert hp.audio_format(b"OggS\x00\x02") == "ogg"
    assert hp.audio_format(b"RIFF....WAVEfmt ") is None
    assert hp.audio_format(b"") is None


def test_audio_duration_seconds_reads_opus_granule_minus_pre_skip():
    data = _opus_bytes(1000.0, 2276652)
    assert hp.audio_duration_seconds(data) == pytest.approx(1000.0, abs=0.01)


def test_audio_duration_seconds_keeps_96kbps_estimate_for_mp3():
    data = b"\xff\xfb" + b"\x00" * (29988012 - 2)
    assert hp.audio_duration_seconds(data) == pytest.approx(2499.001, rel=1e-6)


def _mark_all_done_except(file_list_bytes: bytes, done: Path, keep: str) -> None:
    frames, _ = hp.parse_frames(file_list_bytes)
    for entry in hp.parse_file_list_entries(frames[0][2]):
        if entry.filename != keep:
            (done / f"{Path(entry.filename).stem}.json").write_text("{}")


def _run_sync_on_rec01(file_list_bytes, tmp_path, payload: bytes, min_seconds: str):
    done = tmp_path / "transcripts"
    done.mkdir()
    audio = tmp_path / "audio"
    _mark_all_done_except(file_list_bytes, done, "2026Sep01-090855-Rec01.hda")
    frame = hp.build_frame(hp.CMD_TRANSFER_FILE, seq=2, body=payload)
    transport = FakeTransport([[file_list_bytes], [frame]])
    code = hp.main(
        ["sync", "-o", str(audio), "--done-dir", str(done), "--min-seconds", min_seconds],
        transport_factory=_factory(transport),
    )
    return code, audio


def test_sync_writes_opus_as_ogg_and_judges_min_seconds_by_real_duration(file_list_bytes, tmp_path, capsys):
    # Rec01's listed size is 189.7 s as MP3; as Opus it is 1000 s, so it must
    # pass --min-seconds 200 and land as .ogg.
    payload = _opus_bytes(1000.0, 2276652)
    code, audio = _run_sync_on_rec01(file_list_bytes, tmp_path, payload, "200")
    out = capsys.readouterr()
    assert code == 0, out.err
    assert (audio / "2026Sep01-090855-Rec01.ogg").read_bytes() == payload
    assert not (audio / "2026Sep01-090855-Rec01.mp3").exists()
    events = {e["file"]: e for e in (json.loads(l) for l in out.out.splitlines())}
    assert events["2026Sep01-090855-Rec01.hda"]["status"] == "downloaded"


def test_sync_skips_short_opus_after_download_and_writes_nothing(file_list_bytes, tmp_path, capsys):
    payload = _opus_bytes(50.0, 2276652)
    code, audio = _run_sync_on_rec01(file_list_bytes, tmp_path, payload, "120")
    out = capsys.readouterr()
    assert code == 0, out.err
    assert list(audio.glob("*")) == []
    events = {e["file"]: e for e in (json.loads(l) for l in out.out.splitlines())}
    assert events["2026Sep01-090855-Rec01.hda"]["status"] == "skipped"
    assert "min-seconds" in events["2026Sep01-090855-Rec01.hda"]["reason"]


def test_sync_treats_existing_ogg_of_same_size_as_already_present(file_list_bytes, tmp_path, capsys):
    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "2026Sep02-090319-Rec12.ogg").write_bytes(b"\x00" * 15297132)
    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(
        ["sync", "-o", str(audio), "--since", "2026-09-03"],
        transport_factory=_factory(transport),
    )
    assert code == 0
    events = {e["file"]: e for e in (json.loads(l) for l in capsys.readouterr().out.splitlines())}
    assert events["2026Sep02-090319-Rec12.hda"]["reason"] == "already present"
    assert len(transport.written) == 1


def test_sync_applies_since_before_downloading(file_list_bytes, tmp_path, capsys):
    # Every fixture entry is older than this date: nothing may be downloaded,
    # even though real duration is only known after a download.
    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(
        ["sync", "-o", str(tmp_path), "--since", "2026-11-01", "--min-seconds", "0"],
        transport_factory=_factory(transport),
    )
    assert code == 0
    assert len(transport.written) == 1
