import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_report_packet_cli_writes_schema_valid_packet_for_good_bundle(tmp_path):
    output = tmp_path / "reviewer-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "reviewer_report_packet.py"),
            "--bundle-dir",
            str(ROOT / "examples/good/artifact.md.bundle"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(output.read_text(encoding="utf-8"))
    stdout_payload = json.loads(result.stdout)
    schema = json.loads((ROOT / "schema/reviewer-report-packet.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(payload), key=lambda error: list(error.path))

    assert errors == []
    assert stdout_payload == payload
    assert payload["schema"] == "mirror.reviewer-report-packet.v0.1"
    assert payload["bundle"] == "examples/good/artifact.md.bundle"
    assert payload["verifier_status"] == "ok"
    assert payload["reproducible_local_facts"] == [
        {
            "kind": "artifact_hash",
            "path": "artifact.md",
            "message": "The artifact digest matched the manifest during local verification.",
        },
        {
            "kind": "source_hash",
            "path": "sources/source-1.txt",
            "message": "1 bundled source file digest matched the manifest during local verification.",
        },
        {
            "kind": "schema_validation",
            "path": "claims.json",
            "message": "The local claims file matched the supported MIRROR v0.1 claim structure.",
        },
    ]
    assert payload["review_prompts"] == [
        {
            "kind": "claim_scope",
            "claim_id": "claim-1",
            "message": "Check whether the cautious wording remains aligned with the artifact text before citation.",
        }
    ]
    assert [item["kind"] for item in payload["out_of_scope_questions"]] == [
        "authorship",
        "external_time",
        "legal_compliance",
        "source_authority",
        "scholarly_quality",
    ]
    assert "does not certify" in payload["safe_interpretation"]
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_reviewer_report_packet_cli_reports_missing_bundle_as_json_failure(tmp_path):
    missing_bundle = tmp_path / "missing.bundle"
    output = tmp_path / "reviewer-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "reviewer_report_packet.py"),
            "--bundle-dir",
            str(missing_bundle),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["errors"] == ["missing bundle directory: omitted-private-workspace-path"]
    assert "does not certify" in payload["safe_interpretation"]
    assert not output.exists()


def test_reviewer_report_packet_missing_bundle_fixture_matches_cli_failure():
    missing_bundle = ROOT / "examples/reviewer-report-packet/missing.bundle"
    output = ROOT / "examples/reviewer-report-packet/unused-output.json"
    fixture = json.loads((ROOT / "examples/reviewer-report-packet/missing-bundle-failure.json").read_text(encoding="utf-8"))

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "reviewer_report_packet.py"),
            "--bundle-dir",
            str(missing_bundle),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == fixture
    assert fixture["status"] == "fail"
    assert fixture["errors"] == ["missing bundle directory: examples/reviewer-report-packet/missing.bundle"]
    assert "does not certify" in fixture["safe_interpretation"]
    assert not output.exists()
