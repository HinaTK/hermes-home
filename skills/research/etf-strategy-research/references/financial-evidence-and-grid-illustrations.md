# Financial evidence and grid illustrations

## PDF tables: verify spatial relationships

Index factsheets often extract numbers in a different order from their visual labels. A dividend yield can appear beside a volatility figure when plain text flattens the page. A working retrieval route used in research was an HTTP download followed by `pypdf.PdfReader(io.BytesIO(response.content))`; `page.extract_text(extraction_mode='layout')` helped preserve column relationships. Check HTTP status and document type before parsing. If layout remains ambiguous, render and inspect the page visually rather than pairing labels and values by guesswork.

For public documents, direct HTTP retrieval is an alternative to a failed extraction service, not a bypass for authentication or access controls. Fetch product documents and index factsheets independently; a fund's name does not establish its current fee or holdings.

Distinguish price-index returns, total-return index returns, and fund total returns. Annualized volatility is not maximum drawdown. Index dividend yield is not a fund distribution commitment. Document mirrors can contain issuer-authored primary material, but disclose the mirror and original document date and check for superseding disclosures.

## Chinese citation validation: semantic review is mandatory

In a Chinese-language financial draft, a citation checker reported zero prose sentences while returning `citations OK`. That establishes neither citation coverage nor factual correctness. Review all numerical and causal claims manually when segmentation makes coverage meaningless.

A short Chinese verbatim quote may also fail a whitespace-word minimum. Use a relevant complete passage as it actually occurs in the extracted document. Do not fabricate spaces or attach arbitrary opening text just to satisfy a gate. Attaching the first several thousand characters can pass a per-source evidence check while omitting the fee table or concentration statistic actually cited. Evidence must support each load-bearing claim, not merely exist somewhere for the source. If tooling cannot validate the relevant passage, retain exact evidence with manual claim-to-passage notes and disclose the validation limitation.

These are observations to guard against false assurance, not a claim that all citation tools have the same limitations. The bundled grounded-citations skill is protected; any proposed improvement to that skill requires its authorized maintenance/adoption path.

## Illustrations, not recommended constants

A worked capital partition used 25% initial inventory, 25% finite grid reserve, and 50% cash excluded from averaging down. On 250,000 units of account currency, those amounts are 62,500, 62,500, and 125,000. Five equal reserve tranches are 12,500 each. Recompute for the current task; neither the partition nor the tranche count was backtest-optimized.

For a geometric descending buy ladder with 4% drops between levels, the levels are `P0 * 0.96**k`. Selling each purchased lot at 4% above its own buy price is a separate convention: it does NOT exactly return to the preceding ladder node, which requires a rise of `1/0.96 - 1`. Specify one convention rather than conflating them.

A 50% risky-asset/50% cash snapshot followed by a 40% risky-asset loss yields an approximately 20% account loss if there are no intervening trades, cash returns, or additional costs. A 50% risky-asset loss yields approximately 25% account loss. This illustrates why a cash reserve cannot promise a 20% maximum drawdown. It is neither a full grid path simulation nor a bound on drawdown from an earlier equity high.

A 12,500 purchase sold 4% higher has 500 gross trading profit. If commission is 5 each way, 490 remains before other costs. This example says nothing about annual returns or losses on inventory still held. Broker minimum commissions, spread, lot rounding, and sell eligibility must be checked before turning examples into orders.

## Reusable source locations discovered

- CSI index factsheets: `https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300factsheet.pdf` and `.../H30269factsheet.pdf`. These URLs may update in place: record the date printed inside the fetched document.
- Shanghai Stock Exchange fund disclosures provide issuer product summaries; use discovery to find the exact current document, not guessed filenames.
- Tracker Fund official information: `https://www.trahk.com.hk/zh-hk/trahk-fund/`. Risk disclosures can be available even when dynamic price fields are blank; do not interpret blank fields as actual prices.

Do not preserve dated valuations, sector weights, fund fees, or a prior session's chosen ETF as current facts. Re-fetch them on each new recommendation.
