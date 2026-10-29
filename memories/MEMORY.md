表格交付铁律（2026-10-23 编造 recent20 列，同类第4次）：交付任何数据表必须由脚本渲染产出原样粘贴（entry_rank --render / grid_summary / render_eod），禁止聊天层手打数字；终端输出没有的列不得凭印象填。已固化 render_markdown（f8e06b7）；weekly 周报+飞书摘要均带 entry_rank 双规则榜单（888a347，94测试过，真实输出与CSV逐字节一致），cron 5d8180a8d025 无需改配置自动生效。断言用共享常量 ENTRY_BLOCK_TITLE，禁止手写字符串比对表头。
§
User expects immediate updated operation suggestions after each confirmed trade execution.
§
User wants all trading data verified against actual brokerage statements and considers local ledger as provisional until confirmed.
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
账本铁律（2026-10-09算错题被骂后确立）：任何金额/份额/成本计算逐笔列明反复核对，禁凭印象。账本规则：每lot记数量/单价/买入日/T+1可用日；pos[qty]=Σlot且sync_qty同步；可卖库存=available_from≤今日的lot合计（T+1池）；卖出消耗T+1池按FIFO，目标格标识不变；T+0当日不可卖但可挂T+1卖价；cost_cash=Σ(qty×price+佣金)，卖出从T+1池扣成本。
§
接回格铁律：卖哪格接哪格（卖D格→D-rebuy；10-12两次犯“卖E接F”被纠正）。ID具体到格号，不说“下一格”。接回价=卖出价÷1.015、份额=LOT_BUDGET÷接回价取整百，必须脚本算出，不得另编价冒充；成交价偏离网格点要明说差异。159992迁移退出只有卖单。
§
用户明确ETF状态需求：每只ETF的qty、sellable_qty、max_grid(A-Z)都是持久化、脚本可修改的变量，不是展示时临时计算的口径。买入从当前max_grid取下一号并更新，卖出取当前号再退一号；标签保存到交易记录，不人工硬编码。每日00:01从交易记录重算qty并写回sellable_qty=qty；买入增加qty不增加sellable_qty，卖出同时扣减二者，卖出建议读取持久化sellable_qty。用户要求汇报数字来自真实脚本输出，区分用户输入、人工设置与脚本自动生成。
§
曾讨论单边行情（@session:default/20260922_141141_e5b6cb 消息4354/5332）：上涨不追涨、下跌只买不卖时评估暂停/换ETF，旧亏损不消失。检索不到≠没聊过。
§
159866 日经ETF：用户2026-10-20曾定三档建仓方案但未执行，2026-10-27用户明确说"没有159866"——无持仓。后续不得引用为用户持仓。
§
A股交易日计数必须扣除法定节假日，不能只扣周末。2026年：中秋节9/25(五)-9/27(日)休市、国庆10/1-10/7休市、10/10(周六)补班不开市。曾把09-23→10-16算成18个交易日，实际只有11天。任何涉及交易日/交易天数的汇总，先查当年交易所休市安排再算。
§
网格汇总合计必含：交易区间、自然日、交易日数、成交笔数、买卖金额、佣金、净投入、持有份额、T轮数/毛利/双边佣金/净利；交易日数按A股休市算。
§
ETF网格盘前条件建议推送时间：原09:31→09:24(2026-10-16)→09:20(2026-10-20)。任务e01b833b150d，schedule weekdays at 9:20am，仍推飞书。改时间时注意避免当天重复推送（手动触发+定时触发会撞车）。
§
排名交付纪律：用户要“前N”=完整往返次数榜，必须过建仓资格（entry_rank.py 调 entry_timing.judge_entry）；持仓不排除——并入同一张榜正常排名、标“持仓”标签。禁止拿综合 score 榜冒充；同次数按 full_cycle_net 降序再按 code 升序；标注模型/窗口/覆盖；同一日多轮取最新目录。
§
【高优先级原则（用户于2026-10-22明确要求提升）】一个任务如果用户可能多次提问且可通过脚本代码落地，必须首选代码脚本方案，禁止临时口算或一次性脚本。判断顺序：接到任务→找现成模块→没有则评估是否重复性→是则TDD落代码+测试→以后一律跑模块。已实例：grid_summary.py汇总（e702249）、account_total_pnl总盈亏（c1645bb）。与“代码改动走Superpowers TDD”构成闭环；同类错误第三次视为流程问题。
§
项目级 skills 在 D:/Code/AH_analyse/skills/。159866溢价系结构性（100净值日 79%>2%，中位+2.36%）：只用于同指数选品与>5%预警。左侧vs右侧（500日）：左60日+16.6%/胜率93%占优但有牛市区间偏差，尾部风险靠 25% 止损覆盖。
§
两段式=汇总表（标的|收盘|涨跌|动作成数|三信号●○|理由），2026-10-29 起【关键读数】分节已砍（ae2bb72，用户嫌太长），推送到表格为止；
§
盘中触价规则（10-26）：建议只在成交确认后生成起有效，首见记极值基准，仅现价触价或越过基准的新极值才提醒；消失即清窗，重生窗口重开。实现于 monitor()（5724005）。
§
用户会跨轮次比对历次交付，每个数字默认会被审计；单字“落地”=立即TDD执行并提交推送，不再确认。
§
盘后建议转述照 plan() 原样给，禁止附加“明日某格解锁后方可卖”类推论（10-26再犯）：卖出建议校验=可卖池总量≥目标格数量，脚本给出即今日可执行；未生成时才说明池子不足。
§
四级门控 gate_check（ea79f5d）：①五线全破拦＞②强动能拦（ADX≥20且-DI＞+DI且收盘<60日线）＞③试错仓（附退出价）＞④正常；从严者胜、fail-open、+DI主导不拦。全池依据（n=3684）与工具 tools/probe_gate_full_study.py 见 etf-grid-maintenance skill。盘中未接gate。
§
群“个股分析”=个股分析。主力 skill：个股排雷(stockscreening)+valuation-analysis+caopan-baodian；stock-analysis 的 scripts 是 .so 平台锁死（Py3.13/Linux 编译），本机 Windows/Py3.12 不可跑，其 SKILL.md 方法论可参考但脚本勿试。个股取数一律走 stock-data-toolkit skill（westock CLI C:/Users/Administrator/.local/bin/westock.exe + 腾讯实时价仲裁；股息率 TTM 口径；限流空表退避重试禁静默丢票）。neodata 已卸载（付费壳）；公告/新闻用 web_search 兜底。
§
个股分析统一框架（2026-10-27定调）：用户只关心分红到手+股价上涨两轴。ROE 等中间指标只作定价工具（盈利收益率=ROE÷PB），禁止单独吹 ROE——用户用美菷2021案例实证：108元买入五年含息回报≈0，ROE 高但买贵了照样白拿。结论：分红是拿得住的理由，买入理由=便宜（盈利收益率够高）+趋势止跌。
§
大任务交付要求（10-27原话"不要中断，不要偷工减料"）：多步大任务先建todo清单，连续执行到完整交付，不中途中断确认。
§
推送排版铁律（2026-10-29 收紧）：多标的盘后推送先汇总表（表头+分隔行飞书才渲染）；开关状态用●/○串；数字逐格来自脚本。市况推送已砍【关键读数】分节（ae2bb72）：render_report=表头口径+汇总表，到表格为止；render_instrument 仅人工查询。坑：链式三元优先级、备用源pct硬编码0、改渲染须同步改所有调用方并真跑验收。
§
纳指趋势持有方案存档 reports/nasdaq-etf-trend-holding-plan.md（4c7add2）：底仓40%+回撤≥8%加仓（cap8）+反弹≥10%卖加仓；513300；回测9买9卖全+10~12%离场；当前未到买点，触发价2.208。
§
cron script字段铁律（10-29第4/5次部署事故）：①script=脚本文件名/路径，绝不能塞shell命令（会拼成路径→Script not found）；②cron会话的 sys.executable=hermes CLI二进制非纯python——cron脚本里起子进程禁用sys.executable，一律显式SYSTEM_PY绝对路径（错误特征：报错含'usage: hermes'）；③新建任何cron后必须先手动run触发一次并读真实输出才算部署完成——手动跑+3.14跑都通过≠cron会通过，唯一生产级验收=真实cron run触发并读输出文件。
§
hermes-home仓库（公开!）已净化（10-29 d4b959a）：软重置剔除backups/、config.yaml.bak*、installs/、shared/nous_auth.json（含活refresh_token，曾躺在公开远端）；.gitignore加固；git_daily_push.py加提交前秘密守卫（TDD 6测试）。OpenRouter key从未到达远端。待办：用户需在Nous Portal轮换refresh_token。备份分支backup/pre-scrub-20261029仅存本地。
§
OpenViking守卫已双保险（2026-10-29部署）：①Hermes cron 1861dff8e422（*/5分钟，no_agent，脚本 openviking_auto_heal.py 于 hermes-home/scripts/，健康静默/挂了DETACHED重启+告警飞书，真实故障演练通过：杀进程→14秒内自愈）；②Windows计划任务 OpenViking_Supervisor（曾静默丢注册致10-20~10-29宕机9天，已重建）。排障要点：tasklist/curl查1933端口；agent.log报'openviking-server not found'=服务器死；schtasks /query 查任务是否还在。