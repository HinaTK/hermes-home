# ETF 取数协议（API Data Source Protocol）

## 一、双引擎职责分工

### 1.1 yfinance 引擎

**优势**：
- 全球 ETF 覆盖（美股、港股、A股部分）
- 含持仓数据（`holdings` 属性）
- 含费率数据（`info` 字段）
- 历史行情获取便利（`history()` 方法）

**ETF 可获取字段**：

| 字段组 | 关键字段 | 说明 |
|--------|---------|------|
| price | regularMarketPrice, previousClose, fiftyTwoWeekHigh/Low | ETF实时/收盘价 |
| fund_info | totalAssets, navPrice, yield, annualReportExpenseRatio | NAV/规模/费率 |
| holdings | top_holdings (DataFrame) | 前10大持仓 |
| performance | ytdReturn, threeYearAverageReturn, fiveYearAverageReturn | 历史业绩 |
| risk | beta, threeYearStandardDeviation | 风险指标 |

**代码示例**：
```python
import yfinance as yf

# 获取ETF信息
etf = yf.Ticker("SPY")
info = etf.info  # 基本信息
holdings = etf.major_holders  # 持仓人结构
# 部分ETF支持: etf.institutional_holders

# 历史行情
hist = etf.history(period="5y")

# 关键字段
nav = info.get("navPrice")
total_assets = info.get("totalAssets")
expense_ratio = info.get("annualReportExpenseRatio")
yield_val = info.get("yield")
```

**yfinance 对 A 股 ETF 的支持**：
- 代码格式：`510300.SS`（上交所）/ `159919.SZ`（深交所）
- 数据质量不稳定，建议仅作验证用，不作主力

---

### 1.2 AkShare 引擎

**优势**：
- A 股 ETF 数据最全面
- 覆盖基金规模、净值、持仓、估值
- 更新及时（多数当日可取）
- 中文友好

**ETF 相关核心接口**：

| 接口函数 | 用途 | 返回数据 |
|---------|------|---------|
| `fund_etf_spot_em()` | 全部ETF实时行情 | 代码/名称/最新价/涨跌幅/成交额/成交量等 |
| `fund_etf_hist_em(symbol, period, start_date, end_date, adjust)` | ETF历史行情 | 日期/开高低收/成交量/成交额 |
| `fund_etf_fund_info_em()` | ETF基金信息列表 | 基金代码/简称/类型/规模等 |
| `fund_portfolio_hold_em(symbol, date)` | 基金持仓明细 | 股票代码/名称/持仓数量/市值/占比 |
| `fund_open_fund_info_em(symbol, indicator)` | 开放式基金信息 | 累计净值/单位净值等 |
| `index_value_hist_funddb(symbol, indicator)` | 指数估值历史 | PE/PB/股息率/分位数 |

**代码示例**：
```python
import akshare as ak

# 1. 获取ETF实时行情
df_etf_spot = ak.fund_etf_spot_em()
# 筛选目标ETF
target = df_etf_spot[df_etf_spot["代码"] == "510300"]

# 2. 获取ETF历史行情
df_hist = ak.fund_etf_hist_em(
    symbol="510300",
    period="daily",
    start_date="20210101",
    end_date="20260516",
    adjust="qfq"
)

# 3. 获取基金持仓
df_hold = ak.fund_portfolio_hold_em(
    symbol="510300",
    date="2025"  # 年份
)

# 4. 获取指数估值（需要指数代码映射）
# 中证指数估值
df_val = ak.index_value_hist_funddb(
    symbol="沪深300",
    indicator="市盈率"
)
```

---

## 二、数据字段标准化

### 2.1 输出 JSON 标准结构

`fetch_etf_data.py` 输出的标准 JSON 包含以下字段组：

