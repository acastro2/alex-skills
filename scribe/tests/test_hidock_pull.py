"""Behaviour tests for hidock_pull.py.

Most tests inject a FakeTransport at the same seam production code uses
(main()'s transport_factory) -- USB hardware is the real outside-the-process
boundary, so that's where the fake belongs. One test at the bottom talks to
the real device and is skipped automatically when none is connected.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import hidock_pull as hp  # noqa: E402


# --- fake transport ------------------------------------------------------------

class FakeTransport:
    """Each write() arms the next canned response (a list of read() chunks,
    drained in order); once that response is exhausted, read() returns empty
    bytes until the next write() arms a new one. This mirrors the real
    device, which only ever sends data in reply to a command -- a queue
    that ignored write() boundaries would let one command's response leak
    into another's read loop and starve it."""

    def __init__(self, responses: list[list[bytes]]):
        self._responses = list(responses)
        self._current: list[bytes] = []
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written.append(data)
        self._current = list(self._responses.pop(0)) if self._responses else []

    def read(self, size: int, timeout_ms: int) -> bytes:
        if self._current:
            return self._current.pop(0)
        return b""

    def close(self) -> None:
        self.closed = True


def _factory(transport: FakeTransport):
    return lambda vid, pid: transport


def _raising_factory(exc: Exception):
    def factory(vid, pid):
        raise exc
    return factory


@pytest.fixture
def file_list_bytes(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "hidock_file_list.bin").read_bytes()


# --- protocol parsing (pure functions) ------------------------------------------

def test_parse_file_list_entries_from_real_capture_yields_17_entries_with_correct_names_sizes_starts(
    file_list_bytes,
):
    frames, leftover = hp.parse_frames(file_list_bytes)
    assert leftover == b""
    assert len(frames) == 1
    cmd, _seq, body = frames[0]
    assert cmd == hp.CMD_GET_FILE_LIST

    entries = hp.parse_file_list_entries(body)
    assert len(entries) == 17
    assert entries[0].filename == "2026Sep01-090855-Rec01.hda"
    assert entries[0].size == 2276652
    assert entries[-1].filename == "2026Sep02-150056-Rec17.hda"
    assert entries[-1].size == 29988012

    start = hp.parse_filename_start(entries[-1].filename, "America/Chicago")
    assert start.isoformat() == "2026-09-02T15:00:56-05:00"


def test_estimate_duration_seconds_uses_96kbps_bitrate():
    # 29,988,012 B * 8 / 96000 bps == 2499.001s, matching ffprobe's own
    # estimate for the real Rec17 file -- not the device's version-keyed
    # formula, which was 4x off (9996s) against that same file.
    assert hp.estimate_duration_seconds(29988012) == pytest.approx(2499.001, rel=1e-6)
    assert hp.estimate_duration_seconds(0) == 0.0


@pytest.mark.parametrize(
    "filename",
    [
        "not-a-hidock-name.mp3",
        "2026Sep02-150056-Rec17.mp3",  # wrong extension
        "2026Xyz02-150056-Rec17.hda",  # bad month abbreviation
        "2026Sep32-150056-Rec17.hda",  # invalid day
        "",
    ],
)
def test_parse_filename_start_returns_none_for_bad_names(filename):
    assert hp.parse_filename_start(filename, "America/Chicago") is None


def test_parse_filename_start_parses_valid_name_in_requested_timezone():
    start = hp.parse_filename_start("2026Sep02-150056-Rec17.hda", "UTC")
    assert start.isoformat() == "2026-09-02T15:00:56+00:00"


def test_looks_like_mp3_accepts_frame_sync_and_id3_rejects_other_bytes():
    assert hp.looks_like_mp3(b"\xff\xfb\x90\x00rest of an mp3 frame") is True
    assert hp.looks_like_mp3(b"ID3\x03\x00\x00\x00\x00\x00\x00") is True
    assert hp.looks_like_mp3(b"RIFF....WAVEfmt ") is False
    assert hp.looks_like_mp3(b"") is False


# --- JensenClient read loop (the drain-until-idle bug fix) ----------------------

