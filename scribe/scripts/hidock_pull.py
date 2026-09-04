#!/usr/bin/env python3
# Jensen protocol re-implemented from the hidock-next project (MIT licensed).
"""Read-only USB puller for HiDock P1 recordings: list, download, and sync.

Talks the vendor-specific "Jensen" USB protocol directly (bulk OUT/IN, no
mass-storage). Only two commands exist in this file: GET_FILE_LIST and
TRANSFER_FILE. There is no delete, format, or settings command implemented
here, and none should ever be added -- recordings on the device must never
be modified.

Usage:
    python3 hidock_pull.py list [--json] [--tz TZ]
    python3 hidock_pull.py download <name> -o <dir>
    python3 hidock_pull.py sync -o <dir> [--since YYYY-MM-DD] [--min-seconds N] [--done-dir DIR]

Common flags: --vid --pid --timeout-ms.

Exit codes: 0 ok, 1 requested file not found on device, 2 device not found,
3 USB claim error (device busy -- likely the HiNotes browser tab), 4
downloaded payload failed size or magic-byte verification.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

import usb.core
import usb.util

DEFAULT_VID = 0x10D6
DEFAULT_PID = 0xB00E
DEFAULT_TIMEOUT_MS = 3000
DEFAULT_TZ = "America/Chicago"

SYNC = b"\x12\x34"
FRAME_HEADER_LEN = 12
CMD_GET_FILE_LIST = 4
CMD_TRANSFER_FILE = 5

# 96kbps mono is what firmware 1.4.5 actually encodes on this P1, confirmed
# with ffprobe against a downloaded file. The device's own "version" byte
# maps to a different codec/rate table in the upstream client; that formula
# was 4x off against the real duration. Bitrate-derived duration matches
# ffprobe's own estimate.
MP3_BITRATE_BPS = 96_000


class DeviceNotFoundError(Exception):
    pass


class DeviceNoResponseError(Exception):
    """The device took the command but never sent a frame back."""


class UsbClaimError(Exception):
    pass


# --- pure protocol functions -------------------------------------------------

def build_frame(cmd: int, seq: int, body: bytes = b"") -> bytes:
    if len(body) > 0x00FFFFFF:
        raise ValueError("Jensen frame body exceeds the 24-bit length field")
    return struct.pack(">BBHII", 0x12, 0x34, cmd, seq, len(body)) + body


def parse_frames(buf: bytes) -> tuple[list[tuple[int, int, bytes]], bytes]:
    """Split buf into complete Jensen frames (sync, cmd:u16, seq:u32, len:u32,
    body). Bytes before the first sync marker are dropped as noise; an
    incomplete trailing frame is returned as carry-over for the next read."""
    frames: list[tuple[int, int, bytes]] = []
    n = len(buf)
    pos = 0
    while True:
        sync_pos = buf.find(SYNC, pos)
        if sync_pos == -1:
            return frames, b""
        if sync_pos + FRAME_HEADER_LEN > n:
            return frames, buf[sync_pos:]
        cmd, seq, raw_len = struct.unpack(">HII", buf[sync_pos + 2:sync_pos + 12])
        body_len = raw_len & 0x00FFFFFF
        checksum_len = (raw_len >> 24) & 0xFF
        total = FRAME_HEADER_LEN + body_len + checksum_len
        if sync_pos + total > n:
            return frames, buf[sync_pos:]
        body = buf[sync_pos + FRAME_HEADER_LEN:sync_pos + FRAME_HEADER_LEN + body_len]
        frames.append((cmd, seq, body))
        pos = sync_pos + total


@dataclass(frozen=True)
class FileEntry:
    filename: str
    size: int
    version: int
    signature: str


def parse_file_list_entries(body: bytes) -> list[FileEntry]:
    pos = 0
    n = len(body)
    if n >= 6 and body[0] == 0xFF and body[1] == 0xFF:
        pos = 6
    entries: list[FileEntry] = []
    while pos < n:
        if pos + 4 > n:
            break
        version = body[pos]
        pos += 1
        name_len = int.from_bytes(body[pos:pos + 3], "big")
        pos += 3
        if name_len <= 0 or name_len > 200 or pos + name_len > n:
            break
        filename = body[pos:pos + name_len].rstrip(b"\x00").decode("ascii", errors="ignore")
        pos += name_len
        if pos + 4 > n:
            break
        size = struct.unpack(">I", body[pos:pos + 4])[0]
        pos += 4
        if pos + 6 > n:
            break
        pos += 6  # reserved, unused
        if pos + 16 > n:
            break
        signature = body[pos:pos + 16].hex()
        pos += 16
        entries.append(FileEntry(filename=filename, size=size, version=version, signature=signature))
    return entries


def estimate_duration_seconds(size_bytes: int) -> float:
    return size_bytes * 8 / MP3_BITRATE_BPS


_FILENAME_PATTERN = re.compile(r"^(\d{4})([A-Za-z]{3})(\d{2})-(\d{2})(\d{2})(\d{2})-Rec\d+\.hda$")
_MONTH_ABBR = {
    m: i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1
    )
}


def parse_filename_start(filename: str, tz_name: str) -> datetime | None:
    """The device exposes no separate timestamp field -- the filename
    ("YYYYMonDD-HHMMSS-RecNN.hda") is the only source of a recording's
    start time, and it's local device-clock time with no offset attached."""
    match = _FILENAME_PATTERN.match(filename)
    if not match:
        return None
    year, month_abbr, day, hour, minute, second = match.groups()
    month = _MONTH_ABBR.get(month_abbr.title())
    if month is None:
        return None
    try:
        naive = datetime(int(year), month, int(day), int(hour), int(minute), int(second))
    except ValueError:
        return None
    return naive.replace(tzinfo=ZoneInfo(tz_name))