```json
{
  "meta": {
    "symbol_input": "510300",
    "market": "A",
    "etf_type": "broad_index",
    "symbol_normalized": {"akshare": "510300", "yfinance": "510300.SS"},
    "fetch_time_utc": "2026-05-16T10:00:00Z",
    "fetch_time_local": "2026-05-16 18:00:00",
    "engines_used": ["akshare"],
    "engines_failed": []
  },
  "price": {
    "current": 4.125,
    "currency": "CNY",
    "previous_close": 4.110,
    "change_pct": 0.36,
    "fifty_two_week_high": 4.350,
    "fifty_two_week_low": 3.450,
    "volume": 150000000,
    "turnover": 618000000,
    "data_type": "regular_market_close",
    "source": "akshare"
  },
  "nav": {
    "unit_nav": 4.1180,
    "accumulated_nav": 5.2340,
    "nav_date": "2026-05-16",
    "premium_discount_rate": 0.17,
    "source": "akshare"
  },
  "valuation": {
    "pe_ttm": 12.5,
    "pb": 1.35,
    "dividend_yield": 2.8,
    "pe_percentile_3y": 35.2,
    "pe_percentile_5y": 28.6,
    "pe_percentile_10y": 22.1,
    "source": "funddb/csindex"
  },
  "holdings": {
    "top_10": [
      {"code": "600519", "name": "贵州茅台", "weight": 5.2},
      {"code": "601318", "name": "中国平安", "weight": 3.8}
    ],
    "top_10_total_weight": 28.5,
    "total_holdings_count": 300,
    "update_date": "2026-03-31",
    "source": "akshare/fund_company"
  },
  "operation": {
    "fund_size_billion": 350.5,
    "management_fee": 0.15,
    "custody_fee": 0.05,
    "total_expense_ratio": 0.20,
    "tracking_error_annual": 0.35,
    "avg_daily_turnover_million": 5200,
    "listing_date": "2012-05-28",
    "fund_company": "华泰柏瑞基金",
    "source": "akshare/fund_company"
  },
  "performance": {
    "return_ytd": 5.2,
    "return_1y": 12.5,
    "return_3y_annual": 8.3,
    "return_5y_annual": 9.1,
    "max_drawdown_3y": -22.5,
    "sharpe_3y": 0.65,
    "volatility_annual": 18.5,
    "source": "calculated/akshare"
  },
  "tracking_index": {
    "index_code": "000300",
    "index_name": "沪深300",
    "index_current": 4050.25,
    "index_pe": 12.3,
    "index_pb": 1.33,
    "source": "csindex/yfinance"
  },
  "errors": []
}
```

---

## 三、市场适配规则

### 3.1 A 股 ETF 取数流程

```
输入: ETF代码（如 510300）
  │
  ├── Step 1: AkShare fund_etf_spot_em → 获取实时行情
  ├── Step 2: AkShare fund_etf_hist_em → 获取历史行情
  ├── Step 3: AkShare fund_portfolio_hold_em → 获取持仓
  ├── Step 4: AkShare fund_etf_fund_info_em → 获取规模/费率
  ├── Step 5: AkShare index_value_hist_funddb → 获取估值分位
  │
  └── 验证: yfinance 510300.SS → 交叉验证价格
```

### 3.2 港股/美股 ETF 取数流程

```
输入: ETF代码（如 2800.HK 或 SPY）
  │
  ├── Step 1: yfinance.Ticker(symbol).info → 基本信息+价格+费率
  ├── Step 2: yfinance.Ticker(symbol).history("5y") → 历史行情
  ├── Step 3: yfinance.Ticker(symbol).holdings → 持仓（如有）
  │
  └── 兜底: 网页抓取补充缺失字段
```

### 3.3 QDII ETF 取数流程

```
输入: QDII ETF代码 + 底层指数代码（如 513100 + ^NDX）
  │
  ├── 线路A（场内）: AkShare fund_etf_spot_em → A股场内价格
  ├── 线路B（底层）: yfinance Ticker(^NDX) → 底层指数行情
  ├── Step 3: 计算折溢价 = (场内价 - 净值) / 净值
  ├── Step 4: AkShare → 规模/净值/费率
  │
  └── 特别: 检查是否暂停申购（官网/天天基金）
```

---

## 四、数据质量校验规则

### 4.1 必校验项

