#!/usr/bin/env python3
"""Verify a MIRROR v0.1 evidence bundle using only local files.

This reference verifier rehashes local bundle files and validates the local
MIRROR v0.1.0 JSON Schemas. It does not perform network retrieval, signing,
timestamping, certification, or trust-service operations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import jsonschema

ROOT = Path(__file__).resolve().parent
MANIFEST_SCHEMA_PATH = ROOT / "schema" / "manifest.schema.json"
CLAIMS_SCHEMA_PATH = ROOT / "schema" / "claims.schema.json"
FORBIDDEN_PUBLIC_EMPLOYER_TOKEN = "forbiddencorp"
UNSAFE_ASSURANCE_PHRASES = (
    "certifies compliance",
    "proves legal compliance",
    "official audit",
    "guarantees",
    "qualified electronic signature",
    "qualified timestamp",
    "qualified trust service",
    "regulated trust service",
)


class VerificationContext:
    def __init__(self, bundle_dir: Path):
        self.bundle_dir = bundle_dir
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)


def sha256_hex_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str, ctx: VerificationContext) -> dict[str, Any] | None:
    if not path.is_file():
        ctx.add(f"missing file: {label}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        ctx.add(f"{label}: invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(value, dict):
        ctx.add(f"{label}: must be a JSON object")
        return None
    return value


def load_schema(path: Path, label: str, ctx: VerificationContext) -> dict[str, Any] | None:
    schema = load_json(path, label, ctx)
    if schema is None:
        return None
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        ctx.add(f"{label}: invalid draft-07 schema: {exc.message}")
        return None
    return schema


def format_schema_path(error: jsonschema.ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return path or "<root>"


def validate_against_schema(instance: dict[str, Any], schema: dict[str, Any], label: str, ctx: VerificationContext) -> None:
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(instance), key=lambda err: (list(err.absolute_path), err.message)):
        ctx.add(f"{label}.{format_schema_path(error)}: {error.message}")


def is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def is_hash_object(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("algorithm") == "SHA-256"
        and is_sha256_hex(value.get("value"))
    )


def expected_hash(value: Any) -> str | None:
    """Return a canonical SHA-256 hex digest from v0.1 schema strings or legacy objects."""
    if is_sha256_hex(value):
        return value
    if is_hash_object(value):
        return value["value"]
    return None


def safe_bundle_path(
    bundle_dir: Path,
    relative_path: Any,
    label: str,
    ctx: VerificationContext,
    *,
    allow_parent_reference: bool = False,
) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        ctx.add(f"{label}: must be a non-empty relative path")
        return None
    path = Path(relative_path)
    if path.is_absolute() or relative_path in {".", ""}:
        ctx.add(f"{label}: must be a relative path")
        return None
    if ".." in path.parts and not allow_parent_reference:
        ctx.add(f"{label}: must be a relative path inside the bundle")
        return None
    root = bundle_dir.resolve()
    candidate = (bundle_dir / path).resolve(strict=False)
    if allow_parent_reference:
        artifact_root = bundle_dir.parent.resolve()
        try:
            candidate.relative_to(artifact_root)
        except ValueError:
            ctx.add(f"{label}: must resolve inside the bundle directory or its parent artifact directory")
            return None
    else:
        try:
            candidate.relative_to(root)
        except ValueError:
            ctx.add(f"{label}: resolves outside the bundle")
            return None
    return bundle_dir / path


def verify_hashed_file(
    bundle_dir: Path,
    relative_path: Any,
    hash_value: Any,
    label: str,
    ctx: VerificationContext,
    *,
    allow_parent_reference: bool = False,
) -> None:
    path = safe_bundle_path(
        bundle_dir,
        relative_path,
        f"{label}.path",
        ctx,
        allow_parent_reference=allow_parent_reference,
    )
    expected = expected_hash(hash_value)
    if expected is None:
        ctx.add(f"{label}.sha256: must be a SHA-256 hash object")
    if path is None:
        return
    display_path = str(relative_path)
    if not path.is_file():
        ctx.add(f"missing file: {display_path}")
        return
    if expected is None:
        return
    actual = sha256_hex_file(path)
    if actual != expected:
        ctx.add(f"hash mismatch for {display_path}: expected {expected}, got {actual}")


def normalize_relative_path_text(path_text: str) -> str:
    normalized_parts: list[str] = []
    for part in Path(path_text).parts:
        if part in {"", "."}:
            continue
        normalized_parts.append(part)
    return "/".join(normalized_parts)


def verify_manifest_sources_are_unique(bundle_dir: Path, manifest: dict[str, Any], ctx: VerificationContext) -> None:
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return
    first_seen_ids: dict[str, int] = {}
    first_seen_paths: dict[str, int] = {}
    first_seen_normalized_paths: dict[str, int] = {}
    sources_root = (bundle_dir / "sources").resolve(strict=False)
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        if isinstance(source_id, str):
            if source_id in first_seen_ids:
                ctx.add(
                    f"manifest.sources[{index}].id: duplicate source id {source_id} first defined at manifest.sources[{first_seen_ids[source_id]}].id"
                )
            else:
                first_seen_ids[source_id] = index
        source_path = source.get("path")
        if isinstance(source_path, str):
            source_path_obj = Path(source_path)
            normalized_source_path = normalize_relative_path_text(source_path)
            if ".." in source_path_obj.parts:
                ctx.add(f"manifest.sources[{index}].path: source records must not contain parent-directory segments")
            if not normalized_source_path.startswith("sources/"):
                ctx.add(f"manifest.sources[{index}].path: source records must be stored under sources/")
            if not source_path_obj.is_absolute():
                resolved_source_path = (bundle_dir / source_path).resolve(strict=False)
                try:
                    resolved_source_path.relative_to(sources_root)
                except ValueError:
                    ctx.add(f"manifest.sources[{index}].path: source records must resolve under sources/")
            source_path_seen_before = source_path in first_seen_paths
            if source_path_seen_before:
                ctx.add(
                    f"manifest.sources[{index}].path: duplicate source path {source_path} first defined at manifest.sources[{first_seen_paths[source_path]}].path"
                )
            else:
                first_seen_paths[source_path] = index
            if normalized_source_path in first_seen_normalized_paths and not source_path_seen_before:
                ctx.add(
                    f"manifest.sources[{index}].path: duplicate normalized source path {normalized_source_path} "
                    f"first defined at manifest.sources[{first_seen_normalized_paths[normalized_source_path]}].path"
                )
            else:
                first_seen_normalized_paths.setdefault(normalized_source_path, index)


def is_https_url_with_host(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def verify_manifest_assumption_ids_are_unique(manifest: dict[str, Any], ctx: VerificationContext) -> None:
    assumptions = manifest.get("assumptions")
    if not isinstance(assumptions, list):
        return
    first_seen_ids: dict[str, int] = {}
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            continue
        assumption_id = assumption.get("id")
        if isinstance(assumption_id, str):
            if assumption_id in first_seen_ids:
                ctx.add(
                    f"manifest.assumptions[{index}].id: duplicate assumption id {assumption_id} "
                    f"first defined at manifest.assumptions[{first_seen_ids[assumption_id]}].id"
                )
            else:
                first_seen_ids[assumption_id] = index


def public_text_names_forbidden_employer(value: Any) -> bool:
    return isinstance(value, str) and FORBIDDEN_PUBLIC_EMPLOYER_TOKEN in value.casefold()


def unsafe_assurance_phrase(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.casefold().split())
    negation_markers = ("not ", "no ", "without ", "does not ", "do not ")
    sentence_boundaries = (". ", "! ", "? ")
    contrast_markers = (" but ", " however ", " nevertheless ", " nonetheless ", "; but ")
    for phrase in UNSAFE_ASSURANCE_PHRASES:
        start = normalized.find(phrase)
        while start != -1:
            prefix_window = normalized[max(0, start - 256) : start]
            same_sentence_prefix = prefix_window
            for boundary in sentence_boundaries:
                boundary_index = same_sentence_prefix.rfind(boundary)
                if boundary_index != -1:
                    same_sentence_prefix = same_sentence_prefix[boundary_index + len(boundary) :]

            negation_hits = [
                (same_sentence_prefix.rfind(marker), marker) for marker in negation_markers
            ]
            last_negation, last_negation_marker = max(negation_hits, key=lambda item: item[0])
            last_contrast = max(same_sentence_prefix.rfind(marker) for marker in contrast_markers)
            not_only_pos = same_sentence_prefix.rfind("not only")
            text_after_negation = ""
            if last_negation != -1:
                text_after_negation = same_sentence_prefix[
                    last_negation + len(last_negation_marker) :
                ]
            subject_restart_after_negation = any(
                restart in text_after_negation
                for restart in (
                    " and this ",
                    " and the ",
                    " and it ",
                    " and we ",
                    " and tyche ",
                    " and mirror ",
                    " and bundle ",
                    " and package ",
                )
            )
            negated_in_same_clause = (
                last_negation != -1
                and last_negation > last_contrast
                and not not_only_pos >= last_negation
                and not subject_restart_after_negation
            )
            if not negated_in_same_clause:
                return phrase
            start = normalized.find(phrase, start + 1)
    return None


def verify_created_by_public_affiliation(manifest: dict[str, Any], ctx: VerificationContext) -> None:
    created_by = manifest.get("created_by")
    if not isinstance(created_by, dict):
        return
    for field, value in created_by.items():
        if not public_text_names_forbidden_employer(value):
            continue
        if field == "affiliation":
            ctx.add(
                "manifest.created_by.affiliation: must not name a current or former employer; "
                "use Tyche Institute, Tallinn, Estonia for public MIRROR artifacts"
            )
        else:
            ctx.add(
                f"manifest.created_by.{field}: "
                "must not name a current or former employer in public MIRROR metadata"
            )


def verify_public_manifest_text_avoids_unsafe_assurance_language(manifest: dict[str, Any], ctx: VerificationContext) -> None:
    compatibility = manifest.get("compatibility")
    if not isinstance(compatibility, dict):
        return
    statement = compatibility.get("statement")
    phrase = unsafe_assurance_phrase(statement)
    if phrase is not None:
        ctx.add(f"manifest.compatibility.statement: must not use unsafe assurance language: {phrase}")


def verify_public_claim_text_avoids_named_employer(claims_doc: dict[str, Any], ctx: VerificationContext) -> None:
    claims = claims_doc.get("claims")
    if not isinstance(claims, list):
        return
    for claim_index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        for field in ("text", "safe_wording"):
            value = claim.get(field)
            if public_text_names_forbidden_employer(value):
                ctx.add(
                    f"claims.json.claims[{claim_index}].{field}: "
                    "must not name a current or former employer in public MIRROR claim text"
                )
            phrase = unsafe_assurance_phrase(value)
            if phrase is not None:
                ctx.add(
                    f"claims.json.claims[{claim_index}].{field}: "
                    f"must not use unsafe assurance language: {phrase}"
                )


def verify_manifest_source_kind_requirements(bundle_dir: Path, manifest: dict[str, Any], ctx: VerificationContext) -> None:
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_kind = source.get("kind")
        if source_kind == "url_record":
            url = source.get("url")
            if not is_https_url_with_host(url):
                ctx.add(f"manifest.sources[{index}].url: url_record sources must include an HTTPS url with a host")
                continue
            descriptor_path = safe_bundle_path(bundle_dir, source.get("path"), f"manifest.sources[{index}].path", ctx)
            if descriptor_path is None or not descriptor_path.is_file():
                continue
            try:
                descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                ctx.add(
                    f"manifest.sources[{index}].url: url_record descriptor has invalid JSON "
                    f"at line {exc.lineno} column {exc.colno}: {exc.msg}"
                )
                continue
            if not isinstance(descriptor, dict):
                ctx.add(f"manifest.sources[{index}].url: url_record descriptor must be a JSON object")
                continue
            descriptor_url = descriptor.get("url")
            if descriptor_url != url:
                ctx.add(
                    f"manifest.sources[{index}].url: url_record descriptor url {descriptor_url} "
                    f"does not match manifest url {url}"
                )
            descriptor_accessed_at = descriptor.get("accessed_at")
            manifest_accessed_at = source.get("accessed_at")
            if descriptor_accessed_at != manifest_accessed_at:
                ctx.add(
                    f"manifest.sources[{index}].accessed_at: url_record descriptor accessed_at {descriptor_accessed_at} "
                    f"does not match manifest accessed_at {manifest_accessed_at}"
                )
        elif source_kind == "local_file":
            if source.get("id", "").startswith("S-") and not isinstance(source.get("source_path"), str):
                ctx.add(f"manifest.sources[{index}].source_path: local_file sources must include a source_path")
            continue
        elif source_kind == "derived_note":
            notes = source.get("notes")
            source_path = source.get("source_path")
            if not ((isinstance(notes, str) and notes) or (isinstance(source_path, str) and source_path)):
                ctx.add(
                    f"manifest.sources[{index}]: derived_note sources must include notes or source_path "
                    "explaining derivation provenance"
                )


def verify_manifest_hashes(bundle_dir: Path, manifest: dict[str, Any], ctx: VerificationContext) -> None:
    artifact = manifest.get("artifact")
    if isinstance(artifact, dict):
        verify_hashed_file(
            bundle_dir,
            artifact.get("path"),
            artifact.get("sha256"),
            "manifest.artifact",
            ctx,
            allow_parent_reference=True,
        )

    for index, source in enumerate(manifest.get("sources", [])):
        if isinstance(source, dict):
            verify_hashed_file(bundle_dir, source.get("path"), source.get("sha256"), f"manifest.sources[{index}]", ctx)

    claims_file = manifest.get("claims_file")
    if isinstance(claims_file, dict):
        verify_hashed_file(bundle_dir, claims_file.get("path"), claims_file.get("sha256"), "manifest.claims_file", ctx)


def evidence_pointer_path_part(pointer: str) -> str:
    return pointer.split("#", 1)[0]


def normalize_evidence_pointer_path(pointer: str) -> tuple[str, bool]:
    """Return the path-like portion and whether it used `artifact:`.

    MIRROR v0.1.0 allows bare bundle-relative pointers such as
    `sources/source-1.txt#quote` and the explicit artifact pseudo-scheme
    `artifact:artifact.md#claim`. The pseudo-scheme is not a filesystem root;
    strip it before checking path safety. Parent references are accepted only
    for artifact pointers that exactly match `manifest.artifact.path`, because
    v0.1.0 permits the artifact itself to live next to its bundle.
    """

    path_part = evidence_pointer_path_part(pointer)
    if path_part.startswith("artifact:"):
        return path_part.removeprefix("artifact:"), True
    return path_part, False


def is_unsafe_evidence_pointer(pointer: Any, artifact_path: Any = None) -> bool:
    if not isinstance(pointer, str):
        return False
    path_part, is_artifact_pointer = normalize_evidence_pointer_path(pointer)
    if not path_part:
        return False
    path = Path(path_part)
    if path.is_absolute():
        return True
    if ".." in path.parts:
        if not (is_artifact_pointer and isinstance(artifact_path, str)):
            return True
        return normalize_relative_path_text(path_part) != normalize_relative_path_text(artifact_path)
    return False


def verify_claim_ids_are_unique(claims_doc: dict[str, Any], ctx: VerificationContext) -> None:
    claims = claims_doc.get("claims")
    if not isinstance(claims, list):
        return
    first_seen_ids: dict[str, int] = {}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("id")
        if isinstance(claim_id, str):
            if claim_id in first_seen_ids:
                ctx.add(
                    f"claims.json.claims[{index}].id: duplicate claim id {claim_id} first defined at claims.json.claims[{first_seen_ids[claim_id]}].id"
                )
            else:
                first_seen_ids[claim_id] = index


def verify_evidence_source_ids(manifest: dict[str, Any], claims_doc: dict[str, Any], ctx: VerificationContext) -> None:
    sources = manifest.get("sources")
    known_ids = {source.get("id") for source in sources if isinstance(source, dict)} if isinstance(sources, list) else set()
    known_ids.discard(None)
    source_paths_by_id = {
        source.get("id"): source.get("path")
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("id"), str) and isinstance(source.get("path"), str)
    } if isinstance(sources, list) else {}
    normalized_source_paths_by_id = {
        source_id: normalize_relative_path_text(source_path)
        for source_id, source_path in source_paths_by_id.items()
    }
    known_normalized_source_paths = set(normalized_source_paths_by_id.values())
    artifact = manifest.get("artifact")
    artifact_path = artifact.get("path") if isinstance(artifact, dict) else None
    claims = claims_doc.get("claims")
    if not isinstance(claims, list):
        return
    for claim_index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not isinstance(claim.get("evidence"), list):
            continue
        for evidence_index, evidence in enumerate(claim["evidence"]):
            if not isinstance(evidence, dict):
                continue
            source_id = evidence.get("source_id")
            pointer = evidence.get("pointer")
            if source_id is not None and source_id not in known_ids:
                ctx.add(
                    f"claims.json.claims[{claim_index}].evidence[{evidence_index}].source_id: unknown source id {source_id}"
                )
            if isinstance(pointer, str):
                pointer_path, is_artifact_pointer = normalize_evidence_pointer_path(pointer)
                normalized_pointer_path = normalize_relative_path_text(pointer_path) if pointer_path else ""
                if not is_artifact_pointer and urlparse(pointer_path).scheme:
                    ctx.add(
                        f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: "
                        f"unsupported external-scheme evidence pointer {pointer}"
                    )
                if (
                    not isinstance(source_id, str)
                    and not is_artifact_pointer
                    and pointer_path.startswith("sources/")
                    and normalized_pointer_path not in known_normalized_source_paths
                ):
                    ctx.add(
                        f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: "
                        f"pointer references unlisted source path {pointer_path}"
                    )
                if isinstance(source_id, str) and source_id in source_paths_by_id:
                    expected_source_path = source_paths_by_id[source_id]
                    normalized_expected_source_path = normalized_source_paths_by_id[source_id]
                    if pointer_path == source_id:
                        continue
                    if pointer_path and normalized_pointer_path != normalized_expected_source_path:
                        if not is_artifact_pointer and normalized_pointer_path in known_normalized_source_paths:
                            ctx.add(
                                f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: source_id {source_id} "
                                f"points to {expected_source_path} but pointer references {pointer_path}"
                            )
                        elif not is_artifact_pointer and pointer_path.startswith("sources/"):
                            ctx.add(
                                f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: source_id {source_id} "
                                f"points to {expected_source_path} but pointer references unlisted source path {pointer_path}"
                            )
                        else:
                            ctx.add(
                                f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: source_id {source_id} "
                                f"points to {expected_source_path} but pointer references non-source path {pointer_path}"
                            )
            if is_unsafe_evidence_pointer(pointer, artifact_path):
                ctx.add(
                    f"claims.json.claims[{claim_index}].evidence[{evidence_index}]: unsafe evidence pointer {pointer}"
                )


def verify_required_bundle_entries(bundle_dir: Path, ctx: VerificationContext) -> None:
    if not (bundle_dir / "notes.md").is_file():
        ctx.add("missing file: notes.md")


def verify_bundle(bundle_dir: Path) -> list[str]:
    ctx = VerificationContext(bundle_dir)
    if not bundle_dir.is_dir():
        return [f"bundle directory not found: {bundle_dir}"]

    verify_required_bundle_entries(bundle_dir, ctx)
    manifest_schema = load_schema(MANIFEST_SCHEMA_PATH, "schema/manifest.schema.json", ctx)
    claims_schema = load_schema(CLAIMS_SCHEMA_PATH, "schema/claims.schema.json", ctx)
    manifest = load_json(bundle_dir / "manifest.json", "manifest.json", ctx)

    claims_doc: dict[str, Any] | None = None
    if manifest is not None:
        if manifest_schema is not None:
            validate_against_schema(manifest, manifest_schema, "manifest.json", ctx)
        verify_manifest_sources_are_unique(bundle_dir, manifest, ctx)
        verify_manifest_assumption_ids_are_unique(manifest, ctx)
        verify_created_by_public_affiliation(manifest, ctx)
        verify_public_manifest_text_avoids_unsafe_assurance_language(manifest, ctx)
        verify_manifest_source_kind_requirements(bundle_dir, manifest, ctx)
        verify_manifest_hashes(bundle_dir, manifest, ctx)
        claims_file = manifest.get("claims_file")
        claims_relative_path = claims_file.get("path") if isinstance(claims_file, dict) else "claims.json"
        claims_path = safe_bundle_path(bundle_dir, claims_relative_path, "manifest.claims_file.path", ctx)
        if claims_path is not None:
            claims_doc = load_json(claims_path, "claims.json", ctx)
    else:
        claims_doc = load_json(bundle_dir / "claims.json", "claims.json", ctx)

    if claims_doc is not None:
        if claims_schema is not None:
            validate_against_schema(claims_doc, claims_schema, "claims.json", ctx)
        verify_claim_ids_are_unique(claims_doc, ctx)
        verify_public_claim_text_avoids_named_employer(claims_doc, ctx)
        if manifest is not None:
            verify_evidence_source_ids(manifest, claims_doc, ctx)

    return sorted(set(ctx.errors))


def classify_failure_kinds(errors: list[str]) -> list[str]:
    """Classify verifier failures for reviewer-facing triage.

    The classes are deliberately coarse: they distinguish local public-policy
    guardrail failures from ordinary integrity or structure failures without
    turning either class into certification, audit, or publication-readiness
    language.
    """

    kinds: set[str] = set()
    for error in errors:
        if (
            "must not use unsafe assurance language" in error
            or "must not name a current or former employer" in error
        ):
            kinds.add("policy_guardrail")
        else:
            kinds.add("integrity_or_structure")
    return sorted(kinds)


def build_payload(errors: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"errors": errors, "status": "fail" if errors else "ok"}
    if errors:
        payload["failure_kinds"] = classify_failure_kinds(errors)
        payload["note"] = (
            "failure_kinds distinguish deterministic local integrity/structure failures "
            "from policy guardrail failures; they do not certify claim truth or publication readiness"
        )
    return payload


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a MIRROR v0.1 evidence bundle without network calls.")
    parser.add_argument("bundle_dir", type=Path, help="Path to the <artifact>.bundle directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    errors = verify_bundle(args.bundle_dir.expanduser().resolve())
    print(json.dumps(build_payload(errors), sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
