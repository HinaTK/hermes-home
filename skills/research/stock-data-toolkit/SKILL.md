---
name: stock-data-toolkit
description: "Use when 分析个股/股息率验证/批量行情采集/高股息两轴分析/选股决策(买入或回避)。westock CLI 语义与陷阱；东财PE分位；四维交叉决策引擎。"
---

# 个股数据工具箱（westock CLI + 股息率核实）

本机个股/ETF 结构化数据主通道。2026-10-27 全量实测（48只标的采集零失败）。触发：个股分析、股息率验证/榜单核伪、批量行情财务分红采集、多源价格仲裁。

## westock CLI

- 位置：`C:/Users/Administrator/.local/bin/westock.exe`（Go 二进制，腾讯自选股数据）
- 来源：skill `@tencent-adm/westock-data` 的 setup.cjs 安装（SHA256 信任链校验）
- 参数不确定时 `westock <命令> --help`；传错报 `unknown flag` 并列出真实支持项

### 高频命令（实测语义）

```
westock search 中国神华            # 定代码（sh/sz/hk五前缀，如 sh601088/hk00005）
westock profile sh601088          # 简况
westock finance sh601088 --limit 4 # 三大表N期。A股字段全（EPSTTM/ROETTM/净利YoY），港股字段少
westock kline sh601088 --period day --limit 250 [--fq qfq]  # K线。港股/指数强制不复权
westock technical sh600036         # 最新一根K的 MA/MACD/KDJ/RSI/BOLL 全套
westock chip sh600519              # 筹码成本（仅沪深A股）
westock dividend sh601088          # 分红历史
westock shareholder sh600036      # 十大股东
westock consensus sh600519         # 机构预期
westock risk sh601088             # 风险事件（仅A股）
```

### 陷阱与语义（踩过的坑）

1. **K线表按日期倒序（最新在前）**：`rows[0]` 是今天。MA20 = 前 20 根。
2. **A股分红 `cashDiviRMB` 是每10股派息**，DPS = 字段÷10。港股 `cashDivPerShare`（+`specialDivPerShare`）无需除。
3. **限流表现是空表不是报错**：偶发返回无行 markdown 表。必须“空结果→退避重试 2-4 次（sleep 1~1.5s×n）”，仍空则显式上报失败清单到 stderr，**严禁静默丢弃**（53只候选丢过23只的事故教训）。
4. **偶发返回旧快照**：finance 接口曾给与实时价矛盾的价格（汇丰 168 vs 实时 142）。**多源打架必仲裁**：以 `https://qt.gtimg.cn/q=<codes>` 腾讯实时为准（GBK，f[3]=现价），westock K线收盘价交叉验证。
5. **批量实时价**：qt.gtimg.cn 一次可拼 30+ 代码，别用 westock 单只循环查现价。
6. **港股 finance 字段少**（无 EPSTTM/ROETTM 全套）：盈利收益率/PE 分位等估值指标对港股需另拉数据源或跳过标注。
7. **历史 PE 序列 westock 没有**：个股 PE 历史分位走东财 datacenter API（见 references/two-axis-analysis-framework.md 的接口与脚本）。

## 股息率口径铁律

**不同榜单无统一口径，同一只票能差出 2-5 个百分点**（实例：中国神华 4.1%/4.51%/5.99%/7.70% 四源四数）。

看任何股息榜先验三件事：
1. TTM 还是单财年？
2. 是否含特别股息？
3. 分母是实时价还是旧价/成本价？

**本机标准口径**：近 365 天已实施除息日每股现金分红合计 ÷ 实时价（TTM）。单财年口径在银行股会系统性低估（2025 起大行普遍中期分红，工行单财年 3.61% vs TTM 5.36%）。

### 高股息陷阱信号

- **股息率是分母跌出来的**：先查净利 YoY，净利 -20% 以上而股息率 >5% → 周期顶/盈利崩塌陷阱（实例：浙能电力 -57%、中国建筑 -24%、华夏银行 -18%）。
- **周期顶高派息**：航运/资源股巅峰股息率是最危险信号（中远海控 App 榜 10.37% vs TTM 5.24%）。
- **TTM 窗口效应**：中期分红首年会把“旧年报末期+新中期”双份塞进窗口，榜首可能是窗口水分（成都银行 7.43% vs 可持续约 5.3%）。

## skill 可用性提示（负资产原则）

用户 2026-10-27 明确：“装了不能用的 skill 没必要留着；依赖不可用 skill 才能发挥作用的 skill 也是负资产”。
- **.so 平台锁死形态**（stock-analysis 实例）：入口脚本 import `core_xxx.cpython-313-x86_64-linux-gnu.so`，绑死 Py3.13+Linux，本机 Windows/Py3.12 报 `ModuleNotFoundError`。文件完整≠可用，实跑验证失败且无法修复 → 卸载或绕过，用本工具箱数据实现同等分析逻辑。
- **PaySkill 壳**：frontmatter `payment.mode: metered` + `service_id` 为 mock 占位符 → 调不通，别装。
- skill 的 SKILL.md/references 里仅“建议数据来源”而非硬依赖时，可用 westock/web_search 等价替代，主 skill 保留。

