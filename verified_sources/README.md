# Verified response recovery archive

`primary_source_archive.json.gz` is a bounded JSON archive of original public-source cache responses collected on 9 November 2026. It contains SEC companyfacts/submissions/filing HTML and Shell's issuer voting-rights response, with their real retrieval timestamps. `manifest.json` records response hashes. The individual source URLs are retained in submissions, issuer supplemental records and the hashed research-document cache/discovery logic.

This recovery source is deliberately separate from `tests/fixtures`. It contains no generated market demo, fixed valuation, synthetic company financials or investment conclusion. Production reparses the original responses with the normal collectors and prefers newer successful source records. Historical data must never be labelled as a fresh live retrieval. See RELEASE21_CORRECTIONS.md for source failures, retention policy and SEC identity setup.
