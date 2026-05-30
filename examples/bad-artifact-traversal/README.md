# Bad artifact traversal fixture

This fixture is intentionally schema-valid but verifier-failing.

`artifact.md.bundle/claims.json` uses the pointer `artifact:../outside.md#claim`. The pointer is accepted by `schema/claims.schema.json` because JSON Schema can only evaluate the claim file in isolation and cannot compare a claim pointer with `manifest.artifact.path`.

`verify.py` loads both `manifest.json` and `claims.json`, strips the `artifact:` pseudo-scheme for local path-safety checks, and rejects this bundle because the normalized pointer path `../outside.md` does not exactly match the manifest artifact path `artifact.md`.

The fixture demonstrates a local replay boundary only. It supports testing deterministic verifier behavior; it does not certify claim truth, legal/regulatory status, publication readiness, or any regulated trust-service property.
