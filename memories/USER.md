用户偏好Hermes思考深度High。晨间网格建议09:20（北京时间）推飞书，不重复；按账本、格号和可卖库存算价，不等待开盘行情。健康检查报错仅本地保存、不推飞书，交易提醒保留。当前模型 group/smart-split（本地Magpie路由组，单笔不可归因成员，延迟57-121秒）；auto/gpt-6.1-sol 已下线曾致10-22飞书404，当晚已恢复。2026-10-22 589720-024 买F格10,000份@0.797（新一轮F，10-21曾021卖F）：持有57,700/可卖47,700/最大格F/净投入46,818.50/T净利1,189.20。PostgreSQL 待装 D:/Program Files（网络受限，三替代方向待选）。用户对算术准确性要求极高、会逐笔核对：交易日数须扣 A 股假期（2026中秋9/25-27、国庆10/1-7休市，09-23→10-16 实际 11 个交易日）。
§
User wants requested code/docs auto-committed and pushed to origin. Not git add -A; skip secrets, data/, logs/, and unrelated dirty files.
§
When the user scopes a conversation to one product path, stay on that path until they change it; do not bring back other pipelines unprompted.
§
网格记账与汇报要求：用户回复“成功”时，不能默认整张票据所有委托都成交；必须先确认具体代码、买卖方向、成交份额和成交均价，再入账并汇报持仓。
§
用户要求：每确认一笔网格真实成交并入账后，立即给出对应的新剩余操作建议；不能只报持仓/盈亏。建议必须核对当天T+1总可卖库存池和银河旧挂单；存在冲突时明确标注待核，避免重复挂单。
§
用户2026-10-08明确159992→589720迁移允许一边卖旧ETF、一边买新ETF，不要求先清空旧仓；新旧共用4.6万元创新药成本额度。用户期望589720正常单格约8000元，不接受把“首批8000分两批”的试入方案默认为每格约4000元；不授权自动下单。
§
**账本重建铁律（2026-10-13 用户极度愤怒后确立）**：本地票据 status 字段不可作为成交依据。78 张票据中仅 7 张 status="成功"，但 history 有 33 条记录、用户声称做了很多次做T。票据之间存在冲突（如同一天两张票据都卖 A 格 9,100 份），说明 pending 票据不都是独立真实成交。**任何账本重建前必须先向用户索要银河证券交割单作为权威来源**，逐笔核对日期/代码/方向/数量/均价后再入库。绝不假设 pending=未成交，也不假设 history 记录=已成交。用户对记录错误极度愤怒，说"我就不该信你"。
§
用户持有三只 ETF，不是两只：sh589720 科创创新药ETF国泰、sz159363 创业板人工智能ETF华宝、sz159992 创新药ETF银华 (as of 2026-10-14)。159992 处于迁移退出模式（停买、停接回、只卖不买），但仍是真实持仓，不能被排除在 00:01 之外或清零。
§
用户明确任何代码改动都要用Superpowers技能落实（根因调试、失败测试→修复→回归、审查），不需反复提醒，不能只口头声明已使用。排名与ETF代码须分隔，回读原数据，严禁拼错代码。
§
盈利计算分工（2026-10-14）：用户明确期望用 etf_research 回测引擎算网格盈利，不接受手动外推。etf-grid-screener 的 methodology.md §8 明确声明 no backtest，正确做法是把用户引向 AH_analyse/tools/etf_research/ 的 simulate() 引擎，而非自己拍脑袋给月利润/年化数字。
§
etf_research 引擎已知限制（2026-10-14）：grid_model.py 第37行 `if core_qty+4*q > vol[0]*.01` 存在单位不匹配——vol[0] 是手数（lots），core_qty+4*q 是股数。对首根K线成交量偏低的 ETF（如 159569 首根仅 1,464,800 手），1% 手数换算后不够覆盖初始订单股数，导致 ValueError。589720/159363 首根成交量极大（数千万手），即使单位错了也照样通过。这不是低流动性标的的问题，是模型对非资格池标的的系统性偏差。
§
迁移退出模式下的 ETF（当前 sz159992）在 00:01 重算后，可卖份额保持等于持有份额，不要改回 null。用户 2026-10-14 明确拒绝将 sellable_qty 重置为 null，认为可卖的就是可卖的。active=false 只控制是否生成买卖建议，不控制库存可见性。
§
User runs ETF grid trading via 银河证券 and uses Hermes desktop + Feishu as primary interface. Expects messaging to work reliably — "后续不要出问题可以吗" is a recurring expectation, not a one-off request. When Feishu group chat stopped responding after a gateway restart, user's first assumption was that their own configuration was wrong ("我之前不是要求不需要at吗"), not that a setting had silently changed. User accepts proactive monitoring (cron-based health checks) as a valid solution and does not want to be asked permission for every 5-minute check. User's tolerance for configuration drift is near zero — they expect FEISHU_REQUIRE_MENTION=false and FEISHU_GROUP_POLICY=open to stay set without manual re-checking.
§
用户对网格机制理解深入，能区分"接回"与"新一格"概念。2026-10-16 正确指出 0.821 不是 D 格接回价而是 C 下方新格买入价，无需助手过度简化解释。
§
用户关注单边行情下网格的处理方式。2026-10-16 主动提及"之前聊过的单边情况"但当时会话未找到该讨论记录，需在后续会话中主动跟进。159363 当时持续下跌（现价 1.029，跌破 I 格 1.039），九格全仓未平仓。
§
用户要的市况/操作信号必须细到成数（0/1/3/5/7/8成），禁止用粗粒度“半仓”交付。2026-10-23 原话：“半仓只是我举个例子，你可以说1成仓位试探之类的”。已落成 tools/market_phase_check.py 的 action_label 三元组 (label, fraction, reason) 与成数阶梯。
§
用户偏好“直接一点”的表达：要可执行动作（买入/空仓/卖出/几成仓），不要学术指标堆砌。看多/看空结论都要带具体触发条件和时间窗口。