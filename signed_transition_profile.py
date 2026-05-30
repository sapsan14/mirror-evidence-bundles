#!/usr/bin/env python3
"""Generate a local MIRROR signed-transition profile payload.

This helper records exact local digests for an unsigned MIRROR bundle and a
reviewer-report packet so a later operator-controlled signing step can decide
whether to cover those same bytes. It does not sign, timestamp, certify research
quality, or make any legal/regulatory finding.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

SAFE_INTERPRETATION = (
    "This signed transition profile fixture records local digest subjects and unresolved assumptions "
    "for later operator-controlled review; it does not certify completeness, publication "
    "readiness, scholarly quality, audit status, or legal/regulatory status."
)
MUTATION_POLICY = "record exact digests without rewriting unsigned bundle or reviewer report packet"
DEFAULT_PROFILE = "future-operator-controlled-eatf-compatible-profile"
DEFAULT_ASSUMPTIONS = [
    "No external timestamp is present in this MIRROR lane fixture.",
    "Any later signature would need to cover these exact digests or state the reason for divergence.",
]


def sha256_uri(path: Path) -> str:
    """Return the sha256: URI for a local file."""
    return f"sha256:{sha256(path.read_bytes()).hexdigest()}"


def digest_subject(path: Path, status: str) -> dict[str, str]:
    """Build a schema-shaped digest subject for a local file."""
    return {
        "path": str(path),
        "sha256": sha256_uri(path),
        "status": status,
    }


def build_profile(
    unsigned_bundle: Path,
    reviewer_report_packet: Path,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Build a deterministic signed-transition profile payload."""
    return {
        "reviewer_report_packet": digest_subject(reviewer_report_packet, "derived-local"),
        "safe_interpretation": SAFE_INTERPRETATION,
        "schema": "mirror.signed-transition-profile.v0.1",
        "signing_transition": {
            "external_timestamp": None,
            "mutation_policy": MUTATION_POLICY,
            "operator_controlled": True,
            "profile": profile,
            "signature_present": False,
        },
        "unresolved_assumptions": DEFAULT_ASSUMPTIONS,
        "unsigned_bundle": digest_subject(unsigned_bundle, "unsigned-local"),
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
        description="Generate a local MIRROR signed-transition profile JSON payload.",
        epilog=(
            "Boundary: this helper records exact local digests for later operator-controlled "
            "review. It does not sign, timestamp, certify completeness, establish publication "
            "readiness, or provide audit/legal/regulatory status."
        ),
    )
    parser.add_argument("--unsigned-bundle", required=True, type=Path, help="Path to unsigned bundle manifest or bundle file to hash.")
    parser.add_argument("--reviewer-report-packet", required=True, type=Path, help="Path to reviewer-report packet JSON to hash.")
    parser.add_argument("--output", required=True, type=Path, help="Path where the signed-transition profile JSON will be written.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Future signing profile label to record; no signing is performed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    if not args.unsigned_bundle.is_file():
        errors.append(f"missing unsigned bundle: {args.unsigned_bundle}")
    if not args.reviewer_report_packet.is_file():
        errors.append(f"missing reviewer report packet: {args.reviewer_report_packet}")
    if errors:
        print(json.dumps(failure(errors), sort_keys=True))
        return 1

    payload = build_profile(args.unsigned_bundle, args.reviewer_report_packet, args.profile)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
