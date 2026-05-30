import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


def run_verify(bundle_dir: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "verify.py"), str(bundle_dir)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def load_status(result: subprocess.CompletedProcess) -> dict:
    assert result.stderr == ""
    return json.loads(result.stdout)


def test_known_good_example_has_schema_valid_manifest_and_verifies_ok():
    bundle_dir = ROOT / "examples" / "good" / "artifact.md.bundle"
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))

    assert manifest["schema"] == "urn:tyche:mirror:bundle:0.1"
    assert set(manifest) >= {
        "schema",
        "schema_version",
        "bundle_created_at",
        "created_by",
        "artifact",
        "sources",
        "claims_file",
        "attestation",
        "verification",
    }
    assert manifest["schema_version"] == "0.1.0"
    assert manifest["created_by"]["affiliation"] == "Tyche Institute, Tallinn, Estonia"
    assert manifest["artifact"]["sha256"]["algorithm"] == "SHA-256"
    assert manifest["sources"][0]["path"] == "sources/source-1.txt"
    assert manifest["sources"][0]["sha256"]["algorithm"] == "SHA-256"
    assert manifest["attestation"]["signed"] is False
    assert claims["schema"] == "urn:tyche:mirror:claims:0.1"
    assert claims["schema_version"] == "0.1.0"

    result = run_verify(bundle_dir)
    assert result.returncode == 0
    assert load_status(result) == {"errors": [], "status": "ok"}


def test_good_success_payload_matches_verifier_output_fixture():
    bundle_dir = ROOT / "examples" / "good" / "artifact.md.bundle"
    fixture_path = ROOT / "examples" / "verifier-output" / "good-success.json"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    expected_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert payload == expected_payload
    assert payload == {"errors": [], "status": "ok"}
    assert "failure_kinds" not in payload
    assert "note" not in payload


def test_known_bad_hash_example_reports_hash_mismatch():
    bundle_dir = ROOT / "examples" / "bad-hash" / "artifact.md.bundle"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any("hash mismatch for sources/source-1.txt" in error for error in payload["errors"])


def test_known_bad_unsafe_evidence_example_reports_unsafe_pointer():
    bundle_dir = ROOT / "examples" / "bad-unsafe-evidence" / "artifact.md.bundle"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: unsafe evidence pointer ../outside.txt"
        in payload["errors"]
    )




def test_known_bad_artifact_traversal_example_reports_unsafe_artifact_pointer():
    bundle_dir = ROOT / "examples" / "bad-artifact-traversal" / "artifact.md.bundle"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: unsafe evidence pointer artifact:../outside.md#claim"
        in payload["errors"]
    )


def test_artifact_traversal_fixture_is_schema_valid_but_verifier_failing():
    bundle_dir = ROOT / "examples" / "bad-artifact-traversal" / "artifact.md.bundle"
    claims_schema = json.loads((ROOT / "schema" / "claims.schema.json").read_text(encoding="utf-8"))
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))

    schema_errors = sorted(
        Draft7Validator(claims_schema).iter_errors(claims),
        key=lambda error: list(error.path),
    )
    result = run_verify(bundle_dir)
    payload = load_status(result)

    assert schema_errors == []
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any("unsafe evidence pointer artifact:../outside.md#claim" in error for error in payload["errors"])


def test_artifact_traversal_fixture_readme_documents_schema_verifier_boundary():
    readme = (ROOT / "examples" / "bad-artifact-traversal" / "README.md").read_text(encoding="utf-8")

    assert "schema-valid but verifier-failing" in readme
    assert "claims.schema.json" in readme
    assert "verify.py" in readme
    assert "does not certify" in readme


def test_known_bad_unsafe_assurance_example_reports_public_claim_wording_guardrail():
    bundle_dir = ROOT / "examples" / "bad-unsafe-assurance" / "artifact.md.bundle"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any(
        "claims.json.claims[0].text: must not use unsafe assurance language: certifies compliance" in error
        for error in payload["errors"]
    )
    assert any(
        "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in error
        for error in payload["errors"]
    )


def test_unsafe_assurance_failure_payload_is_classified_as_policy_guardrail():
    bundle_dir = ROOT / "examples" / "bad-unsafe-assurance" / "artifact.md.bundle"
    fixture_path = ROOT / "examples" / "verifier-output" / "bad-unsafe-assurance-policy-failure.json"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    expected_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert result.returncode == 1
    assert payload == expected_payload
    assert payload["failure_kinds"] == ["policy_guardrail"]
    assert payload["note"] == (
        "failure_kinds distinguish deterministic local integrity/structure failures "
        "from policy guardrail failures; they do not certify claim truth or publication readiness"
    )


