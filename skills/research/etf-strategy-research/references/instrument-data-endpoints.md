# A股ETF工具品质取数：限流时的端点降级链（2026-10-27 实测）

场景：同类粗筛/深评需要 费率、规模、成立日期、净值序列、成交额。akshare 与东财 push2 行情域被限流（RemoteDisconnected）时，以下端点仍可用（fund 域名独立）。

## 端点清单（全部实测 200）

| 数据 | 端点 | 提取方式 |
|---|---|---|
| 管理费/托管费/跟踪标的 | `https://fundf10.eastmoney.com/jbgk_{code}.html` | 正则 `管理费率</th><td[^>]*>([^<]+)`；成立日期用宽松正则 `成立日期[^0-9]*(\d{4}-\d{2}-\d{2})`（首版严格正则漏抓） |
| 规模历史（季度） | `https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=gmbd&code={code}&rt=0.1`，带 Referer=`gmbd_{code}.html` | 返回 JS var 含 HTML 表：`<tr><td>(日期)</td><td class='tor'>(申购)</td>...(期末净资产亿)</td>`；直接正则行组 |
| 净值序列 | `https://fund.eastmoney.com/pingzhongdata/{code}.js` | `Data_netWorthTrend = [{x: 毫秒时间戳, y: 单位净值}]`，取尾部 N 根 |
| 实时价/昨收/涨跌 | `https://qt.gtimg.cn/q=sh512980,...`（gbk） | `~` 分隔：f[3]现价 f[4]昨收 f[32]涨跌% f[30]时间 |
| 日K成交量 | `https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param={sym},day,,,{lmt},qfq` | 行=[date,open,close,high,low,volume(手)]，无成交额列 |

- 成交额近似：`vol(手)×100×(high+low)/2` 的20日均值（粗筛够用，标注"近似"）。
- 同类清单来源：akshare spot 挂了就**从研究池 result.json 的 ranking 拿 code/name**（321只生产宇宙），不重新爬全市场。

## 跟踪误差口径（重要）

- **必须用净值序列算**（pingzhongdata NAV vs 指数日收益差 std×√252）。市价口径混入盘口折溢价噪音：512980 市价口径 4.67% vs 净值口径 0.63%，差 7 倍。
- 增强型 ETF（如159680）的"跟踪偏离"是主动偏离：年化 5.03%、累计漂移 +8.6%（跑赢）是增强生效，不是跟踪失败；负向持续偏离才是。
- 指数基准腾讯可用：sz399971（中证传媒）、sh000852（中证1000）、sh000906；**801750/931186 腾讯没有**（中证全指软件拿不到→标数据缺失，不许拿计算机指数(399369)硬替后当跟踪误差算——算出来 27.57% 是基准错配，不是产品问题）。

## 限流现场特征

- push2 ulist 单次成功后 clist/ulist/push2his 随机断连（RemoteDisconnected），过段时间可能恢复——重试2-3次再降级。
- 腾讯 fqkline 偶发 HTTP 501，重试即可。

## 深评委派（subagent）注意

- 三路并行深评（512980/515230/159680）两路因**输出超长截断/未过 output_schema** 标记 failed，但正文完整落在 `subagent-summary-*.txt`——失败标记≠内容丢失，先读全文再决定重发。
- 给子代理的 context 要预先带齐已验数字（费率/规模/成交额/网格数据），避免其重爬被限流的源。
