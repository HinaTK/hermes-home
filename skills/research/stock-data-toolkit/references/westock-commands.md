# westock 全量命令速查（2026-10-27 实机实测）

CLI 路径：`C:/Users/Administrator/.local/bin/westock.exe`。原始文档在 skill `@tencent-adm/westock-data` 的 references/（commands.md / routing-guide.md / scenarios-guide.md / ai_usage_guide.md），本文只收高频命令与实测补充。

## 命令树

- 行情：kline（m1~year 周期；--start/--end 优先于 --limit；qfq/hfq/bfq 复权，港股指数强制不复权）
- 技术：technical（MA/MACD/KDJ/RSI/BOLL，多股逗号分隔可对比）、chip（筹码，仅沪深A股）
- 市场：changedist、connect、ipo、lhb（全市场龙虎榜）、market-overview（--type trade/interval/technical/updown/margin/valuation/rotation，多类逗号一次拉）、trade-calendar
- 指数：index list / index constituent
- 板块：sector constituent/finance/forecast/info/oper/ranking/valuation
- 发现：search（默认仅股票；--type etf,bond,sector,index,futures,forex 多类型逗号分隔；别加 --market hk/us）
- 财务：finance（--limit N 期数）、disclosure（披露日历）
- 资金：fund block/flow/lhb/margin/north-holding/short/south-holding
- 简况：buyback、dividend、profile、shareholder
- ETF：etf holdings/nav/overview/profile
- 研究：consensus（机构预期，A股港股）、esg、rating（港美股）、report list/detail、score
- 资讯：notice list/detail
- 事件：calendar、risk（仅A股）、suspension
- 宏观：macro

## 实测补充（官方文档没写的）

1. kline 输出列名是 `date/open/last/high/low/volume/amount/exchange`（收盘在 `last`，不是 `close`；港股无 exchange 列差异）。**行序倒序**：最新在 rows[0]。
2. volume 是手数不是股数（与 etf_research 引擎的教训一致）。
3. dividend 表：A股列 bonusShareRatio/cashDiviRMB(每10股)/dividendPlan/exDiviDate/reportEndDate/totalCashDiviComRMB；港股列 cashDivPerShare/cashPayDate/exDiviDate/reportEndDate/specialDivPerShare/totalCashDivi。
4. finance 表用 `**利润表**` / `**资产负债表**` / `**现金流量表**` 分段，markdown 表解析时可按此 split。
5. technical 表最新一根的字段：BOLL_LOWER/MID/UPPER、DEA、DIF、KDJ_D/J/K、MACD、MA_5/10/20/60/120/250、RSI_6/12/24、closePrice。
6. consensus 输出目标价 + 分年 eps/pe/pb/ps/netProfitYoy 表（A股）；港股按季度 epsForecast/netProfitForecast/peRatioForecast。
7. 腾讯实时备用：`https://qt.gtimg.cn/q=sh601088,hk00005`（GBK；f[1]名称 f[3]现价 f[4]昨收 f[31]涨跌 f[32]涨跌幅 f[45]市值；数据时间戳在 f[30]）。价格仲裁以它为准。
8. 限流：连爆几十次查询后偶发空表，退避 1~1.5s 递增重试 2-4 次即恢复；千万别把空表当"无分红"入库。
