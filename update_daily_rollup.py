#!/usr/bin/env python3
"""Build MIRROR daily cross-lane artifact roll-ups.

This script reads sibling-lane ARTIFACT_INDEX.md files in read-only mode,
normalizes their markdown table rows, writes daily-roll-up/YYYY-MM-DD.json,
and appends a local daily anchor record to daily-anchors.jsonl.

It performs no network calls and no external timestamping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WORKSPACE = Path(__file__).resolve().parent
PROJECTS_ROOT = WORKSPACE.parent
SIBLING_LANES = [
    "model-card-x-ray",
    "road2pq-shadow",
    "pki-atlas-trusted-lists",
    "echo",
]
ANCHOR_SCHEMA = "mirror.daily-anchor.v0.1"
ROLLUP_SCHEMA = "mirror.daily-roll-up.v0.1"
NO_TRUST_SERVICE_NOTE = (
    "Local research anchor only; no external timestamping or regulated trust service is performed."
)
MAX_TICKET_DIAGNOSTIC_LINE_LENGTH = 500


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def split_markdown_table_row(row: str) -> list[str]:
    """Split a markdown table row while preserving escaped pipe literals."""
    stripped = row.strip().strip("|")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped:
        if escaped:
            if char == "|":
                current.append("|")
            else:
                current.append("\\")
                current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def parse_markdown_table(path: Path, lane: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    entries: list[dict[str, str]] = []
    seen_path_hashes: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "`" not in stripped:
            continue
        cells = split_markdown_table_row(stripped)
        if len(cells) < 4 or cells[0] in {"Path", "---"}:
            continue
        rel_path, purpose, digest, verified = cells[:4]
        rel_path = rel_path.strip("`")
        digest = digest.strip("`")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            continue
        path_hash_key = (rel_path, digest)
        if path_hash_key in seen_path_hashes:
            continue
        seen_path_hashes.add(path_hash_key)
        entries.append(
            {
                "lane": lane,
                "path": rel_path,
                "purpose": purpose,
                "sha256": digest,
                "verified": verified,
            }
        )
    return entries


def artifact_index_diagnostics(index_path: Path, lane_root: Path, lane: str) -> list[dict[str, object]]:
    """Return structured diagnostics for ARTIFACT_INDEX.md byte checks.

    ARTIFACT_INDEX.md cannot reliably record its own digest because editing the
    digest changes the file. The self-entry is therefore intentionally excluded
    from byte-level consistency checks, matching the MIRROR register note.
    """
    if not index_path.exists():
        message = f"{lane}: missing artifact index: {index_path}"
        return [{"category": "missing_artifact_index", "lane": lane, "path": str(index_path), "message": message}]

    diagnostics: list[dict[str, object]] = []
    entries_by_path: dict[str, list[dict[str, str]]] = {}
    for entry in parse_markdown_table(index_path, lane):
        entries_by_path.setdefault(entry["path"], []).append(entry)

    for rel_path, entries in entries_by_path.items():
        candidate = Path(rel_path)
        windows_parts = [part for part in rel_path.replace("\\", "/").split("/") if part]
        has_windows_absolute_prefix = len(rel_path) >= 3 and rel_path[1] == ":" and rel_path[2] in {"/", "\\"}
        if rel_path == "ARTIFACT_INDEX.md":
            continue
        if (
            candidate.is_absolute()
            or has_windows_absolute_prefix
            or ".." in candidate.parts
            or ".." in windows_parts
            or rel_path in {"", "."}
        ):
            message = f"{lane}: unsafe indexed path in ARTIFACT_INDEX.md: {rel_path}"
            diagnostics.append({"category": "unsafe_path", "lane": lane, "path": rel_path, "message": message})
            continue
        artifact_path = lane_root / candidate
        if not artifact_path.is_file():
            message = f"{lane}: missing file indexed by ARTIFACT_INDEX.md: {rel_path}"
            diagnostics.append({"category": "missing_file", "lane": lane, "path": rel_path, "message": message})
            continue

        actual = sha256_bytes(artifact_path.read_bytes())
        expected_hashes = sorted({entry["sha256"] for entry in entries})
        if len(expected_hashes) == 1:
            expected = expected_hashes[0]
            if actual != expected:
                message = f"{lane}: {rel_path} hash mismatch: expected {expected}, got {actual}"
                diagnostics.append(
                    {
                        "category": "hash_mismatch",
                        "lane": lane,
                        "path": rel_path,
                        "message": message,
                        "actual_sha256": actual,
                        "expected_sha256": expected,
                    }
                )
            continue

        stale_hashes = [digest for digest in expected_hashes if digest != actual]
        if actual in expected_hashes:
            row_label = "row" if len(stale_hashes) == 1 else "rows"
            message = (
                f"{lane}: {rel_path} has {len(stale_hashes)} stale historical hash {row_label}; "
                f"current file matches {actual}; stale expected: {', '.join(stale_hashes)}"
            )
            diagnostics.append(
                {
                    "category": "stale_historical_hash_rows",
                    "lane": lane,
                    "path": rel_path,
                    "message": message,
                    "actual_sha256": actual,
                    "stale_sha256": stale_hashes,
                }
            )
        else:
            message = (
                f"{lane}: {rel_path} has {len(expected_hashes)} conflicting indexed hash rows; "
                f"none match current file: expected one of {', '.join(expected_hashes)}, got {actual}"
            )
            diagnostics.append(
                {
                    "category": "conflicting_hash_rows",
                    "lane": lane,
                    "path": rel_path,
                    "message": message,
                    "actual_sha256": actual,
                    "expected_sha256": expected_hashes,
                }
            )
    return sorted(diagnostics, key=lambda item: str(item["message"]))


def format_outgoing_ticket(
    lane: str,
    diagnostics: list[dict[str, object]],
    *,
    created: str,
    rollup_path: str,
    max_examples: int = 10,
) -> str:
    """Render a local outgoing diagnostic ticket for a sibling lane.

    The ticket is advisory MIRROR triage only. It must remain safe for public
    research use: no legal certification language and no sibling workspace writes.
    """
    category_guidance = {
        "hash_mismatch": "current file bytes do not match the single indexed digest; refresh the row if the file change is expected.",
        "stale_historical_hash_rows": "at least one row matches current bytes, but older rows for the same path remain in the index.",
        "conflicting_hash_rows": "multiple indexed digests exist for the same path and none match the current file bytes.",
        "missing_file": "the index names a relative path that is absent from the lane workspace.",
        "missing_artifact_index": "the lane artifact index was not available for this roll-up; this does not imply the lane has no artifacts and does not certify lane completeness.",
        "unsafe_path": "the index contains an absolute, parent-traversing, empty, or current-directory path.",
    }
    lines = [
        f"# Outgoing MIRROR diagnostic ticket — {lane}",
        "",
        f"Date: {created}",
        "",
        "Scope: local MIRROR read-only diagnostics from sibling lane ARTIFACT_INDEX.md; sibling workspace was not modified.",
        f"Roll-up: `{rollup_path}`",
        "",
    ]

    if not diagnostics:
        lines.extend(
            [
                "Status: resolved for this roll-up",
                "",
                "No structured artifact-index diagnostics were observed for this lane in the referenced roll-up.",
                "",
                "Safe interpretation:",
                "- This only reflects MIRROR byte-consistency checks over available indexed files.",
                "- It does not certify completeness, audit the lane, or make a legal/regulatory finding.",
            ]
        )
        return "\n".join(lines) + "\n"

    counts: dict[str, int] = {}
    by_category: dict[str, list[dict[str, object]]] = {}
    for diagnostic in diagnostics:
        category = str(diagnostic.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
        by_category.setdefault(category, []).append(diagnostic)

    lines.append("Summary:")
    for category in sorted(counts):
        lines.append(f"- {category}: {counts[category]}")

    path_counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        rel_path = str(diagnostic.get("path", ""))
        if rel_path:
            path_counts[rel_path] = path_counts.get(rel_path, 0) + 1
    if path_counts:
        lines.extend(["", "Most repeated paths:"])
        for rel_path, count in sorted(path_counts.items(), key=lambda item: (-item[1], item[0]))[:5]:
            label = "diagnostic" if count == 1 else "diagnostics"
            lines.append(f"- `{rel_path}`: {count} {label}")
        lines.append("- Group repeated paths before escalating wording; repeated rows are triage pointers, not severity scores.")

    lines.extend(["", "Category guidance:"])
    for category in sorted(counts):
        guidance = category_guidance.get(category, "unclassified local byte-consistency diagnostic.")
        lines.append(f"- {category}: {guidance}")

    lines.extend(["", "Representative diagnostics:"])
    emitted = 0
    total = len(diagnostics)
    sorted_categories = sorted(by_category)
    category_examples = {
        category: sorted(items, key=lambda item: str(item.get("message", "")))
        for category, items in by_category.items()
    }
    index = 0
    while emitted < max_examples:
        made_progress = False
        for category in sorted_categories:
            examples = category_examples[category]
            if index >= len(examples):
                continue
            line = f"- [{category}] {examples[index].get('message', '')}"
            if len(line) > MAX_TICKET_DIAGNOSTIC_LINE_LENGTH:
                line = line[: MAX_TICKET_DIAGNOSTIC_LINE_LENGTH - 1].rstrip() + "…"
            lines.append(line)
            emitted += 1
            made_progress = True
            if emitted >= max_examples:
                break
        if not made_progress:
            break
        index += 1
    if total > emitted:
        lines.append(f"- ... {total - emitted} additional diagnostics recorded in {rollup_path}")

    lines.extend(
        [
            "",
            "Safe interpretation:",
            "- These are local byte-consistency diagnostics over available indexed files only.",
            "- They do not certify completeness, audit the lane, or make a legal/regulatory finding.",
        ]
    )
    return "\n".join(lines) + "\n"



def write_outgoing_tickets(
    rollup: dict[str, object],
    *,
    ticket_dir: Path,
    rollup_path: Path,
    workspace: Path,
) -> list[Path]:
    """Write local outgoing diagnostic tickets grouped by sibling lane."""
    ticket_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_by_lane: dict[str, list[dict[str, object]]] = {lane: [] for lane in SIBLING_LANES}
    for diagnostic in rollup.get("artifact_index_diagnostics", []):
        if not isinstance(diagnostic, dict):
            continue
        lane = str(diagnostic.get("lane", ""))
        if lane in diagnostics_by_lane:
            diagnostics_by_lane[lane].append(diagnostic)

    try:
        rollup_pointer = str(rollup_path.relative_to(workspace))
    except ValueError:
        rollup_pointer = str(rollup_path)

    written: list[Path] = []
    for lane in SIBLING_LANES:
        ticket_path = ticket_dir / f"{lane}.md"
        ticket_path.write_text(
            format_outgoing_ticket(
                lane,
                diagnostics_by_lane.get(lane, []),
                created=str(rollup["created"]),
                rollup_path=rollup_pointer,
            ),
            encoding="utf-8",
        )
        written.append(ticket_path)
    return written


def validate_artifact_index(index_path: Path, lane_root: Path, lane: str) -> list[str]:
    """Check that indexed artifact hashes match files on disk."""
    return [str(item["message"]) for item in artifact_index_diagnostics(index_path, lane_root, lane)]


def summarize_diagnostics(diagnostics: list[dict[str, object]]) -> dict[str, object]:
    """Return compact deterministic diagnostic counts for CLI consumers.

    The summary is local MIRROR triage metadata only. It intentionally counts
    observed diagnostics without ranking lane quality, severity, or publication
    readiness.
    """
    by_category: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for diagnostic in diagnostics:
        category = str(diagnostic.get("category", "unknown"))
        lane = str(diagnostic.get("lane", "unknown"))
        by_category[category] = by_category.get(category, 0) + 1
        by_lane[lane] = by_lane.get(lane, 0) + 1
    return {
        "total": len(diagnostics),
        "by_category": dict(sorted(by_category.items())),
        "by_lane": dict(sorted(by_lane.items())),
    }


def merkle_root(leaves: list[str]) -> str | None:
    if not leaves:
        return None
    level = [bytes.fromhex(leaf) for leaf in sorted(leaves)]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def previous_anchor_hash(anchor_path: Path) -> str | None:
    if not anchor_path.exists():
        return None
    lines = [line for line in anchor_path.read_bytes().splitlines() if line.strip()]
    if not lines:
        return None
    return sha256_bytes(lines[-1])


def validate_anchor_chain(anchor_path: Path) -> list[str]:
    """Return deterministic local-anchor chain diagnostics.

    MIRROR anchors are local research records only. Validation therefore checks
    byte-level continuity between JSONL records and rejects any non-null
    external timestamp field without claiming external timestamp semantics.
    """
    if not anchor_path.exists():
        return [f"{anchor_path.name}: missing anchor log"]

    errors: list[str] = []
    previous_line_variants: tuple[bytes, ...] = ()
    for index, raw_line in enumerate(anchor_path.read_bytes().splitlines(keepends=True), start=1):
        line = raw_line.rstrip(b"\r\n")
        if not line.strip():
            continue
        try:
            anchor = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{anchor_path.name} line {index}: invalid JSON: {exc.msg}")
            previous_line_variants = (line, raw_line)
            continue

        expected_previous_values = {sha256_bytes(candidate) for candidate in previous_line_variants}
        actual_previous = anchor.get("previous_anchor_hash")
        if previous_line_variants and actual_previous not in expected_previous_values:
            errors.append(
                f"{anchor_path.name} line {index}: previous_anchor_hash does not match line {index - 1}"
            )
        if not previous_line_variants and actual_previous is not None:
            errors.append(
                f"{anchor_path.name} line {index}: previous_anchor_hash must be null on first anchor"
            )
        if anchor.get("external_timestamp") is not None:
            errors.append(
                f"{anchor_path.name} line {index}: external_timestamp must be null for MIRROR local anchors"
            )
        previous_line_variants = (line, raw_line)
    return errors


def build_rollup(now: datetime, anchor_path: Path | None = None) -> tuple[dict[str, object], dict[str, object], Path]:
    entries: list[dict[str, str]] = []
    missing: list[str] = []
    artifact_index_diagnostics_list: list[dict[str, object]] = []
    for lane in SIBLING_LANES:
        lane_root = PROJECTS_ROOT / lane
        index_path = lane_root / "ARTIFACT_INDEX.md"
        lane_entries = parse_markdown_table(index_path, lane)
        if lane_entries:
            entries.extend(lane_entries)
        elif not index_path.exists():
            missing.append(str(index_path))
        artifact_index_diagnostics_list.extend(artifact_index_diagnostics(index_path, lane_root, lane))

    entries.sort(key=lambda item: (item["lane"], item["path"], item["sha256"]))
    artifact_index_diagnostics_list.sort(key=lambda item: str(item["message"]))
    artifact_index_errors = [str(item["message"]) for item in artifact_index_diagnostics_list]
    root = merkle_root([entry["sha256"] for entry in entries])
    date = now.date().isoformat()
    rollup_path = WORKSPACE / "daily-roll-up" / f"{date}.json"
    diagnostic_summary = summarize_diagnostics(artifact_index_diagnostics_list)
    rollup = {
        "schema": ROLLUP_SCHEMA,
        "date": date,
        "created": now.isoformat(timespec="seconds"),
        "source_indexes": [
            str(PROJECTS_ROOT / lane / "ARTIFACT_INDEX.md") for lane in SIBLING_LANES
        ],
        "missing_indexes": missing,
        "artifact_index_errors": artifact_index_errors,
        "artifact_index_diagnostics": artifact_index_diagnostics_list,
        "diagnostic_summary": diagnostic_summary,
        "entry_count": len(entries),
        "merkle_root": root,
        "note": NO_TRUST_SERVICE_NOTE,
        "entries": entries,
    }
    rollup_path.parent.mkdir(parents=True, exist_ok=True)
    rollup_path.write_text(json.dumps(rollup, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rollup_sha256 = sha256_bytes(rollup_path.read_bytes())

    anchor_path = anchor_path or (WORKSPACE / "daily-anchors.jsonl")
    anchor = {
        "schema": ANCHOR_SCHEMA,
        "date": date,
        "created": now.isoformat(timespec="seconds"),
        "rollup_path": str(rollup_path.relative_to(WORKSPACE)),
        "rollup_sha256": rollup_sha256,
        "entry_count": len(entries),
        "merkle_root": root,
        "previous_anchor_hash": previous_anchor_hash(anchor_path),
        "external_timestamp": None,
        "note": NO_TRUST_SERVICE_NOTE,
    }
    with anchor_path.open("ab") as handle:
        handle.write(canonical_json(anchor) + b"\n")
    return rollup, anchor, rollup_path


def main() -> int:
    global WORKSPACE, PROJECTS_ROOT, SIBLING_LANES

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Hermetic/replay options:\n"
            "  Use these options for tests or local replay only: "
            "--workspace, --projects-root, and repeatable --sibling-lane.\n"
            "  Normal Zeus runs should rely on the default MIRROR workspace "
            "and configured sibling lanes.\n\n"
            "Local outgoing-ticket options:\n"
            "  Use --write-outgoing-tickets with --outgoing-tickets-dir to write "
            "advisory tickets in the MIRROR workspace only. These tickets are local "
            "triage notes, not external publication or legal/regulatory findings.\n\n"
            "Missing-index diagnostics:\n"
            "  A missing_artifact_index diagnostic means the ARTIFACT_INDEX.md file "
            "was unavailable for that roll-up. It does not imply that the lane has no artifacts, "
            "and it does not certify lane completeness.\n\n"
            "Local anchor validation:\n"
            "  --validate-anchors checks JSONL hash-chain continuity only. It confirms local "
            "previous_anchor_hash linkage and that external_timestamp remains null; it does not provide external timestamping, notarization, certification, or legal/regulatory assurance.\n\n"
            "Default JSON output:\n"
            "  The default command reports local MIRROR roll-up metadata only, including "
            "missing_indexes, artifact_index_diagnostics, diagnostic_summary, "
            "outgoing_tickets, and "
            "outgoing_ticket_count when ticket writing is requested. Use --compact-output "
            "for log-safe summaries that omit high-volume diagnostic arrays while preserving "
            "diagnostic_summary and explicit counts."
        ),
    )
    parser.add_argument("--timezone", default="Europe/Tallinn", help="IANA timezone for created/date fields")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=WORKSPACE,
        help="Workspace for roll-up output; defaults to the MIRROR workspace",
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=PROJECTS_ROOT,
        help="Parent directory containing sibling lanes; defaults to the parent of the MIRROR workspace",
    )
    parser.add_argument(
        "--sibling-lane",
        action="append",
        dest="sibling_lanes",
        help="Sibling lane to scan; repeatable. Defaults to the configured Zeus sibling lanes",
    )
    parser.add_argument(
        "--validate-anchors",
        action="store_true",
        help="Validate the local daily anchor JSONL hash chain and exit without creating a new anchor",
    )
    parser.add_argument(
        "--anchor-log",
        type=Path,
        default=None,
        help="Anchor JSONL path to validate or append to; defaults to daily-anchors.jsonl in the selected workspace",
    )
    parser.add_argument(
        "--validate-artifact-index",
        action="store_true",
        help="Validate a local ARTIFACT_INDEX.md and exit without creating a roll-up or anchor",
    )
    parser.add_argument(
        "--artifact-index",
        type=Path,
        default=None,
        help="ARTIFACT_INDEX.md path for --validate-artifact-index; defaults to ARTIFACT_INDEX.md in the selected workspace",
    )
    parser.add_argument(
        "--lane-root",
        type=Path,
        default=None,
        help="Lane root directory for --validate-artifact-index; defaults to the selected workspace",
    )
    parser.add_argument(
        "--lane",
        default="mirror",
        help="Lane name for --validate-artifact-index diagnostics; defaults to mirror",
    )
    parser.add_argument(
        "--write-outgoing-tickets",
        action="store_true",
        help="After building a roll-up, write local outgoing diagnostic tickets grouped by sibling lane",
    )
    parser.add_argument(
        "--compact-output",
        action="store_true",
        help=(
            "Emit a log-safe CLI payload that omits high-volume diagnostic arrays and includes "
            "artifact_index_error_count and artifact_index_diagnostic_count instead. The roll-up "
            "file on disk still contains full structured diagnostics."
        ),
    )
    parser.add_argument(
        "--outgoing-tickets-dir",
        type=Path,
        default=None,
        help="Directory for --write-outgoing-tickets output; defaults to outgoing-tickets/ in the selected workspace",
    )
    args = parser.parse_args()

    WORKSPACE = args.workspace.resolve()
    PROJECTS_ROOT = args.projects_root.resolve()
    anchor_log = (args.anchor_log or (WORKSPACE / "daily-anchors.jsonl")).resolve()
    if args.sibling_lanes:
        SIBLING_LANES = args.sibling_lanes

    if args.validate_anchors:
        errors = validate_anchor_chain(anchor_log)
        status = "fail" if errors else "ok"
        print(json.dumps({"status": status, "errors": errors}, sort_keys=True))
        return 1 if errors else 0

    if args.validate_artifact_index:
        artifact_index = (args.artifact_index or (WORKSPACE / "ARTIFACT_INDEX.md")).resolve()
        lane_root = (args.lane_root or WORKSPACE).resolve()
        errors = validate_artifact_index(artifact_index, lane_root, args.lane)
        status = "fail" if errors else "ok"
        print(json.dumps({"status": status, "errors": errors}, sort_keys=True))
        return 1 if errors else 0

    now = datetime.now(ZoneInfo(args.timezone))
    rollup, anchor, rollup_path = build_rollup(now, anchor_log)
    outgoing_tickets: list[str] = []
    if args.write_outgoing_tickets:
        outgoing_tickets = [
            str(path)
            for path in write_outgoing_tickets(
                rollup,
                ticket_dir=(args.outgoing_tickets_dir or (WORKSPACE / "outgoing-tickets")).resolve(),
                rollup_path=rollup_path,
                workspace=WORKSPACE,
            )
        ]
    anchor_errors = validate_anchor_chain(anchor_log)
    status = "fail" if anchor_errors else "ok"
    payload = {
        "status": status,
        "rollup_path": str(rollup_path.relative_to(WORKSPACE)),
        "entry_count": rollup["entry_count"],
        "merkle_root": rollup["merkle_root"],
        "rollup_sha256": anchor["rollup_sha256"],
        "previous_anchor_hash": anchor["previous_anchor_hash"],
        "anchor_errors": anchor_errors,
        "missing_indexes": rollup["missing_indexes"],
        "diagnostic_summary": rollup["diagnostic_summary"],
        "outgoing_tickets": outgoing_tickets,
        "outgoing_ticket_count": len(outgoing_tickets),
    }
    artifact_index_errors = rollup.get("artifact_index_errors", [])
    artifact_index_diagnostics = rollup.get("artifact_index_diagnostics", [])
    artifact_index_error_count = len(artifact_index_errors) if isinstance(artifact_index_errors, list) else 0
    artifact_index_diagnostic_count = (
        len(artifact_index_diagnostics) if isinstance(artifact_index_diagnostics, list) else 0
    )
    if args.compact_output:
        payload.update(
            {
                "artifact_index_error_count": artifact_index_error_count,
                "artifact_index_diagnostic_count": artifact_index_diagnostic_count,
            }
        )
    else:
        payload.update(
            {
                "artifact_index_errors": rollup["artifact_index_errors"],
                "artifact_index_diagnostics": rollup["artifact_index_diagnostics"],
            }
        )
    print(json.dumps(payload, sort_keys=True))
    return 1 if anchor_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
