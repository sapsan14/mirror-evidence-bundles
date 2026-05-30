# Methodology-bundle coverage fixture policy

This directory contains compact semantic fixtures for `methodology_bundle_coverage.py` and `schema/methodology-bundle-coverage.schema.json`.

Current fixtures:

- `default-output.json` is the positive compact-output fixture. It should match `python methodology_bundle_coverage.py --compact` for the current workspace when the methodology bundle covers the required semantic fixture sources.
- `bad-unsafe-boundary.json` is the negative vocabulary-boundary fixture. It is intentionally schema-shaped but uses unsafe interpretation text that the schema must reject.
- `missing-manifest.json` is the negative graceful-failure fixture. It should match the compact JSON emitted when the methodology helper cannot find `paper/methodology.md.bundle/manifest.json`, demonstrating that a missing methodology bundle manifest becomes a schema-shaped failure payload rather than a traceback.

Update rules:

1. Keep fixtures small enough for reviewers to inspect in full.
2. When `methodology_bundle_coverage.py` output fields change, update the schema, positive fixture, tests, and any methodology or claim text that relies on the changed semantics in the same bounded iteration.
3. Negative fixtures should encode plausible over-interpretations that MIRROR must reject, especially wording that implies certification, audit status, publication readiness, lane completeness, or legal/regulatory status.
4. `default-output.json` is excluded from the required-source summary emitted by `methodology_bundle_coverage.py` because including the fixture's own output digest would create a self-referential hash fixed-point problem. This exclusion is not a completeness exception; the fixture still must match compact helper output and remain schema-valid.
5. These fixtures support local regression checks for output shape and cautious vocabulary. This fixture family does not certify sibling-lane completeness, publication readiness, audit status, or legal/regulatory status.