def test_get_file_list_returns_all_entries_from_a_single_burst_read_and_completes_quickly(file_list_bytes):
    # The upstream bridge this was ported from only stopped waiting when
    # N consecutive timeouts occurred AND the receive buffer was non-empty.
    # A single-burst response (this fixture) empties that buffer as soon as
    # it's parsed, so that condition never re-fires and the call waits out
    # its full budget. This asserts the fix: idle exit fires regardless of
    # buffer state, so this returns near-instantly, not after 30s.
    transport = FakeTransport([[file_list_bytes]])
    client = hp.JensenClient(transport)

    started = time.monotonic()
    entries = client.get_file_list(budget_s=30.0)
    elapsed = time.monotonic() - started

    assert len(entries) == 17
    assert elapsed < 2.0


def test_download_file_stops_once_expected_size_is_reached():
    payload = b"\xff\xfb" + b"\x00" * 100
    frame = hp.build_frame(hp.CMD_TRANSFER_FILE, seq=1, body=payload)
    transport = FakeTransport([[frame]])
    client = hp.JensenClient(transport)

    data = client.download_file("2026Sep02-150056-Rec17.hda", expected_size=len(payload))

    assert data == payload


# --- CLI: list -------------------------------------------------------------

def test_cli_list_json_reports_all_entries(file_list_bytes, capsys):
    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(["list", "--json"], transport_factory=_factory(transport))

    assert code == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 17
    assert rows[-1]["name"] == "2026Sep02-150056-Rec17.hda"
    assert rows[-1]["size_bytes"] == 29988012
    assert rows[-1]["est_duration_s"] == pytest.approx(2499.001, rel=1e-6)
    assert transport.closed is True


# --- CLI: download -----------------------------------------------------------

def test_cli_download_verifies_size_and_magic_bytes_then_writes_mp3(file_list_bytes, tmp_path):
    payload = b"\xff\xfb" + b"\x00" * (2276652 - 2)  # matches Rec01's listed size
    file_frame = hp.build_frame(hp.CMD_TRANSFER_FILE, seq=2, body=payload)
    transport = FakeTransport([[file_list_bytes], [file_frame]])

    code = hp.main(
        ["download", "2026Sep01-090855-Rec01.hda", "-o", str(tmp_path)],
        transport_factory=_factory(transport),
    )

    assert code == 0
    dest = tmp_path / "2026Sep01-090855-Rec01.mp3"
    assert dest.read_bytes() == payload


def test_cli_download_rejects_bad_magic_bytes_and_writes_nothing(file_list_bytes, tmp_path):
    payload = b"RIFF" + b"\x00" * (2276652 - 4)  # right size, wrong magic
    file_frame = hp.build_frame(hp.CMD_TRANSFER_FILE, seq=2, body=payload)
    transport = FakeTransport([[file_list_bytes], [file_frame]])

    code = hp.main(
        ["download", "2026Sep01-090855-Rec01.hda", "-o", str(tmp_path)],
        transport_factory=_factory(transport),
    )

    assert code == 4
    assert list(tmp_path.glob("*.mp3")) == []


def test_cli_download_unknown_filename_exits_1(file_list_bytes, tmp_path):
    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(
        ["download", "does-not-exist.hda", "-o", str(tmp_path)],
        transport_factory=_factory(transport),
    )
    assert code == 1


# --- CLI: sync ---------------------------------------------------------------

def test_cli_sync_skips_already_present_short_and_old_files_without_downloading(file_list_bytes, tmp_path, capsys):
    # Rec01 (189.7s est. duration) is shorter than --min-seconds; every
    # other entry is dated 2026-09-01/02 and gets skipped by --since. None
    # of these paths require a real TRANSFER_FILE response.
    already_present = tmp_path / "2026Sep02-090319-Rec12.mp3"
    already_present.write_bytes(b"\xff\xfb" + b"\x00" * (15297132 - 2))  # matches Rec12's listed size

    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(
        ["sync", "-o", str(tmp_path), "--since", "2026-09-03", "--min-seconds", "200"],
        transport_factory=_factory(transport),
    )

    assert code == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    by_file = {e["file"]: e for e in events}

    assert len(events) == 17
    assert all(e["status"] == "skipped" for e in events)
    assert by_file["2026Sep02-090319-Rec12.hda"]["reason"] == "already present"
    assert "min-seconds" in by_file["2026Sep01-090855-Rec01.hda"]["reason"]
    assert "since" in by_file["2026Sep02-150056-Rec17.hda"]["reason"]
    # Only the GET_FILE_LIST command was ever sent -- no download attempted.
    assert len(transport.written) == 1


