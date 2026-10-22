# MIRROR

MIRROR is a small research-software method for keeping drafts, scripts,
source copies, and claim records reviewable while a project is still moving.

It is deliberately narrow. A MIRROR bundle can help a reviewer ask which
bytes were retained, which claim points to which evidence, and whether a
local verifier can replay the recorded hashes and schemas. It does not prove
truth, authorship, legal compliance, peer review, public-release readiness,
external timestamping, or regulated assurance.

## Public release surface

The canonical public release package for journal and thesis review is the
Zenodo software record:

```text
https://doi.org/10.5281/zenodo.20463358
```

That archived package is the safe public surface. This working repository may
contain local development notes that are not part of the public evidence
package.

## Contents

- `bundle.py` creates local evidence bundles.
- `verify.py` verifies bundle schema and SHA-256 digest consistency.
- `update_daily_rollup.py` builds local roll-up payloads.
- `signed_transition_profile.py` prepares unsigned transition payloads for a
  future signing layer.
- `schema/` contains JSON Schemas for bundle and report structures.
- `examples/` contains positive and negative fixtures.
- `release/mirror-methodology-rc1/` contains the minimal public-safe evidence
  package used by the article.
- `paper/jors-issues-2026-05-30/` contains the article package as submitted to
  the Journal of Open Research Software on 30 May 2026, with its build manifest,
  source checks, and review-gate reports. The published article is
  https://doi.org/10.5334/jors.753.

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

Please cite the article that describes MIRROR:

```text
Sokolov A 2026 MIRROR: Local Evidence Bundles for Reproducible Research
Software Review, with a JANUS Case Study. Journal of Open Research Software,
14: 65. DOI: https://doi.org/10.5334/jors.753
```

and the software release (`CITATION.cff`):

```text
https://doi.org/10.5281/zenodo.20463358
```
