# Release 2.2 — reliability and navigation

## Official DMO retrieval

The previous downloader guessed `TradeDate`/`COBDate` and required XLSX. The official D10B report's own public `PDFData.js`/`DataReport.js` instead supplies **`Trade Date`**, including the space, as the URL-encoded parameter string `&Trade Date=dd/mm/yyyy`. The Excel option requests `exportFormatValue=xls`. Its actual response is legacy OLE/BIFF XLS, even when served as `application/octet-stream`.

`gilt_market.py` now uses that official request and a bounded `xlrd` reader for XLS, retaining the original stdlib XLSX reader. It validates the report title, column definitions, both gilt families, numeric bid/offer fields and the embedded **quotation date**. The separate `Data Date` is report generation time: the 9 November 2026 export received on 10 November says `Data Date: 10-Nov-2026` but its quotation date is **9 November**. The latter is used for prices, history and valuation dates. Empty/unpublished reports and date mismatches cannot become quotations. Requests are normal public HTTPS downloads; no anti-bot controls are bypassed.

Purchase means the DMO buys from the investor (investor bid); Sale means the DMO sells to the investor (investor offer). These are DMO retail-service reference prices, not executable stockbroker quotations. Index-linked clean prices remain real; their dirty prices include indexation. Both conventional and index-linked coverage is retained.

Local live validation downloaded the official 9 November report: **103 gilts, including 34 index-linked**. A 10 November request before publication returned a report with no prices and was rejected. This is genuine current official retrieval, not an estimated price series or an updated date pasted onto the 6 November seed. The separate GitHub Actions workflow provides runner-level evidence; its result and raw diagnostics are linked in the PR.

## Freshness and recovery

The DMO page says prices load at approximately 14:00 each UK business day. Freshness uses Europe/London time and a visible 30-minute grace: before 14:30 the expected quotation is the preceding UK business day; after 14:30 it is today if it is a business day. Weekends and the official GOV.UK England-and-Wales holiday calendar are excluded. Retrieval first tries the current business day so an early publication is not missed, then falls back to earlier business days if the report is not yet available. The checked-in calendar is an original official response, refreshed online when older than 24 hours. Uncovered/unavailable calendars cannot produce a successful freshness verdict. This calendar is used only for source freshness; existing yield/settlement formulas are unchanged.

The table prominently distinguishes quotation date from website refresh time. A holiday-aware next-publication deadline also lets the page warn when its snapshot ages past that deadline without another successful website build. Source retrieval time, download origin, request errors and expected date are expandable. The Data Quality section also shows the quotation date. A retrieval failure preserves the newest verified snapshot; it never retimes cached prices. On equal quotation dates a successful newer download wins over an uploaded seed, preserving its real retrieval metadata. Existing published `dmo_latest.json` and `gilt_history_cache.json` provide continuity across scheduled runners.

`Official DMO quotation freshness` is an independent PR/scheduled/manual Actions workflow. `verify_dmo.py` requires a genuinely successful download, expected quotation date, calendar coverage and the existing yield checks. It cannot pass merely because a cached site builds. The publishing workflow audits the build's own DMO snapshot with `--existing` and `continue-on-error`; a DMO outage does not stop unrelated market data publication. Request URLs, HTTP status, hashes, row coverage, source dates and model-reconciliation results are uploaded as diagnostics.

## Manual official-file update

If the DMO blocks automated retrieval or changes its export, open [official D10B](https://www.dmo.gov.uk/data/pdfdatareport?reportCode=D10B), select the latest published Trade Date and download **Excel**. Upload the original file, unchanged, into `dmo_prices/` (root-level official spreadsheets remain supported). No renaming or CSV conversion is required. The normal parser checks the internal quotation date and coverage; the newest verified report wins. Trigger the normal build. The automatic source remains preferred when it returns an equally recent verified report. `dmo_prices/DMO_D10B_2026-11-09.xls` is the genuine original download and a dated recovery source, not synthetic test data.

## Yield preservation and limits

No gross-yield, after-tax yield, tax-equivalent, DCF, reverse-DCF, stress, FX or Shell reconciliation formula is changed. The live DMO audit verifies zero-tax net equals gross, coupon tax reduces net yields and tax-equivalent outputs remain finite. Accrued interest is compared against official dirty minus clean, reusing the existing regression tolerance.

On 9 November, accrued reconciles for **67 of 69 conventional gilts**. The existing model differs for 4% Treasury Gilt 2029 at its ex-dividend boundary and the previously known irregular first coupon of 4⅝% Treasury Gilt 2032. These limitations are exposed as row-level review notices and in the audit artifact; the release does not silently change conventions or describe every yield as fully reconciled. Index-linked nominal YTM remains excluded. Detailed assumptions stay expandable. The official spreadsheet does not publish gross/net YTM, so internal model consistency and accrued reconciliation are not a claim of issuer-published yields.

## Navigation and layout

Eight top-level workspaces replace ten. Equities & Research groups screening/constituents, Company Research, and breadth/sectors. Markets groups instrument prices with rolling volatility/correlation, relative comparisons, valuation dashboards and scoreboards. Existing calculations/renderers remain in use. Second-level choices persist locally; legacy `#companies`, `#analytics` and section links resolve to their new destinations. Search and existing callbacks use the same alias mapping. No old panel is deleted.

Six research views replace seven. Overview moves the existing price chart, existing indexed benchmark chart, financial summary, risk statistics and executive summary into the requested order. Existing RSI and moving-average tiles move into Advanced Analytics. There is one copy of each chart and one calculation path. Periods retain their existing maths; 10-year risk/benchmark selections use the same window functions and are unavailable when history is insufficient. Research-note labels and storage keys are unchanged.

The gilt identity cell shows the full name and ISIN together, with maturity separate and numeric columns right-aligned. The shared quotation date is prominent above the table rather than repeated in an extra column. Searching, maturity/gross/net sorting, individual selection, manual-price calculations and tax comparison remain available. Treasury and credit tables use consistent compact numeric formatting. The design remains dark and responsive.

## Verification

Existing financial, Shell, research recovery, ETF and gilt tests remain in the workflows. Release 2.2 adds actual XLS parsing, quotation-versus-generation dates, exact export parameters, UK holidays/publication cutoff, cached recovery and navigation invariants. Browser coverage includes eight workspaces, six research views, legacy routes, company search versus personal-watchlist search, saved subsections, retained notes, unique ordered charts, advanced technicals, real DMO gilt rows, tax sorting/filtering and desktop/iPad widths. No test fixture feeds the production collector.
