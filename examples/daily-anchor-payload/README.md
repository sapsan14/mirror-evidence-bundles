# Daily anchor payload fixtures

`default-anchor.json` is a compact copy of a schema-valid MIRROR daily-anchor JSONL record. It exists so consumers can validate the persisted anchor shape without reading the mutable append-only `daily-anchors.jsonl` log during every fixture review.

Consumer boundary: this fixture supports local replay of anchor metadata only. It does not provide external timestamping, does not certify lane completeness, does not audit sibling lanes, does not decide publication readiness, and is not a regulated trust-service output.
