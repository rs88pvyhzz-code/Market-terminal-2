# Release 2.3: dated market intelligence

The existing scheduled static build now assembles a compact Overview briefing. It retains eight workspaces, six Company Research views, the existing financial models and all SEC/DMO retrieval and recovery rules. There is no notification service or new subscription dependency. The pre-existing optional email script is not invoked by the new panel.

## Supported evidence

- Google News search, Bing RSS, BBC Business and CNBC retain their existing fallback roles. Federal Reserve monetary-policy, Bank of England and ECB public RSS feeds supplement them. Feed availability and recent article coverage are separate diagnostics: a successful empty feed does not establish current coverage.
- Six filters classify headline text: Market Moving, Central Banks & Rates, Economic Releases, Corporate, My Watchlist and Regulation & Policy. Regions are inferred only from explicit headline terms, otherwise Global. They are research aids, not verified geographic exposure.
- Materiality ordering uses documented keyword weights in `market_briefing.py`: rates 45, major economic terms 40, corporate events 35, policy 30, watchlist matches 25, market/commodity terms 20, primary-source identification 5, publication within 24 hours 10; a market/commodity headline explicitly reporting a sharp move adds 20. Unclassified general business stories stay in Corporate with low priority. This is relevance triage, not an investment rating. The first five qualifying stories are prominent.
- Canonical identical URLs and conservatively similar dated headlines are grouped across categories. Alternate publisher links remain expandable. Different numeric claims are not collapsed. Paraphrases with little common wording can remain separate; there is no unreliable semantic summariser.
- Headline wording comes from RSS. No article bodies, invented summaries, analyst forecasts, surprise calculations or causal price-move claims are generated.
- Company “What Changed?” reuses dated issuer results and comparable management guidance already extracted by Company Research. It shows reporting basis, source documents and previous/current stated terms. It does not infer a new risk from an old annual-report risk paragraph.

## Calculated observations and alerts

`market_alert_thresholds.json` is the version-controlled configuration; changes take effect on the next scheduled build. Alerts are capped at eight per snapshot. Dates stay beside the observations.

- Share moves: absolute move at least 3% and at least three daily-volatility equivalents, using the existing 1Y annualised historical volatility divided by √252. At least 200 historical closes, a nearby historical date and no discontinuity flag are required. Intraday observations are provisional. This is a research prompt, not a statistical significance test or recommendation.
- VIX: at least 15% and three index points higher, using the existing quote and percentage change to reconcile previous price.
- Sovereign yields: at least 10 basis points between adjacent dated observations, at most seven calendar days apart.
- Credit: at least 10 basis points between adjacent dated FRED/ICE BofA option-adjusted-spread observations.
- Sourced economic/corporate headlines, verified scheduled major economic releases, missing/stale critical quotes and the existing DMO freshness warning can generate prompts.
- Market Conditions reuses dated sovereign observations, the US 10Y–2Y spread, existing breadth counts, VIX and existing credit-spread levels/changes. Dates may differ; the display does not attribute causation.

## Recovery and limitations

Each article retains publication and retrieval dates. Previously published `news_cache.json` and verified local response caches are recovery inputs. Failed retrieval/offline recovery is archived, never current. Unknown retrieval dates are archived too. Current headlines expire after 48 hours, including in an old browser snapshot; recovery lasts at most seven publication days. An old static build suppresses historical alerts after five calendar days. Build time is not a quotation or publication date.

Source-specific requests and coverage are expandable in Data Quality. `verify_market_briefing.py` writes `public/news_verification.json` from the actual production payload, identifying current versus archived coverage and Shell/Microsoft/HSBC issuer dates. Production-source CI uploads this report and the rendered terminal. Missing coverage is reported without blocking unrelated data publication.

Free RSS does not reliably support analyst-consensus earnings surprises, complete issuer announcement coverage, point-in-time index concentration weights, comprehensive guidance comparisons or verified event-to-price causation. Those are coverage gaps, not fabricated analysis. General headline context is deliberately limited when the source supplies only a headline and link.

## Validation

`test_market_briefing.py` uses explicitly synthetic examples for UK CPI, Federal Reserve policy, Shell/Microsoft earnings, event duplicates, conflicting numerical claims, missing/stale/future items and market-alert thresholds. They never populate live caches. Existing financial regression scripts remain in CI.

`tests/browser_market_briefing.py` checks desktop, 1024px and 768px iPad layouts, six news filters, regions, event uniqueness, Overview ordering, company evidence and Data Quality navigation against the supplied unmodified payload. The production workflow runs it on actual collected data separately from the demo regression. No production tests use synthetic replacements for news.
