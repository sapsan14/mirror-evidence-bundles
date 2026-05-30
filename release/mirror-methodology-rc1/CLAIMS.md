# Claim register

Status: human-review claim register for a private release candidate.

| ID | Claim | Evidence pointer | Risk | Safe wording |
| --- | --- | --- | --- | --- |
| MIRROR-RC1-C1 | MIRROR bundles can bind an artifact, sources, claims, notes, and SHA-256 digests for local replay. | paper.md; paper.md.bundle/manifest.json | medium | MIRROR supports local replay of retained artifact and source bytes. |
| MIRROR-RC1-C2 | A green verifier result is not a certificate, audit, legal opinion, peer review, or external timestamp. | LIMITATIONS.md; REPRODUCIBILITY.md | low | Verification indicates local byte/schema consistency only. |
| MIRROR-RC1-C3 | The minimal example demonstrates artifact-source-claim separation. | examples/minimal-artifact.md; examples/minimal-artifact.md.bundle/claims.json | low | The example illustrates bundle structure; it is not a validation study. |
