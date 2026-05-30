import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


def test_signed_transition_profile_cli_writes_deterministic_schema_valid_payload(tmp_path):
    unsigned_bundle = tmp_path / "manifest.json"
    reviewer_report = tmp_path / "reviewer-report.json"
    output = tmp_path / "signed-transition.json"
    unsigned_bundle.write_text('{"schema":"mirror.bundle.v0.1"}\n', encoding="utf-8")
    reviewer_report.write_text('{"schema":"mirror.reviewer-report-packet.v0.1"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "signed_transition_profile.py"),
            "--unsigned-bundle",
            str(unsigned_bundle),
            "--reviewer-report-packet",
            str(reviewer_report),
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
    schema = json.loads((ROOT / "schema/signed-transition-profile.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(payload), key=lambda error: list(error.path))

    assert errors == []
    assert stdout_payload == payload
    assert payload["schema"] == "mirror.signed-transition-profile.v0.1"
    assert payload["unsigned_bundle"] == {
        "path": str(unsigned_bundle),
        "sha256": f"sha256:{sha256(unsigned_bundle.read_bytes()).hexdigest()}",
        "status": "unsigned-local",
    }
    assert payload["reviewer_report_packet"] == {
        "path": str(reviewer_report),
        "sha256": f"sha256:{sha256(reviewer_report.read_bytes()).hexdigest()}",
        "status": "derived-local",
    }
    assert payload["signing_transition"] == {
        "external_timestamp": None,
        "mutation_policy": "record exact digests without rewriting unsigned bundle or reviewer report packet",
        "operator_controlled": True,
        "profile": "future-operator-controlled-eatf-compatible-profile",
        "signature_present": False,
    }
    assert payload["unresolved_assumptions"] == [
        "No external timestamp is present in this MIRROR lane fixture.",
        "Any later signature would need to cover these exact digests or state the reason for divergence.",
    ]
    assert "does not certify" in payload["safe_interpretation"]
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_signed_transition_profile_cli_reports_missing_inputs_as_json_failure(tmp_path):
    missing = tmp_path / "missing-manifest.json"
    reviewer_report = tmp_path / "reviewer-report.json"
    output = tmp_path / "signed-transition.json"
    reviewer_report.write_text("{}\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "signed_transition_profile.py"),
            "--unsigned-bundle",
            str(missing),
            "--reviewer-report-packet",
            str(reviewer_report),
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
    assert payload["errors"] == [f"missing unsigned bundle: {missing}"]
    assert "does not certify" in payload["safe_interpretation"]
    assert not output.exists()


def test_signed_transition_profile_missing_input_fixture_matches_cli_failure(tmp_path):
    missing = Path("examples/signed-transition-profile/missing-manifest.json")
    reviewer_report = tmp_path / "reviewer-report.json"
    output = tmp_path / "signed-transition.json"
    reviewer_report.write_text("{}\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "signed_transition_profile.py"),
            "--unsigned-bundle",
            str(missing),
            "--reviewer-report-packet",
            str(reviewer_report),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    fixture = json.loads((ROOT / "examples/signed-transition-profile/missing-input-failure.json").read_text(encoding="utf-8"))
    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert fixture == payload
    assert fixture["status"] == "fail"
    assert fixture["errors"] == ["missing unsigned bundle: examples/signed-transition-profile/missing-manifest.json"]
    assert "does not certify" in fixture["safe_interpretation"]


def test_signed_transition_profile_missing_reviewer_fixture_matches_cli_failure(tmp_path):
    unsigned_bundle = tmp_path / "manifest.json"
    missing = Path("examples/signed-transition-profile/missing-reviewer-report.json")
    output = tmp_path / "signed-transition.json"
    unsigned_bundle.write_text("{}\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "signed_transition_profile.py"),
            "--unsigned-bundle",
            str(unsigned_bundle),
            "--reviewer-report-packet",
            str(missing),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    fixture = json.loads((ROOT / "examples/signed-transition-profile/missing-reviewer-failure.json").read_text(encoding="utf-8"))
    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert fixture == payload
    assert fixture["status"] == "fail"
    assert fixture["errors"] == ["missing reviewer report packet: examples/signed-transition-profile/missing-reviewer-report.json"]
    assert "does not certify" in fixture["safe_interpretation"]
