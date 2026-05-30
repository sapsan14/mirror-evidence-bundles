#!/usr/bin/env python3
"""Summarize methodology-bundle coverage for MIRROR semantic fixtures.

This helper reports local evidence-bundle source coverage only. It does not
certify lane completeness, publication readiness, audit status, or any
legal/regulatory status.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BUNDLE_RELATIVE = Path("paper/methodology.md.bundle")
DAILY_ANCHOR_FIXTURE_DIR = Path("examples/daily-anchor-payload")
DAILY_ANCHOR_README = DAILY_ANCHOR_FIXTURE_DIR / "README.md"
DAILY_ANCHOR_SCHEMA = Path("schema/daily-anchor.schema.json")
DAILY_ROLLUP_SCHEMA = Path("schema/daily-roll-up.schema.json")
DAILY_ROLLUP_FIXTURE_DIR = Path("examples/daily-roll-up-payload")
DAILY_ROLLUP_README = DAILY_ROLLUP_FIXTURE_DIR / "README.md"
ROLLUP_PAYLOAD_FIXTURE_DIR = Path("examples/roll-up-cli-payload")
ROLLUP_PAYLOAD_SCHEMA = Path("schema/roll-up-cli-payload.schema.json")
ROLLUP_PAYLOAD_POLICY = ROLLUP_PAYLOAD_FIXTURE_DIR / "POLICY.md"
COVERAGE_FIXTURE_DIR = Path("examples/methodology-bundle-coverage")
COVERAGE_SCHEMA = Path("schema/methodology-bundle-coverage.schema.json")
COVERAGE_POLICY = COVERAGE_FIXTURE_DIR / "POLICY.md"
REVIEWER_REPORT_FIXTURE_DIR = Path("examples/reviewer-report-packet")
REVIEWER_REPORT_SCHEMA = Path("schema/reviewer-report-packet.schema.json")
REVIEWER_REPORT_POLICY = REVIEWER_REPORT_FIXTURE_DIR / "POLICY.md"
REVIEWER_REPORT_GENERATOR = Path("reviewer_report_packet.py")
SIGNED_TRANSITION_FIXTURE_DIR = Path("examples/signed-transition-profile")
SIGNED_TRANSITION_SCHEMA = Path("schema/signed-transition-profile.schema.json")
SIGNED_TRANSITION_POLICY = SIGNED_TRANSITION_FIXTURE_DIR / "POLICY.md"
SIGNED_TRANSITION_GENERATOR = Path("signed_transition_profile.py")
ARTIFACT_TRAVERSAL_README = Path("examples/bad-artifact-traversal/README.md")
UNSAFE_ASSURANCE_README = Path("examples/bad-unsafe-assurance/README.md")
VERIFIER_OUTPUT_FIXTURE_DIR = Path("examples/verifier-output")
VERIFIER_OUTPUT_SCHEMA = Path("schema/verifier-output.schema.json")
VERIFIER_OUTPUT_README = VERIFIER_OUTPUT_FIXTURE_DIR / "README.md"
SAFE_INTERPRETATION = (
    "This summary reports local methodology-bundle source coverage for semantic fixtures only; "
    "it does not certify sibling-lane completeness, publication readiness, audit status, "
    "or legal/regulatory status."
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def required_semantic_fixture_paths(root: Path) -> list[Path]:
    """Return semantic-fixture files that methodology evidence should cover."""
    daily_anchor_fixture_paths = sorted((root / DAILY_ANCHOR_FIXTURE_DIR).glob("*.json"))
    daily_rollup_fixture_paths = sorted((root / DAILY_ROLLUP_FIXTURE_DIR).glob("*.json"))
    rollup_fixture_paths = sorted((root / ROLLUP_PAYLOAD_FIXTURE_DIR).glob("*.json"))
    coverage_fixture_paths = sorted(
        path for path in (root / COVERAGE_FIXTURE_DIR).glob("*.json")
        if path.name != "default-output.json"
    )
    reviewer_report_fixture_paths = sorted((root / REVIEWER_REPORT_FIXTURE_DIR).glob("*.json"))
    signed_transition_fixture_paths = sorted((root / SIGNED_TRANSITION_FIXTURE_DIR).glob("*.json"))
    verifier_output_fixture_paths = sorted((root / VERIFIER_OUTPUT_FIXTURE_DIR).glob("*.json"))
    return [
        root / DAILY_ANCHOR_SCHEMA,
        *daily_anchor_fixture_paths,
        root / DAILY_ANCHOR_README,
        root / DAILY_ROLLUP_SCHEMA,
        *daily_rollup_fixture_paths,
        root / DAILY_ROLLUP_README,
        root / ROLLUP_PAYLOAD_SCHEMA,
        *rollup_fixture_paths,
        root / ROLLUP_PAYLOAD_POLICY,
        root / COVERAGE_SCHEMA,
        *coverage_fixture_paths,
        root / COVERAGE_POLICY,
        root / REVIEWER_REPORT_SCHEMA,
        *reviewer_report_fixture_paths,
        root / REVIEWER_REPORT_POLICY,
        root / REVIEWER_REPORT_GENERATOR,
        root / SIGNED_TRANSITION_SCHEMA,
        *signed_transition_fixture_paths,
        root / SIGNED_TRANSITION_POLICY,
        root / SIGNED_TRANSITION_GENERATOR,
        root / ARTIFACT_TRAVERSAL_README,
        root / UNSAFE_ASSURANCE_README,
        root / VERIFIER_OUTPUT_SCHEMA,
        *verifier_output_fixture_paths,
        root / VERIFIER_OUTPUT_README,
    ]


def _summary(covered: list[dict[str, str]], missing: list[str]) -> dict[str, Any]:
    return {
        "status": "ok" if not missing else "fail",
        "bundle": BUNDLE_RELATIVE.as_posix(),
        "required_count": len(covered) + len(missing),
        "covered_count": len(covered),
        "missing_count": len(missing),
        "covered": covered,
        "missing": missing,
        "safe_interpretation": SAFE_INTERPRETATION,
    }


def summarize_semantic_fixture_coverage(root: Path) -> dict[str, Any]:
    """Summarize methodology-bundle source coverage for semantic fixtures."""
    root = root.resolve()
    bundle = root / BUNDLE_RELATIVE
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        return _summary([], [str(BUNDLE_RELATIVE / "manifest.json")])

    manifest = _load_json(manifest_path)
    sources_by_original_path: dict[str, dict[str, Any]] = {}
    for source in manifest.get("sources", []):
        if not isinstance(source, dict):
            continue
        original_path = source.get("original_path") or source.get("source_path")
        if isinstance(original_path, str):
            sources_by_original_path[original_path] = source

    covered: list[dict[str, str]] = []
    missing: list[str] = []
    for required_path in required_semantic_fixture_paths(root):
        relative_path = required_path.relative_to(root).as_posix()
        source = sources_by_original_path.get(str(required_path)) or sources_by_original_path.get(relative_path)
        if source is None:
            missing.append(relative_path)
            continue
        covered.append(
            {
                "path": relative_path,
                "source_id": source["id"],
                "bundle_path": source["path"],
                "sha256": "sha256:"
                + (
                    source["sha256"].get("value")
                    if isinstance(source.get("sha256"), dict)
                    else source["sha256"].removeprefix("sha256:")
                ),
            }
        )

    return _summary(covered, missing)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize local methodology-bundle source coverage for MIRROR semantic fixtures.",
        epilog=(
            "Boundary: default-output.json is excluded from the required-source summary "
            "because including the positive compact-output fixture's own digest would create "
            "a self-referential hash fixed-point. If paper/methodology.md.bundle/manifest.json "
            "is missing, compact mode emits a schema-shaped failure payload matching "
            "examples/methodology-bundle-coverage/missing-manifest.json rather than a traceback. "
            "It does not certify completeness, publication readiness, audit status, "
            "or legal/regulatory status."
        ),
    )
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="MIRROR workspace root; defaults to the directory containing this script.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit single-line JSON for scripts; default output remains indented for reviewers.",
    )
    args = parser.parse_args()
    summary = summarize_semantic_fixture_coverage(args.root)
    if args.compact:
        print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
