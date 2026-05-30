# Reviewer report packet fixture policy

These fixtures define the local MIRROR reviewer-report packet vocabulary for future report tooling. They are conformance fixtures only.

Included files:

- `schema/reviewer-report-packet.schema.json` defines the accepted field shape for reviewer-facing report packets.
- `default-report.json` is a positive fixture showing how a packet separates reproducible local facts, review prompts, and out-of-scope questions.
- `bad-hash-report.json` is a schema-valid failure fixture generated from a locally tampered bundle; it keeps verifier errors as local review facts rather than audit findings.
- `missing-bundle-failure.json` is a CLI failure fixture for an absent bundle directory; it keeps setup errors script-readable without treating them as audit findings.
- `bad-quality-grade.json` is a negative fixture showing language that collapses local verification into a quality grade, publication-readiness claim, or legal/regulatory status.

Safe interpretation:

- These fixtures support local regression checks for report packet semantics.
- They do not certify completeness, scholarly quality, publication readiness, audit status, or legal/regulatory status; in other words, the fixture family does not certify the artifact or lane.
- Future report tooling should preserve the separation between deterministic local facts and interpretive review prompts.
- A report packet should not assign a quality grade or imply that byte-level integrity establishes research adequacy.
