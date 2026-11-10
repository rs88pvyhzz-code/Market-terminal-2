# Release 2.3: dated market intelligence

The existing scheduled static build now assembles a compact Overview briefing. It retains eight workspaces, six Company Research views, the existing financial models and all SEC/DMO retrieval and recovery rules. There is no notification service or new subscription dependency. The pre-existing optional email script is not invoked by the new panel.

## Supported evidence

- Google News search, Bing RSS, BBC Business and CNBC retain their existing fallback roles. Federal Reserve monetary-policy, Bank of England and ECB public RSS feeds supplement them. Feed availability and recent article coverage are separate diagnostics: a successful empty feed does not establish current coverage.
- Six filters classify headline text: Market Moving, Central Banks & Rates, Economic Releases, Corporate, My Watchlist and Regulation & Policy. Regions use explicit headline terms or the jurisdiction of an identified official central-bank feed, otherwise Global. A commercial publisher’s location does not establish story geography. They are research aids, not verified geographic exposure.
- Topic/relevance ordering retains documented keyword weights in `market_briefing.py`: rates 45, major economic terms 40, corporate events 35, policy 30, watchlist matches 25, market/commodity terms 20, primary-source identification 5, publication within 24 hours 10, movement wording 20. Each contribution appears in ranking reasons. **None of these points grants Market Moving status.**
- Market Moving requires separate explicit headline evidence: a reported central-bank rate decision/identified official monetary-policy decision document; an explicit profit warning or issuer guidance revision; an announced/completed acquisition, merger, takeover or buyback with stated value >=1 billion in the headline's currency units ($/£/€/USD/GBP/EUR, no FX conversion); or a reported asset move >=3% / yield move >=10 bp using the existing configurable thresholds. Quantified moves are publisher claims, not causal attribution or independent price confirmation. These conservative criteria do not establish that smaller events are immaterial.
- Previews, speculation, commentary, interviews, calendars and recaps cannot qualify merely through their topics. Earnings results, inflation releases, watchlist membership, primary-source status and words such as “rally” alone are insufficient. Verified significance sorts before topic relevance; the five-story Overview limit is unchanged. If fewer stories qualify, the system leaves the gap rather than filling it with routine news.
- The actual-production verification report now includes the ten highest-ranked current headlines, their categories, every ranking reason and significance evidence, plus the total qualifying Market Moving count. Ten overall headlines do not imply ten Market Moving events.
- Canonical identical URLs and conservatively similar dated headlines are grouped across categories. Alternate publisher links remain expandable. Different numeric claims are not collapsed. Paraphrases with little common wording can remain separate; there is no unreliable semantic summariser.
- Explicit company-name matches can show existing dated share moves inside expandable story context, labelled as separate observations; no causal connection is claimed.
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


## Event-driven daily selection

The five-item briefing reuses qualifying **Calculated** alert records by ID, prioritising actual observed threshold breaches with asset-class coverage before additional movements. Thresholds are unchanged. Missing index/FX/commodity risk metrics use the same existing `market_price_history.metrics_for_records` calculation on the already-collected main history; there are no new downloads or alternative volatility formulas. The alert ledger remains capped at eight; leading items are removed from the additional-alert display rather than duplicated.

Dated confirmed primary releases/results come next, then explicitly reported developments, general news, and finally previews, opinion and speculative commentary. Fresh issuer results documents come only from the existing research cache, with original publication/retrieval dates; an observation period is never substituted for a release date. Reports without primary corroboration remain labelled General news, with “reported development” in their selection reason. A confirmed release is not automatically a material surprise or Market Moving.

Within the same evidence tier, identified official sources and a declared list of established publishers are preferred over other attributed sources; source preference never supplies significance evidence. Recency precedes legacy topic points within that tier. Corporate guidance requires financial context, so ECB appointments and political “guidance” are not corporate earnings guidance. Current Market Moving headline criteria remain unchanged. If neither an observed threshold breach nor a verified significant primary event is available, the briefing explicitly says no significant event was verified.

`public/news_verification.json` records the actual five leading items, classifications, original dates, selection reasons and references to the same alert IDs rendered by the terminal. The production browser test checks display order, five-item limit and absence of duplicated alert IDs.
