# Roll-up CLI Payload Fixture Policy

This directory contains semantic fixtures for the MIRROR roll-up CLI payload contract.
The fixtures support local replay and vocabulary-boundary regression tests only; they do not certify lane completeness, publication readiness, audit status, legal status, or regulatory compliance.

## Current fixtures

- `default-output-required-fields.json` is the positive fixture. It records the expected default CLI JSON payload fields, a compact `diagnostic_summary` routing example, and cautious interpretation language for local replay.
- `bad-unsafe-boundary.json` is the broad negative fixture. It records unsafe completeness and publication-readiness wording that the schema should reject.
- `bad-unsafe-diagnostic-summary-example.json` is the compact-summary negative fixture. It records unsafe guarantee language even though the required non-certification phrase is present, and the schema should reject it.

## Update rule

When adding a future `*.json` fixture in this directory:

1. Mention the fixture by file name in `paper/methodology.md`.
2. Include it as a source in `paper/methodology.md.bundle/manifest.json` when the methodology relies on it.
3. Add or update a project claim in `CLAIMS.md` if the fixture changes MIRROR's substantive vocabulary boundary.
4. Preserve the explicit safe boundary phrase `do not certify` for accepted fixture metadata that explains interpretation scope.
5. Keep wording tied to local replay and triage. Avoid claims of completeness, publication readiness, official audit, legal compliance, or any eIDAS-regulated trust service.

The policy is intentionally local: it helps keep MIRROR fixture changes coordinated across tests, methodology, claims, and evidence bundles without turning fixtures into publication or compliance evidence.
