# Market Terminal: Release 3.3 (12 Nov 2026)

## Fixes
- **Company and watchlist news feeds work again.** The 3-day news rule (Release 3.1) removed whole company feeds instead of only their old articles.
- **ONS rate limiting.** Requests are spaced 1.5 s apart and retried after a wait on HTTP 429 (seen on KAI9).
- **TOPIX removed.** Yahoo no longer serves ^TOPX (404).

## News
- **No repeated stories.** One story, at most two headlines: a word recurring in three or more headlines marks a running story, and only its two top-ranked headlines are kept.
- **Bigger text.** Headline and date text are larger.
- **Caveats removed.** Causation and methodology notes are removed everywhere ("News methodology", "not proof of causation", "no price causation inferred", "related headlines are…").

## Markets and analytics
- **Section order.** Global prices and Price moves now run US & Americas, UK, Europe, Asia-Pacific, Volatility, Equity ETFs, Bond ETFs, Currencies, Government yields, Commodities, Crypto.
- **Major market first.** Each section leads with its main market (S&P 500, FTSE 100, Euro Stoxx 50, Nikkei 225 …).
- **Tighter bars.** Price-moves rows are compact.
- **Overview pulse regrouped.** Equity indices, then currencies, bond yields, VIX, gold, Brent and bitcoin.

## Bonds & Rates
- **Sub-tabs.** Five sub-tabs: UK gilts · US Treasuries · Yield curves · Credit spreads · Sovereign. A link to any section opens its sub-tab.
- **Sovereign table, no chart.** Sovereign is now one table of 10-year yields: UK, US, Germany, France, Italy, Spain, Netherlands, with the spread vs Germany and 1M and 1Y changes.

## ETF Trackers
- **Catalogue counts** moved to Data Quality.
- **"(submethod not confirmed)"** removed.
- **Fund size and fund assets** no longer both shown.
- **Alternatives table.** The selected fund appears beside up to three funds tracking the same market (then closely related markets), largest first, on index, TER, size, 1Y/3Y/5Y, replication and income. Tap a fund to switch to it.

## Watchlist
The four summary tiles are removed.

## Data Quality
"Issue 1…14" is replaced by one table: source, what happened in plain words, and what was affected.
