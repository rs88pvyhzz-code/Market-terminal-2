# Release 2.5 — presentation simplification

Built from main at 6c6c429. No financial formulas, collector, cache, significance threshold, valuation input hierarchy or scheduled publication workflow changes.

## Visible information and navigation

Financial statements, CAGR, source registers, charts, DCF inputs/projections/sensitivities/FCFF reconciliations, research evidence and historical tables are directly visible in their existing views. Only Data Quality audits and explicitly named technical/source-status diagnostics remain disclosures. Material warning text is promoted outside disclosures. Supporting Overview snapshot metrics and dashboard definitions follow the investment summary and analysis. Compact sticky jump links navigate long pages; they do not hide content. Eight main tabs, six research views and the five-section market Overview are retained.

Exact duplicate legacy financial values are omitted only when the fiscal end and raw value match the same company's research statements (same reporting currency). Unique periods and differing provider figures remain in “Additional provider financials”; the source payload is unchanged. Repeated identical research notes are removed from rendering, retaining their original links.

Revenue has a separate chart from operating profit/cash flows. Margins and ROIC/ROE also have separate scales. Legends, currency/percentage units and fiscal-date spans are visible. Chart heights are reduced; all selectors and underlying observations/calculations remain. Gilt headings stay visible within the complete scrolling list, with explicit conventional/index-linked identity. Both accrued-interest restrictions, official bid/offer quotes and freshness warnings remain unchanged.

## Screener defect and fix

There is no code assignment copying Shell FCFF into a screening filter and no stored screener-filter preference. The demonstrated defect was accepting the DOM's numeric value as authoritative on every refresh: an injected/restored `25892.649488670548` became a filter, without range validation. The precise browser autofill/restoration route behind the supplied screenshot cannot be established without that browser session.

Numeric filter state is now isolated in the screener, initially empty. Browser/programmatic DOM mutations are not imported; only focused, trusted input edits update thresholds. Model fields have stable company/field identities and a separate form owner from screener fields. Presets and reset update canonical state explicitly. Invalid user thresholds remain visible with a review notice and export disabled. Reset clears numeric filters, index and sector, and restores default sorting. Existing navigation and research-note preferences are unaffected; browser back/forward resynchronises actual screener state rather than importing another form's values.

## Verification

Backend regressions cover DCF/reverse/stress, Shell's dated reconciliation, FX/GBp, sector exclusions, ETFs, research recovery and all unrestricted gilt yields; the two restricted gilts remain excluded from ranking/ladder optimisation. Browser regressions cover Shell/Microsoft/HSBC, 3Y/5Y tables, all filters/sort modes, index/sector membership, CSV export, injection/restoration, reset, notes/navigation, direct analysis and desktop/iPad/mobile sizing. Demo fixtures are explicitly synthetic; production verification separately builds from real collectors and audits source availability without altering missing-data warnings. GitHub check results and review screenshots are linked in the PR.

External-source gaps are not solved or concealed by this presentation release. No new data, inferred forecasts or fabricated values are introduced.
