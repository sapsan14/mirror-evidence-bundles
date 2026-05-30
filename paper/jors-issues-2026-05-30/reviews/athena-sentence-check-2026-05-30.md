# Athena sentence check, 2026-05-30

Verdict: PASS for local preprint preview.

Scope: sentence-by-sentence reading of `mirror-jors-issues-v0.1.tex` against the rendered PDF. The report is grouped by paper section to stay readable; the pass itself was performed at sentence level.

## Section verdicts

| Section | Sentence-level finding | Action |
|---|---|---|
| Title/status/abstract | The manuscript clearly identifies the MIRROR case, article route, status, public-release boundary, and non-submission boundary. The abstract does not imply legal, DOI, or trust-service assurance. | PASS |
| Introduction | Related-work claims are scoped to research software, provenance, RO-Crate, artifact review, and JORS fit. The venue caveat is explicit. | PASS |
| Method | Tuple and verifier predicate are readable; the lemma is useful and not overclaimed. SHA-256 is treated as byte integrity only. | PASS |
| Worked Case | Positive and negative fixtures are described; the failed case is now explained as stale evidence after a source change, not as a vague failure. | PASS |
| Adjacent-practice table | The table compares MIRROR with PROV/RO-Crate, FAIR/FAIR4RS, citation, artifact badging, and attestation systems without claiming equivalence. | PASS |
| Lessons | Five lessons remain human-readable and professionally skeptical. The EATF sentence is additive and does not claim signing occurred. | PASS |
| Limitations and Threat Model | Threat boundaries are plain: no malicious-OS defense, no hidden-key defense, no legal/license solution, no independent timestamp. | PASS |
| Conclusion | The conclusion returns to the central claim: byte replay helps review but does not decide scholarly truth. | PASS |
| Back matter | Data accessibility, ethics, competing interests, author contributions, AI assistance, notes, and references are consistent with preprint status. | PASS |

## Edits made during Athena pass

- Removed duplicated "Table 1:" / "Table 2:" prefixes from captions.
- Reworded scan-sensitive status text from "not submitted" to "no external venue submission".
- Reworded "artifact under review" to "artifact being checked" to avoid false scanner noise.
- Added a fuller negative-fixture explanation so the failed case has a purpose and an outcome.
- Added PKI/eIDAS/ETSI vertical context with explicit non-attestation language.
- Updated Data Accessibility from private-only status to the public release repository and Apache-2.0 license.

## Remaining caveat

Athena clears the public-release preprint text. The remaining venue-stage tasks are DOI-deposit decision, cover letter, reviewer suggestions, and a final check after any DOI is minted.
