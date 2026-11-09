# Shell final live-data validation — PR #2

Validated on **9 November 2026, 22:20 UTC**. Figures below are a dated validation
snapshot, not a live dealing quote. No merge or deployment was performed.

## Automatic DCF inputs

| Input | Automatic value | Financial / observation date | Source / publication date |
|---|---:|---|---|
| Total debt, including leases | USD 76,075m | 30 Sep 2026 | Shell Q3 interim report, filed 29 Oct 2026 |
| Cash and equivalents | USD 36,425m | 30 Sep 2026 | Same report |
| Debt-related derivatives | USD +963m | 30 Sep 2026 | Same report, net-debt reconciliation E |
| Debt-related collateral | USD −880m | 30 Sep 2026 | Same report, reconciliation E |
| Net debt-related adjustment | USD +83m | 30 Sep 2026 | Calculated: 963 − 880 |
| Reported net debt | USD 39,733m | 30 Sep 2026 | Same report, reconciliation E |
| Ordinary shares | **5,701,440,412** | **30 Oct 2026** | Shell Voting Rights and Capital, published **2 Nov 2026** |
| GBP/USD, USD per GBP | **1.34382** | 9 Nov 2026 observed chart bar | Existing Yahoo chart collector, retrieved 22:20 UTC |
| USD→GBP, GBP per USD | **0.7441472816299802** | Same FX observation | Calculated reciprocal, not a separate assumed rate |
| Equity quote | **3,701 GBp = GBP 37.01** | 9 Nov 2026, 17:54 UTC | Existing Yahoo equity collector |

Primary sources:

