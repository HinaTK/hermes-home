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
User commission structure confirmed: 万一免五 (0.01%) with minimum 1元 per trade (max of turnover*0.0001 and 1.0).
§
用户通过银河证券进行 A 股 ETF 交易，佣金为万一免五（0.01%，无最低 5 元）。
§
用户要求每确认一笔网格真实成交并入账后，立即给出对应的新剩余操作建议；不能只报持仓/盈亏。建议必须核对当天T+1总可卖库存池和银河旧挂单；存在冲突时明确标注待核，避免重复挂单。
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
§
2026-10-20: etf_research 引擎已参数化——simulate(lot_budget=5000, gap=0.02)，底仓=lot_budget×2；engine.run_research() 透传。默认仍与用户实际（1.5%间距、6000/8000元格、逐格建仓）不一致，绝对值不可与账本直接比，可传 lot_budget=6000/gap=0.015 跑贴近实际的一版。同批修复：体积单位 bug（K线 volume 是手数，qty 是股数，三处需 ×100）、cycle_return_on_40k_pct 分母由硬编码 40000 改为实际 4*c、新增初始不变量断言。补 2 项 TDD 测试，共 11 项通过。
§
已查证曾讨论单边行情，不能再称“没聊过”：原会话 @session:default/20260922_141141_e5b6cb；消息4354为上涨卖空/三天接不回，9/29后补参与底仓和提前上移复核；消息5332为持续下跌只买不卖、暂停新增买入、评估下移区间/换ETF且旧亏损不消失。以上是历史讨论，不证明当前代码仍有效；159992后改迁移退出。用户反感跨会话否认已讨论事项；此类问题过去的检索遗漏不等于从未讨论，当前未诊断到记忆服务故障。
§
2026-10-20 用户决定买入日经ETF 159866（买入持有，不接入网格账本；理由：分散非中国资产）。用户三条件：赌后续会涨、期限可放 3 年、可接受 25% 回撤。方案：总投 3 万（账本外 8 万保护性现金出），三档 1.59-1.60(30%)/1.50-1.52(30%)/1.40-1.42(40%)，锚点为 250 日斐波那契 50%/61.8%/78.6% 与历史支撑密集区，加权成本约 1.492；止损=成本×0.75（约1.12，低于历史最低≈不设）；1.68/1.92 压力位减仓，36个月未达1.70换标的。当日现价 1.645、溢价 +1.36%、跌破 MA20/MA60，故未立即建仓。
§
2026-10-20 用户抓到助手口头声称"按 TDD 流程"但实际先改代码后补测试（是回归测试不是 TDD）。教训：声称用了 superpowers skill 就必须真走 RED→GREEN（先写失败测试再改实现），不能口头套用 skill 名；含代码改动的汇报不得把事后补的测试说成流程驱动。
§
A股交易日计数必须扣除法定节假日，不能只扣周末。2026年：中秋节9/25(五)-9/27(日)休市、国庆10/1-10/7休市、10/10(周六)补班不开市。曾把09-23→10-16算成18个交易日，实际只有11天。任何涉及交易日/交易天数的汇总，先查当年交易所休市安排再算。
§
每周研究排名用户要的是完整往返次数(full_cycles)排名，不是综合得分(score)。综合得分是加权指标且默认排除当前持仓，绝不能当作往返次数榜交付。交付前必须从result.json按full_cycles降序重排，并说明是否含持仓、是否含港股相关ETF。
§
网格汇总的合计部分必须包含：交易区间、自然日、交易日数、成交总笔数、买入/卖出金额合计、佣金合计、净投入合计、持有份额合计、做T总轮数/毛利/双边佣金/净利。曾两次被用户指出漏了交易天数和净投入。交易日数要按A股实际休市算。
§
ETF网格盘前条件建议推送时间：原09:31→09:24(2026-10-16)→09:20(2026-10-20)。任务e01b833b150d，schedule weekdays at 9:20am，仍推飞书。改时间时注意避免当天重复推送（手动触发+定时触发会撞车）。
§
2026-10-20: 用户要求把 PostgreSQL 装到 D:/Program Files，但网络受限装不了（无 winget/choco；downloads.edb.com、get.postgresql.org DNS 失败；aliyun/huawei 镜像 postgresql/windows/ 目录均404）。已给浏览器手动下载/内网镜像/Docker 三个替代方向待选。