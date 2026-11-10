# Corrective Release 2.1

## Production diagnosis

The actual GitHub Actions deployment [42725524946](https://github.com/rs88pvyhzz-code/Market-terminal-2/actions/runs/42725524946), job 129530053245, completed successfully but logged HTTP 403 for all six attempted research companies. It reported **0/205 primary-document coverage**. The workflow had no SEC identity secret and did not persist `.terminal_filings` or the raw document cache between runners. Offline fixture regressions therefore did not establish production research coverage.

The downloaded production terminal dated 10 November used Yahoo financials after SEC, Shell SEC-interim and Shell voting-rights retrievals failed. The validated and production FCFF formula is identical; its inputs differ:

| Annual period | Yahoo D&A, USD m | SEC issuer D&A, USD m | Yahoo-based FCFF, USD m | Issuer-preferred FCFF, USD m |
| --- | ---: | ---: | ---: | ---: |
| 2025-12-31 | 22,167 | 25,299 | 18,212.21 | 21,344.21 |
| 2024-12-31 | 22,703 | 26,872 | 21,723.65 | 25,892.65 |
| 2023-12-31 | 23,106 | 31,290 | 25,756.54 | 33,940.54 |

The median therefore fell from USD 25,892.65m to USD 21,723.65m, exactly USD 4,169m. These D&A definitions are not interchangeable; the collector must retain its dated issuer-preferred definition. Other source differences included cash balances and a dividend line; these affect related ratios but not this FCFF bridge. No FCFF formula has been changed.

The production shares 5,699,084,708 were a Yahoo count, not the dated issuer's no-treasury ordinary-share statement (5,701,440,412 as at 30 October, published 2 November). A later provider retrieval does not verify its share observation date. The missing issuer net-debt bridge made the existing zero adjustment default appear usable. The issuer bridge is USD 76,075m debt − USD 36,425m cash + USD 963m derivatives − USD 880m collateral = USD 39,733m net debt, including the USD 83m adjustment.

The 9 November GBP/USD was 1.34382; the downloaded production history contained 1.33604 for 9 November and 1.34416 for 10 November. The model correctly selects FX no later than the company quote date: that published Shell quote was dated 9 November, so it used 1.33604, not the 10 November observation. Even with restored inputs, a later valid FX observation legitimately changes the displayed value. GBP 43.69 is a reproducibility check at the documented 9 November inputs and assumptions (five years, 5% base growth, 10% WACC, 2% terminal growth), never a live constant. The production GBP 36.05 is explained by changed source inputs, shares, omitted financing adjustment and observed FX. Share-price changes affect upside comparisons, not intrinsic DCF value.

An ordered reconciliation at the published quote-date FX (1.33604 USD/GBP) reproduces GBP 36.0537. Restoring only issuer D&A gives GBP 43.9721; restoring issuer ordinary shares gives GBP 43.9540; adding the USD 83m financing adjustment gives GBP 43.9431. Substituting the frozen validation FX 1.34382 then reproduces GBP 43.6886, rounded to GBP 43.69. These are audit calculations, not production constants.

## Repairs

- `source_transport.py` requires a genuine SEC contact identity, paces requests to at most about 3.3 per second across collectors, and stops further requests to a host after 403/429. It never rotates identities or bypasses a block. Set repository Actions secret **SEC_USER_AGENT** to your real organisation/application name and monitored contact email. The workflow exposes only whether it is configured. This connection cannot create repository secrets; no email or credential is invented. Missing configuration is recorded explicitly and other public sources/caches continue.
- `source_archive.py` restores actual original source responses, with hashes and original retrieval dates. The recovery archive in `verified_sources` contains the real 9 November responses from the working source cache, not company test fixtures, valuations or invented reports. It preserves SEC facts, Shell issuer share/debt evidence and research documents. Newer cached responses take precedence. The archive is published to Pages for future restoration; Actions also caches raw/derived records across ephemeral runners. Historical source responses remain dated evidence, not current verification.
- Exact-period financial history retains original field provenance when a provider omits a previously available observation. Values are never copied into a later financial period, and retained components trigger source review.
- Source failures record URL, time, status/reason and affected fields. The published `source_verification.json` and workflow diagnostic artifacts include original known retrieval dates. A failed refresh does not overwrite successful source data. Source status appears prominently beside valuation, with component provenance in expandable details.
- Legitimate issuer-hosted results pages supplement the SEC route when readable and dated. Microsoft's actual first-quarter IR results are readable; HSBC's public results directory links to a readable quick-read and original PDFs. Shell's public results page returned an application shell without extractable reporting text in local validation: it is reported as a coverage limitation, not silently treated as research. No unsupported private API or transcript scraping is added.
- Source-backed Shell results, guidance, catalysts and risk passages are parsed from preserved real documents on the production path. Empty Outlook coverage becomes one compact warning with expandable details; advanced evidence/methodology remains collapsible.
- Multiple snapshots remain a dated table until at least 12 observations span 90 days. Period buttons require at least 12 observations and a full requested period. Two near-identical daily points cannot create a misleading horizontal history chart.

## Production verification

`Production source verification` runs on pull requests using the same live production build command, with no demo flag, fixture injection or deployment. It uploads the actual terminal and source diagnostics. `verify_live_research.py` rejects demo payloads and checks substantive Shell results, guidance, catalysts and risks, dated primary sources for Microsoft and HSBC, the issuer financing/share bridge and visible source-review metadata. Deployment runs the same audit before publishing.

Existing accounting, currency conversions, DCF/reverse DCF, ETF, gilt, economics, analytics and watchlist functions remain intact. Original regressions plus seven corrective source/cache tests are run. A successful cached-source audit does not establish fresh SEC accessibility: the diagnostics distinguish retained source dates from actual successful and failed HTTP requests. Review the PR's workflow artifacts for the GitHub-runner results.

## Cache-independent SEC verification after contact setup

An explicitly requested fresh-source run uses `verify_fresh_sec.py` before the terminal build. The first identified probe was triggered by the PR update for the owner’s request; future manual workflow dispatches offer `fresh_sec`, defaulting to false so routine PR edits do not repeat denied probes. It downloads companyfacts and discovers results/annual documents using direct, identified requests without reading cached bodies as probe successes. Successful responses are validated, hashed, dated and made available to the normal collectors. The artifact `fresh_sec_verification.json` separates fresh financial facts, fresh research documents and prior recovered documents; an unchanged response is not called a new disclosure. A 403/429 stops further requests to both SEC hosts across the probe and build processes for that workflow attempt. A later explicitly requested workflow rerun has its own attempt scope. No identity, proxy or host rotation is used.
