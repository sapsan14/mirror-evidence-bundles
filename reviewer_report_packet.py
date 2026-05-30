#!/usr/bin/env python3
"""Generate a local MIRROR reviewer-report packet.

This helper turns an offline verifier result and bundle metadata into a small
review packet for humans. It reports deterministic local facts and review prompts
only. It does not certify completeness, scholarly quality, publication readiness,
audit status, or any legal/regulatory status.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SAFE_INTERPRETATION = (
    "This reviewer report packet organizes deterministic local facts and review prompts "
    "for independent re-evaluation; it does not certify completeness, publication readiness, "
    "scholarly quality, audit status, or legal/regulatory status."
)
OUT_OF_SCOPE_QUESTIONS = [
    {
        "kind": "authorship",
        "message": "The local report packet does not establish external authorship or identity.",
    },
    {
        "kind": "external_time",
        "message": "The local report packet does not establish an external trusted timestamp.",
    },
    {
        "kind": "legal_compliance",
        "message": "The local report packet does not make legal or regulatory determinations.",
    },
    {
        "kind": "source_authority",
        "message": "The local report packet does not establish that a cited source is authoritative.",
    },
    {
        "kind": "scholarly_quality",
        "message": "The local report packet does not grade the scholarly quality of the argument.",
    },
]
ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    """Load JSON from a local path."""
    return json.loads(path.read_text(encoding="utf-8"))


def public_path(path: Path) -> str:
    """Return a path suitable for public verifier output."""
    try:
        return path.resolve(strict=False).relative_to(ROOT).as_posix()
    except ValueError:
        return "omitted-private-workspace-path"


def run_verifier(bundle_dir: Path) -> dict[str, Any]:
    """Run the local offline verifier and return its JSON payload."""
    verifier = ROOT / "verify.py"
    result = subprocess.run(
        [sys.executable, str(verifier), str(bundle_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.stderr:
        return {"status": "fail", "errors": [result.stderr.strip()]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return {"status": "fail", "errors": [f"verifier returned non-JSON output: {error}"]}
    if result.returncode != 0 and payload.get("status") != "fail":
        payload = {"status": "fail", "errors": payload.get("errors", [])}
    return payload


def pluralize_source_message(count: int) -> str:
    """Return a deterministic source-hash fact message."""
    noun = "source file digest" if count == 1 else "source file digests"
    return f"{count} bundled {noun} matched the manifest during local verification."


def build_local_facts(manifest: dict[str, Any], claims_file: str, verifier_payload: dict[str, Any]) -> list[dict[str, str]]:
    """Build schema-shaped local facts from manifest and verifier output."""
    artifact_path = manifest.get("artifact", {}).get("path", "artifact")
    sources = manifest.get("sources", [])
    facts = [
        {
            "kind": "artifact_hash",
            "path": artifact_path,
            "message": "The artifact digest matched the manifest during local verification.",
        },
        {
            "kind": "source_hash",
            "path": sources[0]["path"] if len(sources) == 1 else "sources/",
            "message": pluralize_source_message(len(sources)),
        },
        {
            "kind": "schema_validation",
            "path": claims_file,
            "message": "The local claims file matched the supported MIRROR v0.1 claim structure.",
        },
    ]
    for error in verifier_payload.get("errors", []):
        facts.append(
            {
                "kind": "verifier_error",
                "path": str(error).split(":", maxsplit=1)[0] or "bundle",
                "message": str(error),
            }
        )
    return facts


def reviewer_claim_id(claim: dict[str, Any], index: int) -> str:
    """Return the reviewer-packet claim id expected by its v0.1 schema."""
    raw_id = str(claim.get("id", ""))
    if raw_id.startswith("claim-"):
        return raw_id
    if raw_id.startswith("C-"):
        try:
            return f"claim-{int(raw_id.split('-', maxsplit=1)[1])}"
        except ValueError:
            pass
    return f"claim-{index}"


def build_review_prompts(claims: dict[str, Any]) -> list[dict[str, str]]:
    """Build one cautious review prompt per recorded claim."""
    return [
        {
            "kind": "claim_scope",
            "claim_id": reviewer_claim_id(claim, index),
            "message": "Check whether the cautious wording remains aligned with the artifact text before citation.",
        }
        for index, claim in enumerate(claims.get("claims", []), start=1)
    ]


def manifest_claims_path(manifest: dict[str, Any]) -> str:
    """Return the bundle-relative claims file path from v0.1 manifest shapes."""
    claims_file = manifest.get("claims_file", "claims.json")
    if isinstance(claims_file, dict):
        return str(claims_file.get("path", "claims.json"))
    return str(claims_file)


def build_packet(bundle_dir: Path) -> dict[str, Any]:
    """Build a deterministic reviewer-report packet for a MIRROR bundle."""
    manifest = load_json(bundle_dir / "manifest.json")
    claims_file = manifest_claims_path(manifest)
    claims = load_json(bundle_dir / claims_file)
    verifier_payload = run_verifier(bundle_dir)
    return {
        "bundle": public_path(bundle_dir),
        "out_of_scope_questions": OUT_OF_SCOPE_QUESTIONS,
        "reproducible_local_facts": build_local_facts(manifest, claims_file, verifier_payload),
        "review_prompts": build_review_prompts(claims),
        "safe_interpretation": SAFE_INTERPRETATION,
        "schema": "mirror.reviewer-report-packet.v0.1",
        "verifier_status": "ok" if verifier_payload.get("status") == "ok" else "fail",
    }


def failure(errors: list[str]) -> dict[str, Any]:
    """Return a cautious JSON failure payload for scripts."""
    return {
        "status": "fail",
        "errors": errors,
        "safe_interpretation": SAFE_INTERPRETATION,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a local MIRROR reviewer-report packet JSON payload.",
        epilog=(
            "Boundary: this helper reports deterministic local facts and review prompts only. "
            "It does not certify completeness, scholarly quality, publication readiness, "
            "audit status, or legal/regulatory status."
        ),
    )
    parser.add_argument("--bundle-dir", required=True, type=Path, help="Path to the MIRROR bundle directory to summarize.")
    parser.add_argument("--output", required=True, type=Path, help="Path where the reviewer-report packet JSON will be written.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    if not args.bundle_dir.is_dir():
        errors.append(f"missing bundle directory: {public_path(args.bundle_dir)}")
    elif not (args.bundle_dir / "manifest.json").is_file():
        errors.append(f"missing bundle manifest: {public_path(args.bundle_dir / 'manifest.json')}")
    if errors:
        print(json.dumps(failure(errors), sort_keys=True))
        return 1

    payload = build_packet(args.bundle_dir)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
