import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_verify(bundle_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "verify.py"), str(bundle_dir)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stderr == ""
    return json.loads(result.stdout)


def test_known_good_example_verifies_ok():
    result = run_verify(ROOT / "examples" / "good" / "artifact.md.bundle")

    assert result.returncode == 0
    assert parse_payload(result) == {"errors": [], "status": "ok"}


def test_known_bad_hash_example_verifies_fail_with_source_hash_mismatch():
    result = run_verify(ROOT / "examples" / "bad-hash" / "artifact.md.bundle")

    assert result.returncode == 1
    payload = parse_payload(result)
    assert payload["status"] == "fail"
    assert any("hash mismatch for sources/source-1.txt" in error for error in payload["errors"])
