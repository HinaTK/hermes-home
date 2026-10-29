# A股 ETF 数据源实战手册

（2026-10-27 三只 ETF 深评实战沉淀；全部端点当日验证过）

## 1. 行情类

### 1.1 腾讯实时快照（最稳）
```
GET https://qt.gtimg.cn/q=sh512980,sz159680,sz159992
编码 GBK；v_sh512980="1~传媒ETF广发~512980~0.797~0.788~..."
字段：~分隔，f[3]=现价 f[4]=昨收
```

### 1.2 腾讯历史K线（东财限流时的主力备源）
```
GET https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param=sh512980,day,,,300,qfq
```
- **param 顺序：code,period,start,end,count,fq —— count 必须在第 5 位**
- 放错位置 → data 为异常 list（静默变形不报错，注意）
- 返回：`data[sym].qfqday` 或 `.day` = [[date,open,close,high,low,volume(手)], ...]
- **无成交额列**；近似：`amount ≈ vol×100×(H+L)/2`（20日均与 AkShare 差异<1%）
- 周K：period=day 换 week
- 偶发 HTTP 501：重试 3 次间隔 3 秒通常能过

### 1.3 东财 push2（分层限流）
- ulist.np/get（多标的市值/现价）：`secids=1.512980,0.159680&fields=f2,f5,f6,f12,f14,f20,f21`——时通时断
- clist/get（全量列表）与 push2his（历史K线）：高频限流 RemoteDisconnected
- akshare `fund_etf_spot_em` 就是 clist 的封装，它挂了别重试库层，直接换源

## 2. 基本面类

### 2.1 天天基金 F10（fundf10.eastmoney.com）
- `jbgk_{code}.html`：静态 HTML 可抓**管理费率/托管费率/跟踪标的**（正则：`管理费率</th><td[^>]*>([^<]+)</td>`）
- **规模/成立日期在静态 HTML 抓不可靠**（JS 渲染）——去 gmbd 接口拿

### 2.2 规模变动（真身接口）⭐
```
GET https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=gmbd&code=512980&rt=0.1
Headers: Referer = https://fundf10.eastmoney.com/gmbd_512980.html
```
返回 `var gmbd_apidata={content:"<table>..."}`，行正则：
```python
re.findall(r"<tr><td>(\d{4}-\d{2}-\d{2})</td><td class='tor'>([\d.,]+)</td>"*5 + ...)
# 列：日期 | 期间申购 | 期间赎回 | 期末总份额(亿份) | 期末净资产(亿元) | 变动率
```
实测输出（2026-09-30 期）：512980=46.84亿、515230=52.42亿、159680=17.83亿、512100=206.28亿…

### 2.3 净值序列（跟踪误差用）⭐
```
GET https://fund.eastmoney.com/pingzhongdata/{code}.js
```
`Data_netWorthTrend = [{"x": 毫秒时间戳, "y": 单位净值}, ...]`（JSON）。

## 3. 跟踪误差计算（双口径陷阱）

- **市价 vs 指数**（腾讯K线直接算）：实测 4.67%/6.33%——含盘口折溢价噪音，**不是官方口径，不要用它下结论**
- **净值 vs 指数**（pingzhongdata + 指数K线）：实测 512980=0.63%、512100=1.22%——官方口径
- 增强型 ETF（159680=5.03%，累计漂移+8.6%）：主动偏离是产品特性；正漂移=跑赢指数
- 指数K线（腾讯可用）：中证传媒=sz399971、中证1000=sh000852；全指软件（801750）腾讯没有

## 4. 环境陷阱

- `sys.path.insert(0, 'tools/etf_research')` 会让目录内 `calendar.py` 遮蔽标准库 → pandas 崩 `day_abbr`。**只插仓库根，包导入**：`from tools.etf_research import gate_check`
- `gate_check.gate(frame)` 接受 **DataFrame 不是 list**（`judge_entry` 内部要 `.columns`）；`gate_check.check` 不存在
- 同类清单捷径：`grid-research/{最新目录}/result.json` 的 `ranking`（321只含 code/name）按名称关键词筛

## 5. 当日实测快照（可作回归对照）

| 代码 | 净资产(亿) | 费率 | 20日均成交(亿) | 成立 |
|---|---:|---|---:|---|
| 512980 | 46.84 | 0.50+0.10 | 3.47 | 2017-12-27 |
| 515230 | 52.42 | 0.50+0.10 | 1.55 | 2021-02-03 |
| 159852 | 90.01 | 0.50+0.10 | 3.29 | 2021-01-29 |
| 159680 | 17.83 | 0.50+0.10 | 1.16 | 2022-11-18 |
| 512100 | 206.28 | 0.15+0.05 | 34.69 | 2016-09-29 |
