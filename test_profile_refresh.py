import datetime as dt
from company_profiles import history_needs_refresh
now=dt.datetime(2026,11,14,tzinfo=dt.timezone.utc)
rows=[{'fiscalEnd':f'{y}-12-31','revenue':0,'netProfit':0,'operatingCashFlow':0} for y in (2023,2024,2025)]
assert not history_needs_refresh({'annual':rows},now)
assert history_needs_refresh({'annual':rows[:2]},now)
assert history_needs_refresh({'annual':[rows[0]]*3},now)
assert history_needs_refresh({'annual':[{**r,'operatingCashFlow':None} for r in rows]},now)
assert history_needs_refresh({'annual':rows},dt.datetime(2028,1,1,tzinfo=dt.timezone.utc))
print('Coverage repair: missing fields, duplicate periods, stale accounts and valid zeros passed')
