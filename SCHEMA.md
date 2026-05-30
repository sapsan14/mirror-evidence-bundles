# MIRROR Evidence Bundle Schema v0.1

This format records reproducible provenance for research artifacts. It does not constitute a qualified electronic signature, qualified timestamp, or any other eIDAS-regulated trust service. Bundles produced by this tooling may be later signed using an EATF-compatible signer, but the MIRROR tooling itself does not sign.

Status: draft v0.1.
Schema identifier: `urn:tyche:mirror:bundle:0.1`.
Canonicalization identifier: `mirror-bundle-json-v0.1`.

## 1. Purpose

A MIRROR evidence bundle is a directory placed next to a substantive artifact. The bundle lets an offline verifier check that:

1. The artifact bytes match the SHA-256 digest recorded in `manifest.json`.
2. Local source copies, when present, match the SHA-256 digests recorded in `manifest.json`.
3. `claims.json` is structurally valid and each claim points to at least one evidence item.
4. Required files are present.

The verifier does not call the network, does not validate legal compliance, and does not verify cryptographic signatures in v0.1.

## 2. Directory layout

For an artifact `example.md`, the bundle directory is `example.md.bundle/`:

```text
example.md.bundle/
  manifest.json
  claims.json
  notes.md
  sources/
    <source files or URL metadata files>
```

The artifact itself remains outside the bundle by default, usually as a sibling of the `.bundle/` directory. The manifest records the artifact path relative to the bundle directory or an absolute path when a relative path is not possible.

## 3. `manifest.json`

Required fields:

- `schema`: must be `urn:tyche:mirror:bundle:0.1` for this draft.
- `bundle_version`: semantic version string; initially `0.1.0`.
- `bundle_id`: stable local identifier for this bundle, preferably `urn:tyche:mirror:bundle:<hash-or-ulid>`.
- `created_at`: UTC RFC 3339 timestamp ending in `Z`.
- `canonicalization`: must identify the deterministic rules used by tooling; initially `mirror-bundle-json-v0.1`.
- `artifact`: object with:
  - `path`: artifact path as recorded by the bundler.
  - `sha256`: lowercase SHA-256 hex digest of artifact bytes.
  - `media_type`: optional IANA media type or `text/markdown` style best-effort value.
- `sources`: array of source objects. Each source object has:
  - `id`: stable local id such as `src-001`.
  - `kind`: `file`, `url`, or `note`.
  - `path`: bundle-relative path when a local file or metadata file exists.
  - `url`: original HTTPS URL when applicable.
  - `sha256`: lowercase SHA-256 hex digest of the local source copy or URL metadata file.
  - `accessed_at`: UTC timestamp for network or local-source access.
  - `reliability`: short label such as `primary`, `official`, `local-reference`, `secondary`, or `unknown`.
- `claims_file`: normally `claims.json`.
- `notes_file`: normally `notes.md`.
- `assumptions`: array of strings; may be empty.

Optional fields:

- `previous_bundle`: prior related bundle id or digest.
- `dependencies`: array of local tool/runtime descriptors.
- `producer`: research context object. Avoid service-provision wording.

## 4. `claims.json`

`claims.json` is an object with:

- `schema`: must be `urn:tyche:mirror:claims:0.1`.
- `bundle_id`: must match `manifest.json.bundle_id`.
- `claims`: array of claim objects.

Each claim object has:

- `id`: stable local id such as `claim-001`.
- `text`: cautious substantive claim text.
- `evidence`: non-empty array of evidence pointers. Each pointer should reference a source id and, when possible, a line range, section, page, or byte range.
- `risk`: one of `low`, `medium`, `high`, or `unknown`.
- `safe_wording`: publication-safe wording for the claim.
- `notes`: optional reviewer notes.

## 5. `sources/` conventions

- Prefer local copies of cited sources when permitted.
- Every downloaded source copy must have a corresponding metadata record, either as a separate `*.meta.json` file or a `source` object in `manifest.json` with enough detail for provenance.
- URL-only references are allowed only when a local copy is not possible or not appropriate. The metadata file itself is then hashed and listed as the source path.
- Do not store credentials, private keys, personal data dumps, or confidential material in bundles.

