# Top-ten reporting and Stock Connect ETF costs

## Verified research workflow

Run from the active repository: `python -m tools.etf_research.research --output-path <new-managed-cache-directory>` (online default). Read `summary.json` and `result.json` from that exact run. Retain `asof`, window bounds, attempted assets, complete assets, fetch errors, data failures and model exclusions.

Default score output is `ranking[:10]`; independently derive completed-cycle top ten from rows with `has_all_four_windows`, union with `holdings.values()`, deduplicate by exact code, sort `(full_cycles, full_cycle_net)` descending, and verify count. This is presentation of existing research results, not a second simulator. `rotation_top10` is a baseline-beating shortlist, not a full-universe top ten. Extract only `code,name,score,full_cycles,full_cycle_net,recent20_cycles` plus optional drawdown. Label qualification and ranking filters clearly. Large raw rows contain every window metric and produce unnecessary output truncation.

Recent20 standalone simulations are initialized separately; do not imply their cycle counts are necessarily the last twenty days of the uninterrupted full-window account. Model net spread excludes remaining inventory mark-to-market. Model accounts are independent per asset, not one shared portfolio.

## Investor tax versus fund tax

For a mainland-listed Hong Kong equity ETF, answer the investor's question about *secondary-market ETF units* first. Distinguish:
- Investor's domestic ETF order: broker commission and domestic ETF trading rules; do not transplant the Hong Kong stock stamp-duty schedule simply because the fund name says 港股通.
- Fund's underlying stock trades/dividends: applicable Hong Kong/Stock Connect taxes and costs affect fund assets/NAV. This is not a claim of total tax exemption.
- Management/custody charges: accrued within NAV, not a fresh charge on every ETF order.
- Investor income/distributions: verify current resident-person rules independently; avoid conflating dividend withholding, transaction stamp duty and capital-gain taxation.

Before trading recommendations, verify the broker's actual instrument-specific tariff, spreads/premium-discount, currency exposure and official same-day resale eligibility. A conservative T+1 backtest is not proof that the product legally requires T+1. Do not modify the model or authorize a purchase merely to answer a tax question.

## Source discovery example (159198, checked October 2026)

Official product URL: https://www.fullgoal.com.cn/fundDetail/159198/index.html
The official site uses `fundDetail`, not an assumed `/fund/` path. Discover prospectus links from the product page; a notice page exposes a PDF download link and iframe. Fetch the actual PDF and extract its tax section with an available PDF reader (requests + pypdf was exercised). Do not rely on third-party ETF summaries for tax rules.

Checked prospectus: https://www.fullgoal.com.cn/wbs-file/fund_report/20260824/CN_50100000_159198_FA010030_20260002.pdf
Section 基金费用与税收 states fund-investment-related taxes are borne by holders and withheld by the manager or other withholding agent under applicable law. This supports indirect fund-level tax exposure, not a specific withholding rate for every dividend.

Product page disclosed management fee 0.500%/year and custody fee 0.100%/year at retrieval; recheck before quoting future rates. Broker fee tables may corroborate domestic ETF stamp-duty treatment, but another broker's schedule cannot verify this user's Galaxy commission. Search snippets must be labeled as snippets if the actual page cannot be fetched; do not claim they were fully read. Use current exchange, tax-authority and manager documents where available. Keep dates and rates as sourced evidence, not timeless policy.
