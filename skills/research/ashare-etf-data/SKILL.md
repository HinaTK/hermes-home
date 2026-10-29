---
name: ashare-etf-data
description: Use when fetching A-share ETF market or fund data.
version: 1.0.0
---

# A股 ETF 取数实战（ashare-etf-data）

触发任务类：任何需要 A股场内 ETF 的**行情、净值、规模、费率、成立日期、成交额、跟踪误差**的取数场景（ETF 深评、同类粗筛、市况监控、网格研究的数据前置层）。

本 skill 只管**取数层**。评分/评估流程走用户 skill（etf-full-analysis / etf-value-analyzer），网格效率走 etf_research 引擎——不重复它们的职责。

## 端点清单（2026-10-27 实战验证）

| 数据 | 首选端点 | 备注 |
|---|---|---|
| 实时快照 | `https://qt.gtimg.cn/q=sh512980,sz159680`（GBK） | 最稳定，几乎不限流 |
| 历史日K/周K | `https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param={sym},day,,,{count},qfq` | **param 顺序：code,period,start,end,count,fq（count 第5位）**；行=[date,open,close,high,low,volume(手)]，无成交额列 |
| 实时列表（多标的市值） | `push2.eastmoney.com/api/qt/ulist.np/get?secids=1.512980,...&fields=f2,f6,f12,f14,f20,f21` | 时通时断 |
| 全量 ETF 列表 | `push2.eastmoney.com/api/qt/clist/get`（akshare `fund_etf_spot_em` 的底层） | **高频限流**（RemoteDisconnected） |
| 历史K线（东财） | `push2his.eastmoney.com/api/qt/stock/kline/get` | 同样高频限流 |
| 费率/跟踪标的 | `fundf10.eastmoney.com/jbgk_{code}.html` | HTML 正则可抓：管理费率/托管费率/跟踪标的；**规模与成立日期抓不可靠** |
| 规模变动（季度） | `fundf10.eastmoney.com/FundArchivesDatas.aspx?type=gmbd&code={code}` | F10 页面 JS 渲染，数据真身在这里；返回 `var gmbd_apidata={content:"<table>..."}`，含期末净资产(亿元)/总份额(亿份)/变动率；需带 Referer |
| 净值序列 | `fund.eastmoney.com/pingzhongdata/{code}.js` | `Data_netWorthTrend = [{x:毫秒, y:单位净值}]`；官方净值口径 |

## 限流现实与降级顺序

东财按域名分层限流，同一天内：`ulist` 可能通而 `clist`/`push2his` 全挂；akshare 报 `ConnectionError: Remote end closed` 时**不要重试库层**，直接换域名/换源。

降级链：东财 push2 → 腾讯 fqkline（行情类）；akshare → fundf10 FundArchivesDatas（基本面类）。两源都抖动时**重试 3 次、间隔 3 秒**的简单循环通常能过（源是抖动不是死）。

同类清单不必拉全市场列表：可从 `grid-research/{最新目录}/result.json` 的 `ranking`（321只池含 code/name）里按名称关键词筛同类。

## 关键陷阱

1. **F10 HTML 是 JS 渲染**：jbgk 页面里表格由接口填充——别在静态 HTML 里硬抠规模/成立日期，去 `FundArchivesDatas.aspx` 拿
2. **腾讯 fqkline param 位置错** → 返回 `data` 为异常 list 结构（不是报错，是静默变形）
3. **sys.path 遮蔽标准库**：把 `tools/etf_research` 插到 `sys.path[0]` 会让它的 `calendar.py` 遮蔽标准库 → pandas 崩 `day_abbr`。**只插仓库根，用 `from tools.etf_research import gate_check` 包导入**
4. **跟踪误差双口径**：市价vs指数（含盘口噪音，实测4-6%）≠ 净值vs指数（官方口径，0.6-1.2%）。**结论必须用净值口径**（pingzhongdata + 指数K线）。增强型 ETF 主动偏离 5%+ 是产品特性不是缺陷——方向为正=跑赢指数
5. **腾讯K线无成交额列**：近似 `成交额 = vol(手)×100×(H+L)/2`，20日均值够用（与 AkShare 独立复算差异<1%）

## 详细资料

- `references/data-sources.md` — URL 模板、返回结构、解析正则、实战输出样例
