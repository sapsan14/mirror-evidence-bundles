import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


def run_bundle(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "bundle.py"), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_verify(bundle_dir):
    return subprocess.run(
        [sys.executable, str(ROOT / "verify.py"), str(bundle_dir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_current_bundle(tmp_path):
    artifact = tmp_path / "artifact.md"
    source = tmp_path / "source.txt"
    bundle_dir = tmp_path / "artifact.md.bundle"
    artifact.write_text("# Artifact\n\nA cautious claim.\n", encoding="utf-8")
    source.write_text("source evidence\n", encoding="utf-8")

    result = run_bundle(
        str(artifact),
        "--output",
        str(bundle_dir),
        "--source",
        str(source),
        "--claim",
        "A cautious claim.",
        "--evidence",
        "S1:source evidence",
    )
    assert result.returncode == 0, result.stderr
    return bundle_dir


def payload(result):
    assert result.stderr == ""
    return json.loads(result.stdout)


def test_verify_accepts_current_bundle_cli_output(tmp_path):
    bundle_dir = make_current_bundle(tmp_path)

    result = run_verify(bundle_dir)

    assert result.returncode == 0
    assert payload(result) == {"errors": [], "status": "ok"}


def test_current_bundle_manifest_and_claims_are_schema_valid(tmp_path):
    bundle_dir = make_current_bundle(tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    manifest_schema = json.loads((ROOT / "schema" / "manifest.schema.json").read_text(encoding="utf-8"))
    claims_schema = json.loads((ROOT / "schema" / "claims.schema.json").read_text(encoding="utf-8"))

    manifest_errors = sorted(Draft7Validator(manifest_schema).iter_errors(manifest), key=lambda error: list(error.path))
    claims_errors = sorted(Draft7Validator(claims_schema).iter_errors(claims), key=lambda error: list(error.path))

    assert manifest_errors == []
    assert claims_errors == []


def test_verify_reports_current_bundle_source_hash_mismatch(tmp_path):
    bundle_dir = make_current_bundle(tmp_path)
    source_path = next((bundle_dir / "sources").glob("S1-*.txt"))
    source_path.write_text("tampered source evidence\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    result_payload = payload(result)
    assert result_payload["status"] == "fail"
    assert any("hash mismatch" in error and str(source_path.relative_to(bundle_dir)) in error for error in result_payload["errors"])


def test_verify_reports_current_bundle_missing_source_file(tmp_path):
    bundle_dir = make_current_bundle(tmp_path)
    source_path = next((bundle_dir / "sources").glob("S1-*.txt"))
    source_path.unlink()

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    result_payload = payload(result)
    assert result_payload["status"] == "fail"
    assert f"missing file: {source_path.relative_to(bundle_dir)}" in result_payload["errors"]


def test_verify_reports_current_bundle_unknown_claim_risk_level(tmp_path):
    bundle_dir = make_current_bundle(tmp_path)
    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["risk"] = "extreme"
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    result_payload = payload(result)
    assert result_payload["status"] == "fail"
    assert any(
        "claims.json.claims.0.risk" in error and "extreme" in error
        for error in result_payload["errors"]
    )
