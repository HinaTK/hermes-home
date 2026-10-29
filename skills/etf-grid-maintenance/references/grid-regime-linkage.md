# 网格×市况统一门控 gate_check（2026-10-26 起历次演进）

用户复盘 159363 后拍板的核心规则：单边下跌确认后，网格不应继续新格买入。
经过 10-26~10-27 三轮演进，已定型为统一四级门控并接入回测引擎。

## 演进时间线

| 提交 | 内容 |
|---|---|
| 88d3ab9 (10-26) | 初版 RegimeGate：ADX≥25 且 -DI>+DI → 拦新格买入 |
| 8101603 (10-26) | 统一四级 gate_check：合并 entry_timing 位置判定与 ADX 动能判定 |
| c0b051e (10-26) | 文案校准：'禁入'→'暂停买入(五线全破)'，行为零改动 |
| 65e065e (10-27) | 回测引擎接入 regime_gate=True（修 3 个真 bug） |
| 5173a50 (10-27) | cron 环境静默失效修复（当日 09:20 事故）——修了 sys.path，但不是真根因 |
| ea79f5d (10-27) | 二级阈值 25→20（全池数据 n=3684 支持，用户确认） |
| fb49ea2 (10-28) | cron 解释器钉子：真根因是 cron 用 Py3.14.7（无 pandas） |

## 当前规则（四级，从严者胜）

```
暂停买入(五线全破)   收盘 < ma5/10/20/30/60 全部      → 拦
暂停买入(强动能跌势)  ADX≥20 且 -DI>+DI 且收盘<60日线  → 拦（10-27起，原≥25）
试错仓              破 1-4 条线（带 20日最低退出价）     → 不拦
正常                收盘 ≥ ma60                        → 不拦
```

- 解除条件：收盘站回 5 日线，自动恢复（不需要人工操作）。
- 卖出建议永远保留。行情缺失 fail-open。
- ⛔ 行显式标注，禁止静默消失。紧急逃生口 `--no-regime-gate`。
- **注意 -DI>+DI 方向检查不可省**：8101603 合并时曾丢失（只留 ADX≥25），
  强动能反弹（+DI 主导）被误拦——10-27 接回测时暴露。

## 数据检验结论（用户'有理有据'要求的执行记录）

用户明确说过：'我的方案只是没有依据的直觉，你不一定要合并方案，而是有理
有据得去处理'、'有数据支持吗'。对规则假设必须先跑全池数据再落地：

- ✅ 五线全破后产出变差：2,538 样本，往返 2.47 vs 均线上方 3.47（-29%），
  未来 20 日最深下探 -8.0% vs -5.2%——用户直觉成立。
- ❌ 偏离深度细分危险区：产出曲线非单调（最低点 -1.5% 档 1.80，-3% 后反弹
  3.69），且五线全破状态下偏离日间噪声 ±1pp、69% 日变动>0.6pp——任何
  硬阈值/窄滞回带都会被日内噪声击穿，拒绝采用。
- ❌ ADX 分层区分磨底/下杀（10-26 小样本口径，已被 10-27 全池研究推翻——见下节新结论）：无梯度（2.2~2.7 波动方向不一致），拒绝。
- ✅ 截尾保险定价（573 次首次全破事件对比）：门控均值少亏 121 元/事件，
  P50 -73 / P90 +1,135，平均省 12,033 元资金占用——多数事件少赚一点，
  少数崩盘救命。规则保留，但语义是'保险'不是'收益增强'。

## ADX 阈值全池研究（10-27，ea79f5d 的依据，推翻旧'ADX 分层无梯度'结论）

工具：`tools/probe_gate_full_study.py`（321 只×500 日，probe_only 状态逐日回放，
生产 wilder_adx 截至当日值，1/3 抽样密度保持无前视，断点续跑增量落盘）。
数据：`reports/_probe_gate_full.csv`（6,295 样本日，可复查）。

破3-4线组（n=4204）后续10日梯度（含 t 检验）：

