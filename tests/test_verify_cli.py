import hashlib
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


def make_good_bundle(tmp_path):
    artifact = tmp_path / "artifact.md"
    source = tmp_path / "source.txt"
    out_dir = tmp_path / "artifact.md.bundle"
    artifact.write_text("# Artifact\n\nA cautious claim.\n", encoding="utf-8")
    source.write_text("source evidence\n", encoding="utf-8")
    result = run_bundle(
        str(artifact),
        "--output",
        str(out_dir),
        "--source",
        str(source),
        "--claim",
        "A cautious claim.",
        "--evidence",
        "sources/source-1.txt",
    )
    assert result.returncode == 0, result.stderr
    return out_dir


def parse_verify(result):
    assert result.stderr == ""
    return json.loads(result.stdout)


def test_verify_cli_missing_bundle_output_validates_against_verifier_output_schema(tmp_path):
    result = run_verify(tmp_path / "missing.bundle")

    assert result.returncode == 1
    payload = parse_verify(result)
    schema = json.loads((ROOT / "schema" / "verifier-output.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    assert sorted(validator.iter_errors(payload), key=lambda error: list(error.path)) == []
    assert payload["status"] == "fail"
    assert payload["failure_kinds"] == ["integrity_or_structure"]
    assert "bundle directory not found" in payload["errors"][0]
    assert "do not certify claim truth or publication readiness" in payload["note"]


def test_verify_accepts_schema_v010_bundle_created_by_bundle_cli(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)

    result = run_verify(bundle_dir)

    assert result.returncode == 0
    assert parse_verify(result) == {"errors": [], "status": "ok"}


def test_verify_reports_artifact_hash_mismatch(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    (bundle_dir / "artifact.md").write_text("# Tampered\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert any("hash mismatch for artifact.md" in error for error in payload["errors"])


def test_verify_reports_missing_source_file(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    (bundle_dir / "sources" / "source-1.txt").unlink()

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "missing file: sources/source-1.txt" in payload["errors"]


def test_verify_reports_missing_required_notes_file(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    (bundle_dir / "notes.md").unlink()

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "missing file: notes.md" in payload["errors"]


def test_verify_reports_claims_hash_mismatch(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims["claims"][0]["text"] = "Tampered claim."
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert any("hash mismatch for claims.json" in error for error in payload["errors"])


def test_verify_reports_unknown_claim_risk_level_from_schema_validation(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims["claims"][0]["risk"] = "extreme"
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert any("claims.json" in error and "risk" in error and "extreme" in error for error in payload["errors"])


def test_verify_reports_duplicate_claim_ids_deterministically(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    claims_path = bundle_dir / "claims.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    duplicate = dict(claims["claims"][0])
    duplicate["text"] = "A second claim reusing the same local identifier."
    claims["claims"].append(duplicate)
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[1].id: duplicate claim id C-0001 first defined at claims.json.claims[0].id" in payload["errors"]


def test_verify_reports_duplicate_manifest_source_ids_deterministically(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    duplicate = dict(manifest["sources"][0])
    duplicate["path"] = "sources/source-duplicate.txt"
    (bundle_dir / "sources" / "source-duplicate.txt").write_text("source evidence\n", encoding="utf-8")
    manifest["sources"].append(duplicate)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[1].id: duplicate source id S-0001 first defined at manifest.sources[0].id" in payload["errors"]


def test_verify_reports_duplicate_manifest_source_paths_deterministically(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    duplicate = dict(manifest["sources"][0])
    duplicate["id"] = "S-0002"
    manifest["sources"].append(duplicate)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[1].path: duplicate source path sources/source-1.txt first defined at manifest.sources[0].path" in payload["errors"]


def test_verify_reports_duplicate_manifest_source_paths_after_normalization(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    duplicate = dict(manifest["sources"][0])
    duplicate["id"] = "S-0002"
    duplicate["path"] = "sources/./source-1.txt"
    manifest["sources"].append(duplicate)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "manifest.sources[1].path: duplicate normalized source path sources/source-1.txt "
        "first defined at manifest.sources[0].path"
    ) in payload["errors"]


def test_verify_reports_duplicate_manifest_source_paths_after_normalization_when_normalized_path_seen_second(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["sources"][0]["path"] = "sources/./source-1.txt"
    duplicate = dict(manifest["sources"][0])
    duplicate["id"] = "S-0002"
    duplicate["path"] = "sources/source-1.txt"
    manifest["sources"].append(duplicate)
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "manifest.sources[1].path: duplicate normalized source path sources/source-1.txt "
        "first defined at manifest.sources[0].path"
    ) in payload["errors"]


def test_verify_reports_manifest_source_path_with_parent_segment(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    nested = bundle_dir / "sources" / "nested"
    nested.mkdir()
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["sources"][0]["path"] = "sources/nested/../source-1.txt"
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].path: source records must not contain parent-directory segments" in payload["errors"]


def test_verify_reports_unsafe_artifact_scheme_evidence_pointer(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0]["source_id"] = None
    claims["claims"][0]["evidence"][0]["pointer"] = "artifact:../outside.md#claim"
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].evidence[0]: unsafe evidence pointer artifact:../outside.md#claim" in payload["errors"]


def test_verify_accepts_normalized_artifact_pointer_matching_external_artifact_path(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact"]["path"] = "../artifact.md"

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": None, "pointer": "artifact:.././artifact.md#claim"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 0
    assert parse_verify(result) == {"errors": [], "status": "ok"}


def test_verify_reports_artifact_path_resolving_outside_bundle_parent(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    outside_artifact = tmp_path.parent / "outside-artifact.md"
    outside_artifact.write_text("# Outside artifact\n", encoding="utf-8")

    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact"]["path"] = "../../outside-artifact.md"
    manifest["artifact"]["sha256"]["value"] = hashlib.sha256(outside_artifact.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.artifact.path: must resolve inside the bundle directory or its parent artifact directory" in payload["errors"]


def test_verify_accepts_source_id_shorthand_evidence_pointer_generated_by_bundle_cli(tmp_path):
    artifact = tmp_path / "artifact.md"
    source = tmp_path / "source.txt"
    out_dir = tmp_path / "artifact.md.bundle"
    artifact.write_text("# Artifact\n\nA cautious claim.\n", encoding="utf-8")
    source.write_text("source evidence\n", encoding="utf-8")
    bundle_result = run_bundle(
        str(artifact),
        "--output",
        str(out_dir),
        "--source",
        str(source),
        "--claim",
        "A cautious claim.",
        "--evidence",
        "S-0001",
    )
    assert bundle_result.returncode == 0, bundle_result.stderr

    result = run_verify(out_dir)

    assert result.returncode == 0
    assert parse_verify(result) == {"errors": [], "status": "ok"}


def test_verify_reports_evidence_source_id_pointer_path_mismatch(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    second_source = bundle_dir / "sources" / "source-2.txt"
    second_source.write_text("different source evidence\n", encoding="utf-8")

    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    second_entry = dict(manifest["sources"][0])
    second_entry.update(
        {
            "id": "S-0002",
            "path": "sources/source-2.txt",
            "sha256": {
                "algorithm": "SHA-256",
                "value": hashlib.sha256(second_source.read_bytes()).hexdigest(),
            },
            "source_path": "source-2.txt",
            "title": "source-2.txt",
        }
    )
    manifest["sources"].append(second_entry)

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "sources/source-2.txt#quote"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: source_id S-0001 points to sources/source-1.txt "
        "but pointer references sources/source-2.txt"
    ) in payload["errors"]


def test_verify_accepts_source_id_pointer_path_after_simple_relative_normalization(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "sources/./source-1.txt#quote"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 0
    assert parse_verify(result) == {"errors": [], "status": "ok"}


def test_verify_reports_source_id_pointer_to_unlisted_source_path(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "sources/unlisted.txt#quote"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: source_id S-0001 points to sources/source-1.txt "
        "but pointer references unlisted source path sources/unlisted.txt"
    ) in payload["errors"]


def test_verify_reports_source_id_pointer_to_non_source_path(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "notes.md#method"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: source_id S-0001 points to sources/source-1.txt "
        "but pointer references non-source path notes.md"
    ) in payload["errors"]


def test_verify_reports_unlisted_source_path_pointer_without_source_id(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": None, "pointer": "sources/unlisted.txt#quote"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "claims.json.claims[0].evidence[0]: pointer references unlisted source path sources/unlisted.txt"
    ) in payload["errors"]


def test_verify_reports_external_scheme_evidence_pointer_without_source_id(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": None, "pointer": "https://example.org/source#quote"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].evidence[0]: unsupported external-scheme evidence pointer https://example.org/source#quote" in payload["errors"]


def test_verify_reports_duplicate_manifest_assumption_ids_deterministically(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(manifest["assumptions"][0])
    duplicate["text"] = "A second assumption reusing the same local identifier."
    manifest["assumptions"].append(duplicate)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.assumptions[2].id: duplicate assumption id A-0001 first defined at manifest.assumptions[0].id" in payload["errors"]


def test_verify_reports_duplicate_verification_semantics_from_schema_validation(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["verification"]["semantics"].append(manifest["verification"]["semantics"][0])
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert any(
        "manifest.json.verification.semantics" in error and "non-unique elements" in error
        for error in payload["errors"]
    )


def test_verify_reports_url_record_source_without_https_url(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["kind"] = "url_record"
    manifest["sources"][0].pop("url", None)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].url: url_record sources must include an HTTPS url with a host" in payload["errors"]


def test_verify_reports_local_file_source_without_source_path(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["kind"] = "local_file"
    manifest["sources"][0].pop("source_path", None)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].source_path: local_file sources must include a source_path" in payload["errors"]


def test_verify_reports_url_record_source_without_https_host(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["kind"] = "url_record"
    manifest["sources"][0]["url"] = "https://"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].url: url_record sources must include an HTTPS url with a host" in payload["errors"]


def make_url_record_bundle(tmp_path):
    artifact = tmp_path / "artifact.md"
    out_dir = tmp_path / "artifact.md.bundle"
    artifact.write_text("# Artifact\n\nA cautious URL-backed claim.\n", encoding="utf-8")
    result = run_bundle(
        str(artifact),
        "--output",
        str(out_dir),
        "--source",
        "https://example.org/source-a",
        "--claim",
        "A cautious URL-backed claim.",
        "--evidence",
        "sources/source-1.url.json",
    )
    assert result.returncode == 0, result.stderr
    return out_dir


def test_verify_reports_url_record_descriptor_url_mismatch(tmp_path):
    out_dir = make_url_record_bundle(tmp_path)

    descriptor_path = out_dir / "sources" / "source-1.url.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["url"] = "https://example.org/source-b"
    descriptor_path.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["sha256"]["value"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(out_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "manifest.sources[0].url: url_record descriptor url https://example.org/source-b "
        "does not match manifest url https://example.org/source-a"
    ) in payload["errors"]


def test_verify_reports_url_record_descriptor_accessed_at_mismatch(tmp_path):
    out_dir = make_url_record_bundle(tmp_path)

    descriptor_path = out_dir / "sources" / "source-1.url.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["accessed_at"] = "2000-01-01T00:00:00Z"
    descriptor_path.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["sha256"]["value"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(out_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "manifest.sources[0].accessed_at: url_record descriptor accessed_at 2000-01-01T00:00:00Z "
        f"does not match manifest accessed_at {manifest['sources'][0]['accessed_at']}"
    ) in payload["errors"]


def test_verify_reports_derived_note_source_without_notes_or_source_path(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["kind"] = "derived_note"
    manifest["sources"][0].pop("source_path", None)
    manifest["sources"][0].pop("notes", None)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert (
        "manifest.sources[0]: derived_note sources must include notes or source_path explaining derivation provenance"
    ) in payload["errors"]


def test_verify_reports_forbidden_named_employer_in_created_by_affiliation(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_by"]["affiliation"] = "Tyche Institute / ForbiddenCorp Estonia"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.created_by.affiliation: must not name a current or former employer; use Tyche Institute, Tallinn, Estonia for public MIRROR artifacts" in payload["errors"]


def test_verify_reports_forbidden_named_employer_in_created_by_tool(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_by"]["tool"] = "ForbiddenCorp Estonia internal exporter"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.created_by.tool: must not name a current or former employer in public MIRROR metadata" in payload["errors"]


def test_verify_reports_forbidden_named_employer_in_claim_text(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["text"] = "Anton works at ForbiddenCorp Estonia."
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].text: must not name a current or former employer in public MIRROR claim text" in payload["errors"]


def test_verify_reports_forbidden_named_employer_in_claim_safe_wording(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = "Anton works at ForbiddenCorp Estonia."
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not name a current or former employer in public MIRROR claim text" in payload["errors"]


def test_verify_reports_unsafe_assurance_language_in_claim_safe_wording(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = "This bundle certifies compliance with the AI Act."
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in payload["errors"]


def test_verify_accepts_negated_assurance_boundary_language(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = (
        "MIRROR supports local review; these checks do not provide external timestamping, "
        "certification, authorship proof, legal compliance, or completeness guarantees."
    )
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 0
    assert parse_verify(result) == {"errors": [], "status": "ok"}


def test_verify_reports_unsafe_assurance_language_after_unrelated_negation(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = (
        "MIRROR does not sign bundles or provide trust services. "
        "Separately, this bundle certifies compliance with the AI Act."
    )
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in payload["errors"]


def test_verify_reports_manifest_source_path_outside_sources_directory(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["path"] = "notes.md"
    manifest["sources"][0]["sha256"]["value"] = hashlib.sha256((bundle_dir / "notes.md").read_bytes()).hexdigest()

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "notes.md#method"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].path: source records must be stored under sources/" in payload["errors"]


def test_verify_reports_manifest_source_path_traversal_outside_sources_directory(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["path"] = "sources/../notes.md"
    manifest["sources"][0]["sha256"]["value"] = hashlib.sha256((bundle_dir / "notes.md").read_bytes()).hexdigest()

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["evidence"][0] = {"source_id": "S-0001", "pointer": "sources/../notes.md#method"}
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.sources[0].path: source records must resolve under sources/" in payload["errors"]


def test_verify_reports_unsafe_assurance_language_in_manifest_compatibility_statement(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["compatibility"]["statement"] = "This MIRROR bundle certifies compliance with research provenance requirements."
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "manifest.compatibility.statement: must not use unsafe assurance language: certifies compliance" in payload["errors"]


def test_verify_reports_unsafe_assurance_language_after_same_sentence_contrast(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = (
        "MIRROR does not sign bundles, but this package certifies compliance with publication policy."
    )
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in payload["errors"]


def test_verify_reports_unsafe_assurance_language_after_unrelated_same_clause_negation(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = (
        "MIRROR does not sign bundles and this package certifies compliance with publication policy."
    )
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in payload["errors"]


def test_verify_reports_not_only_unsafe_assurance_language(tmp_path):
    bundle_dir = make_good_bundle(tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    claims_path = bundle_dir / "claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["safe_wording"] = "This bundle not only certifies compliance but guarantees completeness."
    claims_path.write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["claims_file"]["sha256"]["value"] = hashlib.sha256(claims_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_verify(bundle_dir)

    assert result.returncode == 1
    payload = parse_verify(result)
    assert payload["status"] == "fail"
    assert "claims.json.claims[0].safe_wording: must not use unsafe assurance language: certifies compliance" in payload["errors"]