## 6. `notes.md` conventions

`notes.md` should record:

- Bundle purpose.
- Methodology.
- Known gaps.
- Assumptions.
- Any source acquisition constraints.
- Human review notes, if any.

## 7. Verification semantics

A v0.1 verifier should:

1. Load `manifest.json` and `claims.json`.
2. Check required files exist.
3. Validate both JSON documents against the canonical JSON Schemas.
4. Recompute SHA-256 of the artifact and each local source file listed in `manifest.json`.
5. Check each claim has a supported risk value and at least one evidence pointer.
6. Emit JSON: `{"status": "ok", "errors": []}` or `{"status": "fail", "errors": [...]}`.

The verifier must not make network calls.


## 8. v0.1.0 current manifest and claims contract

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | Stable schema identifier. For v0.1 use `urn:tyche:mirror:bundle:0.1`. |
| `schema_version` | string | Tooling/schema version. For this draft use `0.1.0`. |
| `bundle_created_at` | string | RFC 3339 timestamp for bundle creation. |
| `created_by` | object | Research producer metadata; public affiliation should remain Tyche Institute, Tallinn, Estonia. |
| `attestation` | object | Unsigned MIRROR attestation boundary; `signed` and `timestamped` are always false. |

Hash fields use the current object form: `sha256`: SHA-256 hash object with `algorithm: SHA-256` and a lower-case hexadecimal `value`.

Source records use `kind`: one of `local_file`, `url_record`, or `derived_note`. Claim records use `risk`: one of `low`, `medium`, `high`, or `blocked`.

Evidence pointer fields:

- `source_id`: required source identifier or null for artifact/path-only pointers.
- `pointer`: required bundle-local evidence pointer string.
- `locator`: optional page, section, line, URL fragment, or path fragment.

## 9. Schema-level versus verifier-level pointer checks

JSON Schema can only apply portable string-shape checks to evidence pointers. It cannot compare a claim pointer with `manifest.artifact.path`, cannot rehash files, and cannot decide whether a `sources/` path is present in `manifest.sources[].path`.

The verifier therefore performs local replay checks after schema validation. An artifact pointer containing `..` is accepted only when the normalized pointer path exactly equals `manifest.artifact.path`. A schema-valid `claims.json` file is therefore necessary but not sufficient for a green verifier result.

A claim pointer to an unlisted `sources/` path, meaning a path not present in `manifest.sources[].path`, is a local replay failure. This is an integrity/structure error, not a legal or scholarly-quality finding.

## 10. Verifier output payload fixtures

The example payloads in `examples/verifier-output/` document consumer-facing verifier output:

- `good-success.json` is the green replay shape without failure-only triage fields.
- `bad-hash-integrity-failure.json` is a deterministic local integrity failure shape.
- `bad-unsafe-assurance-policy-failure.json` is a policy guardrail failure shape for unsafe public assurance wording.
- `mixed-policy-and-integrity-failure.json` is a mixed failure payload; a single red result may carry both integrity/structure and policy guardrail classes.

Success payloads are intentionally minimal. Consumers must not infer claim truth, legal compliance, authorship, publication readiness, or scholarly quality from the absence of `failure_kinds`; the absence of `failure_kinds` does not make success an endorsement. Failure classes are triage labels and not misconduct findings.

## 11. Daily roll-up and anchor payload schemas

Daily roll-up payload schema: `schema/daily-roll-up.schema.json` covers local daily roll-up JSON such as `examples/daily-roll-up-payload/default-rollup.json`. The roll-up does not certify lane completeness and does not provide external timestamping.

Daily anchor payload schema: `schema/daily-anchor.schema.json` covers append-only anchor records with `external_timestamp` set to null. `examples/daily-anchor-payload/default-anchor.json` is the positive fixture. The anchor does not provide external timestamping, does not certify lane completeness, and is not a regulated trust-service output.
