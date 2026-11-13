# v3.9

- ETF comparison removed: Cmp column, compare ticks, clear button and the checked-comparison section.
- "Fund size" replaces every AUM label (table, cards, detail, same-index table).
- No SEC / EDGAR / XBRL / form-number references outside Data Quality; source labels now read "Issuer accounts".
- Company research: guidance-change and latest-reported-results block and the supporting-evidence block removed; headlines remain.
- Analyst consensus: labelled tiles (consensus rating, analysts with a price target, mean / median / low-high target, mean target vs price) plus this month's ratings split — strong buy, buy, hold, sell, strong sell, with counts, % and a bar. Ratings come from Yahoo's recommendation trend (current month), captured in company_data.py.