def looks_like_mp3(data: bytes) -> bool:
    return data[:2] == b"\xff\xfb" or data[:3] == b"ID3"


# --- transport boundary -------------------------------------------------------

class Transport(Protocol):
    def write(self, data: bytes) -> None: ...
    def read(self, size: int, timeout_ms: int) -> bytes: ...
    def close(self) -> None: ...


class UsbTransport:
    """Real transport: bulk OUT/IN endpoints on the vendor-specific Jensen
    interface, via pyusb. PyUSB's implicit interface claim (on first
    write()/read()) is what raises LIBUSB_ERROR_ACCESS / BUSY when another
    process -- typically the HiNotes browser tab holding a WebUSB claim --
    already owns the interface."""

    def __init__(self, vid: int, pid: int):
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise DeviceNotFoundError(f"0x{vid:04x}:0x{pid:04x}")
        try:
            # macOS already configures the device; calling set_configuration on
            # an active device fails with errno 19, so only set it when needed.
            try:
                cfg = dev.get_active_configuration()
            except usb.core.USBError:
                dev.set_configuration()
                cfg = dev.get_active_configuration()
            intf = cfg[(0, 0)]
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
            )
            ep_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN,
            )
        except usb.core.USBError as exc:
            raise UsbClaimError(str(exc)) from exc
        if ep_out is None or ep_in is None:
            raise DeviceNotFoundError(f"0x{vid:04x}:0x{pid:04x} has no vendor bulk endpoints")

        self._dev = dev
        self._ep_out = ep_out
        self._ep_in = ep_in

    def write(self, data: bytes) -> None:
        try:
            self._ep_out.write(data, timeout=5000)
        except usb.core.USBError as exc:
            raise UsbClaimError(str(exc)) from exc

    def read(self, size: int, timeout_ms: int) -> bytes:
        try:
            return bytes(self._dev.read(self._ep_in.bEndpointAddress, size, timeout=timeout_ms))
        except usb.core.USBTimeoutError:
            return b""
        except usb.core.USBError as exc:
            raise UsbClaimError(str(exc)) from exc

    def close(self) -> None:
        usb.util.dispose_resources(self._dev)


