---
name: ashare-etf-data-sourcing
description: Use when 为A股ETF/基金分析取数，或AkShare/东财被限流需回退源。含跟踪偏离/估值口径铁律。
version: 1.0.0
---

# A股 ETF/基金数据取数与口径（ashare-etf-data-sourcing）

为 A 股场内 ETF / 场外基金分析提供取数路径、限流回退链与指标口径铁律。AkShare/yfinance 可用则优先，被限流时按本表回退，所有字段均可纯 urllib+正则取到。

## 触发场景
- 任何需要 ETF 行情/净值/规模/费率/成立日期/跟踪标的 的分析（选品、深评、同类粗筛）
- AkShare 或东财 push2 报 RemoteDisconnected（连接直接断，非 429/403；同会话可能先通后断，重试无用）
- 计算跟踪偏离/成交额/折溢价等派生指标（口径陷阱高发区）

## 限流症状识别
- 表现：http.client.RemoteDisconnected: Remote end closed connection without response；akshare request_with_retry 耗尽后抛 requests.exceptions.ConnectionError
- 特征：push2 同一会话 ulist 先成功后失败；push2his/clist 可能全断。**不是代码 bug，重试与换库都无效，直接切端点**
- fundf10.eastmoney.com / fund.eastmoney.com / proxy.finance.qq.com / qt.gtimg.cn 是独立域名，通常不受波及

## 字段 → 端点速查表

| 字段 | 首选 | 限流回退（实测可用） |
|---|---|---|
| 现价/涨跌快照 | AkShare spot | qt.gtimg.cn/q={sym列表}（GBK，~ 分隔，f[3]现价） |
| 日K/指数K线 | AkShare hist | 腾讯 proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param={sym},day,,,{count},qfq；取 data[sym].qfqday（无则 .day）；行=[date,open,close,high,low,vol(手)]，无成交额列，近似=mean(vol×100×(H+L)/2) |
| 基金规模（季度净资产） | AkShare | fundf10.eastmoney.com/FundArchivesDatas.aspx?type=gmbd&code={code}&rt=0.1（Referer=gmbd 页）；返回 var gmbd_apidata 内嵌表，td.tor 顺序：日期|期间申购|期间赎回|期末总份额|期末净资产亿元|变动率，首行=最新季 |
| 费率/跟踪标的/成立日期 | AkShare | fundf10.eastmoney.com/jbgk_{code}.html 静态 HTML 正则；成立日期用宽松 r'成立日期[^0-9]*(\d{4}-\d{2}-\d{2})'（严格 th/td 配对会漏）；该页资产规模常为 None |
| 净值序列（跟踪偏离用） | — | fund.eastmoney.com/pingzhongdata/{code}.js 的 Data_netWorthTrend（Referer 必需） |
| 同类清单 | push2 clist 全表 | 本地 grid-research/{最新目录}/result.json 的 ranking[].code/name，按名称关键词聚类 |

## 腾讯可用指数代码
sz399971（中证传媒）、sh000852（中证1000）、sh000906（中证800）。**不可用**：801750 等申万系、H30202 全指软件等中证行业 → 返回 0 根，标数据缺失。

## 口径铁律（踩坑实录，违反即产生无意义数字）
1. **跟踪偏离必须净值口径**：市价 vs 指数含折溢价噪音（实测 512980：市价口径 4.67% vs 净值口径 0.63%）。算法：pingzhongdata 净值与指数日K按日期对齐 → 日收益差 → std×√252
2. **增强型 ETF 的正向偏离是增强生效**，不是跟踪失败，不触发"跟踪误差>2%"否决；触发线是"持续**负向**偏离"（实测 159680：年化 5.03%/累计 +8.6% 跑赢中证1000 = 正常）
3. **基准指数取不到时禁止近似硬算**：拿相邻指数当基准会算出荒谬值（实测 515230 拿计算机指数代替全指软件 = 27.57% 垃圾数字）。正确做法：标"数据缺失"
4. **估值多源冲突 >30% 弃弱源**：取与行业 TTM 量级一致的口径，并在报告披露弃用原因
5. **估值分位取不到 → 按缺失保守处理**：对应否决项"既不触发也不视为通过"，禁止编造分位
6. **腾讯K线无成交额列**：20日日均成交额 ≈ mean(vol手×100×(H+L)/2)，报告标注"近似估算"（实测与 AkShare 差 <5%）

## 批量候选深评（"都跑"）的编排要点
- **父会话先取齐粗筛数据**（规模/费率/成交额/成立日期），经 context 注入各子代理——避免 N 个子代理重复踩限流
- 子代理终答可能被截断（status=failed: output truncated / schema 不合规）——完整输出已落盘 cache/delegation/subagent-summary-N-*.txt，read_file 提取 verdict/scores/否决表即可，**勿因 failed 重跑**（实测 3 只里 2 只 failed 但内容全在）
- 合并报告收尾必须是"结论排序面向决策"：哪只能上/哪只等信号/哪只否决 + 一句话理由
- 网格用途的六维交叉修正：网格场景下好时机/好匹配权重实质上升，护城河脆弱/低ROE 杀伤力下降——综合分按定投口径，但结论段按实际用途修正

## 实测快照（2026-10-27，供交叉验证）
- 512980 传媒：净资产46.84亿，费率0.50+0.10，成交3.47亿/日，成立2017-12-27，净值口径偏离0.63%，中证传媒 PE-TTM 30.57/分位27.88%（蛋卷口径）
- 515230 软件：52.42亿，0.50+0.10，1.55亿，2021-02-03，PE≈71 → 盈利收益率1.40%<10Y国债1.62%（B3触发）
- 159680 1000增强：17.83亿，0.50+0.10（同指数被动仅0.20%），1.16亿，2022-11-18，偏离5.03%为增强正向（累计+8.6%）
- 512100 1000被动：206.28亿，0.15+0.05，34.69亿，2016-09-29

## 边界
- 本 skill 只管取数与口径；评分框架归 etf-value-analyzer，编排归 etf-full-analysis，网格参数归回测引擎
- 东财 push2 ulist 字段备忘（限流前可用）：f2现价 f6成交额 f12代码 f14名称 f20总市值 f21流通市值；secid 前缀 sh=1, sz=0
