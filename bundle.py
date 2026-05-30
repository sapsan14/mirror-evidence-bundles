#!/usr/bin/env python3
"""Create a MIRROR v0.1 evidence bundle for a local research artifact.

This reference bundler records reproducible local provenance only. It does not
sign, timestamp, certify, or contact external services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BUNDLE_SCHEMA_ID = "urn:tyche:mirror:bundle:0.1"
CLAIMS_SCHEMA_ID = "urn:tyche:mirror:claims:0.1"
SCHEMA_VERSION = "0.1.0"
TOOL_NAME = "bundle.py"
TOOL_VERSION = "0.1.0"
SAFE_COMPATIBILITY_STATEMENT = (
    "This MIRROR bundle records reproducible provenance for research artifacts. "
    "It is unsigned and is not a qualified electronic signature, qualified "
    "timestamp, or other eIDAS-regulated trust service."
)
ROOT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today() -> str:
    return date.today().isoformat()


def sha256_hex_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def public_source_path(path: Path) -> str:
    """Return a public-safe source path for bundle metadata."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "omitted-private-workspace-path"


def media_type_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def slugify(value: str, default: str) -> str:
    stem = Path(value).stem if not is_https_url(value) else (urlparse(value).netloc or default)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._")
    return slug[:48] or default


def source_filename(source_id: str, source: str, *, legacy: bool = False, index: int = 1) -> str:
    if legacy:
        if is_https_url(source):
            return f"source-{index}.url.json"
        suffix = Path(source).suffix or ".bin"
        return f"source-{index}{suffix}"
    if is_https_url(source):
        return f"{source_id}-{slugify(source, 'url')}.url.json"
    suffix = Path(source).suffix or ".bin"
    return f"{source_id}-{slugify(source, 'source')}{suffix}"


def source_meta_filename(source_file: str) -> str:
    return f"{source_file}.meta.json"


def validate_input_files(artifact: Path, sources: list[str]) -> None:
    if not artifact.is_file():
        raise ValueError(f"artifact is not a readable file: {artifact}")
    for source in sources:
        if is_https_url(source):
            continue
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise ValueError(f"source is not a readable file or HTTPS URL: {source}")


def hash_value(path: Path, *, legacy: bool = False) -> str | dict[str, str]:
    value = sha256_hex_file(path)
    return {"algorithm": "SHA-256", "value": value}


def copy_artifact(artifact: Path, bundle_dir: Path, *, legacy: bool = False) -> dict:
    if legacy:
        dest = bundle_dir / artifact.name
        shutil.copy2(artifact, dest)
        return {
            "path": artifact.name,
            "sha256": hash_value(dest, legacy=True),
            "media_type": media_type_for(dest),
            "title": artifact.stem,
        }
    artifact_dir = bundle_dir / "artifact"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dest = artifact_dir / artifact.name
    shutil.copy2(artifact, dest)
    return {
        "path": f"artifact/{artifact.name}",
        "sha256": hash_value(dest, legacy=False),
        "media_type": media_type_for(dest),
        "title": artifact.stem,
    }


