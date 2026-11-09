# Company Research — Release 1

Seven existing views are retained. Release 1 automates financial analysis and
valuation inputs; qualitative research notes remain user-authored. No Release 2
features, investment ratings, analyst forecasts or generated narratives are added.

## Data sources and units

`company_filings.py` prefers SEC issuer-filed XBRL facts for verified mappings:
Shell (`SHEL.L`, CIK 1306965), Microsoft (`MSFT`, CIK 789019) and HSBC
(`HSBA.L`, CIK 1089113). These provide up to five annual periods. This is a
bounded primary-source integration, not a claim of filings coverage for every
listed company. Other companies and unmapped fields use the existing Yahoo /
yfinance collector. `SEC_USER_AGENT` can optionally identify the operator.

Fields join on **exact fiscal end date and currency**. Duration facts must cover
330–380 days in annual filings; quarter/YTD flows are excluded. The latest filed
restatement of the selected tag takes precedence, with filing, period, retrieval
date, tag and URL retained per field. Facts are absolute currency amounts or
absolute shares; millions/billions are formatting only. No weighted-average share
count is substituted for outstanding shares. The view uses latest restatements;
it is not suitable as a point-in-time backtest of historical information.

Cash flow outflows from positive XBRL payment tags are normalised to negative
capex/distributions. An individual statement or provider failing does not erase
other available data. Missing fields and periods stay blank. Field-level sources
are expandable in Financials. Broad-universe profile cache schema 4 refreshes the
existing rotation to obtain provenance and dated balances.

## Automatic analysis

`company_research.py` calculates annual growth, actual-interval CAGR, operating,
net and FCF margins, cash conversion, debt/equity, ROIC and ROE. EBITDA is the
provider's unadjusted EBITDA where supplied, otherwise operating profit + D&A
with a calculated label. Neither measure is relabelled as issuer adjusted EBITDA.

- Annual growth requires adjacent annual dates and a positive prior base.
- CAGR requires positive endpoints and shows the actual measured interval.
- FCF = operating cash flow − absolute capital expenditure.
- Cash conversion = OCF / positive shareholder net profit.
- ROIC = EBIT × (1 − effective tax rate) / average (equity + debt − cash).
- ROE = shareholder net profit / average shareholder equity; it is not RoTE.

The Overview uses six compact cards and visible rules, without a composite score:
price, financial strength, profitability, growth, cash generation and observed
valuation. Net debt / positive EBITDA is shown directly; a disclosed 3× threshold
is only a screening prompt. Detailed figures and methodology remain collapsible.

Financials retains expandable annual statements and field-level sources, with
cash/margin charts. Annual horizons show 1, 3 and 5 fiscal periods where available;
10Y is disabled without ten periods. Price charts and risk analytics retain the
existing 1/3/5/10-year and custom ranges where their datasets support them.

## Valuation inputs and normalisation

The latest **dated** quarterly or annual Yahoo balance sheet supplies debt, cash
and outstanding shares in reporting currency. The period is always visible; it
is never labelled a current balance. Annual balances are an explicitly labelled
fallback. Inputs over 180 days old, retrieved over seven days ago or undated pause
valuation until the user explicitly reviews and accepts them. Missing individual
components are not silently taken from another date. Outstanding-share quote
units are verified 1:1 for the three test companies; other issuers require a
verified user input rather than guessing ADR ratios.

FX reuses existing observed Yahoo FX history, allowing at most five calendar days
from the quote date. GBP/USD and GBP/EUR conversions support GBP, USD and EUR;
unsupported/missing pairs stay blank. Value/share is expressed in the quote's
major currency. GBp/GBX quotes divide by 100 into GBP. Financial statements and
market capitalisation do not divide by 100. USD→GBP inverts GBPUSD; GBP→USD
multiplies by it. The observed FX date and source are displayed.

The calculated annual FCFF proxy is:

```
EBIT × (1 − tax expense / pre-tax profit)
+ depreciation and amortisation
− |capital expenditure|
+ signed cash-flow contribution from working-capital changes
```

The automatic normalised starting point is the median of complete observations
among the latest three annual periods, with their dates displayed. A single
complete observation is identified as such; no missing term is set to zero. This
is an **unadjusted FCFF proxy**, not management guidance or a fully audited
normalisation. The bridge shows EBIT, NOPAT, D&A, capex, working capital and FCFF.
Impairments, asset disposals, acquisitions, operating/non-operating classifications,
leases and other noncash items can distort it. Users can override the starting
point or enter a separately labelled adjustment; the model shows the sum used.