def test_cli_sync_downloads_a_new_file_that_passes_all_filters(file_list_bytes, tmp_path, capsys):
    # --since 2026-09-02 lets seven entries through (Rec11..Rec17). Mark the
    # other six as already present so only Rec17 is actually downloaded --
    # keeps this test to one canned TRANSFER_FILE response instead of seven.
    already_present_sizes = {
        "2026Sep02-075925-Rec11.hda": 19975116,
        "2026Sep02-090319-Rec12.hda": 15297132,
        "2026Sep02-113150-Rec13.hda": 37204140,
        "2026Sep02-130240-Rec14.hda": 31857708,
        "2026Sep02-140205-Rec15.hda": 18425964,
        "2026Sep02-144440-Rec16.hda": 11647884,
    }
    for filename, size in already_present_sizes.items():
        stem = Path(filename).stem
        (tmp_path / f"{stem}.mp3").write_bytes(b"\x00" * size)

    payload = b"\xff\xfb" + b"\x00" * (29988012 - 2)  # matches Rec17's listed size
    # The frame length field is 3 bytes (max ~16MB/frame), so a file this
    # size arrives as several frames on the real device, never one giant
    # frame -- split the canned response the same way.
    chunk_size = 8_000_000
    offsets = range(0, len(payload), chunk_size)
    file_frames = [
        hp.build_frame(hp.CMD_TRANSFER_FILE, seq=2 + n, body=payload[offset : offset + chunk_size])
        for n, offset in enumerate(offsets)
    ]
    transport = FakeTransport([[file_list_bytes], file_frames])

    code = hp.main(
        ["sync", "-o", str(tmp_path), "--since", "2026-09-02", "--min-seconds", "0"],
        transport_factory=_factory(transport),
    )

    captured = capsys.readouterr()
    assert code == 0, captured.err
    dest = tmp_path / "2026Sep02-150056-Rec17.mp3"
    assert dest.read_bytes() == payload
    events = [json.loads(line) for line in captured.out.splitlines()]
    downloaded = {e["file"] for e in events if e["status"] == "downloaded"}
    assert downloaded == {"2026Sep02-150056-Rec17.hda"}


def test_cli_sync_skips_recordings_already_transcribed_in_done_dir(file_list_bytes, tmp_path, capsys):
    # Local audio is deleted after transcription, so presence of the transcript
    # JSON is what must stop a re-download.
    done = tmp_path / "transcripts"
    done.mkdir()
    (done / "2026Sep02-150056-Rec17.json").write_text("{}")
    transport = FakeTransport([[file_list_bytes]])
    code = hp.main(
        ["sync", "-o", str(tmp_path / "audio"), "--since", "2026-09-03", "--done-dir", str(done)],
        transport_factory=_factory(transport),
    )
    assert code == 0
    events = {e["file"]: e for e in (json.loads(l) for l in capsys.readouterr().out.splitlines())}
    assert events["2026Sep02-150056-Rec17.hda"]["reason"] == "already transcribed"
    assert len(transport.written) == 1


# --- CLI: connection errors ----------------------------------------------------

def test_cli_exits_2_with_hint_when_device_not_found(capsys):
    code = hp.main(["list"], transport_factory=_raising_factory(hp.DeviceNotFoundError("0x10d6:0xb00e")))
    assert code == 2
    assert "Plug in the P1" in capsys.readouterr().err


def test_cli_exits_3_with_hint_when_usb_claim_fails(capsys):
    code = hp.main(["list"], transport_factory=_raising_factory(hp.UsbClaimError("[Errno 13] Access denied")))
    err = capsys.readouterr().err
    assert code == 3
    assert "[Errno 13] Access denied" in err
    assert "HiNotes" in err


# --- real device integration test ----------------------------------------------

def _real_device_present() -> bool:
    try:
        return usb_core_find() is not None
    except Exception:
        return False


def usb_core_find():
    import usb.core

    return usb.core.find(idVendor=hp.DEFAULT_VID, idProduct=hp.DEFAULT_PID)


@pytest.mark.skipif(not _real_device_present(), reason="no HiDock P1 connected")
def test_real_device_list_returns_at_least_one_entry(run_script):
    result = run_script("hidock_pull.py", "list", "--json")
    assert result.returncode == 0, result.stderr
    entries = json.loads(result.stdout)
    assert len(entries) >= 1
