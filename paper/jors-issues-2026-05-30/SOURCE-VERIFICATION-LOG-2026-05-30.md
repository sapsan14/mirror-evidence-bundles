# MIRROR source verification log, 2026-05-30

Status: public web/source check for the JORS-shaped MIRROR article package. This log records what was checked and how it is used. It is not a venue submission record.

## Venue and sample papers

| Source | Check | Use |
|---|---|---|
| JORS Submission Guidelines, `https://openresearchsoftware.metajnl.com/about/submissions` | Live page checked 2026-05-30. Lines reviewed for Issues in Research Software scope, article length, structure, Vancouver references, PDF/source submission, note/endnote guidance, figures/tables, and checklist. | Venue selection, back-matter structure, display item policy, and route decision. |
| Fehr et al. 2021, JORS DOI `10.5334/jors.307` | JORS article page checked for article type, abstract, issue, DOI, and peer-reviewed status. | Sample experience/report style anchor and reference. |
| Lamprecht et al. 2022, JORS DOI `10.5334/jors.384` | JORS article page checked for Issues in Research Software type, abstract, DOI, and research-software practice framing. | Sample Issues article and RSE related work. |
| Katz et al. 2019, JORS DOI `10.5334/jors.242` | JORS article page checked for Issues article type and sustainable research software framing. | Sample Issues article and sustainability related work. |
| Barker et al. 2025, JORS DOI `10.5334/jors.625` | Search/PDF snippet checked for JORS article 13:39, DOI, policy/pathways framing. | Current sample of JORS Issues style and research-software policy context. |

## Standards, specifications, and adjacent practices

| Source | Check | Use |
|---|---|---|
| FAIR Guiding Principles, Scientific Data DOI `10.1038/sdata.2016.18` | DOI/title/year checked through Nature/Search result. | Related work on digital research object stewardship. |
| FAIR4RS, Scientific Data DOI `10.1038/s41597-022-01710-x` | Nature/Search result checked for title, year, and DOI. | Related work on FAIR principles for research software. |
| Software Citation Principles, PeerJ Computer Science DOI `10.7717/peerj-cs.86` | FORCE11/Search result checked for title, venue, DOI. | Related work on software as a citable research product. |
| W3C PROV-Overview, `https://www.w3.org/TR/prov-overview/` | Live W3C page checked for date, editors, status, PROV family list, provenance definition, and reproducibility/versioning recommendations. | Related work on provenance and scope comparison. |
| RO-Crate 1.1 specification, DOI `10.5281/zenodo.7867028` | Live specification page checked for version, publication date, Recommendation status, authors/editors, and DOI. | Related work on research-object packaging. |
| ACM Artifact Review and Badging v1.1 | ACM current policy/search result checked for Version 1.1, badge families, and functional/reusable artifact language. | Artifact-evaluation comparison and refusal to claim a badge. |
| SLSA specification v1.2, `https://slsa.dev/spec/v1.2/` | Live page checked for approved v1.2 status, provenance/attestation track, and supply-chain security scope. | Supply-chain attestation comparison. |
| in-toto USENIX Security 2019 page | USENIX page/search result checked for title, year, and conference. | Supply-chain provenance comparison. |
| C2PA specifications 2.1, `https://spec.c2pa.org/specifications/specifications/2.1/index.html` | Live page checked for C2PA purpose, version list, specification sections, and provenance/content-authenticity framing. | Content-provenance comparison. |
| Sigstore docs overview, `https://docs.sigstore.dev/` | Live page checked for signing/verification, transparency log, keyless/ephemeral-key posture, and open-source status. | Signing ecosystem comparison. |
| NIST FIPS 180-4, DOI `10.6028/NIST.FIPS.180-4` | NIST CSRC/search result checked for Secure Hash Standard, SHA family, and DOI. | SHA-256 boundary language: byte-integrity primitive, not truth or authorship. |
| RFC 5280, DOI `10.17487/RFC5280` | RFC Editor page/search result checked for X.509 PKI Certificate and CRL Profile title, RFC number, date, and DOI. | PKI vertical-adjacent governance layer. |
| Regulation (EU) No 910/2014, `https://eur-lex.europa.eu/eli/reg/2014/910/oj/eng` | EUR-Lex page checked for eIDAS title, Official Journal date, and trust-services scope. | Legal trust-services comparison without claiming legal attestation. |
| ETSI EN 319 102-1 V1.4.1, `https://www.etsi.org/deliver/etsi_en/319100_319199/31910201/01.04.01_60/en_31910201v010401p.pdf` | ETSI deliverable checked for AdES creation/validation title and 2024-06 version. | ETSI validation-procedure reference for the “higher governance stack” paragraph. |

## Local MIRROR checks

| Source | Check | Use |
|---|---|---|
| `pyproject.toml` | Local file declares Python `>=3.12`, `jsonschema==4.23.0`, `pytest==8.3.5`. | Reproducibility environment note. |
| `uv run pytest -q` | 166 tests passed on 2026-05-30. | Main test statistic in abstract and method. |
| `python3 verify.py examples/good/artifact.md.bundle` | Returned `{"errors": [], "status": "ok"}`. | Positive verifier fixture. |
| `python3 verify.py examples/bad-hash/artifact.md.bundle` | Returned expected `fail` with hash mismatch. | Negative verifier fixture. |
| `python3 verify.py release/mirror-methodology-rc1/examples/minimal-artifact.md.bundle` | Returned `ok`. | Worked-example verification. |
| `python3 verify.py release/mirror-methodology-rc1/paper.md.bundle` | Returned `ok`. | RC1 paper bundle verification. |

## Known source limits

- Public release metadata was added after the first local article build: Apache License 2.0, `README.md`, `CITATION.cff`, `.zenodo.json`, `codemeta.json`, contributor notes, reviewer guide, and release notes.
- The canonical public software record is `https://zenodo.org/records/20463358`.
- Zenodo DOI published for the public release package: `10.5281/zenodo.20463358`, record `https://zenodo.org/records/20463358`.
- JORS route remains an article-submission route until venue submission, cover letter, and reviewer suggestions are finalized.
