# Contributing to MIRROR

MIRROR is currently a small research-software artifact maintained for a paper
and thesis case study. Contributions are welcome when they preserve the narrow
scope of the project.

## Local checks

Before proposing a change, run:

```bash
uv run pytest -q
python3 verify.py examples/good/artifact.md.bundle
python3 verify.py examples/bad-hash/artifact.md.bundle
```

The negative fixture should fail closed with a clear hash-mismatch report.

## Claim discipline

Please do not describe MIRROR as a certification system, legal attestation,
authorship proof, timestamping service, or publication-readiness badge. Its
claim is narrower: retained bytes and structured claims can be replayed and
challenged more easily.

## Licensing

By contributing, you agree that your contribution is provided under the
Apache License 2.0 unless a separate written agreement says otherwise.
