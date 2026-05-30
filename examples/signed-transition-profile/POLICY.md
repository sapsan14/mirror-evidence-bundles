# Signed transition profile fixture policy

These fixtures exercise the boundary between unsigned MIRROR local provenance and any later operator-controlled signing or timestamping profile.

- `default-transition.json` is the positive fixture: it records exact local bundle and reviewer-report packet digests, leaves external timestamping absent, and preserves unresolved assumptions.
- `missing-input-failure.json` is the helper-failure fixture: it records a missing unsigned bundle input as a script-readable local preparation error, not as an audit, misconduct, publication-readiness, legal-compliance, or regulatory finding.
- `missing-reviewer-failure.json` is the companion helper-failure fixture: it records a missing reviewer-report packet input as a script-readable local preparation error, not as a finding about the unsigned bundle's quality, completeness, publication readiness, legal compliance, or regulatory status.
- `bad-upgrade-language.json` is the negative fixture: it is structurally plausible but overstates the transition as legal compliance or publication readiness.
- `schema/signed-transition-profile.schema.json` validates only local field shape and cautious interpretation text for transition records; helper-failure payloads remain a separate CLI automation fixture with the same cautious boundary.

The fixture family may support regression checks for signed-profile transition semantics, but it does not certify completeness, scholarly quality, publication readiness, audit status, legal compliance, or regulatory status. Future updates should keep fixtures small, preserve the mutation policy that unsigned local evidence is not rewritten, and refresh the methodology bundle when this fixture family supports a paper claim.
