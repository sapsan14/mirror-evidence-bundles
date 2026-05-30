# Bad unsafe-assurance fixture

This directory is a schema-valid but verifier-failing MIRROR example. Its `claims.json` intentionally uses unsafe assurance language (`certifies compliance`) in public claim wording so `verify.py` can demonstrate the local claim-wording guardrail.

The fixture is a regression aid for cautious vocabulary only. It does not certify claim truth, completeness, publication readiness, audit status, legal compliance, or regulated trust-service status.
