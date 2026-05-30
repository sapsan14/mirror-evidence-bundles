# Verifier output fixtures

This directory stores compact JSON payloads emitted by `verify.py` for selected conformance examples. The fixtures are local regression aids for reviewer-facing payload shape and boundary wording.

`good-success.json` records the compact success payload for `examples/good/artifact.md.bundle`. It demonstrates that a successful local replay contains only `status: "ok"` and an empty `errors` list; success payloads intentionally omit `failure_kinds` and `note` because those fields are failure-only triage aids. A green success payload does not certify claim truth, source completeness, publication readiness, or legal/regulatory status.

`bad-unsafe-assurance-policy-failure.json` records the compact failure payload for the schema-valid but policy-guardrail-failing bundle under `examples/bad-unsafe-assurance/artifact.md.bundle`. It demonstrates the `failure_kinds: ["policy_guardrail"]` label and the accompanying note that the label does not certify claim truth or publication readiness.

`bad-hash-integrity-failure.json` records the compact failure payload for the intentionally tampered source under `examples/bad-hash/artifact.md.bundle`. It demonstrates the `failure_kinds: ["integrity_or_structure"]` label for a byte-integrity failure while preserving the same non-certification boundary note.

`mixed-policy-and-integrity-failure.json` records a synthetic replay payload for a local copy of the unsafe-assurance bundle with its source bytes tampered. It demonstrates that mixed failures are represented as `failure_kinds: ["integrity_or_structure", "policy_guardrail"]`, not as a stronger finding about claim truth, misconduct, publication readiness, or legal/regulatory status.

These fixtures do not certify artifacts, enumerate every unsafe phrase, decide publication readiness, or provide legal/regulatory assurance. They only pin expected local verifier output for replay and tests.

`schema/verifier-output.schema.json` records the compact consumer contract for these payloads: `status`, `errors`, failure-only `failure_kinds`, and the non-certification boundary `note`. A schema-valid verifier-output fixture remains only a local replay aid; it does not certify claim truth, publication readiness, legal/regulatory status, or guardrail completeness.
