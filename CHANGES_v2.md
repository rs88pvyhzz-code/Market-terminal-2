# Market Terminal v2: what changed (9 Nov 2026)

## Corrections
1. **Workflow.** The repo had two different `publish.yml` files. Only `.github/workflows/publish.yml` runs. The root copy, never executed, held three steps: Eurostat repair, research layout/after-tax gilt panel, analysis and data-quality clean-up. All three now run. The Eurostat repair is applied permanently to `regional_data.py` instead of patching code during each build.
2. **Gilt yields.** The old model settled on the trade date, used 365.25-day years and ignored ex-dividend periods. It understated short-gilt yields by up to 28bp (4⅛% 2027: 3.96% shown, 4.24% correct). The new model uses DMO conventions:
   - T+3 settlement for DMO Purchase & Sale prices, verified because DMO dirty minus clean reconciles exactly for 68 of 69 conventional gilts
   - T+1 settlement for your own price
   - actual/actual accrual
   - 7-business-day ex-dividend period, with negative accrued interest and the coupon excluded
3. **US Treasuries** are excluded from the ex-dividend rule, which doesn't exist in that market.
4. **Publish guard.** The old guard published if 12 of ~76 instruments were quoted. Now it needs 40, and the latest price must be at most 4 days old (was 7). A bad build leaves yesterday's site live.
5. **Portability.** Cache URLs and repository links follow `GITHUB_REPOSITORY`, so the code runs in any repo.
6. **Clutter removed.** Deleted the duplicate `publish.yml`, the stale `market_terminal_upload_files.zip` and the obsolete `README_FIX.txt`.

## Additions
- **After-tax gilt table.** Net YTM and gross-equivalent yield on every conventional gilt, at the coupon tax rate you select (default 45%). Coupons are taxed; the gain to par is CGT-exempt. Gross-equivalent is the taxable deposit rate you'd need to match.
- **Sort options:** maturity, highest after-tax yield, or highest gross yield.
- **Ex-dividend flag** on the selected gilt.
- **`test_gilt_model.py`** runs before every build and stops the build if the yield model drifts from DMO conventions.

## Known limits
- DMO prices update only if the automated DMO export works from GitHub's servers, which is unverified. Otherwise the page shows the last dated snapshot, marked STALE. Upload a fresh `dmo_gilt_prices.xlsx` to refresh it.
- Not modelled: bank holidays in ex-dividend dates, irregular first coupons (the DMO dirty price is still used for these), the accrued income scheme (holdings over £5,000 nominal), and dealing costs.
- Market data comes from Yahoo Finance via an unofficial interface, so it can break without notice.