## 已固化脚本（AH_analyse 仓库，git 跟踪）

| 脚本 | 用途 |
|---|---|
| `D:/Code/AH_analyse/tools/dividend_yield_screener.py` | 候选池×分红史×实时价 → TTM 股息率榜（--market a/hk/all --top N）|
| `D:/Code/AH_analyse/tools/divi_universe_collect.py` | 任意名单全量采集：TTM DPS+财务快照+技术面 → JSON |
| `D:/Code/AH_analyse/tools/divi_rank_analyze.py` | 综合 0.45×股息+0.35×基本面+0.20×技术面 → 排名 |
| `D:/Code/AH_analyse/tools/divi_two_axis.py` + `divi_fill_missing.py` | 两轴框架重刷：盈利收益率/派息率红旗/52周分位（分位抓取失败时补漏 pass） |
| `D:/Code/AH_analyse/tools/divi_pe_pctile.py` | 东财历史PE_TTM → 近5年PE分位（westock 无此能力，用东财 datacenter API） |
| `D:/Code/AH_analyse/tools/divi_decision_engine.py`（+`test_divi_decision.py` 10单测） | 四维交叉终局决策：两轴json+PE分位json → 买入/等回调/等消化/观望/回避（提交 85fa811） |

## 个股分析统一框架（用户定调，必守）

**两轴：分红到手 + 股价上涨**。ROE/PE 等中间指标只作定价工具（盈利收益率 = ROE÷PB = EPS÷现价 = 1÷PE），禁止单独吹 ROE。买入理由 = 便宜（盈利收益率够高）+ 趋势止跌；分红是拿得住的理由不是买入理由。净利 YoY>+50% 必查低基数（五粮液 +89.3% 实为基数重述陷阱）。完整框架见 [两轴分析框架](references/two-axis-analysis-framework.md)。

批量采集 >10 只时直接改 POOL 跑脚本，禁止聊天层手算。交付表格必须脚本渲染原样粘贴。

### 高股息决策流水线（同类问题一律走此链，2026-10-27 用户令固化）

用户原话：「你这个是脚本也好skill也好，问到类似问题的话记得走同样逻辑判断。」凡高股息筛选、股息榜核伪、"XX股值不值得买/该不该回避"类问题，禁止临时口算，必须走下面脚本链：

```
dividend_yield_screener.py   候选池×分红史 → TTM股息率榜
→ divi_universe_collect.py   全量采集（TTM DPS/财务快照/技术面）
→ divi_two_axis.py (+divi_fill_missing.py)   两轴框架（盈利收益率/红旗/52周分位）
→ divi_pe_pctile.py          东财历史PE_TTM → 近5年PE分位
→ divi_decision_engine.py    四维交叉 → 动作+锚价（divi_decision.json + Markdown表）
```

决策规则（透明写死在代码，10项单测锁死，用户可审；PE分位缺失按50中位处理）：
- **回避** = 任一红旗：净利 YoY<-20%（水源枯竭）或 派息率>100%（分本金）
- **买入⚠️边界（2026-10-30 固化，华夏银行事故）** = 四维全达标但净利 YoY 在 -15%~-20% 边界带 → 禁止裸输出"买入"，必须输出"买入⚠️边界"并强制携带小仓提示（≤总资金 3%）+"触-20%即转回避"退出线。起因：华夏银行净利-18.4%，引擎给裸"买入"，人工警告只写在表格下方注脚里，用户暴怒"半点都没看到"。教训固化：**引擎判定与人工保留意见冲突时，保留必须写进代码动作列，不许藏在注脚**。边界带测试已入 test_divi_decision.py（实参回放华夏银行通过，30b918f）。
- **买入** = 股息率≥4.5% 且 盈利收益率≥7% 且 PE分位<50% 且 52周价格分位<60% 且 趋势非空头 且 净利不在边界带
- **等回调** = PE分位<30%（便宜）但价格/趋势/盈利未配合 → 锚价=年线；或 两轴达标但价格分位≥85%（一年高位）
- **等消化** = 两轴达标但 PE分位≥70%（贵）
- **观望** = 其余（两轴至少一轴不够硬）

输出表列：动作|代码|名称|现价|股息率|盈利收益率|PE|PE分位|价格分位|趋势|买点锚|理由。数据源日期变了要重刷上游 json 再决策，不得拿旧快照出新结论。

## 参考文件

- [westock 全量命令速查](references/westock-commands.md)
- [股息率验证实战案例](references/dividend-verification-cases.md) — 2026-10-27 三表核验全过程