| ADX档 | n | 10日均 | 胜率 | p |
|---|---|---|---|---|
| <15 | 662 | -0.21% | 48% | 0.229 |
| 15-17.5 | 585 | -0.77% | 42% | 0.000 |
| 17.5-20 | 619 | -0.77% | 40% | 0.000 |
| **20-22.5** | 529 | **-1.66%** | **35%** | **0.000（全场最差）** |
| 22.5-25 | 470 | -0.62% | 40% | 0.014 |
| 25-27.5 | 391 | +0.02% | 51% | 0.926 |
| 27.5-30 | 244 | +1.05% | 56% | 0.004 |
| 30+ | 704 | +1.59% | 60% | 0.000 |

**U型曲线**：20-25'爬坡区'最差（t=-9.10 vs ≥25组），≥25反而最好（超跌反弹
温床）。旧小样本'20-25中间态无害'是样本量错觉。决策：拦 20-25（ea79f5d），
**≥25 维持拦不放开**——均值+1.03%是底仓视角，下尾 14.2% 样本 10 日跌超 5%，
且网格逐格接货在单边下坠中的路径回撤未测量，宁严勿松。

**方法教训（本轮连续三次翻车后的总结）**：
1. 我提的规则假设先让数据审判再落地——本会话从小样本U型→全池证实但推翻
   '中间态无害'，两步走才到真结论；
2. 小样本（<100）的组间差异不可作为规则依据，±5%级差异在薄样本下不显著；
3. 10日方向收益≠网格往返收益——动拦截规则前要问'这测的是底仓还是逐格接货'，
   缺口径时宁可不拦也不滥拦（但已拦的宁严勿松）。
- 589720 型脉冲式全破（123 日中 23 日全破、月开关 9 次）与 159363 型
  持续全破是两种物种；现有数据中无可靠变量区分，接受统一规则。

## 回测引擎接入（65e065e，用户要求'回测过程也要符合规则'）

- `gate_check.blocked_buy_days(m5_frame)`：每个交易日 D 用截至 D-1 的日线
  跑生产 gate()（无前视），复用 wilder_adx 同源 ADX，历史不足 65 根 fail-open。
- `grid_model.simulate(..., gate_days=)`：只拦新格买入（初始建仓、卖出、
  结算不受影响）。`regime_gate=True` 透传 engine.run_research。
- 全池结果（63日/1.5%间距/6000格/离线同K线）：198/283 只受影响，
  pnl 均值+183、回撤+0.45pp、期末成本占用-5128、min_cash+1293。

### 回测接入时踩的三个坑（后来者必读）

1. **窗口数据陷阱**：engine 门控判定必须用未裁剪全历史——63 日窗口
   < 65 根均线需求 → 全部 fail-open → 门控版与无门控版逐字节相同
   （症状：d_cycles 全 0）。判定'窗口内日期'，数据用全历史。
2. **continue 跳过循环尾**：拦买入时 `continue` 会连 equity 记录与不变式
   检查一起跳过 → 净值曲线缺被拦日 → final/identity_error 全错
   （589720 early 窗口 identity 差 200.8）。拦的只能是'动作'，不是'迭代'。
3. **顺延语义**：被拦买入顺延到次日（价格仍在 target 下方照样触发），
   trades 总数不必然减少。诚实断言是'被拦日零新格买入'，
   不是'总笔数减少'。合成夹具容易'被拦日无买入信号'——用实证受影响的
   真实形态（长横盘→阶梯深跌→修复）构造测试。

## 10-27 cron 静默失效事故（最重要的教训）

**现象**：09:20 推送照常含 589720 买入 G 格，⛔ 一条没有。前一晚开发环境
预演一切正常（拦截生效）。

**根因链（完整复现）**：
```
cron no_agent 环境 sys.path 只有仓库根目录（无 tools/）
  → fetch_daily_regime 函数内 import market_phase_check（顶层名，
    模块实际在 tools/ 下）抛 ImportError
  → 外层 except Exception 吞掉 → dict(adx=None) 且不带 bars
  → RegimeGate 拿不到任何数据 → fail-open 不拦
  → 连完全不依赖 tools/ 的五线判定都被跳过
```

**修复（5173a50）**：
1. `_load_market_phase_check()`：tools 子包 → tools 目录注入 path → 顶层兜底，
   三级定位。
2. `fetch_daily_regime`：**ADX 算不出时仍返回 bars**（五线判定只吃日线）
   ——组件失败只降级该组件，不能拖死其他不依赖它的判定。
3. 回归测试 `test_cron_env_gate.py`：**子进程模拟 cron 纯净 sys.path**，
   断言 has_bars=True 且 blocks=True。

