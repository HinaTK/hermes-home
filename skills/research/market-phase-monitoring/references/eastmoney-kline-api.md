# 东方财富 push2his K线接口备忘

## 端点
```
GET https://push2his.eastmoney.com/api/qt/stock/kline/get
  secid: 1.000001(上证) 1.000300 0.399006(创业板) 1.000688(科创50) 1.589720 0.159363
  klt: 101=日线 102=周线   fqt: 1=前复权   end=20500101   lmt=根数
  fields2=f51..f61: 日期,开,收,高,低,量(手),额(元),振幅,涨跌幅%,涨跌额,换手率
```
Headers 必带 `User-Agent: Mozilla/5.0` 和 `Referer: https://quote.eastmoney.com/`。

## 已验证的坑
- **限流瞬断**：连续请求（12个/6标的×日线+周线）会被 `RemoteDisconnected` 断连。
  修复：每次请求间 sleep 0.8s + fetch_kline 内置3次重试（间隔3s）。单标的失败只打 stderr，不炸全局。
- **盘中运行**：当日K线是实时未收盘棒，收盘价非确认值——报告必须标注"盘中快照"，盘后15:35跑才是确认数据。
- **ETF精度**：东财返回3位小数（0.775），格式化别截成2位；ETF成交额分母小，地量比值参考意义弱于指数，ETF 以 ADX/均线为主。
- volume 字段是手数不是股数（×100 才是股数）。
