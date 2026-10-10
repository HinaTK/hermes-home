SkillHub CN CLI 已装在本机：skillhub 2026.8.5，包装脚本 C:/Users/Administrator/.local/bin/skillhub（Windows 须 cygpath -w 再交给 python）。安装指南缓存 HERMES_HOME/skills/web/skillhub/。装技能必须 --dir HERMES_HOME/skills。仅搜索/安装时不要问优先源；首次装 CLI 才问一次。
§
A-share cash auction 09:15–09:25, continuous 09:30. Grid ops must not lock limit prices at 09:10 (usually prev close). Scripts: hermes-home/scripts/grid_weixin_preview.py and grid_weixin_execute.py wrapping grid_weixin_ops.py --phase preview|execute. Execute falls back to preview if Tencent quote time is before 09:30 same day.
§
网格卖单排序纠错（2026-09-28）：同一ETF存在多个已到T+1可卖网格时，必须按卖出目标价从低到高、优先最近一格卖出，以提高往返成交和资金周转；不能用 max(sell) 选择最高价的远端A格。159992当时应卖C格9400@0.863，而不是A格9100@0.888；159363应卖B格4700@1.298，而不是A格4600@1.306。生成操作单前必须检查：当天新买不可卖、旧卖单需先核对是否成交/撤单，不能重复挂卖；挂单不等于成交。
§
网格关键规则（2026-09-28用户明确）：网格卖出不按买入lot绑定；同一ETF应维护“总可卖库存池”，只要T+1可卖库存足够，就可以用较早A/B格可卖份额为最新下跌格配置对应数量的+2%卖单。优先资金周转：159363 D格5100@1.169成交后，应撤/不保留远端B格4700@1.298，改挂D格5100@1.192；不能同时占用超过总可卖库存。默认采用方案A（最近成交格优先），卖出后按实际卖出数量生成对应接回价。
§
网格账本与操作单不能把“D格买入当日不可卖”误解为“D格对应卖价不可挂”：卖价可立即挂在A/B的T+1可卖库存上，只要可卖池覆盖数量；只有当日新买的D份额本身不能作为可卖库存。用户目标是反复成交净差价和资金周转，不能机械等待新lot T+1。
§
2026-10-08用户授权将6,000元网格成本额度从159992+589720创新药迁移组合挪给159363：159363成本上限调整为40,000元，创新药迁移组合共享上限调整为40,000元；总网格成本上限仍80,000元、账户现金底20,000元、2%间距不变。
§
2026-10-08 用户确认 589720 买入 9,400 份 @ 0.859 成交（实际成交价优于限价 0.869）。佣金按万一免五最低 1 元计 1.00 元，银河交割单待核；其他委托未计成交。
§
User insists on only having one active buy order and one active sell order per ETF at any time. Other orders should be automatically canceled to avoid conflicts.
§
User expects immediate updated operation suggestions after each confirmed trade execution.
§
User is highly sensitive to data accuracy, particularly market data field parsing and cost basis calculations, and will repeatedly correct mistakes until resolved.
§
User wants all trading data verified against actual brokerage statements and considers local ledger as provisional until confirmed.
§
User's primary trading metrics are net price difference per round trip and capital turnover efficiency, not just win rate.
§
User follows a 2% grid trading strategy with focus on capital efficiency and repeated trading opportunities.
§
User commission structure confirmed: 万一免五 (0.01%) with minimum 1元 per trade (max of turnover*0.0001 and 1.0).
§
Updated skill library with new class-level skill 'etf-grid-maintenance' that encapsulates ETF grid trading system maintenance: cleaning unconfirmed orders, collecting closing prices, verifying ledger integrity, and preparing next-day suggestions. Includes reference and template support files.
§
用户通过银河证券进行 A 股 ETF 交易，佣金为万一免五（0.01%，无最低 5 元）。
§
用户要求每确认一笔网格真实成交并入账后，立即给出对应的新剩余操作建议；不能只报持仓/盈亏。建议必须核对当天T+1总可卖库存池和银河旧挂单；存在冲突时明确标注待核，避免重复挂单。
§
用户运行 2% 间距 ETF 网格交易程序，专用账户 10 万元、网格成本上限合计 8 万元（159363 单独 4 万；159992+589720 迁移组合共享 4 万，2026-10-08 由 46,000 元下调为 40,000 元）。
§
用户明确网格目标：可容忍短期底仓下跌，优先关注反复成交的净差价、资金周转与持续交易能力；不希望以短期浮亏或站上均线作为否决网格的主要依据。
§
用户坚持每只ETF同时只保留一个最合适的买单和一个最合适的卖单，其余挂单同步取消。
§
用户要求网格轮换检查不能局限同类ETF：若整个题材网格效率下降，应每周跨题材筛选候选，比较最近约3个月同窗完成往返次数；同一候选连续两周领先只触发人工复核，不自动换仓。
§
用户的主要交易指标是每轮净价差和资金周转效率，而非仅胜率。
§
用户对数据准确性极度敏感，特别是市场数据字段解析和成本基础计算，会反复纠正错误直到解决。
§
用户要求交易情况‘汇总’必须包含每只ETF持仓份额、持仓成本与加权单位成本、现金及成交核对；不可仅概述策略或只报网格价差。
§
用户于2026-09-30同意将当前 Hermes Desktop 默认配置的 model.context_length 设为400000 tokens；压缩参数保持不变，暂不直接拉满百万上下文。
§
网格代码修复记录（2026-10-09）：

