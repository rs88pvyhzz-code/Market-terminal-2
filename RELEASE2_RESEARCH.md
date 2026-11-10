# Company Research — Release 2

Release 2 adds a reusable evidence system inside the existing seven views. It does not add navigation tabs or investment ratings. Release 1 financial calculations, currency conventions, DCF and reverse DCF remain in place. Personal research notes retain their company-specific local-storage keys.

## Collection and provenance

`research_intelligence.py` discovers SEC annual, interim and earnings documents using issuer submissions. Shell, Microsoft and HSBC reuse the verified issuer mappings; other US-listed companies can resolve through the SEC ticker directory. Existing Yahoo profiles, financials, ownership and news remain secondary sources. Unsupported issuer mappings display a coverage gap.

`research_documents.py` reads public filing HTML and inline XBRL. Revenue breakdowns require explicit revenue tags, annual periods, matching currency and a single segment or geography dimension. Geography disclosures can overlap: subsidiary countries must not be summed with regions. Current-quarter narrative business areas retain their own period and definitions rather than being spliced into annual segment series.

Material findings carry source links, publication dates, reporting periods where identifiable and original retrieval dates. Short issuer excerpts are classified as reported statements, management expectations or possible scenarios. Issuer claims are evidence to investigate, not independent proof of pricing power, market share or a moat. Named competitors require an actual mention in collected competition evidence; industry/sector peer suggestions are labelled separately.

Guidance comparisons require matching metric, explicit horizon, units and basis. Qualifiers such as “at least” are retained. Ambiguous duplicate measures are not automatically compared, and changed amounts are not labelled upgrades or downgrades without interpreting conditions. Historical RPO balances are not revenue forecasts. No analyst consensus is invented. Only legitimately discoverable transcript links are exposed; the system does not fabricate or reproduce unavailable calls.

## Scheduled cache and refresh

The existing build/publish pipeline collects at most six companies per run, prioritising the three validation issuers. Source manifests refresh after 24 hours; failures retry after six hours. Immutable SEC archive documents reuse local content and original retrieval dates. Up to eight successful documents per company preserve comparison history. A failed refresh preserves successful prior evidence and reports the failure separately. A cache check date never replaces the underlying document retrieval date.

The derived `research_evidence_cache.json` is published and restored through the existing published-data mechanism between scheduled runs. Raw documents stay in the ignored `.terminal_research` cache and are not deployed. Source downloads are bounded to 24 MB and approved public HTTPS hosts; there is no paid API, access-control bypass or unsupported transcript scraping. Failure of this research layer cannot stop the existing terminal build.

## Calculated research

Five-year allocation reuses annual statements: capital expenditure, signed net business acquisitions/disposals, dividends, buybacks and ROIC. The new acquisition field preserves whether the source is gross payments or a net cash-flow line; missing values remain missing. Net disposal proceeds are not turned into acquisition spending. Distribution coverage needs both dividend and repurchase observations.

The executive summary uses observable financial rules, sourced developments and the existing model value. ROIC minus an assumed WACC is a comparison, not proof of realised shareholder value. Five prioritised financial warnings cover cash conversion, debt, dilution, margin deterioration and distribution coverage. Their thresholds are visible. Missing observations mean unassessed risk, never low risk. Corporate cash-flow, leverage and margin rules are excluded where inappropriate for financial companies. Ownership retains provider/date limitations and missing holder observations are disclosed.

## Valuation stress methodology

The unchanged Release 1 scenarios are accompanied by a separate downturn model. Editable assumptions impose first-year revenue contraction, operating-margin compression, additional reinvestment, a WACC increase and linear recovery. Sector presets are illustrative assumptions, not forecasts. The incremental operating shock uses annual revenue held flat as its counterfactual and the selected forward tax assumption; baseline FCFF follows the existing growth assumption. Negative interim FCFF is allowed, while a non-positive terminal cash flow has no standard perpetuity value.

Enterprise-to-equity conversion reuses sourced debt, cash, financing adjustments, absolute ordinary shares and reporting-to-quote FX. GBp/GBX quotes divide by 100; USD reporting figures are not divided by 100. Margin of safety is `(model value − market price) / model value`. Terminal value dependence is shown explicitly.

Debt repricing stress is a separate liquidity illustration, assuming all stated debt immediately reprices. It is not deducted again from unlevered FCFF; financing stress enters valuation through WACC. Maturity schedules, hedging and lease resets require further evidence.

For Shell, extracted issuer commodity sensitivity describes asset impairment/reversal under a changed price outlook. It is not a cash-flow coefficient and cannot automatically produce a commodity DCF. The optional cash-flow response coefficient starts blank and requires an explicit user assumption. Dollar asset sensitivity extraction is limited to USD-reporting issuers. Banks and insurers remain excluded from standard FCFF DCF and these corporate stress calculations; regulatory-capital stress requires reliable exposure data not supplied here.

## Validation and limitations

Real-source fixtures cover Shell, Microsoft and HSBC without hard-coded investment conclusions. Shell's Q3 balance-sheet inputs and validated Release 1 base DCF remain unchanged (GBP 43.69 using the frozen validation inputs). Shell guidance comparison preserves the current USD 23–25 billion versus prior USD 24–26 billion 2026 capital-expenditure ranges and source dates. Microsoft results and changing segment definitions are checked separately from annual data. HSBC targets are management expectations, and its standard FCFF exclusion is retained.

Complex disclosures can exceed the bounded HTML parser: HSBC's large annual filing exceeded the document-size limit in validation. Current/interim evidence remains available and the unparsed original source is linked; missing segments are not invented. Other issuers or unusual tables may similarly need a maintained adapter or manual review. Free filings cannot reliably automate an independent moat verdict, comprehensive competitor universe, exhaustive catalyst discovery, consensus forecasts or a commodity-to-cash-flow response. The UI exposes these evidence gaps and retains personal notes.

Tests cover provenance, guidance comparability, annual units, cache persistence/failure/retry, missing data, financial-sector exclusions, downturn mathematics, FX and existing calculations. Browser regressions exercise all workspaces, all seven research views, persisted notes and desktop/iPad widths. The existing ETF, gilt, economics, analytics and watchlist paths remain regression-tested. Run the commands in `.github/workflows/research-checks.yml` for the reproducible offline build and browser checks. Source fixtures are deterministic regression inputs; deployed source availability and freshness remain visible rather than guaranteed.
