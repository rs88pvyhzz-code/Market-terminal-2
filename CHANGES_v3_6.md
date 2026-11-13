# v3.6 — total returns

- ETF 1Y/3Y/5Y are now total returns from dividend-adjusted closes for every fund, Dist and Acc alike.
- When the latest point is an after-close quote with no adjusted value, it is chain-linked to the prior adjusted close instead of dropping the whole calculation to price only.
- Price-only returns are used only for funds with no adjusted history, and are labelled "Price only (no adjusted closes)".
- Detail labels read "1Y total return" / "3Y total return (annualised)".
- Tests updated; new tests cover a distributing fund, the chain-link and the price-only fallback.
