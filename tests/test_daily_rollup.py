import hashlib
import json
import subprocess
import sys
from pathlib import Path

import update_daily_rollup
from update_daily_rollup import canonical_json, validate_anchor_chain, validate_artifact_index

ROOT = Path(__file__).resolve().parents[1]


def write_anchor(path: Path, **overrides):
    anchor = {
        "schema": "mirror.daily-anchor.v0.1",
        "date": "2026-05-18",
        "created": "2026-05-18T19:00:00+03:00",
        "rollup_path": "daily-roll-up/2026-05-18.json",
        "rollup_sha256": "a" * 64,
        "entry_count": 1,
        "merkle_root": "b" * 64,
        "previous_anchor_hash": None,
        "external_timestamp": None,
        "note": "Local research anchor only; no external timestamping or regulated trust service is performed.",
    }
    anchor.update(overrides)
    encoded = canonical_json(anchor)
    with path.open("ab") as handle:
        handle.write(encoded + b"\n")
    return hashlib.sha256(encoded).hexdigest()


def test_validate_anchor_chain_accepts_repeated_same_day_anchors(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    first_hash = write_anchor(anchor_path, created="2026-05-18T19:00:00+03:00")
    write_anchor(
        anchor_path,
        created="2026-05-18T20:00:00+03:00",
        rollup_sha256="c" * 64,
        merkle_root="d" * 64,
        previous_anchor_hash=first_hash,
    )

    assert validate_anchor_chain(anchor_path) == []


def test_validate_anchor_chain_accepts_legacy_newline_including_previous_hash(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    anchor = {
        "schema": "mirror.daily-anchor.v0.1",
        "date": "2026-05-18",
        "created": "2026-05-18T19:00:00+03:00",
        "rollup_path": "daily-roll-up/2026-05-18.json",
        "rollup_sha256": "a" * 64,
        "entry_count": 1,
        "merkle_root": "b" * 64,
        "previous_anchor_hash": None,
        "external_timestamp": None,
        "note": "Local research anchor only; no external timestamping or regulated trust service is performed.",
    }
    encoded = canonical_json(anchor)
    with anchor_path.open("ab") as handle:
        handle.write(encoded + b"\n")
    legacy_previous_hash = hashlib.sha256(encoded + b"\n").hexdigest()
    write_anchor(
        anchor_path,
        created="2026-05-18T20:00:00+03:00",
        rollup_sha256="c" * 64,
        merkle_root="d" * 64,
        previous_anchor_hash=legacy_previous_hash,
    )

    assert validate_anchor_chain(anchor_path) == []


def test_validate_anchor_chain_reports_broken_previous_anchor_hash(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    write_anchor(anchor_path, created="2026-05-18T19:00:00+03:00")
    write_anchor(
        anchor_path,
        created="2026-05-18T20:00:00+03:00",
        rollup_sha256="c" * 64,
        merkle_root="d" * 64,
        previous_anchor_hash="0" * 64,
    )

    assert validate_anchor_chain(anchor_path) == [
        "daily-anchors.jsonl line 2: previous_anchor_hash does not match line 1"
    ]


def test_validate_anchor_chain_reports_external_timestamp_claim(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    write_anchor(anchor_path, external_timestamp="2026-05-18T19:00:00Z")

    assert validate_anchor_chain(anchor_path) == [
        "daily-anchors.jsonl line 1: external_timestamp must be null for MIRROR local anchors"
    ]


def test_rollup_cli_validate_anchors_reports_ok_for_valid_chain(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    first_hash = write_anchor(anchor_path, created="2026-05-18T19:00:00+03:00")
    write_anchor(anchor_path, created="2026-05-18T20:00:00+03:00", previous_anchor_hash=first_hash)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--validate-anchors",
            "--anchor-log",
            str(anchor_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"errors": [], "status": "ok"}


def test_rollup_cli_validate_anchors_reports_fail_for_broken_chain(tmp_path):
    anchor_path = tmp_path / "daily-anchors.jsonl"
    write_anchor(anchor_path, created="2026-05-18T19:00:00+03:00")
    write_anchor(anchor_path, created="2026-05-18T20:00:00+03:00", previous_anchor_hash="0" * 64)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--validate-anchors",
            "--anchor-log",
            str(anchor_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["errors"] == [
        "daily-anchors.jsonl line 2: previous_anchor_hash does not match line 1"
    ]


def test_validate_artifact_index_accepts_matching_hashes_and_skips_self_entry(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{artifact_digest}` | yes |\n"
        f"| `ARTIFACT_INDEX.md` | Self register. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == []


def test_parse_markdown_table_keeps_rows_with_escaped_pipe_in_purpose(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact with A\\|B table label. | `{artifact_digest}` | yes |\n",
        encoding="utf-8",
    )

    assert update_daily_rollup.parse_markdown_table(index, "tmp-lane") == [
        {
            "lane": "tmp-lane",
            "path": "artifact.txt",
            "purpose": "Example artifact with A|B table label.",
            "sha256": artifact_digest,
            "verified": "yes",
        }
    ]



def test_validate_artifact_index_reports_hash_mismatch(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        f"tmp-lane: artifact.txt hash mismatch: expected {'0' * 64}, got {hashlib.sha256(artifact.read_bytes()).hexdigest()}"
    ]


def test_validate_artifact_index_deduplicates_repeated_path_hash_rows(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    stale_digest = "0" * 64
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{stale_digest}` | yes |\n"
        f"| `artifact.txt` | Example artifact, repeated stale row. | `{stale_digest}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        f"tmp-lane: artifact.txt hash mismatch: expected {stale_digest}, got {hashlib.sha256(artifact.read_bytes()).hexdigest()}"
    ]


def test_validate_artifact_index_distinguishes_stale_historical_rows_from_current_match(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("current research bytes\n", encoding="utf-8")
    current_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    stale_digest = "0" * 64
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Historical stale artifact row. | `{stale_digest}` | yes |\n"
        f"| `artifact.txt` | Current artifact row. | `{current_digest}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        f"tmp-lane: artifact.txt has 1 stale historical hash row; current file matches {current_digest}; stale expected: {stale_digest}"
    ]


def test_validate_artifact_index_distinguishes_conflicting_rows_with_no_current_match(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("current research bytes\n", encoding="utf-8")
    actual_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    stale_a = "0" * 64
    stale_b = "1" * 64
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Historical stale artifact row. | `{stale_a}` | yes |\n"
        f"| `artifact.txt` | Another stale artifact row. | `{stale_b}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        f"tmp-lane: artifact.txt has 2 conflicting indexed hash rows; none match current file: expected one of {stale_a}, {stale_b}, got {actual_digest}"
    ]


def test_validate_artifact_index_reports_missing_file(tmp_path):
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `missing.txt` | Missing artifact. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        "tmp-lane: missing file indexed by ARTIFACT_INDEX.md: missing.txt"
    ]


def test_validate_artifact_index_reports_windows_style_parent_traversal(tmp_path):
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `..\\private.txt` | Unsafe artifact path. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )

    assert validate_artifact_index(index, tmp_path, "tmp-lane") == [
        "tmp-lane: unsafe indexed path in ARTIFACT_INDEX.md: ..\\private.txt"
    ]


def test_rollup_cli_validate_artifact_index_reports_ok_for_matching_hashes(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{artifact_digest}` | yes |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--validate-artifact-index",
            "--artifact-index",
            str(index),
            "--lane-root",
            str(tmp_path),
            "--lane",
            "tmp-lane",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"errors": [], "status": "ok"}


def test_rollup_cli_validate_artifact_index_reports_fail_for_mismatch(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("research bytes\n", encoding="utf-8")
    index = tmp_path / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--validate-artifact-index",
            "--artifact-index",
            str(index),
            "--lane-root",
            str(tmp_path),
            "--lane",
            "tmp-lane",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["errors"] == [
        f"tmp-lane: artifact.txt hash mismatch: expected {'0' * 64}, got {hashlib.sha256(artifact.read_bytes()).hexdigest()}"
    ]


def test_build_rollup_includes_missing_artifact_index_in_structured_diagnostics(tmp_path, monkeypatch):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "missing-lane"
    lane_root.mkdir()
    index_path = lane_root / "ARTIFACT_INDEX.md"
    monkeypatch.setattr(update_daily_rollup, "WORKSPACE", workspace)
    monkeypatch.setattr(update_daily_rollup, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(update_daily_rollup, "SIBLING_LANES", ["missing-lane"])

    rollup, _anchor, _rollup_path = update_daily_rollup.build_rollup(
        update_daily_rollup.datetime(2026, 5, 18, 19, 0, tzinfo=update_daily_rollup.timezone.utc),
        workspace / "daily-anchors.jsonl",
    )

    expected_message = f"missing-lane: missing artifact index: {index_path}"
    assert rollup["missing_indexes"] == [str(index_path)]
    assert rollup["artifact_index_errors"] == [expected_message]
    assert rollup["artifact_index_diagnostics"] == [
        {
            "category": "missing_artifact_index",
            "lane": "missing-lane",
            "path": str(index_path),
            "message": expected_message,
        }
    ]


def test_build_rollup_includes_structured_artifact_index_diagnostics(tmp_path, monkeypatch):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "model-card-x-ray"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("changed research bytes\n", encoding="utf-8")
    actual_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    expected_digest = "0" * 64
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{expected_digest}` | yes |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(update_daily_rollup, "WORKSPACE", workspace)
    monkeypatch.setattr(update_daily_rollup, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(update_daily_rollup, "SIBLING_LANES", ["model-card-x-ray"])

    rollup, _anchor, _rollup_path = update_daily_rollup.build_rollup(
        update_daily_rollup.datetime(2026, 5, 18, 19, 0, tzinfo=update_daily_rollup.timezone.utc),
        workspace / "daily-anchors.jsonl",
    )

    assert rollup["artifact_index_diagnostics"] == [
        {
            "category": "hash_mismatch",
            "lane": "model-card-x-ray",
            "path": "artifact.txt",
            "message": f"model-card-x-ray: artifact.txt hash mismatch: expected {expected_digest}, got {actual_digest}",
            "actual_sha256": actual_digest,
            "expected_sha256": expected_digest,
        }
    ]


def test_build_rollup_reports_artifact_index_diagnostics_without_dropping_entries(tmp_path, monkeypatch):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "model-card-x-ray"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("changed research bytes\n", encoding="utf-8")
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{'0' * 64}` | yes |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(update_daily_rollup, "WORKSPACE", workspace)
    monkeypatch.setattr(update_daily_rollup, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(update_daily_rollup, "SIBLING_LANES", ["model-card-x-ray"])

    rollup, anchor, rollup_path = update_daily_rollup.build_rollup(
        update_daily_rollup.datetime(2026, 5, 18, 19, 0, tzinfo=update_daily_rollup.timezone.utc),
        workspace / "daily-anchors.jsonl",
    )

    assert rollup_path == workspace / "daily-roll-up" / "2026-05-18.json"
    assert rollup["entry_count"] == 1
    assert anchor["entry_count"] == 1
    assert rollup["artifact_index_errors"] == [
        f"model-card-x-ray: artifact.txt hash mismatch: expected {'0' * 64}, got {hashlib.sha256(artifact.read_bytes()).hexdigest()}"
    ]


def test_rollup_cli_help_documents_hermetic_override_flags():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "Hermetic/replay options:" in result.stdout
    assert "--workspace" in result.stdout
    assert "--projects-root" in result.stdout
    assert "--sibling-lane" in result.stdout
    assert "Use these options for tests or local replay only" in result.stdout


def test_rollup_cli_help_documents_outgoing_ticket_options():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "Local outgoing-ticket options:" in result.stdout
    assert "--write-outgoing-tickets" in result.stdout
    assert "--outgoing-tickets-dir" in result.stdout
    assert "advisory tickets in the MIRROR workspace only" in result.stdout


def test_rollup_cli_help_documents_missing_index_diagnostic_boundary():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "Missing-index diagnostics:" in result.stdout
    assert "missing_artifact_index" in result.stdout
    assert "does not imply that the lane has no artifacts" in result.stdout



def test_rollup_cli_help_documents_local_anchor_validation_boundary():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "Local anchor validation:" in result.stdout
    assert "--validate-anchors" in result.stdout
    assert "checks JSONL hash-chain continuity only" in result.stdout
    assert "does not provide external timestamping" in result.stdout



def test_rollup_cli_help_documents_default_json_payload_fields():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "Default JSON output:" in result.stdout
    assert "missing_indexes" in result.stdout
    assert "outgoing_ticket_count" in result.stdout
    assert "outgoing_tickets" in result.stdout
    assert "reports local MIRROR roll-up metadata only" in result.stdout



def test_format_outgoing_ticket_groups_structured_diagnostics_by_category():
    ticket = update_daily_rollup.format_outgoing_ticket(
        "echo",
        [
            {
                "category": "hash_mismatch",
                "lane": "echo",
                "path": "PLAN.md",
                "message": "echo: PLAN.md hash mismatch: expected a, got b",
            },
            {
                "category": "stale_historical_hash_rows",
                "lane": "echo",
                "path": "CLAIMS.md",
                "message": "echo: CLAIMS.md has 2 stale historical hash rows; current file matches c; stale expected: a, b",
            },
            {
                "category": "hash_mismatch",
                "lane": "echo",
                "path": "SOURCES.md",
                "message": "echo: SOURCES.md hash mismatch: expected d, got e",
            },
        ],
        created="2026-05-18T21:30:00+03:00",
        rollup_path="daily-roll-up/2026-05-18.json",
        max_examples=2,
    )

    assert "# Outgoing MIRROR diagnostic ticket — echo" in ticket
    assert "Date: 2026-05-18T21:30:00+03:00" in ticket
    assert "- hash_mismatch: 2" in ticket
    assert "- stale_historical_hash_rows: 1" in ticket
    assert "Category guidance:" in ticket
    assert "hash_mismatch: current file bytes do not match the single indexed digest" in ticket
    assert "stale_historical_hash_rows: at least one row matches current bytes" in ticket
    assert "- [hash_mismatch] echo: PLAN.md hash mismatch: expected a, got b" in ticket
    assert "- [stale_historical_hash_rows] echo: CLAIMS.md has 2 stale historical hash rows" in ticket
    assert "daily-roll-up/2026-05-18.json" in ticket
    assert "They do not certify completeness" in ticket


def test_format_outgoing_ticket_summarizes_repeated_diagnostic_paths():
    ticket = update_daily_rollup.format_outgoing_ticket(
        "echo",
        [
            {
                "category": "hash_mismatch",
                "lane": "echo",
                "path": "paper.md",
                "message": "echo: paper.md hash mismatch: expected a, got b",
            },
            {
                "category": "conflicting_hash_rows",
                "lane": "echo",
                "path": "paper.md",
                "message": "echo: paper.md has 2 conflicting indexed hash rows",
            },
            {
                "category": "missing_file",
                "lane": "echo",
                "path": "notes/source.txt",
                "message": "echo: missing file indexed by ARTIFACT_INDEX.md: notes/source.txt",
            },
        ],
        created="2026-05-18T21:30:00+03:00",
        rollup_path="daily-roll-up/2026-05-18.json",
        max_examples=2,
    )

    assert "Most repeated paths:" in ticket
    assert "- `paper.md`: 2 diagnostics" in ticket
    assert "- `notes/source.txt`: 1 diagnostic" in ticket
    assert "Group repeated paths before escalating wording" in ticket



def test_format_outgoing_ticket_truncates_very_long_representative_messages():
    long_hash_list = ", ".join([f"{'a' * 63}{index:x}" for index in range(10)])
    ticket = update_daily_rollup.format_outgoing_ticket(
        "road2pq-shadow",
        [
            {
                "category": "conflicting_hash_rows",
                "lane": "road2pq-shadow",
                "path": "CLAIMS.md",
                "message": (
                    "road2pq-shadow: CLAIMS.md has 10 conflicting indexed hash rows; "
                    f"none match current file: expected one of {long_hash_list}, got {'b' * 64}"
                ),
            }
        ],
        created="2026-05-18T21:30:00+03:00",
        rollup_path="daily-roll-up/2026-05-18.json",
    )

    representative_lines = [line for line in ticket.splitlines() if line.startswith("- [conflicting_hash_rows]")]
    assert len(representative_lines) == 1
    assert len(representative_lines[0]) <= update_daily_rollup.MAX_TICKET_DIAGNOSTIC_LINE_LENGTH
    assert representative_lines[0].endswith("…")
    assert "additional diagnostics recorded" not in ticket



def test_format_outgoing_ticket_marks_lane_resolved_when_no_diagnostics():
    ticket = update_daily_rollup.format_outgoing_ticket(
        "model-card-x-ray",
        [],
        created="2026-05-18T21:30:00+03:00",
        rollup_path="daily-roll-up/2026-05-18.json",
    )

    assert "Status: resolved for this roll-up" in ticket
    assert "No structured artifact-index diagnostics were observed for this lane" in ticket



def test_format_outgoing_ticket_explains_missing_index_boundary():
    ticket = update_daily_rollup.format_outgoing_ticket(
        "pki-atlas-trusted-lists",
        [
            {
                "category": "missing_artifact_index",
                "lane": "pki-atlas-trusted-lists",
                "path": "/tmp/projects/pki-atlas-trusted-lists/ARTIFACT_INDEX.md",
                "message": "pki-atlas-trusted-lists: missing artifact index: /tmp/projects/pki-atlas-trusted-lists/ARTIFACT_INDEX.md",
            }
        ],
        created="2026-05-18T21:45:00+03:00",
        rollup_path="daily-roll-up/2026-05-18.json",
    )

    assert "- missing_artifact_index: 1" in ticket
    assert "the lane artifact index was not available for this roll-up" in ticket
    assert "does not imply the lane has no artifacts" in ticket
    assert "does not certify lane completeness" in ticket



def test_rollup_cli_default_output_includes_structured_artifact_index_diagnostics(tmp_path):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "model-card-x-ray"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("changed research bytes\n", encoding="utf-8")
    actual_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    expected_digest = "0" * 64
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{expected_digest}` | yes |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "model-card-x-ray",
            "--anchor-log",
            str(workspace / "daily-anchors.jsonl"),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    expected_message = f"model-card-x-ray: artifact.txt hash mismatch: expected {expected_digest}, got {actual_digest}"
    assert payload["artifact_index_errors"] == [expected_message]
    fixture = json.loads(
        (ROOT / "examples/roll-up-cli-payload/default-output-required-fields.json").read_text(encoding="utf-8")
    )
    assert fixture["schema"] == "mirror.roll-up-cli-payload-fixture.v0.1"
    assert set(fixture["required_fields"]) == set(payload)
    assert "do not certify sibling-lane completeness" in fixture["safe_interpretation"]
    assert payload["artifact_index_diagnostics"] == [
        {
            "category": "hash_mismatch",
            "lane": "model-card-x-ray",
            "path": "artifact.txt",
            "message": expected_message,
            "actual_sha256": actual_digest,
            "expected_sha256": expected_digest,
        }
    ]
    rollup_path = workspace / payload["rollup_path"]
    rollup_payload = json.loads(rollup_path.read_text(encoding="utf-8"))
    assert rollup_payload["artifact_index_diagnostics"] == payload["artifact_index_diagnostics"]
    assert payload["diagnostic_summary"] == {
        "total": 1,
        "by_category": {"hash_mismatch": 1},
        "by_lane": {"model-card-x-ray": 1},
    }
    assert rollup_payload["diagnostic_summary"] == payload["diagnostic_summary"]


def test_rollup_cli_compact_output_omits_high_volume_diagnostic_arrays(tmp_path):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "model-card-x-ray"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("changed research bytes\n", encoding="utf-8")
    expected_digest = "0" * 64
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{expected_digest}` | yes |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "model-card-x-ray",
            "--anchor-log",
            str(workspace / "daily-anchors.jsonl"),
            "--compact-output",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "artifact_index_errors" not in payload
    assert "artifact_index_diagnostics" not in payload
    assert payload["artifact_index_error_count"] == 1
    assert payload["artifact_index_diagnostic_count"] == 1
    assert payload["diagnostic_summary"] == {
        "total": 1,
        "by_category": {"hash_mismatch": 1},
        "by_lane": {"model-card-x-ray": 1},
    }
    rollup_payload = json.loads((workspace / payload["rollup_path"]).read_text(encoding="utf-8"))
    assert len(rollup_payload["artifact_index_diagnostics"]) == 1


def test_rollup_cli_help_documents_compact_output_boundary():
    result = subprocess.run(
        [sys.executable, str(ROOT / "update_daily_rollup.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert "--compact-output" in result.stdout
    assert "log-safe summaries" in result.stdout
    assert "omit high-volume diagnostic arrays" in result.stdout


def test_rollup_cli_writes_outgoing_tickets_from_structured_diagnostics(tmp_path):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "echo"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("changed research bytes\n", encoding="utf-8")
    expected_digest = "0" * 64
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{expected_digest}` | yes |\n",
        encoding="utf-8",
    )
    ticket_dir = workspace / "outgoing-tickets"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "echo",
            "--anchor-log",
            str(workspace / "daily-anchors.jsonl"),
            "--write-outgoing-tickets",
            "--outgoing-tickets-dir",
            str(ticket_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ticket_path = ticket_dir / "echo.md"
    assert payload["outgoing_tickets"] == [str(ticket_path)]
    ticket = ticket_path.read_text(encoding="utf-8")
    assert "# Outgoing MIRROR diagnostic ticket — echo" in ticket
    assert "- hash_mismatch: 1" in ticket
    assert "Roll-up: `daily-roll-up/" in ticket
    assert "They do not certify completeness" in ticket


def test_rollup_cli_writes_resolved_outgoing_ticket_without_assurance_language(tmp_path):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    lane_root = projects_root / "echo"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("stable research bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    index = lane_root / "ARTIFACT_INDEX.md"
    index.write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{artifact_digest}` | yes |\n",
        encoding="utf-8",
    )
    ticket_dir = workspace / "outgoing-tickets"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "echo",
            "--anchor-log",
            str(workspace / "daily-anchors.jsonl"),
            "--write-outgoing-tickets",
            "--outgoing-tickets-dir",
            str(ticket_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ticket_path = ticket_dir / "echo.md"
    assert payload["artifact_index_diagnostics"] == []
    assert payload["outgoing_ticket_count"] == 1
    assert payload["outgoing_tickets"] == [str(ticket_path)]
    ticket = ticket_path.read_text(encoding="utf-8")
    assert "Status: resolved for this roll-up" in ticket
    assert "does not certify completeness" in ticket
    assert "qualified electronic signature" not in ticket
    assert "qualified timestamp" not in ticket



def make_workspace_override_fixture(tmp_path):
    tool_root = tmp_path / "tool-root"
    tool_root.mkdir()
    script = tool_root / "update_daily_rollup.py"
    script.write_text((ROOT / "update_daily_rollup.py").read_text(encoding="utf-8"), encoding="utf-8")
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    lane_root = projects_root / "echo"
    lane_root.mkdir()
    artifact = lane_root / "artifact.txt"
    artifact.write_text("stable research bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (lane_root / "ARTIFACT_INDEX.md").write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `artifact.txt` | Example artifact. | `{artifact_digest}` | yes |\n",
        encoding="utf-8",
    )
    return tool_root, script, workspace, projects_root


def test_rollup_cli_default_anchor_log_tracks_workspace_override(tmp_path):
    tool_root, script, workspace, projects_root = make_workspace_override_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "echo",
        ],
        cwd=tool_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert (workspace / "daily-anchors.jsonl").is_file()
    assert not (tool_root / "daily-anchors.jsonl").exists()


def test_rollup_cli_default_outgoing_tickets_dir_tracks_workspace_override(tmp_path):
    tool_root, script, workspace, projects_root = make_workspace_override_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "echo",
            "--write-outgoing-tickets",
        ],
        cwd=tool_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    workspace_ticket = workspace / "outgoing-tickets" / "echo.md"
    assert payload["outgoing_tickets"] == [str(workspace_ticket)]
    assert workspace_ticket.is_file()
    assert not (tool_root / "outgoing-tickets").exists()


def test_rollup_cli_default_artifact_index_validation_tracks_workspace_override(tmp_path):
    tool_root, script, workspace, _projects_root = make_workspace_override_fixture(tmp_path)
    artifact = workspace / "local-artifact.txt"
    artifact.write_text("workspace-local artifact bytes\n", encoding="utf-8")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (workspace / "ARTIFACT_INDEX.md").write_text(
        "# Artifact Index\n\n"
        "| Path | Purpose | SHA-256 | Verified |\n"
        "|---|---|---|---|\n"
        f"| `local-artifact.txt` | Workspace-local artifact. | `{artifact_digest}` | yes |\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(workspace),
            "--validate-artifact-index",
        ],
        cwd=tool_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"errors": [], "status": "ok"}


def test_rollup_cli_writes_missing_index_outgoing_ticket_with_count(tmp_path):
    workspace = tmp_path / "mirror"
    workspace.mkdir()
    (workspace / "daily-roll-up").mkdir()
    projects_root = tmp_path
    missing_lane_root = projects_root / "pki-atlas-trusted-lists"
    missing_lane_root.mkdir()
    ticket_dir = workspace / "outgoing-tickets"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "update_daily_rollup.py"),
            "--workspace",
            str(workspace),
            "--projects-root",
            str(projects_root),
            "--sibling-lane",
            "pki-atlas-trusted-lists",
            "--anchor-log",
            str(workspace / "daily-anchors.jsonl"),
            "--write-outgoing-tickets",
            "--outgoing-tickets-dir",
            str(ticket_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    ticket_path = ticket_dir / "pki-atlas-trusted-lists.md"
    expected_message = f"pki-atlas-trusted-lists: missing artifact index: {missing_lane_root / 'ARTIFACT_INDEX.md'}"
    assert payload["outgoing_ticket_count"] == 1
    assert payload["outgoing_tickets"] == [str(ticket_path)]
    assert payload["missing_indexes"] == [str(missing_lane_root / "ARTIFACT_INDEX.md")]
    assert payload["artifact_index_errors"] == [expected_message]
    assert payload["artifact_index_diagnostics"] == [
        {
            "category": "missing_artifact_index",
            "lane": "pki-atlas-trusted-lists",
            "path": str(missing_lane_root / "ARTIFACT_INDEX.md"),
            "message": expected_message,
        }
    ]
    ticket = ticket_path.read_text(encoding="utf-8")
    assert "- missing_artifact_index: 1" in ticket
    assert "does not imply the lane has no artifacts" in ticket
    assert "does not certify lane completeness" in ticket
