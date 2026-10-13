SkillHub CN CLI 已装在本机：skillhub 2026.8.5，包装脚本 C:/Users/Administrator/.local/bin/skillhub（Windows 须 cygpath -w 再交给 python）。安装指南缓存 HERMES_HOME/skills/web/skillhub/。装技能必须 --dir HERMES_HOME/skills。仅搜索/安装时不要问优先源；首次装 CLI 才问一次。
§
A-share cash auction 09:15–09:25, continuous 09:30. Grid ops must not lock limit prices at 09:10 (usually prev close). Scripts: hermes-home/scripts/grid_weixin_preview.py and grid_weixin_execute.py wrapping grid_weixin_ops.py --phase preview|execute. Execute falls back to preview if Tencent quote time is before 09:30 same day.
§
网格关键规则（2026-09-28用户明确）：网格卖出不按买入lot绑定；同一ETF应维护“总可卖库存池”，只要T+1可卖库存足够，就可以用较早A/B格可卖份额为最新下跌格配置对应数量的+2%卖单。优先资金周转：159363 D格5100@1.169成交后，应撤/不保留远端B格4700@1.298，改挂D格5100@1.192；不能同时占用超过总可卖库存。默认采用方案A（最近成交格优先），卖出后按实际卖出数量生成对应接回价。
§
网格账本与操作单不能把“D格买入当日不可卖”误解为“D格对应卖价不可挂”：卖价可立即挂在A/B的T+1可卖库存上，只要可卖池覆盖数量；只有当日新买的D份额本身不能作为可卖库存。用户目标是反复成交净差价和资金周转，不能机械等待新lot T+1。
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
用户对账本准确性的要求极高，不容忍任何基础计算错误。2026-10-09 因为算错 8,069.40 + 8,075.60 + 7,959.40 - 8,120.60 这道简单算术题，被用户两次骂"傻逼"。教训：任何涉及金额、份额、成本的计算必须逐笔列明并反复核对，不能凭印象给数。用户会逐笔对账，发现错误会直接指出并要求重新计算。

用户明确的账本规则（2026-10-09）：
1. 每个格子（lot）独立记录数量、单价、买入日、T+1可用日
2. pos["qty"] 必须等于所有 lot 的 qty 之和，卖出后用 sync_qty() 同步
3. 可卖库存 = 所有 available_from <= 今日的 lot 的 qty 之和（T+1池）
4. 卖出时消耗来源是 T+1 池（按买入日期 FIFO），目标格（act["lot"]）的 qty 保持不变——它只是标识哪个网格价位被触发，不是被卖出的那个 lot
5. 当日买入的 lot（T+0）不能作为可卖库存，但其卖价可以挂在 T+1 池上
6. cost_cash 必须等于所有 lot 的 (qty × price + 佣金) 之和，卖出时从 T+1 池扣减对应成本
§
网格计算规则（用户多次纠正，必须严格遵守）：
- 买入价 = 上一格买入价 ÷ 1.015（不是卖价反推，不是当前价）
- 卖出价 = 买入价 × 1.015
- 份额 = LOT_BUDGET ÷ 买入价，取整百（159363: 6,000元，589720: 8,000元）
- 接回格命名：G-rebuy、C-rebuy 等，ID 要具体，不说"下一格"
- 每只ETF一卖一买，159992迁移退出只有卖单
- T+0当天不可卖，可卖池 = 所有已过T+1且未卖出格
- 最新成交格卖出优先（卖价最低的可卖格），用旧T+1库存覆盖
- 账本每格记录：买入价、持有股数、是否已卖出、T+1可卖状态
§
2026-10-12：飞书会话模型切换为 gpt-6.1-sol（provider: custom:aicode-api-gz4399-com）。此前为 gpt-6-sol，再之前为 dots-studio/dots-3-note-preview:free。
§
2026-10-12 用户再次纠正：卖出哪个格子就接回哪个格子（卖D格接D-rebuy，卖E格接E-rebuy），不是卖E格接F格。接回价 = 卖出价÷1.015，份额 = LOT_BUDGET÷接回价取整百。这个错误今天犯了两次，必须记住。
§
10-13: 159612选黄金分割方案B(0.809/0.236,1%,3档2.053~2.109,全仓23,638,月ROI7.4%)。突破2.109切方案A(箱体1%,5档2.066~2.160,全仓39,401,月ROI4.4%)。跌破2.053暂停买入。切换成本~8元。用户偏好黄金分割口径。
§
用户明确ETF状态需求：每只ETF的qty、sellable_qty、max_grid(A-Z)都是持久化、脚本可修改的变量，不是展示时临时计算的口径。买入从当前max_grid取下一号并更新，卖出取当前号再退一号；标签保存到交易记录，不人工硬编码。每日00:01从交易记录重算qty并写回sellable_qty=qty；买入增加qty不增加sellable_qty，卖出同时扣减二者，卖出建议读取持久化sellable_qty。用户要求汇报数字来自真实脚本输出，区分用户输入、人工设置与脚本自动生成。