# Athena venue and deposit advice, 2026-05-30

## Venue recommendation

Primary venue: **Journal of Open Research Software, Issues in Research Software**.

Why: MIRROR is currently a research-software practice case study. Its strongest
claim is about local evidence bundles, negative verifier semantics, and the
discipline of not turning byte replay into scholarly truth. That is more
interesting than a short software announcement.

## Deposit recommendation

| Target | Use | Recommendation |
|---|---|---|
| GitHub public release | Public code, license, tests, minimal evidence package, paper source/PDF | Do now from a sanitized public repository. |
| Zenodo | Versioned software/evidence DOI for citation and Data Accessibility | Do next, after checking the public release archive. Preferred DOI route. |
| OSF / MetaArXiv | Manuscript preprint and discussion surface | Optional. Use only if public preprint circulation helps the JORS route. |
| Software Heritage | Long-term code preservation | Nice additional archive after the public repository is stable. |

## JANUS dependency

If JANUS cites MIRROR only as an internal workflow used during preparation,
then a public MIRROR DOI is not strictly required before JANUS submission, but
public availability is still cleaner.

If JANUS cites MIRROR as a method, artifact, reusable tool, or evidence layer,
then MIRROR should be public before JANUS submission and preferably have a
Zenodo DOI. Otherwise JANUS inherits a weak sentence: it would be relying on an
unpublished local method to support a reproducibility claim.

Athena recommendation: make MIRROR public before JANUS submission if JANUS uses
MIRROR in any methodological or evidentiary sentence. Cite the GitHub release
immediately; replace with Zenodo DOI once minted.
