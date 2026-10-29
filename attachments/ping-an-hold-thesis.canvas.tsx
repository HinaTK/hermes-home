import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  LineChart,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from "cursor/canvas";

const PRICE = 52.61;
const BVPS = 56.78;
const EVPS = 86.58;
const TRAILING_DPS = 2.73;

const GROWTH = [200, 300, 400, 500];
const COST = [800, 850, 900, 1000];
const ROE = [800, 1000, 1270, 1400];

function pctLabel(bps: number): string {
  const value = bps / 100;
  return Number.isInteger(value) ? `${value.toFixed(0)}%` : `${value.toFixed(1)}%`;
}

function yuan(value: number): string {
  return `${value.toFixed(1)}元`;
}

function AssumptionLab() {
  const [growthBps, setGrowthBps] = useCanvasState("growth-bps", 300);
  const [costBps, setCostBps] = useCanvasState("cost-bps", 850);
  const [roeBps, setRoeBps] = useCanvasState("roe-bps", 1270);

  const growth = growthBps / 10000;
  const cost = costBps / 10000;
  const roe = roeBps / 10000;
  const spread = cost - growth;
  const valid = spread > 0;
  const dividendValue = valid ? (TRAILING_DPS * (1 + growth)) / spread : 0;
  const justifiedPb = valid ? (roe - growth) / spread : 0;
  const residualValue = justifiedPb * BVPS;

  return (
    <Card>
      <CardHeader trailing={<Text size="small">现价 {yuan(PRICE)}</Text>}>
        假设试算：同一价格，两套公式
      </CardHeader>
      <CardBody>
        <Stack gap={14}>
          <Text size="small" tone="secondary">
            股息用近12个月每股2.73元（2025年末期1.75元加2026年中期0.98元）。净资产用2026年6月30日每股56.78元。默认一组审慎假设：分红增长3%，股权成本8.5%，营运ROE维持2025年的12.7%。
          </Text>
          <Stack gap={6}>
            <Text size="small" weight="semibold">
              分红长期增长率
            </Text>
            <Row gap={8} wrap>
              {GROWTH.map((bps) => (
                <span key={bps}>
                  <Pill active={growthBps === bps} onClick={() => setGrowthBps(bps)}>
                    {pctLabel(bps)}
                  </Pill>
                </span>
              ))}
            </Row>
          </Stack>
          <Stack gap={6}>
            <Text size="small" weight="semibold">
              股权成本
            </Text>
            <Row gap={8} wrap>
              {COST.map((bps) => (
                <span key={bps}>
                  <Pill active={costBps === bps} onClick={() => setCostBps(bps)}>
                    {pctLabel(bps)}
                  </Pill>
                </span>
              ))}
            </Row>
          </Stack>
          <Stack gap={6}>
            <Text size="small" weight="semibold">
              长期营运净资产收益率
            </Text>
            <Row gap={8} wrap>
              {ROE.map((bps) => (
                <span key={bps}>
                  <Pill active={roeBps === bps} onClick={() => setRoeBps(bps)}>
                    {pctLabel(bps)}
                  </Pill>
                </span>
              ))}
            </Row>
          </Stack>
          <Divider />
          {valid ? (
            <Grid columns={2} gap={16}>
              <Stat
                value={yuan(dividendValue)}
                label="戈登增长模型价值"
                tone={dividendValue > PRICE * 1.1 ? "success" : dividendValue < PRICE * 0.9 ? "warning" : "info"}
              />
              <Stat
                value={yuan(residualValue)}
                label={`剩余收益价值，对应市净率 ${justifiedPb.toFixed(2)} 倍`}
                tone={residualValue > PRICE * 1.1 ? "success" : residualValue < PRICE * 0.9 ? "warning" : "info"}
              />
            </Grid>
          ) : (
            <Callout tone="danger" title="这组假设不能用于永续模型">
              股权成本必须高于永续增长率，否则公式分母为零或为负。
            </Callout>
          )}
          {valid ? (
            <Text size="small" tone="secondary">
              {reading(dividendValue, residualValue, roeBps)}
            </Text>
          ) : null}
        </Stack>
      </CardBody>
    </Card>
  );
}

function reading(dividendValue: number, residualValue: number, roeBps: number): string {
  const dividendGap = ((dividendValue - PRICE) / PRICE) * 100;
  const residualGap = ((residualValue - PRICE) / PRICE) * 100;
  const roeNote =
    roeBps >= 1270
      ? "这条路径要求寿险利差不再继续收窄。"
      : "这条路径承认寿险营运回报会继续向股权成本靠拢。";
  return `股息模型相对现价 ${signed(dividendGap)}，剩余收益模型相对现价 ${signed(residualGap)}。${roeNote}`;
}