def copy_or_record_source(source: str, bundle_dir: Path, index: int, created_at: str, *, legacy: bool = False) -> dict:
    source_dir = bundle_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_id = f"S-{index:04d}" if legacy else f"S{index}"
    file_name = source_filename(source_id, source, legacy=legacy, index=index)
    dest = source_dir / file_name
    rel_path = f"sources/{file_name}"
    accessed = today()

    if is_https_url(source):
        descriptor = {
            "url": source,
            "accessed_at": accessed if legacy else accessed,
            "accessed": accessed,
            "retrieved": False,
            "retrieved_by": f"{TOOL_NAME} {TOOL_VERSION}",
            "notes": "URL descriptor only; remote bytes were not fetched by MIRROR bundling.",
        }
        write_json(dest, descriptor)
        sha = hash_value(dest, legacy=legacy)
        meta = {
            "source_id": source_id,
            "url": source,
            "accessed": accessed,
            "http_status": None,
            "sha256": sha,
            "retrieved_by": f"{TOOL_NAME} {TOOL_VERSION}",
            "notes": "Offline descriptor generated without network retrieval.",
        }
        write_json(source_dir / source_meta_filename(file_name), meta)
        record = {
            "id": source_id,
            "kind": "url_record" if legacy else "url_snapshot",
            "title": source,
            "reliability": "unknown",
            "path": rel_path,
            "sha256": sha,
            "url": source,
            "accessed": accessed,
            "notes": "Descriptor file only; verification remains offline and does not re-fetch the URL.",
        }
        if legacy:
            record["accessed_at"] = accessed
            record["source_path"] = source
        return record

    source_path = Path(source).expanduser().resolve()
    public_path = public_source_path(source_path)
    shutil.copy2(source_path, dest)
    sha = hash_value(dest, legacy=legacy)
    meta = {
        "source_id": source_id,
        "original_path": public_path,
        "accessed": accessed,
        "http_status": None,
        "sha256": sha,
        "retrieved_by": f"{TOOL_NAME} {TOOL_VERSION}",
        "notes": "Local file copied into the bundle.",
    }
    write_json(source_dir / source_meta_filename(file_name), meta)
    record = {
        "id": source_id,
        "kind": "local_file",
        "title": source_path.name,
        "reliability": "primary",
        "path": rel_path,
        "sha256": sha,
        "accessed": accessed,
        "notes": f"Copied from public fixture path {public_path}.",
    }
    if legacy:
        record["source_path"] = public_path
    return record


def legacy_mode_for_evidence(evidence: list[str]) -> bool:
    return any(value.strip().startswith("sources/") or re.fullmatch(r"S-[0-9]{4}(:.*)?", value.strip()) for value in evidence)


def parse_evidence(value: str, *, legacy: bool = False) -> dict:
    """Parse evidence as SOURCE_ID[:locator], bundle path, or artifact=PATH[:locator]."""
    raw = value.strip()
    if not raw:
        raise ValueError("--evidence must not be empty")
    if legacy:
        if re.fullmatch(r"S-[0-9]{4}", raw):
            return {"source_id": raw, "pointer": raw}
        if raw.startswith("sources/"):
            return {"source_id": None, "pointer": raw}
        if raw.startswith("artifact="):
            return {"source_id": None, "pointer": "artifact:" + raw[len("artifact="):]} 
    if raw.startswith("artifact="):
        rest = raw[len("artifact=") :]
        path, sep, locator = rest.partition(":")
        pointer = {"source_id": None, "artifact_path": path, "pointer": f"artifact:{path}"}
        if sep and locator:
            pointer["locator"] = locator
        return pointer
    source_id, sep, locator = raw.partition(":")
    if not re.fullmatch(r"S[0-9]+[A-Za-z0-9_-]*", source_id):
        raise ValueError(f"evidence pointer must start with a source id like S1 or artifact=path: {value}")
    pointer = {"source_id": source_id, "pointer": source_id}
    if sep and locator:
        pointer["locator"] = locator
    return pointer


def build_claims(claims: list[str], evidence: list[str], *, legacy: bool = False) -> dict:
    if len(claims) != len(evidence):
        raise ValueError("--claim requires a matching --evidence for each claim")
    claim_entries = []
    for index, (claim, evidence_value) in enumerate(zip(claims, evidence), start=1):
        claim_entries.append(
            {
                "id": f"C-{index:04d}" if legacy else f"C{index}",
                "text": claim,
                "evidence": [parse_evidence(evidence_value, legacy=legacy)],
                "risk": "medium",
                "safe_wording": claim,
                "review_status": "draft",
                "notes": "Generated from CLI arguments; review before publication.",
            }
        )
    return {"schema": CLAIMS_SCHEMA_ID, "schema_id": CLAIMS_SCHEMA_ID, "schema_version": SCHEMA_VERSION, "claims": claim_entries}