**教训（必须内化）**：
- **生产验证必须在 cron 同构环境跑**：子进程里只注入 cron 实际有的
  sys.path，跑生产脚本本体（不是开发环境里的 import 组装）。'开发环境
  预演通过'不等于'生产生效'。
- **宽 except 是静默失效的温床**：`except Exception: return 默认值` 会把
  import 失败、网络失败、逻辑错误全部折叠成同一个 fail-open。降级必须
  分层：哪个组件失败就只降级哪个组件，并在 reason 里如实标注。
- fail-open 的方向性代价：门控 fail-open = 放行买入（用户多接货）；
  报警 fail-open = 漏报。设计时要明知哪个方向在失败时更安全。

## 10-28 cron 静默失效二次复发（真根因：解释器不匹配）

**现象**：5173a50 修复后的第一个交易⽇，09:20 cron 推送再次无 ⛔ 且含两只
五线全破 ETF 的买入建议。用户 09:23 报告。手动跑同一脚本同一数据——拦截正常。

**根因链（证据闭合）**：
```
cron 调度器用 Hermes 自带 Python 3.14.7
（C:/Users/Administrator/AppData/Local/hermes/tools/python-3.14.7*/python.exe）
  → 3.14 环境没有 pandas（pandas 是 confirmed_runtime.py 第111行函数内延迟 import）
  → fetch_daily_regime → judge_entry 链路 ModuleNotFoundError
  → ops_main 外层 except 吞掉 → gate=None → fail-open → ⛔ 行消失
```

**为什么 5173a50 没修住**：它的"cron 同构"测试用子进程+纯净 sys.path——但子
进程跑的还是系统 Python312（有 pandas）。**路径同构 ≠ 解释器同构**。连续两天
同类事故（10-27/10-28）都是'验证环境≠生产环境'：第一天错在 sys.path，第二天
错在解释器。

**修复（fb49ea2）——解释器钉子**：
```python
SYSTEM_PY = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
_IS_312 = sys.version_info[:2] == (3, 12) and 'Programs' in sys.executable
if __name__ == '__main__' and not _IS_312:
    sys.exit(subprocess.call([SYSTEM_PY, os.path.abspath(__file__)] + sys.argv[1:]))
```
同款钉子铺到 hermes-home/scripts 全部 10 个 confirmed_runtime 系 cron 脚本
（confirm/eod/rollover/intraday/ops/preview/weekly_rotation/run_rotation/
intraday_bars/rotation_review），蓝本存仓库 deploy_scripts/。

**验证方式（这次才对）**：用 cron 的真实 3.14 二进制直接调 launcher
`"$PY314/python.exe" grid_weixin_execute.py --phase grid` → 接力 312 →
⛔2行、买入0行、卖单保留。3.14 下抽查 confirm（--help 出 usage）与 eod
（盘中正确拒绝）接力正常。

**铁律（升级版）**：cron 验证 = 真实解释器 + 真实 sys.path + 生产脚本本体，
三者缺一不可。找到调度器实际用的 python（`AppData/Local/hermes/tools/python-*`）
直接拿它跑，而不是假设它和你同款。

## 测试索引

- `test_regime_gate.py`：RegimeGate 四级行为 + plan 集成。
- `test_gate_check.py` / `test_entry_timing.py`：统一判定与文案。
- `test_pause_adx20.py`（ea79f5d）：二级阈值 20 的边界钉子（19.9放行/20.0拦/22拦/
  30拦/+DI主导不拦/①级回归/fail-open回归）。
- `test_blocked_buy_days.py` / `test_gate_days_engine.py` /
  `test_regime_gate_engine.py`：回测接入（含无前视、不变式、顺延语义）。
- `test_cron_env_gate.py`：cron 纯净路径回归（10-27 事故的钉子）——注意它只覆盖
  路径同构，解释器同构靠 launcher 钉子 + 手动 3.14 验收（10-28 教训）。
- pytest 收集环境下 `Path(__file__).resolve().parents[1]` 曾解析出意外目录
  导致模块遮蔽——测试文件顶部 sys.path.insert 用显式绝对路径更稳。
  单跑过、全量挂=测试顺序依赖（如 sys.path 里有无 tools/ 导致 ADX 分支
  分叉）：测试自己把依赖路径补齐，不要假设运行环境。