- [Shell Q3 2026 interim financial statements](https://www.sec.gov/Archives/edgar/data/1306965/000162828026068044/quarterlyexhibit992-q32026.htm),
  debt Note 6 and alternative performance reconciliation E. Includes USD 34,147m
  lease liabilities inside total debt; they must not be deducted a second time.
- [Shell issuer Voting Rights and Capital announcement](https://shell.gcs-web.com/news-releases/news-release-details/voting-rights-and-capital-128).
  The issuer reports no treasury shares. This is the latest issuer capital count
  located in the live announcement feed; it is not asserted to be a count as of
  9 November. Subsequent buyback trade notices are not mechanically subtracted.
- [Yahoo GBP/USD history](https://finance.yahoo.com/quote/GBPUSD=X/history/).
  The model uses the chart-history observation (1.34382), rather than the rounded
  headline FX quote (1.3438). The daily bar can move intraday; this is a snapshot.

The financing deduction now reconciles exactly:

```
76,075 − 36,425 + 963 − 880 = USD 39,733m
```

Before this fix the DCF used debt minus cash (USD 39,650m), omitting the USD 83m
financing adjustment. It also used Yahoo's 30 September balance-sheet ordinary
share count, 5,699,084,708. Yahoo's undated current summary returned 5,663,324,316;
neither is silently relabelled as the latest issuer count. Shell reported
5,729,497,530 issued shares at 30 September, before later cancellations. Basic
and diluted weighted-average EPS shares are different measures and are not used.

`shell_issuer_inputs.py` now automatically
finds the interim exhibit through SEC submissions and the latest capital notice
through Shell's issuer feed (with bounded listing/cache fallback). It validates
the report's debt reconciliation, requires a dated no-treasury ordinary-share
notice and preserves separate balance/share periods and retrieval dates. Changed
formats fail closed with a source warning. Cached data retain original retrieval
dates on failure; no constants are used as supposedly fresh financial inputs.
Newer quarterly data are never overwritten with the older validated quarter.

## Normalised FCFF and reconciliation to cash flows

The starting point remains the **calculated, unadjusted FCFF proxy**, using the
median of complete observations from FY2023–FY2025. It is not Shell's reported
FCF, adjusted earnings or a forecast. USD millions:

| Component | FY2025 | FY2024 | FY2023 |
|---|---:|---:|---:|
| Operating profit (Yahoo definition) | 27,582.00 | 29,992.00 | 30,737.00 |
| NOPAT = operating profit × (1 − effective tax rate) | 16,795.21 | 16,559.65 | 18,498.54 |
| D&A | 25,299.00 | 26,872.00 | 31,290.00 |
| Less capital expenditure | −18,947.00 | −19,601.00 | −22,993.00 |
| Signed working-capital cash contribution | −1,803.00 | +2,062.00 | +7,145.00 |
| **Annual FCFF proxy** | **21,344.21** | **25,892.65** | **33,940.54** |
| Reported operating cash flow | 42,863.00 | 54,687.00 | 54,191.00 |
| Calculated OCF − capex FCF | 23,916.00 | 35,086.00 | 31,198.00 |
| OCF-to-operating-proxy residual bridge | −2,571.79 | −9,193.35 | +2,742.54 |

For each year: **OCF − capex + residual bridge = FCFF proxy**. The residual is
calculated as `NOPAT + D&A + working-capital cash contribution − OCF`; it is a
mathematical reconciliation, not a separately reported adjusting item. It can
reflect cash taxes versus booked tax, joint-venture dividends, noncash items,
non-operating items and cash-flow classification. The system does not invent a
breakdown of that residual.

**Normalised starting FCFF = median(21,344.209638, 25,892.649489, 33,940.535936)
= USD 25,892.649489m.** User FCFF adjustment defaults to zero, explicitly labelled
as an assumption of no additional adjustment.

Source attribution: [Shell Annual Report 2025](https://www.sec.gov/Archives/edgar/data/1306965/000162828026017024/shel-20251231.htm)
via SEC supplies annual tax, pre-tax profit, D&A and OCF; Yahoo supplies the
unmapped operating-profit definition, capex and working-capital cash contribution.
Capex and annual OCF reconcile to the issuer cash-flow statement; the provider's
operating-profit measure is not relabelled as audited Shell EBIT. Effective tax
rates use tax expense / pre-tax profit for the same annual periods. Reported Shell
2025 FCF is USD 26,052m under its own definition, not the terminal's USD 23,916m
OCF-minus-capex measure and not its USD 21,344.21m FCFF proxy.

The Q3 report separately shows **nine-month 2026 OCF of USD 48,538m** and capital
expenditure of USD 15,366m (OCF−capex USD 33,172m). These are nine-month figures:
they are **not silently annualised or mixed into the three full-year median**.
Forward normalisation needs judgement about the ARC acquisition, lease commitments,
commodity conditions, cash-tax effects, reinvestment and dilution. Automatic
history is not a forecast of the enlarged 2026 business.

## Resulting illustrative DCF values

All cases use the same sourced balance/share/FX inputs above and calculated
FCFF of USD 25,892.649489m. Explicit assumptions: **5 forecast years, WACC 10%,
terminal growth 2%, FCFF adjustment zero**, with growth varied as below.

| Scenario | Assumed annual FCFF growth | Enterprise value USD m | Equity value USD m | GBP per issued ordinary share |
|---|---:|---:|---:|---:|
| Bear | 0% | 303,139.06 | 263,406.06 | **£34.38** |
| Base | 5% | 374,462.58 | 334,729.58 | **£43.69** |
| Bull | 10% | 459,594.53 | 419,861.53 | **£54.80** |

Equity value = enterprise value − USD 39,733m. Value/share = equity value × 1e6 /
5,701,440,412 × 0.7441472816299802. These are model outputs under illustrative
assumptions, not analyst targets, forecasts or investment ratings. The denominator
is dated issued ordinary shares with no treasury; any different treatment of
employee-trust shares or forward dilution requires a documented verified override.

## What is automatic and what needs review

- **Automatic sourced facts:** dated gross debt/cash, issuer financing adjustments,
  latest located issuer ordinary-share count and its separate date, dated observed
  FX, historical annual components. Issuer report/announcement links appear in UI.
- **Automatic calculations:** USD→GBP reciprocal, net financing deduction,
  annual FCFF proxies, residual cash-flow bridges, three-year median and model
  outputs. GBp prices divide by 100 once; financial statements do not.
- **Assumptions:** growth scenarios, WACC, terminal growth, forecast duration,
  FCFF adjustment (default none), and any further claims/dilution adjustment.
  Users must review whether historical normalisation is appropriate for the
  acquired business and lease/capital structure. No analyst forecasts are created.
- **Fallback/override:** unavailable or unverified primary facts remain labelled
  Yahoo fallbacks or missing inputs. Unsourced debt adjustments default to an
  explicitly labelled zero assumption; they do not claim to reproduce reported
  net debt. Old or undated balance **or share** data pause valuation for review.

## Tests

`test_shell_live_validation.py` freezes real issuer table/capital excerpts and
this live input snapshot. It checks exact debt/cash/net-debt reconciliation,
independent dates, newer-source precedence, no EPS-share substitution, failed
refreshes, future/malformed sources, FCFF identities, GBP/USD inversion, pence,
claims, reverse DCF and all three values. All existing ETF, gilt, research and
Release 1 tests are rerun. Browser regression now checks Shell's issuer share
count, USD 83m debt adjustment and £43.69 base value using the actual FX snapshot,
as well as HSBC exclusions, responsive layouts and the other workspaces.
