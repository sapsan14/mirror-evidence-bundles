import json
import subprocess
import sys
from pathlib import Path


def test_bundle_cli_creates_manifest_claims_notes_and_copied_sources(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    artifact = tmp_path / "artifact.md"
    source = tmp_path / "source.txt"
    out = tmp_path / "out"
    artifact.write_text("# Tiny artifact\n\nThis artifact suggests a traceable claim.\n", encoding="utf-8")
    source.write_text("A local source supporting the traceable claim.\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo / "bundle.py"),
            str(artifact),
            "--output-dir",
            str(out),
            "--source",
            str(source),
            "--claim",
            "The artifact has a traceable local source.",
            "--evidence",
            "S1:line 1",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    bundle_dir = Path(payload["bundle"])
    assert bundle_dir.is_dir()

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))

    assert manifest["schema_id"] == "urn:tyche:mirror:bundle:0.1"
    assert manifest["artifact"]["path"] == "artifact/artifact.md"
    assert len(manifest["sources"]) == 1
    assert manifest["sources"][0]["id"] == "S1"
    assert manifest["sources"][0]["path"].startswith("sources/S1-")
    assert (bundle_dir / manifest["sources"][0]["path"]).is_file()
    assert manifest["compatibility"]["signed"] is False
    assert manifest["compatibility"]["timestamped"] is False
    assert claims["claims"][0]["evidence"][0]["source_id"] == "S1"
    assert claims["claims"][0]["evidence"][0]["locator"] == "line 1"
    assert (bundle_dir / "notes.md").is_file()
