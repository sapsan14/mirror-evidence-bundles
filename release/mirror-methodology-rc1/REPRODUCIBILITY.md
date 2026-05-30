# Reproducibility

From the MIRROR repository root, verify the release-candidate bundles with:

```bash
.venv/bin/python verify.py release/mirror-methodology-rc1/paper.md.bundle
.venv/bin/python verify.py release/mirror-methodology-rc1/examples/minimal-artifact.md.bundle
```

Expected result for each command is JSON with `"status": "ok"`.

These checks are offline. They do not fetch remote URLs, publish artifacts, sign files, timestamp files, or decide publication readiness.