class JensenClient:
    """Sequences Jensen commands over a Transport and assembles frame bodies.
    Frame parsing itself is pure (parse_frames); this class only owns the
    read loop and its stopping conditions."""

    _READ_CHUNK = 32768
    _IDLE_READS = 10
    _IDLE_AFTER_DATA_MS = 500

    def __init__(self, transport: Transport, timeout_ms: int = DEFAULT_TIMEOUT_MS):
        self._transport = transport
        self._timeout_ms = timeout_ms
        self._seq = 0

    def _send(self, cmd: int, body: bytes = b"") -> None:
        self._seq += 1
        self._transport.write(build_frame(cmd, self._seq, body))

    def _read_bodies(
        self,
        cmd: int,
        *,
        require_progress: bool,
        budget_s: float,
        expected_size: int | None = None,
    ) -> tuple[list[bytes], bool]:
        """Return (bodies, answered). `answered` is False when no frame for `cmd`
        arrived at all, which is how a silent device differs from one that
        replied with an explicit empty end-of-stream frame."""
        bodies: list[bytes] = []
        answered = False
        carry = b""
        empty_streak = 0
        received = 0
        deadline = time.monotonic() + budget_s
        while time.monotonic() < deadline:
            # The device answers in one burst (list) or a stream that stops at
            # expected_size (download), so once data has arrived a short idle
            # read is enough to detect the end. The upstream bridge gated its
            # idle exit on a non-empty buffer and so waited out its full timeout.
            timeout_ms = self._IDLE_AFTER_DATA_MS if received > 0 else self._timeout_ms
            chunk = self._transport.read(self._READ_CHUNK, timeout_ms)
            if not chunk:
                empty_streak += 1
                if received > 0 or (empty_streak >= self._IDLE_READS and not require_progress):
                    return bodies, answered
                continue
            empty_streak = 0
            carry += chunk
            frames, carry = parse_frames(carry)
            for frame_cmd, _seq, body in frames:
                if frame_cmd != cmd:
                    continue
                answered = True
                if not body:
                    return bodies, answered  # explicit end-of-stream frame
                bodies.append(body)
                received += len(body)
            if expected_size is not None and received >= expected_size:
                return bodies, answered
        return bodies, answered

    def get_file_list(self, budget_s: float = 30.0) -> list[FileEntry]:
        # On 2026-09-04 the first list after plugging in came back silent and was
        # reported as "No recordings found", hiding a full day of calls. One
        # retry covers that warm-up; a second silence is an error, not an empty
        # device.
        for _attempt in range(2):
            self._send(CMD_GET_FILE_LIST)
            bodies, answered = self._read_bodies(CMD_GET_FILE_LIST, require_progress=False, budget_s=budget_s)
            if answered:
                return parse_file_list_entries(b"".join(bodies))
        raise DeviceNoResponseError("device did not answer the file-list request")

    def download_file(self, filename: str, expected_size: int, budget_s: float | None = None) -> bytes:
        self._send(CMD_TRANSFER_FILE, filename.encode("ascii"))
        budget = budget_s if budget_s is not None else max(30.0, expected_size / (64 * 1024))
        bodies, _answered = self._read_bodies(
            CMD_TRANSFER_FILE, require_progress=True, budget_s=budget, expected_size=expected_size
        )
        return b"".join(bodies)


# --- CLI ----------------------------------------------------------------------

def _entry_to_row(entry: FileEntry, tz_name: str) -> dict:
    start = parse_filename_start(entry.filename, tz_name)
    return {
        "name": entry.filename,
        "size_bytes": entry.size,
        "est_duration_s": round(estimate_duration_seconds(entry.size), 3),
        "start": start.isoformat() if start else None,
    }


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No recordings found.")
        return
    print(f"{'Name':<32} {'Size':>10} {'Duration':>9}  Start")
    for row in rows:
        print(
            f"{row['name']:<32} {_format_size(row['size_bytes']):>10} "
            f"{_format_duration(row['est_duration_s']):>9}  {row['start'] or 'unknown'}"
        )


def _verify_download(entry: FileEntry, data: bytes) -> tuple[bool, int]:
    if len(data) != entry.size:
        print(f"error: {entry.filename}: expected {entry.size} bytes, got {len(data)}", file=sys.stderr)
        return False, 4
    if not looks_like_mp3(data):
        print(f"error: {entry.filename}: downloaded payload does not look like MP3 (bad magic bytes)", file=sys.stderr)
        return False, 4
    return True, 0


def _write_mp3(data: bytes, filename: str, output_dir: str) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{Path(filename).stem}.mp3"
    dest.write_bytes(data)
    return dest


def _cmd_list(client: JensenClient, args: argparse.Namespace) -> int:
    rows = [_entry_to_row(e, args.tz) for e in client.get_file_list()]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        _print_table(rows)
    return 0


def _cmd_download(client: JensenClient, args: argparse.Namespace) -> int:
    entries = client.get_file_list()
    entry = next((e for e in entries if e.filename == args.name), None)
    if entry is None:
        print(f"error: {args.name!r} not found on device", file=sys.stderr)
        return 1
    data = client.download_file(entry.filename, entry.size)
    ok, code = _verify_download(entry, data)
    if not ok:
        return code
    dest = _write_mp3(data, entry.filename, args.output)
    print(str(dest))
    return 0