| 字段 | 校验规则 | 异常处理 |
|------|---------|---------|
| 价格 | 与昨收偏差<15% | >15%标记异常，可能除权或错误 |
| NAV | 与价格偏差<5%（A股ETF） | QDII可能>5%，标注溢价 |
| 规模 | >0 且为合理量级 | =0或极小值标记异常 |
| 费率 | 0<费率<3% | 超范围标记异常 |
| 持仓权重和 | ≈100%（允许±5%） | 偏差过大标记异常 |

### 4.2 时效性要求

| 数据类型 | 最大允许延迟 | 说明 |
|---------|------------|------|
| 价格/成交额 | 当日（T+0） | 必须是最新交易日 |
| NAV | T+1 | QDII可能T+2 |
| 持仓 | 季度 | 季报披露，可能延迟1-2月 |
| 规模 | 周度 | 天天基金有周度更新 |
| 估值分位 | 日度 | 理杏仁/中证指数每日更新 |

### 4.3 异常处理协议

```
数据异常处理:
  ├── API返回空值/None → 标记字段为null，不参与评分
  ├── API返回明显异常值 → 用网页源验证，取可信值
  ├── 多源严重不一致(>15%) → 暂停评分，人工确认
  └── API完全失败 → 降级到网页取数，报告标注⚠️
```

---

## 五、指数代码映射表

### 5.1 常见 A 股 ETF → 跟踪指数映射

| ETF代码 | ETF名称 | 指数代码 | 指数名称 | yfinance指数代码 |
|---------|---------|---------|---------|----------------|
| 510300 | 沪深300ETF | 000300 | 沪深300 | 000300.SS |
| 510500 | 中证500ETF | 000905 | 中证500 | 000905.SS |
| 159915 | 创业板ETF | 399006 | 创业板指 | 399006.SZ |
| 510050 | 上证50ETF | 000016 | 上证50 | 000016.SS |
| 512100 | 中证1000ETF | 000852 | 中证1000 | — |
| 513100 | 纳指ETF(QDII) | — | 纳斯达克100 | ^NDX |
| 513500 | 标普500ETF(QDII) | — | 标普500 | ^GSPC |
| 518880 | 黄金ETF | — | Au99.99 | GC=F |

### 5.2 常见港股/美股 ETF

| ETF代码 | 名称 | 跟踪指数 |
|---------|------|---------|
| 2800.HK | 盈富基金 | 恒生指数(^HSI) |
| 3067.HK | 安硕恒生科技 | 恒生科技(^HSTECH) |
| SPY | SPDR S&P 500 | ^GSPC |
| QQQ | Invesco QQQ | ^NDX |
| IWM | iShares Russell 2000 | ^RUT |
| GLD | SPDR Gold | 黄金现货 |
| EEM | iShares MSCI EM | MSCI新兴市场 |

---

## 六、信源等级在ETF评估中的应用

### 6.1 ETF 特有信源分级

| 数据类型 | Tier 0 (API) | Tier 1 (官方) | Tier 2 (权威) | Tier 3 (参考) |
|---------|-------------|-------------|-------------|-------------|
| ETF价格 | AkShare/yfinance | 交易所行情 | 天天基金/同花顺 | 雪球/集思录 |
| 基金净值 | 基金公司系统 | 基金公司公告 | 天天基金 | 第三方APP |
| 基金规模 | — | 基金公司季报 | 天天基金 | 新闻报道 |
| 指数估值 | — | 中证指数公司 | 理杏仁/Wind | 雪球/投资APP |
| 持仓明细 | yfinance(部分) | 基金季报/半年报 | 天天基金 | — |
| 跟踪误差 | — | 基金年报 | 晨星/Wind | 第三方计算 |
| 费率 | — | 基金合同/公告 | 天天基金 | — |

### 6.2 报告引用格式

```markdown
| 字段 | 数据类型 | 采用值 | 信源1(API) | 信源2 | 信源等级 | 取数时间 |
|------|---------|--------|-----------|-------|:---:|---------|
| 510300最新价 | 场内收盘价 | ¥4.125 | akshare@2026-05-16 | 天天基金4.125 | 🟢🟢🟢🟢+🟢🟢 | 2026-05-16 15:00 |
```
