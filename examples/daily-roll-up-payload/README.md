# Daily roll-up payload fixture

`default-rollup.json` is a stable schema-valid example of a MIRROR v0.1 daily roll-up payload for local consumer tests. It is copied from a local `daily-roll-up/YYYY-MM-DD.json` file so tests can validate the persisted JSON shape without treating the live roll-up as the only fixture.

Consumer boundary: this fixture supports local replay and schema-conformance checks only. It does not certify lane completeness, does not audit sibling lanes, does not decide publication readiness, does not provide external timestamping, and is not a regulated trust-service output.
