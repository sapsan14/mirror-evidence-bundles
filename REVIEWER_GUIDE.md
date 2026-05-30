# MIRROR reviewer guide

This guide gives a compact route through the public evidence package.

## What to inspect first

1. Read `README.md` and `LICENSE`.
2. Run `uv run pytest -q`.
3. Run the positive fixture:

   ```bash
   python3 verify.py examples/good/artifact.md.bundle
   ```

4. Run the negative fixture:

   ```bash
   python3 verify.py examples/bad-hash/artifact.md.bundle
   ```

5. Inspect the minimal release-candidate example:

   ```bash
   python3 verify.py release/mirror-methodology-rc1/examples/minimal-artifact.md.bundle
   ```

## What a pass means

A pass means the retained local files match the recorded schema and digests.
It does not mean the claim is true, complete, novel, fair, authored by a
particular person, legally compliant, peer reviewed, or ready for publication.

## What the negative case means

The `bad-hash` fixture changes a retained source byte after bundling. The
verifier should report a deterministic integrity failure. The intended reviewer
question is: which evidence moved, which claim depends on it, and should the
claim be narrowed, refreshed, or blocked?
