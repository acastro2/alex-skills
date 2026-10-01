"""Behaviour tests for claude_session_payloads.py, exercised through the CLI.

The fixtures build a miniature Claude Code project: a session `.jsonl` holding a
tool result, and a sibling `tool-results/` spill file. Both shapes are what the
OpenCode route has to read, so the tests reproduce them rather than mocking.
"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import claude_session_payloads  # noqa: E402


def _payload(subject, join_url, start, end, speakers=("Ana Silva", "Bruno Costa")):
    cues = []
    for index, speaker in enumerate(speakers):
        cues.append(
            f"00:00:0{index * 5}.000 --> 00:00:0{index * 5 + 4}.000\r\n"
            f"<v {speaker}>line {index} for {subject}</v>"
        )
    return {
        "meeting": {
            "id": "meeting-" + subject.replace(" ", "-").lower(),
            "subject": subject,
            "startDateTime": "2026-01-05T20:00:00Z",  # series start: never the occurrence
            "joinWebUrl": join_url,
        },
        "transcripts": [
            {"createdDateTime": start, "endDateTime": end, "content": "WEBVTT\r\n\r\n" + "\r\n\r\n".join(cues)}
        ],
    }


def _token(join_url):
    return base64.urlsafe_b64encode(join_url.encode()).decode().rstrip("=")


def _uri(join_url, start, end):
    return (
        f"meeting-transcript:///events/{_token(join_url)}"
        f"?start={start.replace(':', '%3A')}&end={end.replace(':', '%3A')}"
    )


def _project(tmp_path, sessions):
    """sessions: list of (session_name, [payloads...], [spilled payloads...], [uris...])"""
    project = tmp_path / "projects" / "-Users-someone-repo"
    project.mkdir(parents=True)
    for name, inline, spilled, uris in sessions:
        lines = []
        for payload in inline:
            lines.append(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "tool_result", "content": json.dumps(payload)}],
                        },
                    }
                )
            )
        for uri in uris:
            lines.append(json.dumps({"type": "user", "text": f"read_resource {uri}"}))
        (project / f"{name}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if spilled:
            spill_dir = project / name / "tool-results"
            spill_dir.mkdir(parents=True)
            for index, payload in enumerate(spilled):
                (spill_dir / f"mcp-read_resource-{index}.txt").write_text(
                    json.dumps(payload), encoding="utf-8"
                )
    return project


def _manifest(tmp_path, rows):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _run(run_script, tmp_path, project, manifest, *extra):
    raw = tmp_path / "raw"
    notes = tmp_path / "transcripts"
    result = run_script(
        "claude_session_payloads.py",
        "--manifest", str(manifest),
        "--project", str(project),
        "--raw-dir", str(raw),
        "--transcripts-dir", str(notes),
        *extra,
    )
    return result, raw, notes


STANDUP = "https://teams.microsoft.com/l/meetup-join/19%3ameeting_aaa%40thread.v2/0?context=%7b%7d"
REVIEW = "https://teams.microsoft.com/l/meetup-join/19%3ameeting_bbb%40thread.v2/0?context=%7b%7d"


def test_recovers_inline_and_spilled_payloads_into_raw_files(run_script, tmp_path):
    inline = _payload("EA Daily Standup", STANDUP, "2026-09-30T14:00:55Z", "2026-09-30T14:29:31Z")
    spilled = _payload("CURO / Heights Risks - Weekly review", REVIEW, "2026-09-30T15:59:33Z", "2026-09-30T16:26:01Z", speakers=("Greg Glazier",))
    project = _project(
        tmp_path,
        [
            (
                "session-one",
                [inline],
                [spilled],
                [
                    _uri(STANDUP, "2026-09-30T14:00:00.000Z", "2026-09-30T14:15:00.000Z"),
                    _uri(REVIEW, "2026-09-30T16:00:00.000Z", "2026-09-30T16:30:00.000Z"),
                ],
            )
        ],
    )
    manifest = _manifest(
        tmp_path,
        [
            {"subject": "EA Daily Standup", "event_id": "evt-standup", "start": "2026-09-30T14:00:00Z", "end": "2026-09-30T14:15:00Z"},
            {"subject": "CURO / Heights Risks - Weekly review", "event_id": "evt-review", "start": "2026-09-30T16:00:00Z", "end": "2026-09-30T16:30:00Z"},
        ],
    )

    result, raw, _ = _run(run_script, tmp_path, project, manifest)

    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in raw.iterdir()) == [
        "2026-09-30-curo-heights-risks-weekly-review.json",
        "2026-09-30-curo-heights-risks-weekly-review.vtt",
        "2026-09-30-ea-daily-standup.json",
        "2026-09-30-ea-daily-standup.vtt",
    ]
    recovered = json.loads((raw / "2026-09-30-ea-daily-standup.json").read_text(encoding="utf-8"))
    assert recovered["meeting"]["subject"] == "EA Daily Standup"
    # The .vtt is the record: it keeps the CRLF block separators the payload carried.
    vtt = (raw / "2026-09-30-ea-daily-standup.vtt").read_bytes().decode("utf-8")
    assert vtt.startswith("WEBVTT\r\n\r\n")
    assert vtt == inline["transcripts"][0]["content"]
    assert "CURO / Heights Risks - Weekly review" in result.stdout
    assert "2 rebuilt" in result.stdout or "2 of 2" in result.stdout


def test_chooses_the_uri_window_that_holds_the_transcript(run_script, tmp_path):
    payload = _payload("EA Daily Standup", STANDUP, "2026-09-30T14:00:55Z", "2026-09-30T14:29:31Z")
    project = _project(
        tmp_path,
        [
            (
                "session-two",
                [payload],
                [],
                [
                    # A neighbouring occurrence of the same series, read first: must not win.
                    _uri(STANDUP, "2026-09-29T14:00:00.000Z", "2026-09-29T14:15:00.000Z"),
                    _uri(STANDUP, "2026-09-30T14:00:00.000Z", "2026-09-30T14:15:00.000Z"),
                ],
            )
        ],
    )
    manifest = _manifest(
        tmp_path,
        [{"subject": "EA Daily Standup", "event_id": "evt-standup", "start": "2026-09-30T14:00:00Z", "end": "2026-09-30T14:15:00Z"}],
    )

    result, _, notes = _run(run_script, tmp_path, project, manifest, "--normalize", "--vault", str(tmp_path / "vault"))

    assert result.returncode == 0, result.stderr
    normalized = json.loads((notes / "2026-09-30-ea-daily-standup.json").read_text(encoding="utf-8"))
    assert normalized["schema"] == "scribe.transcript/1"
    assert normalized["source"] == "teams"
    assert normalized["start"] == "2026-09-30T14:00:00.000Z"
    assert normalized["speakers"] == ["Ana Silva", "Bruno Costa"]
    assert normalized["provenance"]["teams_event_id"] == "evt-standup"
    assert normalized["provenance"]["transcript_uri"].endswith("end=2026-09-30T14%3A15%3A00.000Z")
    assert "2026-09-30 0900 EA Daily Standup.md" in result.stdout


def test_payload_recovered_twice_is_not_reported_as_unmapped(run_script, tmp_path):
    # The real artifacts hold the same payload inline in the .jsonl and again in
    # the spill file; neither copy may look like an unrequested meeting.
    payload = _payload("DLP Open Questions", STANDUP, "2026-09-30T16:32:10Z", "2026-09-30T17:00:24Z")
    project = _project(
        tmp_path,
        [("session-six", [payload], [payload], [_uri(STANDUP, "2026-09-30T16:30:00.000Z", "2026-09-30T17:00:00.000Z")])],
    )
    manifest = _manifest(
        tmp_path,
        [{"subject": "DLP Open Questions", "event_id": "evt-dlp", "start": "2026-09-30T16:30:00Z", "end": "2026-09-30T17:00:00Z"}],
    )

    result, _, _ = _run(run_script, tmp_path, project, manifest)

    assert result.returncode == 0, result.stderr
    assert "no manifest row" not in result.stderr


def test_manifest_row_without_a_payload_exits_nonzero(run_script, tmp_path):
    payload = _payload("DLP Open Questions", STANDUP, "2026-09-30T16:32:10Z", "2026-09-30T17:00:24Z")
    project = _project(tmp_path, [("session-three", [payload], [], [_uri(STANDUP, "2026-09-30T16:30:00.000Z", "2026-09-30T17:00:00.000Z")])])
    manifest = _manifest(
        tmp_path,
        [
            {"subject": "DLP Open Questions", "event_id": "evt-dlp", "start": "2026-09-30T16:30:00Z", "end": "2026-09-30T17:00:00Z"},
            {"subject": "Project sizing", "event_id": "evt-sizing", "start": "2026-09-30T21:00:00Z", "end": "2026-09-30T21:30:00Z"},
        ],
    )

    result, raw, _ = _run(run_script, tmp_path, project, manifest)

    assert result.returncode != 0
    assert "Project sizing" in result.stderr
    assert not (raw / "2026-09-30-project-sizing.json").exists()
    assert (raw / "2026-09-30-dlp-open-questions.json").exists()


def test_payload_with_no_manifest_row_is_reported_but_not_fatal(run_script, tmp_path):
    wanted = _payload("DLP Open Questions", STANDUP, "2026-09-30T16:32:10Z", "2026-09-30T17:00:24Z")
    extra = _payload("EA Daily Mob Time (Optional)", REVIEW, "2026-09-29T19:30:14Z", "2026-09-29T19:47:50Z")
    project = _project(
        tmp_path,
        [
            (
                "session-four",
                [wanted, extra],
                [],
                [
                    _uri(STANDUP, "2026-09-30T16:30:00.000Z", "2026-09-30T17:00:00.000Z"),
                    _uri(REVIEW, "2026-09-30T19:00:00.000Z", "2026-09-30T19:30:00.000Z"),
                ],
            )
        ],
    )
    manifest = _manifest(
        tmp_path,
        [{"subject": "DLP Open Questions", "event_id": "evt-dlp", "start": "2026-09-30T16:30:00Z", "end": "2026-09-30T17:00:00Z"}],
    )

    result, raw, _ = _run(run_script, tmp_path, project, manifest)

    assert result.returncode == 0, result.stderr
    assert "EA Daily Mob Time (Optional)" in result.stderr
    assert "no manifest row" in result.stderr
    assert (raw / "2026-09-30-dlp-open-questions.json").exists()
    # The unmatched payload is left alone: scribe never writes a note nobody asked for.
    assert not (raw / "2026-09-29-ea-daily-mob-time-optional.json").exists()


def test_missing_window_is_synthesized_from_the_manifest_slot_and_flagged(run_script, tmp_path):
    payload = _payload("Project sizing", STANDUP, "2026-09-30T21:00:10Z", "2026-09-30T21:29:00Z")
    project = _project(
        tmp_path,
        [("session-five", [payload], [], [f"meeting-transcript:///events/{_token(STANDUP)}"])],
    )
    manifest = _manifest(
        tmp_path,
        [{"subject": "Project sizing", "event_id": "evt-sizing", "start": "2026-09-30T21:00:00Z", "end": "2026-09-30T21:30:00Z"}],
    )

    result, _, notes = _run(run_script, tmp_path, project, manifest, "--normalize", "--vault", str(tmp_path / "vault"))

    assert result.returncode == 0, result.stderr
    assert "no window" in result.stderr
    normalized = json.loads((notes / "2026-09-30-project-sizing.json").read_text(encoding="utf-8"))
    assert normalized["start"] == "2026-09-30T21:00:00.000Z"
    assert normalized["provenance"]["transcript_uri"].endswith(
        "?start=2026-09-30T21%3A00%3A00.000Z&end=2026-09-30T21%3A30%3A00.000Z"
    )


def test_project_dir_defaults_to_the_working_directory_name():
    # Claude Code names a project after the cwd, which is how the OpenCode route
    # finds the session without being told a path.
    derived = claude_session_payloads.default_project_dir(Path("/Users/someone/Developer/enterprise-architecture"))
    assert derived == Path.home() / ".claude" / "projects" / "-Users-someone-Developer-enterprise-architecture"


def test_slug_key_flattens_a_subject_for_filenames():
    assert claude_session_payloads.subject_key("CURO / Heights Risks - Weekly review") == "curo-heights-risks-weekly-review"
    assert claude_session_payloads.subject_key("DLP Open Questions") == "dlp-open-questions"