1. **apply() 卖出 bug**：卖出时 `pos["qty"] -= qty` 减了总持仓，但 `act["lot"]` 对应的 lot 的 qty 没跟着减，导致已卖出的格（如 159363 G 格、589720 C 格）在账本里永远留着 qty，plan() 重复生成卖单。修复：在 `pos["qty"] -= qty` 后同步减少 `act["lot"]` 对应 lot 的 qty。

2. **next_sell_lot() available_from 过滤**：错误地过滤掉了 `available_from > today` 的 lot，导致 589720 选了 B 格（0.876）而不是 C 格（0.846）。修复：去掉 `available_from` 过滤，只按卖价排序选最低。T+1 池覆盖即可挂单。

3. **CASH_FLOOR 20,000→0**：用户确认 2 万从"硬底"变为"可动用的买入储备"。买入不再被现金底卡住，只受总投资上限约束。

4. **TOTAL_CAP=80,000 共用额度**：买入约束从"每只 ETF 各自卡 CAP[code]"改为"总投资卡 TOTAL_CAP"。某只 ETF 单只超 4 万时，只要总投资不超 8 万、现金够，仍可继续买入。实现：新增 `total_invested(book)` 函数，plan() 和 apply() 中所有 CAP[code] 判断改为 TOTAL_CAP/total_invested(book)。

5. **grid_migration.py 安全网**：load_policy() 增加 `target_buy_authorized_by_user` 二次确认，防止仅改配置开关就启用 589720 自动买入。

6. **CODES/NAMES/CAP/LOT_BUDGET/CORE_QTY 加入 sh589720**：589720 正式纳入网格系统，CAP=40,000，LOT_BUDGET=8,000，CORE_QTY=0。

7. **一买一卖规则**：每只 ETF 操作建议只出一个买单和一个卖单。卖单选最低价（最接近现价），买单选最高价。迁移退出标的（159992）只有卖单。
§
用户对账本准确性的要求极高，不容忍任何基础计算错误。2026-10-09 因为算错 8,069.40 + 8,075.60 + 7,959.40 - 8,120.60 这道简单算术题，被用户两次骂"傻逼"。教训：任何涉及金额、份额、成本的计算必须逐笔列明并反复核对，不能凭印象给数。用户会逐笔对账，发现错误会直接指出并要求重新计算。

用户明确的账本规则（2026-10-09）：
1. 每个格子（lot）独立记录数量、单价、买入日、T+1可用日
2. pos["qty"] 必须等于所有 lot 的 qty 之和，卖出后用 sync_qty() 同步
3. 可卖库存 = 所有 available_from <= 今日的 lot 的 qty 之和（T+1池）
4. 卖出时消耗来源是 T+1 池（按买入日期 FIFO），目标格（act["lot"]）的 qty 保持不变——它只是标识哪个网格价位被触发，不是被卖出的那个 lot
5. 当日买入的 lot（T+0）不能作为可卖库存，但其卖价可以挂在 T+1 池上
6. cost_cash 必须等于所有 lot 的 (qty × price + 佣金) 之和，卖出时从 T+1 池扣减对应成本