def test_verifier_output_fixture_readme_documents_failure_kind_boundary():
    readme = (ROOT / "examples" / "verifier-output" / "README.md").read_text(encoding="utf-8")

    assert "good-success.json" in readme
    assert "status: \"ok\"" in readme
    assert "success payloads intentionally omit `failure_kinds` and `note`" in readme
    assert "bad-unsafe-assurance-policy-failure.json" in readme
    assert "bad-hash-integrity-failure.json" in readme
    assert "mixed-policy-and-integrity-failure.json" in readme
    assert "failure_kinds" in readme
    assert "integrity_or_structure" in readme
    assert "policy_guardrail" in readme
    assert "does not certify claim truth" in readme
    assert "publication readiness" in readme
    assert "legal/regulatory" in readme


def test_schema_documents_mixed_failure_kind_fixture_boundary():
    schema_doc = (ROOT / "SCHEMA.md").read_text(encoding="utf-8")

    assert "good-success.json" in schema_doc
    assert "green replay shape without failure-only triage fields" in schema_doc
    assert "mixed-policy-and-integrity-failure.json" in schema_doc
    assert "mixed failure payload" in schema_doc or "single red result may carry both" in schema_doc
    assert "not misconduct findings" in schema_doc


def test_schema_documents_success_payload_consumer_boundary():
    schema_doc = (ROOT / "SCHEMA.md").read_text(encoding="utf-8")

    assert "Success payloads are intentionally minimal" in schema_doc
    assert "Consumers must not infer claim truth" in schema_doc
    assert "absence of `failure_kinds`" in schema_doc
    assert "does not make success an endorsement" in schema_doc


def test_mixed_failure_payload_matches_policy_and_integrity_output_fixture(tmp_path):
    source_bundle = ROOT / "examples" / "bad-unsafe-assurance" / "artifact.md.bundle"
    bundle_dir = tmp_path / "artifact.md.bundle"
    fixture_path = ROOT / "examples" / "verifier-output" / "mixed-policy-and-integrity-failure.json"
    subprocess.run(["cp", "-R", str(source_bundle), str(bundle_dir)], check=True)
    (bundle_dir / "sources" / "source-1.txt").write_text("tampered source evidence\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    payload = load_status(result)
    expected_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert result.returncode == 1
    assert payload == expected_payload
    assert payload["failure_kinds"] == ["integrity_or_structure", "policy_guardrail"]


def test_bad_hash_failure_payload_matches_integrity_output_fixture():
    bundle_dir = ROOT / "examples" / "bad-hash" / "artifact.md.bundle"
    fixture_path = ROOT / "examples" / "verifier-output" / "bad-hash-integrity-failure.json"

    result = run_verify(bundle_dir)

    payload = load_status(result)
    expected_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert result.returncode == 1
    assert payload == expected_payload
    assert payload["failure_kinds"] == ["integrity_or_structure"]


def test_unsafe_assurance_fixture_is_schema_valid_but_verifier_failing():
    bundle_dir = ROOT / "examples" / "bad-unsafe-assurance" / "artifact.md.bundle"
    claims_schema = json.loads((ROOT / "schema" / "claims.schema.json").read_text(encoding="utf-8"))
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))

    schema_errors = sorted(
        Draft7Validator(claims_schema).iter_errors(claims),
        key=lambda error: list(error.path),
    )
    result = run_verify(bundle_dir)
    payload = load_status(result)

    assert schema_errors == []
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any("must not use unsafe assurance language: certifies compliance" in error for error in payload["errors"])


def test_unsafe_assurance_fixture_readme_documents_claim_wording_boundary():
    readme = (ROOT / "examples" / "bad-unsafe-assurance" / "README.md").read_text(encoding="utf-8")

    assert "schema-valid but verifier-failing" in readme
    assert "certifies compliance" in readme
    assert "verify.py" in readme
    assert "does not certify" in readme


def test_verifier_reports_missing_source_file_on_example_copy(tmp_path):
    source_bundle = ROOT / "examples" / "good" / "artifact.md.bundle"
    bundle_dir = tmp_path / "artifact.md.bundle"
    subprocess.run(["cp", "-R", str(source_bundle), str(bundle_dir)], check=True)
    (bundle_dir / "sources" / "source-1.txt").unlink()

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any("missing file: sources/source-1.txt" in error for error in payload["errors"])


def test_verifier_reports_unknown_claim_risk_on_example_copy(tmp_path):
    source_bundle = ROOT / "examples" / "good" / "artifact.md.bundle"
    bundle_dir = tmp_path / "artifact.md.bundle"
    subprocess.run(["cp", "-R", str(source_bundle), str(bundle_dir)], check=True)
    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["risk"] = "extreme"
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    payload = load_status(result)
    assert result.returncode == 1
    assert payload["status"] == "fail"
    assert any(
        "claims.json.claims.0.risk" in error and "extreme" in error
        for error in payload["errors"]
    )
