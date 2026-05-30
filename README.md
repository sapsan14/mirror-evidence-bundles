# MIRROR

MIRROR is a small research-software method for keeping drafts, scripts,
source copies, and claim records reviewable while a project is still moving.

It is deliberately narrow. A MIRROR bundle can help a reviewer ask which
bytes were retained, which claim points to which evidence, and whether a
local verifier can replay the recorded hashes and schemas. It does not prove
truth, authorship, legal compliance, peer review, public-release readiness,
external timestamping, or regulated assurance.

## Public release surface

The public release package for journal and thesis review is:

```text
https://github.com/sapsan14/mirror-evidence-bundles
```

That repository is the safe public surface. This working repository may contain
local development notes that are not part of the public evidence package.

## Contents

- `bundle.py` creates local evidence bundles.
- `verify.py` verifies bundle schema and SHA-256 digest consistency.
- `update_daily_rollup.py` builds local roll-up payloads.
- `signed_transition_profile.py` prepares unsigned transition payloads for a
  future signing layer.
- `schema/` contains JSON Schemas for bundle and report structures.
- `examples/` contains positive and negative fixtures.
- `release/mirror-methodology-rc1/` contains the minimal public-safe evidence
  package used by the preprint.
- `paper/jors-issues-2026-05-30/` contains the current JORS Issues preprint
  candidate, build manifest, source checks, and review-gate reports.

## Quick check

```bash
uv run pytest -q
python3 verify.py examples/good/artifact.md.bundle
python3 verify.py examples/bad-hash/artifact.md.bundle
python3 verify.py release/mirror-methodology-rc1/examples/minimal-artifact.md.bundle
```

The `bad-hash` command is expected to fail closed with a digest mismatch. That
fixture is part of the method, not a broken test.

## License

MIRROR is released under the Apache License 2.0. See `LICENSE`.

## Citation

Please cite the public release repository using `CITATION.cff`. A Zenodo DOI is
planned for the first public release archive; until that DOI exists, cite the
public GitHub release URL and the release tag.