def _emit_sync_event(name: str, status: str, reason: str | None) -> None:
    event: dict = {"file": name, "status": status}
    if reason:
        event["reason"] = reason
    print(json.dumps(event))


def _cmd_sync(client: JensenClient, args: argparse.Namespace) -> int:
    entries = client.get_file_list()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    since = date.fromisoformat(args.since) if args.since else None

    for entry in entries:
        dest = out_dir / f"{Path(entry.filename).stem}.mp3"
        duration = estimate_duration_seconds(entry.size)
        start = parse_filename_start(entry.filename, args.tz)

        if dest.exists() and dest.stat().st_size == entry.size:
            _emit_sync_event(entry.filename, "skipped", "already present")
            continue
        if args.done_dir and (Path(args.done_dir) / f"{Path(entry.filename).stem}.json").exists():
            _emit_sync_event(entry.filename, "skipped", "already transcribed")
            continue
        if duration < args.min_seconds:
            _emit_sync_event(
                entry.filename, "skipped", f"shorter than --min-seconds ({duration:.1f}s < {args.min_seconds}s)"
            )
            continue
        if since is not None and (start is None or start.date() < since):
            _emit_sync_event(entry.filename, "skipped", f"older than --since {since.isoformat()}")
            continue

        data = client.download_file(entry.filename, entry.size)
        ok, code = _verify_download(entry, data)
        if not ok:
            return code
        dest.write_bytes(data)
        _emit_sync_event(entry.filename, "downloaded", None)

    return 0


def _vid_pid_type(value: str) -> int:
    return int(value, 0)


def build_arg_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vid", type=_vid_pid_type, default=DEFAULT_VID)
    common.add_argument("--pid", type=_vid_pid_type, default=DEFAULT_PID)
    common.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", parents=[common], help="List recordings on the device")
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--tz", default=DEFAULT_TZ)

    p_download = sub.add_parser("download", parents=[common], help="Download one recording")
    p_download.add_argument("name")
    p_download.add_argument("-o", "--output", required=True)

    p_sync = sub.add_parser("sync", parents=[common], help="Download recordings not already present")
    p_sync.add_argument("-o", "--output", required=True)
    p_sync.add_argument("--since", default=None, help="Skip recordings that started before this date (YYYY-MM-DD)")
    p_sync.add_argument("--min-seconds", type=float, default=0.0, help="Skip recordings shorter than this")
    p_sync.add_argument(
        "--done-dir", default=None,
        help="Skip recordings whose <stem>.json transcript exists here (local audio is deleted after transcription)",
    )
    p_sync.add_argument("--tz", default=DEFAULT_TZ)

    return parser


def main(argv: list[str] | None = None, transport_factory: Callable[[int, int], Transport] = UsbTransport) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        transport = transport_factory(args.vid, args.pid)
    except DeviceNotFoundError:
        print(f"No HiDock device found (vid=0x{args.vid:04x} pid=0x{args.pid:04x}). Plug in the P1 and try again.", file=sys.stderr)
        return 2
    except UsbClaimError as exc:
        print(f"USB claim error: {exc}", file=sys.stderr)
        print("Close the HiNotes tab in your browser -- it likely holds the WebUSB claim on the device.", file=sys.stderr)
        return 3

    try:
        client = JensenClient(transport, timeout_ms=args.timeout_ms)
        if args.command == "list":
            return _cmd_list(client, args)
        if args.command == "download":
            return _cmd_download(client, args)
        if args.command == "sync":
            return _cmd_sync(client, args)
        parser.error(f"unknown command {args.command!r}")
        return 1
    except UsbClaimError as exc:
        print(f"USB claim error: {exc}", file=sys.stderr)
        print("Close the HiNotes tab in your browser -- it likely holds the WebUSB claim on the device.", file=sys.stderr)
        return 3
    except DeviceNoResponseError as exc:
        print(f"No response: {exc}", file=sys.stderr)
        print("The P1 is connected but silent. Unplug and replug it, close HiNotes, then retry.", file=sys.stderr)
        return 4
    finally:
        transport.close()


if __name__ == "__main__":
    sys.exit(main())