def write_notes(bundle_dir: Path, created_at: str) -> None:
    (bundle_dir / "notes.md").write_text(
        "# MIRROR bundle notes\n\n"
        "## Purpose\n\n"
        "This bundle records local research provenance for offline reproducibility review.\n\n"
        "## Methodology\n\n"
        f"Generated by `{TOOL_NAME}` version {TOOL_VERSION} at {created_at}. The artifact and local sources were copied into the bundle and hashed with SHA-256. HTTPS inputs, when supplied, are recorded as local descriptor files without network retrieval.\n\n"
        "## Safety caveat\n\n"
        f"{SAFE_COMPATIBILITY_STATEMENT}\n\n"
        "## Known gaps\n\n"
        "Claim wording is mechanically recorded from command-line arguments and requires human review before publication.\n",
        encoding="utf-8",
    )


def make_bundle(artifact: Path, output_dir: Path | None, sources: list[str], claims: list[str], evidence: list[str]) -> Path:
    artifact = artifact.expanduser().resolve()
    validate_input_files(artifact, sources)
    if len(claims) != len(evidence):
        raise ValueError("--claim requires a matching --evidence for each claim")

    bundle_dir = output_dir.expanduser().resolve() if output_dir else artifact.with_name(artifact.name + ".bundle").resolve()
    if bundle_dir.exists() and any(bundle_dir.iterdir()):
        raise ValueError(f"output bundle directory already exists and is not empty: {bundle_dir}")

    created_at = utc_now()
    legacy = legacy_mode_for_evidence(evidence)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    artifact_entry = copy_artifact(artifact, bundle_dir, legacy=legacy)
    source_entries = [copy_or_record_source(source, bundle_dir, index, created_at, legacy=legacy) for index, source in enumerate(sources, start=1)]
    claims_doc = build_claims(claims, evidence, legacy=legacy)
    claims_path = bundle_dir / "claims.json"
    write_json(claims_path, claims_doc)
    write_notes(bundle_dir, created_at)

    manifest = {
        "schema": BUNDLE_SCHEMA_ID,
        "schema_id": BUNDLE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "created": created_at,
        "bundle_created_at": created_at,
        "created_by": {
            "name": "Tyche Institute",
            "affiliation": "Tyche Institute, Tallinn, Estonia",
            "location": "Tallinn, Estonia",
            "tool": f"{TOOL_NAME} {TOOL_VERSION}",
            "orcid": "0000-0003-2452-7096",
            "lane": "mirror",
        },
        "artifact": artifact_entry,
        "sources": source_entries,
        "claims_file": {"path": "claims.json", "sha256": hash_value(claims_path, legacy=legacy)},
        "assumptions": [
            {
                "id": "A-0001" if legacy else "A1",
                "text": "Generated claims require human review before publication.",
                "impact": "medium",
            },
            {
                "id": "A-0002" if legacy else "A2",
                "text": "HTTPS source inputs are recorded as descriptor files and are not fetched by this bundler.",
                "impact": "low",
            },
        ],
        "attestation": {"signed": False, "timestamped": False, "signature_profile": None},
        "verification": {
            "network_required": False,
            "offline_only": True,
            "hash_algorithm": "sha256",
            "semantics": ["offline_hash_replay", "schema_validation"],
            "checks": [
                "manifest_schema",
                "claims_schema",
                "artifact_hash",
                "claims_hash",
                "source_hashes",
                "claim_source_links",
                "notes_present",
            ],
        },
        "compatibility": {
            "eatf_compatible_shape": True,
            "signed": False,
            "timestamped": False,
            "signature_profile": "none",
            "statement": SAFE_COMPATIBILITY_STATEMENT,
        },
    }
    write_json(bundle_dir / "manifest.json", manifest)
    return bundle_dir


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a MIRROR v0.1 evidence bundle.")
    parser.add_argument("artifact", help="Path to the artifact file to bundle")
    parser.add_argument(
        "--output-dir",
        "--output",
        "-o",
        dest="output_dir",
        type=Path,
        help="Bundle directory to create; defaults to <artifact>.bundle",
    )
    parser.add_argument("--source", action="append", default=[], help="Repeatable local source path or HTTPS URL descriptor")
    parser.add_argument("--claim", action="append", default=[], help="Repeatable substantive claim text")
    parser.add_argument("--evidence", action="append", default=[], help="Evidence pointer for the corresponding --claim, e.g. S1:line 4")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        bundle_dir = make_bundle(Path(args.artifact), args.output_dir, args.source, args.claim, args.evidence)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status": "ok", "bundle": str(bundle_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
