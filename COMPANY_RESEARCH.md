# Company Research

Company Research now has seven views: Overview, Financials, Valuation,
Performance & Risk, Business & Competition, Outlook & Catalysts, and
Red Flags & Ownership. The standalone Forensic workspace has been removed;
its accounting checks follow the selected company under Red Flags & Ownership.
Existing price charts, benchmark comparison, momentum, risk, news, peer tools
and events are reused. ETF, gilt, macro, market and watchlist calculations are
unchanged.

## Data and evidence

The existing Yahoo/yfinance collector supplies up to five annual fiscal dates
across income, balance-sheet and cash-flow statements. Statements join on exact
fiscal end dates. One unavailable statement does not suppress the others.
Missing values remain absent; coverage and retrieval dates are displayed.
Yahoo frequently supplies only four years or incomplete fifth-year statements.
No extra year, forecast, moat assessment or investment rating is manufactured.
A live smoke test on 9 November 2026 returned four MSFT annual periods
(income, balance sheet and cash flow); the fifth year remained unavailable.
Cached broad-universe profiles refresh to schema 3 through the existing rotation.

Business descriptions and aggregate ownership fractions are provider facts.
Ownership retrieval dates are not filing dates; unknown observation dates are
explicit. Qualitative competitive advantages, catalysts, capital allocation
judgements and risks use a company-specific research notebook for dated evidence
and source links. They are user-entered judgements, not automated conclusions.
Notes save in browser local storage; storage failures fall back to session memory
with a visible message. They are not synced across devices.

Financials display income, balance sheet, cash flow, capital allocation, margins,
cash conversion, debt ratios, derived ROIC and historical charts. ROIC requires
valid effective tax and average invested capital from two periods. Generic debt
ratios, ROIC and FCFF DCF are suppressed for financial companies.

## Valuation

The DCF discounts user-entered normalised **unlevered FCFF** at WACC. Inputs in
reporting-currency millions are projected for 1–20 years, then a Gordon-growth
terminal value is discounted and debt/cash bridged to equity. Share counts use
absolute units. Reported operating cash flow less capital expenditure is **not**
automatically treated as FCFF. Users must consider cash-flow classification,
leases, minority interests, dilution and other claims.

Bear/base/bull growth rates and discount/terminal rates are explicitly labelled
illustrative assumptions. No valuation appears until required inputs and both
currencies are known. Reverse DCF solves for annual FCFF growth matching the
observed market price, holding other inputs fixed; no solution is reported
outside the stated −90% to +100% search range. Sensitivity tables vary WACC
and terminal growth; invalid combinations remain blank.

GBp and GBX quotes divide by 100 into GBP for comparison with model values.
Market capitalisation and financial statements are not divided by 100. Cross-
currency valuation requires explicit FX (quote major currency per reporting
currency); 1 is supplied only for identical currencies. Debt, cash and shares
are initially sourced from the latest fiscal period and remain editable.
Models persist per company in memory during the current page session.

## Validation

Run `python test_equity_research.py`, `python test_etf_tracker.py`, and
`python test_gilt_model.py`. New checks cover exact-date statement joins,
partial statement failure, missing data, five-period limits, DCF reconciliation,
reverse DCF, FX, GBp/GBP, cash flow and ROIC. Pull requests run these checks
and the demo build with both existing post-build processors, without deployment.

The explicitly synthetic demo can be built using:

```sh
python build_terminal.py --demo --output /tmp/research-demo.html
python terminal_research_upgrade.py /tmp/research-demo.html
python market_terminal_cleanup.py --post --html /tmp/research-demo.html
```

`verify_snapshot.py` intentionally rejects demos; do not bypass its publication
guard. Production continues to fetch real data and run the existing validation
before publication. No generated snapshots or cached financial data are committed.