function signed(percent: number): string {
  const rounded = percent.toFixed(0);
  return percent >= 0 ? `高 ${rounded}%` : `低 ${Math.abs(percent).toFixed(0)}%`;
}

export default function PingAnHoldThesis() {
  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>中国平安还能否持有</H1>
        <Text tone="secondary">
          A股 601318，2026年10月27日收盘 52.61 元。基本面截至 2026 年 6 月 30 日中报，三季报未纳入。这是估值框架下的研究判断，不是买卖指令。
        </Text>
      </Stack>

      <Callout tone="info" title="质地支持长期持有，价格只在特定假设下明显便宜">
        近 12 个月股息率 5.19%，市净率 0.93 倍，集团内含价值 0.61 倍，滚动市盈率 5.98 倍。股息贴现把现价解释成一份约 3% 增长、8.5% 要求回报的现金流。剩余收益和内含价值要便宜得多，前提是营运净资产收益率守住约 13%，并且 4% 的长期投资回报假设不被利率证伪。
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat value="0.61×" label="市值 / 集团内含价值" tone="info" />
        <Stat value="0.93×" label="市净率，每股净资产 56.78 元" />
        <Stat value="5.19%" label="近 12 个月股息率" tone="success" />
        <Stat value="6.8×" label="滚动营运利润市盈率" tone="warning" />
      </Grid>

      <H2>从 2026 年 10 月持有两年</H2>
      <Text>
        按 2026 年 10 月 27 日收盘价买入、2028 年 10 月 27 日按当时市价卖出。2026 年中期股息每股 0.98 元已于 9 月 10 日除息，这次买入领不到。两年内按往年节奏大约有四次分红：2026 年末期、2027 年中期、2027 年末期、2028 年中期。股息按现金计算，不假设再投入股票。持股满一年的 A 股个人投资者，这几笔股息目前按免征个人所得税处理。
      </Text>
      <Grid columns={3} gap={16}>
        <Stat value="7%" label="最可能路径的年化收益" tone="info" />
        <Stat value="14%" label="这条路径的两年累计收益" />
        <Stat value="8%" label="三条路径按概率加权后的年化" />
      </Grid>
      <Table
        headers={["路径", "概率", "两年后股价", "两年股息", "两年累计", "年化"]}
        columnAlign={["left", "right", "right", "right", "right", "right"]}
        rows={[
          ["压力：内含价值不增长，倍数降到 0.50", "30%", "43.3 元", "5.4 元", "-7.5%", "-3.8%"],
          ["磨底：内含价值每年 +4%，倍数降到 0.58", "45%", "54.3 元", "5.8 元", "+14.3%", "+6.9%"],
          ["修复：内含价值每年 +7%，倍数升到 0.75", "25%", "74.3 元", "6.1 元", "+53.0%", "+23.7%"],
        ]}
        rowTone={["warning", "info", "success"]}
        striped
      />
      <Text size="small" tone="secondary">
        概率是判断权重，用来计算期望，不是频率。三条路径合成的期望终端财富约合年化 8.4%。磨底路径权重最高。若倍数停在现在的 0.61 倍、内含价值仍每年增长 4%，年化约为 9.2%，可以看成磨底情形的上沿。
      </Text>
      <H3>每投入 100 元，两年后股价加股息</H3>
      <BarChart
        categories={["压力", "磨底", "修复"]}
        series={[{ name: "两年后收回的金额", data: [92.5, 114.3, 153], tone: "info" }]}
        referenceLines={[{ value: 100, label: "本金 100 元" }]}
        valueSuffix=" 元"
        yMax={180}
        height={220}
        showValues
      />
      <Text size="small" tone="tertiary">
        起点为 2026 年 10 月 27 日收盘价 52.61 元，终点内含价值从 2026 年 6 月 30 日每股 86.58 元按情景增速外推两年。分红增速在压力路径取 0、磨底取 4%、修复取 7%，与公司过去五年现金分红总额复合增速 4.1% 对照。
      </Text>

      <H2>三套理论和现价怎么对上</H2>
      <Text>
        保险公司的债务是经营原料，达摩达兰的金融企业估值因此直接估股权：用股息或剩余收益，不用企业自由现金流。寿险再加一层精算口径。内含价值等于调整净资产加有效业务价值；评估价值再把未来新业务按倍数加回去。市盈率在这里最容易误导，因为公允价值变动会让单季利润大幅偏离承保和利差的经营结果。
      </Text>
      <Table
        headers={["理论", "用到的锚", "52.61 元在说什么"]}
        columnAlign={["left", "left", "left"]}
        rows={[
          [
            "戈登增长",
            "每股股息 2.73 元",
            "增长 3%、股权成本 8.5% 时，价值约 51 元。现价接近一份能缓慢增长的股息",
          ],
          [
            "剩余收益",
            "每股净资产 56.78 元，2025 年营运 ROE 12.7%",
            "同一贴现率下合理市净率约 1.76 倍、约 100 元。0.93 倍等于市场认为 ROE 会落到 8%–9%",
          ],
          [
            "内含价值",
            "集团内含价值每股 86.58 元",
            "市值 9,526 亿元，比 15,678 亿元内含价值低 39%。过去 12 个月新业务价值倍数约 -16 倍",
          ],
        ]}
        striped
      />
      <AssumptionLab />

      <H2>内含价值折价经不起一次小压力，也没有被一次小压力抹平</H2>
      <Text>
        公司计算有效业务和新业务时，长期投资回报假设是 4.0%，传统险风险贴现率 8.5%，分红险和万能险 7.5%。2026 年 10 月 27 日财政部国债曲线上，10 年期收益率 1.63%，30 年期 2.04%。假设比当前长债高出约 2 个百分点。公司用历史组合收益为 4% 辩护：近 10 年平均净投资收益率 4.8%，平均综合投资收益率 4.9%。前瞻的压力在再投资，2026 年上半年净投资收益率（非年化）1.4%，上年同期 1.8%。
      </Text>
      <BarChart
        horizontal
        height={240}
        categories={["A 股市值", "投资回报假设下调 50bp", "中报披露的集团内含价值"]}
        series={[{ name: "人民币亿元", data: [9526, 14171, 15678], tone: "info" }]}
        valueSuffix=" 亿"
        showValues
      />
      <Text size="small" tone="tertiary">
        来源：中国平安 2026 年中报内含价值敏感性；市值按 2026 年 10 月 27 日收盘价 52.61 元和总股本 181.08 亿股计算。下调 50 个基点后集团内含价值为 14,171 亿元，降幅 9.6%；寿险及健康险内含价值降 15.5%。市值仍比压力后内含价值低约 33%。
      </Text>

      <Grid columns={2} gap={20}>
        <Stack gap={8}>
          <H3>每股现金股息</H3>
          <LineChart
            categories={["2021", "2022", "2023", "2024", "2025"]}
            series={[{ name: "全年每股股息", data: [2.38, 2.42, 2.43, 2.55, 2.7], tone: "success" }]}
            valueSuffix=" 元"
            height={220}
            yMin={0}
            yMax={3.2}
            fill
          />
          <Text size="small" tone="tertiary">
            来源：中国平安 2026 年中报分红表。2025 年按归母营运利润计算的现金分红比例 36.4%。公司称过去五年现金分红总额年复合增长 4.1%，总额已连续 14 年上升。
          </Text>
        </Stack>
        <Stack gap={8}>
          <H3>营运净资产收益率</H3>
          <LineChart
            categories={["2023", "2024", "2025"]}
            series={[
              { name: "寿险及健康险营运 ROE", data: [30.2, 25.7, 21.3], tone: "warning" },
              { name: "集团营运 ROE", data: [12.5, 12.7, 12.7], tone: "info" },
            ]}
            valueSuffix="%"
            height={220}
            yMin={0}
            yMax={36}
          />
          <Text size="small" tone="tertiary">
            来源：中国平安 2025 年报。集团营运 ROE 两年持平，寿险及健康险从 30.2% 降到 21.3%。剩余收益模型里的乐观情形，依赖寿险这条线止跌。
          </Text>
        </Stack>
      </Grid>

      <H2>经营事实里，哪些支撑持有</H2>
      <Table
        headers={["观察", "2026 年上半年", "和持有判断的关系"]}
        columnAlign={["left", "right", "left"]}
        rows={[
          ["归母营运利润", "842 亿元，同比 +8.3%", "分红政策锚定营运利润，比净利润更适合当长期收益"],
          ["归母净利润", "926 亿元，同比 +36.1%", "增幅远高于营运利润，滚动市盈率被投资收益抬好看"],
          ["寿险新业务价值", "248 亿元，同比 +11.2%", "新单仍在创造价值；新业务价值率按标准保费降至 29.0%"],
          ["合同服务边际", "7,378 亿元，较年初 +1.7%", "存量未来利润在连续下滑后转升，斜率仍浅"],
          ["财产险综合成本率", "95.1%", "承保本身赚钱，这部分浮存金的成本为负"],
          ["新业务分红险占比", "超过九成", "把投资风险更多分给保单持有人，降低刚性负债成本"],
          ["集团核心 / 综合偿付能力", "165.6% / 198.1%", "高于 50% 和 100% 的监管底线，分红有资本缓冲"],
          ["平安寿险核心偿付能力", "133.8%", "资本够用，利率下行 50bp 时公司披露的核心充足率压力大于集团"],
          ["平安银行", "不良率 1.05%，核心一级资本 9.32%", "信用成本可控，资本偏薄，是综合金融折价的一部分"],
          ["险资不动产", "2,053 亿元，占投资资产 3.1%", "以收租物业和成本法为主，不再是头等风险，公允价值仍不透明"],
        ]}
        striped
      />

      <H2>适合继续持有的条件</H2>
      <Grid columns="1.2fr 1fr" gap={20}>
        <Stack gap={8}>
          <H3>条件同时成立时，持有有理论依据</H3>
          <Text>
            持有期按五年理解，收益主要来自股息和营运利润增长，估值修复是额外选项。仓位放在能够承受利率、股市和银行信用同时波动的组合里。三季报净利润大起大落时，用营运利润、新业务价值和偿付能力复核，而不是用单季市盈率改判。
          </Text>
          <Text>
            在倍数不扩张的基准情形里，近 5% 的股息加上与过去五年接近的 3%–4% 分红增长，长期年化回报落在高个位数。内含价值倍数若用五年从 0.61 倍回到 0.80 倍，价格部分再贡献约 6 个点的年化，合计才到低两位数。后者需要长端利率和寿险利差的担忧缓解。
          </Text>
        </Stack>
        <Stack gap={8}>
          <H3>这些情况会削弱持有理由</H3>
          <Text>
            资金两年内要用，52 周区间已经是 46.90–74.88 元，价格可以在低估区域停留很久。组合里已经堆了大量银行、保险和长久期利率敞口，再加平安只是加同一类风险。
          </Text>
          <Text>
            若 30 年国债收益率长期停在 2% 附近，而权益收益也接不上，4% 的内含价值假设会被下修，寿险营运 ROE 会继续从 21% 往下走。平安银行核心一级资本只有 9.32%，拨备覆盖率已从 2023 年的 278% 降到 220%，信用周期变坏时集团折价会加深。
          </Text>
        </Stack>
      </Grid>

      <Callout tone="warning" title="低市盈率分位不是安全边际">
        10 月 23 日滚动市盈率约 5.88 倍，同花顺口径处于近十年 0.9% 分位。2026 年上半年净利润增 36%，营运利润只增 8%。用含投资波动的利润做历史分位，会把周期高点当成便宜。营运利润口径的滚动市盈率约 6.8 倍，仍然低于这家公司过去常见的区间，但解释力来自利率和 ROE，不来自分位数本身。
      </Callout>

      <H2>和同业放在一起</H2>
      <Text>
        折价是行业状态。国联民生证券统计，2026 年 8 月 31 日 A 股内含价值倍数为中国人寿 0.71、中国平安 0.64、新华保险 0.60、中国太保 0.46。到 10 月 27 日，平安按 6 月末内含价值计算已到 0.61 倍。H 股 2318 当日收于 48.68 港元，行情页给出的市净率 0.74 倍、滚动市盈率 4.81 倍、股息率 6.46%，同一公司的港股比 A 股更便宜。选平安而不是更低倍数的太保，买的是分红连续性、多渠道新业务和偿付能力，同时必须接受平安银行和医疗养老板块目前贡献有限。
      </Text>

      <Text size="small" tone="tertiary">
        主要来源：中国平安 2026 年中期报告及中期业绩演示（2026-08-20）、2025 年年度报告、财政部国债收益率曲线 2026-10-27、A 股收盘价 2026-10-27。同业倍数引自国联民生证券 2026 年 8 月 31 日截面，未按 10 月 27 日股价重算。新业务价值倍数使用中报敏感性表中的一年新业务价值 394 亿元，等于 2025 全年 369 亿元减去 2025 年上半年 223 亿元再加 2026 年上半年 248 亿元。
      </Text>
    </Stack>
  );
}
