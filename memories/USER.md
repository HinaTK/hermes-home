User prefers Hermes 思考深度 High; UI maps to agent.reasoning_effort and defaults to medium if unset.
§
User wants requested code/docs auto-committed and pushed to origin. Not git add -A; skip secrets, data/, logs/, and unrelated dirty files.
§
Do not treat AH_analyse plans as cross-session memory. Within a session, follow the last agreed plan; do not replace it with the latest audit gap. After the 2026-09-21 health check, the product next step was the pre-market decision card, not adding PE/change/price-date to pick cards.
§
When the user scopes a conversation to one product path, stay on that path until they change it; do not bring back other pipelines unprompted.
§
网格记账与汇报要求：用户回复“成功”时，不能默认整张票据所有委托都成交；必须先确认具体代码、买卖方向、成交份额和成交均价，再入账并汇报持仓。
§
用户要求：每确认一笔网格真实成交并入账后，立即给出对应的新剩余操作建议；不能只报持仓/盈亏。建议必须核对当天T+1总可卖库存池和银河旧挂单；存在冲突时明确标注待核，避免重复挂单。
§
用户2026-10-08明确159992→589720迁移允许一边卖旧ETF、一边买新ETF，不要求先清空旧仓；新旧共用4.6万元创新药成本额度。用户期望589720正常单格约8000元，不接受把“首批8000分两批”的试入方案默认为每格约4000元；不授权自动下单。
§
用户要求交易情况“汇总”必须包含每只ETF持仓份额、持仓成本与加权单位成本、现金及成交核对；不可仅概述策略或只报网格价差。行情需标明确切报价时间、区分盘后最后价与真实收盘价；账本与已确认成交不一致须先核对再汇报。
§
- 成本核算口径（用户认可）：净投入 = 买入含费合计 − 卖出净回笼。卖出不减少剩余份额成本基础，只减少净资金占用。用户会逐笔验算，不接受按 lot 扣减的持仓成本口径。
- T+1 池规则（用户明确）：卖出消耗总可卖库存池（按买入日期 FIFO），目标格 qty 保持不变——目标格只标识哪个网格价位被触发。pos["qty"] 必须始终等于所有 lot 的 qty 之和。
- 网格价差口径（用户明确）：同格卖价减买价，与 T+1 池消耗哪批货无关。池子只是保证有货可卖，经济结果就是那个差价。
- 轮换检查必须用全市场 321 只合格 ETF 池（grid-broad-20260923/eligibility.csv），不能只用 13 只主题候选。持仓永远参与比较但不参与领先者判定。
- 腾讯日线接口 URL 必须用 https://ifzq.gtimg.cn（不带 web. 前缀），web.ifzq.gtimg.cn 返回 501。
§
**账本重建铁律（2026-10-13 用户极度愤怒后确立）**：本地票据 status 字段不可作为成交依据。78 张票据中仅 7 张 status="成功"，但 history 有 33 条记录、用户声称做了很多次做T。票据之间存在冲突（如同一天两张票据都卖 A 格 9,100 份），说明 pending 票据不都是独立真实成交。**任何账本重建前必须先向用户索要银河证券交割单作为权威来源**，逐笔核对日期/代码/方向/数量/均价后再入库。绝不假设 pending=未成交，也不假设 history 记录=已成交。用户对记录错误极度愤怒，说"我就不该信你"。
§
用户明确（2026-10-14）：新成交日期默认使用向助手发送成交信息的北京时间日期；成交ID由脚本沿该ETF序列自动递增，不要求用户提供银河编号。用户要求旧网格账本/脚本移出活跃路径以避免污染，保留新已确认子账。
§
用户要求券商网格设置只按其实际APP截图逐字段指导，勿猜金额/份数、自动委托或挂单数。159612倾向同花顺半自动、每次8000元；未确认提交。不可用日内波幅达标天数冒充完整往返推月/年收益；此前52%年化已撤回。
§
用户持有三只 ETF，不是两只：sh589720 科创创新药ETF国泰、sz159363 创业板人工智能ETF华宝、sz159992 创新药ETF银华 (as of 2026-10-14)。159992 处于迁移退出模式（停买、停接回、只卖不买），但仍是真实持仓，不能被排除在 00:01 之外或清零。
§
代码展示铁律（2026-10-14）：终端输出中排名数字与代码紧邻时（如「2 159569」），用户会误读为「2159569」。展示前必须回读原始数据逐字确认，不能凭视觉印象拼接。用户对数字/代码错误零容忍。
§
盈利计算分工（2026-10-14）：用户明确期望用 etf_research 回测引擎算网格盈利，不接受手动外推。etf-grid-screener 的 methodology.md §8 明确声明 no backtest，正确做法是把用户引向 AH_analyse/tools/etf_research/ 的 simulate() 引擎，而非自己拍脑袋给月利润/年化数字。
§
etf_research 引擎已知限制（2026-10-14）：grid_model.py 第37行 `if core_qty+4*q > vol[0]*.01` 存在单位不匹配——vol[0] 是手数（lots），core_qty+4*q 是股数。对首根K线成交量偏低的 ETF（如 159569 首根仅 1,464,800 手），1% 手数换算后不够覆盖初始订单股数，导致 ValueError。589720/159363 首根成交量极大（数千万手），即使单位错了也照样通过。这不是低流动性标的的问题，是模型对非资格池标的的系统性偏差。
§
迁移退出模式下的 ETF（当前 sz159992）在 00:01 重算后，可卖份额保持等于持有份额，不要改回 null。用户 2026-10-14 明确拒绝将 sellable_qty 重置为 null，认为可卖的就是可卖的。active=false 只控制是否生成买卖建议，不控制库存可见性。