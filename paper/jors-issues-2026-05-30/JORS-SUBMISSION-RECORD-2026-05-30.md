# JORS submission record, 2026-05-30

Status: submitted to the Journal of Open Research Software through OJS.
Editorial outcome pending.

This record freezes the venue decision, uploaded files, portal metadata, and
human/agent boundary for the submitted MIRROR article package. It is an internal
submission record, not part of the manuscript PDF.

## Human and agent boundary

- The agent prepared the JORS OJS form, uploaded the files, and stopped at the
  final Review screen.
- Anton clicked the final Submit button after logging in to the portal and
  checking the last screen.
- No agent clicked final Submit.

## Portal state

| Field | Value |
|---|---|
| Venue | Journal of Open Research Software |
| Portal | `https://account.openresearchsoftware.metajnl.com/index.php/up-j-jors/submission/wizard` |
| OJS submission ID | `753` |
| Section / route | Issues in Research Software |
| Article type | Experience report |
| Submitted | 2026-05-30, after the final OJS review screen was reached |
| Review state at record creation | Submitted / awaiting editorial processing |

## Submitted title

*MIRROR: Local Evidence Bundles for Reproducible Research Software Review, with
a JANUS Case Study*

## Route and venue rationale

JORS Issues in Research Software was selected because the article is strongest
as a research-software practice and experience report: the contribution is
MIRROR as a small local evidence-bundle method, its verifier behavior, and the
boundary discipline around reproducible review before public release.

JOSS was held as a weaker route for this manuscript because the present article
is not primarily a short reusable-software metapaper; it would need a separate
JOSS-shaped rewrite centered on installable software and independent reuse.
Software Impacts was kept as a possible later companion route, not the primary
home. Data & Policy was not used because the paper would require a policy-data
rewrite and because nearby portfolio traffic already makes that route noisy.
Security venues were not used because this version is about research-software
practice, not threat research.

The JORS guidelines were checked live on 2026-05-30. The route fit used the
Issues in Research Software scope, approximate 3000-4000 word / 4-6 page
expectation, PDF plus source upload policy, Vancouver references, and required
back matter. JORS sample anchors were Fehr et al. 2021, Lamprecht et al. 2022,
Katz et al. 2019, and Barker et al. 2025.

## JANUS naming boundary

JANUS is retained only as the name of the laboratory case-study packet used to
exercise MIRROR. The name points to the worked round-trip / dual-view
multilingual drift example; it is not the article's main method, product, or
venue claim. The manuscript makes MIRROR the contribution and treats JANUS as a
public-safe worked case.

## Uploaded files

| Portal role | Repository path | SHA-256 |
|---|---|---|
| Manuscript | `paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1.pdf` | `70558ab105f7bb99933740fd61ff57be9406492eef3d311006cdc5ba07ae055c` |
| Supplementary file (for review) | `paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1-source.zip` | `dd2770afca12de2a216914926ea94ee86c8ac7615742313ca7c0aa853e53b3e6` |
| Local TeX source used for source ZIP | `paper/jors-issues-2026-05-30/mirror-jors-issues-v0.1.tex` | `13450437a01bb1eb9b0c9eeeff0ad07d769043b2956965948a8b4f56b6a3ac7d` |

## Metadata entered

- Sole author: Anton Sokolov, Tyche Institute.
- ORCID: `0000-0003-2452-7096`.
- Keywords visible on final review screen: `research software`,
  `reproducibility`, `evidence bundles`, `artifact review`,
  `software sustainability`.
- Public software record: `https://doi.org/10.5281/zenodo.20463358`.
- License: Apache License 2.0.
- Funding: no external funding reported.
- Competing interests: none declared; professional background disclosed without
  employer, client, or non-public operational material.
- Reviewer exclusions: none.

## Reviewers suggested

1. Stephan Druskat, German Aerospace Center (DLR), Institute of Software
   Technology, Germany, `stephan.druskat@dlr.de`.
   Rationale: research software citation, HERMES, and sustainability.
2. Morane Gruenpeter, Software Heritage / Inria, France,
   `morane@softwareheritage.org`.
   Rationale: software preservation, Software Heritage identifiers, FAIR and
   open-science infrastructure.
3. Eva Maxfield Brown, University of Washington Information School, United
   States, `evamxb@uw.edu`.
   Rationale: scientific software identification, software credit, and research
   software ecosystems.

## Final checks before submission

| Check | Result |
|---|---|
| PDF build | `pdflatex` twice, exit code 0 |
| PDF length | 6 pages |
| MIRROR tests | `uv run pytest -q` -> 115 passed |
| Positive verifier fixtures | main good bundle, RC minimal example, and RC paper bundle returned `ok` |
| Negative verifier fixture | bad-hash bundle failed as expected |
| Layout scan | no final overfull, underfull, citation, font, or rerun warnings |
| Leakage scan | clean for stale DOI, private path, loopback host, personal repository URL, draft-only policy/venue phrases, self-referential approval wording, and over-strong assurance verbs |
| Source reality | JORS guidelines, sample JORS papers, standards, provenance/software-publication sources, EATF docs, and local MIRROR/JANUS package evidence checked and logged |
| Claude/Argus/Kalliope state | Article green; remaining yellow was only submission logistics before the final portal step |

## Submitted-state repository anchor

The article package was clean and pushed before submission at repository commit
`aac69bc` (`paper: add jors submission fields`). This record and the later vault
queue updates are post-submission administrative records.

## Post-submission action

Hekate should monitor OJS submission `753` on a T+14 cadence. Do not submit a
substantially identical version of this manuscript to another peer-reviewed
venue while the JORS route is active.
