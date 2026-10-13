---
name: etf-grid-screener
description: This skill screens T+0 ETFs and LOFs suitable for grid trading and computes grid parameters (upper/lower bounds, grid spacing, base price) from public market data. A strict box-identification filter requires at least two highs forming an upper rail and two lows forming a lower rail, with price still inside the box; instruments without a real oscillation box or already broken out are excluded. All output is for educational and research purposes only and does not constitute investment advice.
agent_created: true
---

# ETF 网格筛选器

## 这是干什么的

一键扫描全市场 ETF，挑出**适合做网格**的横盘标的，并算好你要填进券商 APP 的四个数：**上界、下界、基准价（中枢）、网格间距**。输出一份 HTML 报告（含每只的逐档网格线）。

**仅教育研究用途，输出的是参数计算结果，不是买卖建议。**

## 什么时候用

- "给我今日网格报告" / "筛一下适合做网格的 ETF"
- "帮我算 513090 的网格参数"（单只 → 用 `--code 513090` 加速，见下）

## 怎么跑

```bash
# 全市场扫描（一份合并报告，A股+跨境，10~15只，已去重）
python scripts/grid_tool.py --out 输出目录

# 只跑某几只（快，几秒出结果）
python scripts/grid_tool.py --code 513090,510050 --no_dedup --out 输出目录
```

跑完在输出目录得到 `grid_report.html`（给用户看的报告）和 `grid_results.csv`（原始数据）。

**报告怎么看（转告用户的话术）：**
- 大卡四个数照抄进 APP：上界=卖出线、下界=买入基准、中枢=基准价、网格间距
- 网格间距（填APP的数）：日均波幅×七成，**保底1%**，直接抄；红字"最佳间距"=日均波幅×七成（保底0.6%），仅为更勤参考，是否照抄看费率
- 综合评分（满分100）：衡量"适不适合做网格"，**不是涨幅预测**。按榜内相对水平折算（榜首≈95、榜尾60）——若学员问"为什么都是高分/没有低分"，答：能上榜的已是全市场前十几名，死水票在进榜前就被硬过滤拦掉了
- 箱体模式被拒的票说明不在横盘状态，可试 `--bounds golden`（宽口径兜底）

## 常用参数（其余见 references/methodology.md）

| 参数 | 默认 | 说明 |
|------|------|------|
| `--code` | 空 | 只跑指定代码（逗号分隔），调试单票用 |
| `--bounds` | box | `box`=箱体支撑线口径；`golden`=黄金分割宽口径（下跌半路兜底用） |
| `--step` | 0 | 固定间距%（0=按每只 ETF 的日均波幅自适应） |
| `--min_results` / `--max_results` | 10 / 15 | 结果数量兜底区间 |
| `--max_premium` | 10 | 溢价超过此%的跨境/LOF 直接剔除（溢价回落会额外亏损） |
| `--out` | 当前目录 | 报告输出目录 |

## 注意事项

- **同一只票不要叠加两张网格单**（会双倍接货），换参数前先作废旧单
- 名单快照超 30 天会自动尝试联网刷新，失败则沿用旧名单并在报告页脚**明示**快照日期（不静默）
- 数据源为公开免费接口（无需 key），接口变更时的替换方法见 references/methodology.md

## 合规红线（每次输出都要遵守）

- 只说"高分候选/参数计算"，**不说"推荐/建议买入"**
- 每份报告保留"仅教育研究用途、不构成投资建议"声明
- 不向用户下达任何具体买卖指令