Bear/base/bull FCFF growth assumptions remain editable with shared WACC,
terminal growth and horizon. Defaults are illustrative user assumptions, never
analyst forecasts. Inputs are labelled sourced, calculated or user overrides.
DCF, reverse DCF, scenario values, enterprise/equity bridge and WACC/terminal
sensitivity reuse the existing tested model. Invalid/missing inputs produce no
valuation. Other claims, cash investments and dilution need review.

Banks and insurers, including HSBC even when sector metadata is missing, do not
receive standard FCFF DCF, corporate FCF, cash-conversion, EBITDA leverage or ROIC
screens. ROE and P/E/P/B remain available when sourced; regulatory capital,
liquidity, RoTE and sector valuations require issuer disclosures.

## Historical valuation multiples

Observed Yahoo P/E, EV/EBITDA and P/B snapshots accumulate with retrieval dates in
`research_valuation_cache.json`, published/restored alongside the existing profile
cache. Offline/cached old profiles do not create new historical observations.
Current ratios are never backfilled into past years. History therefore starts at
Release 1 collection; one observation displays a table, not an invented chart.
1/3/5/10-year controls enable only when the observed span supports them. There
is no claim of ten years of historical multiples at first deployment.

## Shell reconciliation and validation

The real-data fixtures were retrieved on 9 November 2026. The Shell issuer report
is [Annual Report and Accounts 2025, filed 12 March 2026](https://www.sec.gov/Archives/edgar/data/1306965/000162828026017024/shel-20251231.htm).
Revenue and shareholder profit reconcile to the Consolidated Statement of Income
(p214), cash to the Balance Sheet (p215) and Cash Flows (p217), debt to key
financial data / Note 21, D&A and capex to the statements. USD millions:

| Measure | 2025 | 2024 | 2023 |
|---|---:|---:|---:|
| Revenue | 266,886 | 284,312 | 316,620 |
| Profit attributable to Shell shareholders | 17,837 | 16,094 | 19,359 |
| Operating cash flow | 42,863 | 54,687 | 54,191 |
| Total debt | 75,643 | 77,078 | 81,541 |
| Cash and equivalents | 30,216 | 39,110 | 38,774 |
| Capital expenditure (outflow) | 18,947 | 19,601 | 22,993 |

The fixture tests compare SEC-extracted facts with independently checked report
figures. Capex is currently a Yahoo fallback and separately reconciles to the
report; Shell-specific extension tags are not in SEC companyfacts. Operating
profit / EBITDA remain explicitly provider-defined where no matching filing tag
is available. Shell's adjusted EBITDA of $56,135m and FCF of $26,052m for 2025
are **not** the terminal's measures. Terminal OCF−capex FCF is $23,916m; Shell's
own FCF definition includes investing cash flows and adjustments. The FCFF proxy
is another distinct calculation. None is silently substituted for another.

Run:

```sh
python test_etf_tracker.py
python test_gilt_model.py
python test_equity_research.py
python test_research_release1.py
python build_terminal.py --demo --output /tmp/research-demo.html
python terminal_research_upgrade.py /tmp/research-demo.html
python market_terminal_cleanup.py --post --html /tmp/research-demo.html
# Optional Playwright/Chromium, also run by pull-request CI:
python tests/browser_research_release1.py /tmp/research-demo.html
```

The browser regression uses real sourced company fixtures inside an explicitly
synthetic market demo, without live network access. It tests Shell, Microsoft,
HSBC, automatic inputs, stale/missing data, source/override labels, charts,
sector exclusions, 390/768/1024/1440px layouts, notes and all existing workspaces.
ETF, gilt, economics, market analytics and watchlist calculations are unchanged.
The demo publication guard in `verify_snapshot.py` remains intact; no synthetic
snapshot is deployed or committed. Live source smoke tests are separate from the
reproducible regression suite.


## Final Shell live-data review

See [SHELL_LIVE_VALIDATION.md](SHELL_LIVE_VALIDATION.md) for the 9 November 2026
snapshot, primary links, component dates, FCFF-to-cash-flow reconciliation and
bear/base/bull GBP values. Shell now prefers its latest issuer interim debt
reconciliation and voting-rights announcement over Yahoo when dates support it.
The DCF separately subtracts sourced debt-related derivative/collateral adjustments
and preserves independent share/balance dates. A zero unsourced claims adjustment
is an explicit assumption, not a claim to match reported net debt.
