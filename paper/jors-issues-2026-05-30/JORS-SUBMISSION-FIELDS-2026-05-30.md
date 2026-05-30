# JORS submission fields, 2026-05-30

Status: prepared for browser submission. Do not click the final submit button without the author's explicit action.

## Journal and section

Journal: Journal of Open Research Software

Section / article route: Issues in Research Software

Article type: Experience report

## Title

MIRROR: Local Evidence Bundles for Reproducible Research Software Review, with a JANUS Case Study

## Author

Anton Sokolov

Affiliation: Researcher, Tyche Institute, Tallinn, Estonia

ORCID: 0000-0003-2452-7096

Country: Estonia

## Abstract

MIRROR is a small research-software method for keeping drafts, scripts, source copies, and claim records reviewable while an iterative research project is still moving. A MIRROR bundle places an artifact, structured claims, provenance notes, source descriptors or retained source copies, assumptions, and SHA-256 digests into a local directory that can be verified offline. This article reports the design as an Issues in Research Software experience paper and uses JANUS, a multilingual drift-triage manuscript and data packet, as the worked case. JANUS is not a second main contribution; it is a deliberately messy case in which claims, generated outputs, source boundaries, public-safe examples, scripts, and reviewer risk had to be separated before release. The central claim is narrow: byte-level replay and schema conformance can reduce the cost of later review, but they do not establish truth, completeness, authorship, legal compliance, public release authority, external timestamping, or regulated assurance. The current MIRROR implementation passed 115 local tests and positive and negative verifier fixtures, while the JANUS public-safe packet passed its own build, test, checksum, and leakage checks. The main contribution is not another assurance badge, but a boundary discipline: a reviewer should be able to ask what bytes were retained, which claim points to which evidence, what failed, and what still requires human judgment.

## Keywords

research software; reproducibility; provenance; evidence bundles; artifact review; software sustainability

## Data availability statement

The MIRROR software, tests, fixtures, paper source, and minimal public-safe evidence package are archived on Zenodo under the Apache License 2.0: https://doi.org/10.5281/zenodo.20463358. The JANUS case is reported as a public-safe worked example; private workspace paths, unpublished third-party material, raw source claims, generated translations, back-translations, per-record reports, and operational notes were excluded from the public package.

## Cover letter

Dear Dr Fachada and the Journal of Open Research Software editorial team,

Please consider the manuscript "MIRROR: Local Evidence Bundles for Reproducible Research Software Review, with a JANUS Case Study" for the Issues in Research Software section as an experience report.

The article reports MIRROR, a small research-software method for keeping drafts, scripts, source descriptors, claim registers, assumptions, and SHA-256 digests reviewable while an iterative project is still moving. The manuscript is intentionally modest in its claims: MIRROR supports byte and schema replay, not truth, authorship, legal compliance, external timestamping, or regulated assurance. The JANUS material is included only as a worked case study that exercises the boundary between public-safe evidence, private working material, and reviewable claims.

The associated MIRROR software, tests, fixtures, article source, and minimal public-safe evidence package have been archived on Zenodo under the Apache License 2.0 with DOI https://doi.org/10.5281/zenodo.20463358. The submitted manuscript includes Data Accessibility, Ethics and Consent, Funding Information, Competing Interests, Author Contributions, AI Assistance Disclosure, Notes, and Vancouver-style references.

The manuscript has not been previously published and is not under consideration by another journal. I am the sole author and approve the submission. I confirm that I am responsible for the manuscript, the supporting materials, and any required permissions.

Sincerely,

Anton Sokolov

## Comments to editor

This is an Issues in Research Software experience report rather than a Software Metapaper. The main contribution is MIRROR, a local evidence-bundle method and reference implementation. JANUS is only a public-safe worked case study used to demonstrate the review boundary. The public software record is archived on Zenodo at https://doi.org/10.5281/zenodo.20463358 under Apache-2.0.

Potential peer reviewers are suggested below because of their expertise in research software metadata, software citation, software preservation, and research software sustainability. I have no known conflicts of interest with these suggested reviewers.

## Suggested reviewers

1. Stephan Druskat
   Affiliation: German Aerospace Center (DLR), Institute of Software Technology, Germany
   Email: stephan.druskat@dlr.de
   Reason: expertise in research software citation, software publication workflows, HERMES, and research software sustainability.

2. Morane Gruenpeter
   Affiliation: Software Heritage / Inria, France
   Email: morane@softwareheritage.org
   Reason: expertise in software preservation, research software metadata, Software Heritage identifiers, and FAIR/open-science infrastructure.

3. Eva Maxfield Brown
   Affiliation: University of Washington Information School, United States
   Email: evamxb@uw.edu
   Reason: expertise in scientific software identification, software credit, research software measurement, and open-source research software ecosystems.

## Files to upload

Primary manuscript PDF:
`/home/anton/projects/mirror-evidence-bundles/paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1.pdf`

Source file:
`/home/anton/projects/mirror-evidence-bundles/paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1.tex`

Source ZIP, if the portal accepts one source upload:
`/home/anton/projects/mirror-evidence-bundles/paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1-source.zip`

Optional BibTeX sidecar, if the portal wants source files separately rather than a ZIP:
`/home/anton/projects/mirror-evidence-bundles/paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1.bib`

Do not upload the review notes unless the portal explicitly asks for supplementary review documentation.
