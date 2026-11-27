/* global echarts */

document.documentElement.dataset.atlasOrigin = "bzwh";

const COLORS = {
  ink: "#172033",
  muted: "#667085",
  line: "#D9E0E8",
  grid: "#E9EDF2",
  blue: "#2F6BFF",
  blueSoft: "#AFC6FF",
  orange: "#F06A3C",
  orangeSoft: "#F8C7B5",
  teal: "#159B83",
  tealSoft: "#A6DDD2",
  red: "#D8484C",
  green: "#3A9D68",
  gray: "#B9C2CF",
  grayLight: "#E8EDF3",
  paper: "#FBFCFD",
};

const GROUP_LABELS = {
  basic: "基础比较与趋势",
  stat: "分布、关系与统计",
  business: "业务过程、贡献与时间",
  advanced: "层级、空间、网络与特殊图",
  composite: "组合图",
};

const CARDS = [
  { id: 1, name: "纵向柱状图", group: "basic", focus: "零基线、降序、柱顶数值与唯一重点色" },
  { id: 2, name: "排名横条图", group: "basic", focus: "长名称、Top N 排名与末端直接标值" },
  { id: 3, name: "分组柱状图", group: "basic", focus: "组内对比、统一基线与差值标注" },
  { id: 4, name: "堆叠柱状图", group: "basic", focus: "总量与构成同时可读，标总计不贴满标签" },
  { id: 5, name: "百分比堆叠条形图", group: "basic", focus: "每组总和 100%，显示样本量和关键占比" },
  { id: 6, name: "折线图", group: "basic", focus: "真实时间顺序、终点直标、峰谷和事件" },
  { id: 7, name: "面积图", group: "basic", focus: "强调量级变化，面积不用于不适合相加的系列" },
  { id: 8, name: "饼图", group: "basic", focus: "少量类别、按值排序、克制使用直接标注" },
  { id: 9, name: "环形图", group: "basic", focus: "中心 KPI、构成标签和总量口径" },
  { id: 10, name: "直方图", group: "basic", focus: "连续分箱、均值中位数与长尾解释边界" },
  { id: 11, name: "斜率图", group: "basic", focus: "两期端点直接标注，突出方向和变化量" },
  { id: 12, name: "哑铃图", group: "basic", focus: "同一对象两值、连接线与差值" },
  { id: 13, name: "点图", group: "basic", focus: "轻量精确比较，避免把点画成粗柱" },
  { id: 14, name: "棒棒糖图", group: "basic", focus: "排名结构、细杆弱化、端点数值突出" },
  { id: 15, name: "方格占比图", group: "stat", focus: "100 格=100%，重点占比与剩余量清楚" },
  { id: 16, name: "箱线图", group: "stat", focus: "中位数、四分位、须与统计异常点规则" },
  { id: 17, name: "散点图", group: "stat", focus: "相关关系、趋势线、样本量与非因果边界" },
  { id: 18, name: "气泡图", group: "stat", focus: "三变量编码、面积比例图例与重点对象" },
  { id: 19, name: "热力矩阵图", group: "stat", focus: "统一色阶、单元格数值、缺失不等于零" },
  { id: 20, name: "雷达图", group: "stat", focus: "同量纲标准化、少量维度与有限系列" },
  { id: 21, name: "小提琴图", group: "stat", focus: "密度镜像、样本量、中位数与四分位" },
  { id: 22, name: "山脊图", group: "stat", focus: "同尺度多组分布、错位层叠与峰值" },
  { id: 23, name: "平行坐标图", group: "stat", focus: "统一标准化、维度顺序与重点路径" },
  { id: 24, name: "误差线图", group: "stat", focus: "区间类型一致、端帽、估计值直接标注" },
  { id: 25, name: "森林图", group: "stat", focus: "无效应基线、置信区间与跨线解释" },
  { id: 26, name: "控制图", group: "stat", focus: "UCL/CL/LCL、超限规则与目标线分离" },
  { id: 27, name: "瀑布图", group: "business", focus: "起点、增减贡献、终点和桥接基线" },
  { id: 28, name: "帕累托图", group: "business", focus: "严格降序、累计 100% 与真实集中度" },
  { id: 29, name: "漏斗图", group: "business", focus: "阶段数量留在主体，下降比例统一放在单独一侧" },
  { id: 30, name: "子弹图", group: "business", focus: "绩效图例、实际与目标清楚，压缩无意义留白" },
  { id: 31, name: "仪表盘", group: "business", focus: "单一 KPI、目标刻度与克制的状态色" },
  { id: 32, name: "日历热力图", group: "business", focus: "日期连续性、色阶、峰值与缺失日期" },
  { id: 33, name: "甘特图", group: "business", focus: "任务起止、依赖、进度和今日线" },
  { id: 34, name: "蜡烛图", group: "business", focus: "OHLC 校验、市场颜色习惯与成交量" },
  { id: 35, name: "桑基图", group: "business", focus: "守恒的流量、节点层级和主要路径" },
  { id: 36, name: "主题河流图", group: "business", focus: "同一时间轴、左端主题名与右端最新值标签列" },
  { id: 37, name: "矩形树图", group: "advanced", focus: "面积表示规模，矩形间只保留细而一致的缝隙" },
  { id: 38, name: "旭日图", group: "advanced", focus: "父子层级一致，所有数据标签水平正对用户" },
  { id: 39, name: "区域分级设色地图", group: "advanced", focus: "可靠边界、单色分级、缺失与零值分开" },
  { id: 40, name: "比例符号地图", group: "advanced", focus: "符号面积映射、位置准确与重叠控制" },
  { id: 41, name: "地理流向图", group: "advanced", focus: "起终点、方向、流量与主要通道" },
  { id: 42, name: "关系网络图", group: "advanced", focus: "节点边完整，使用近方形绘图区避免非等比压扁" },
  { id: 43, name: "南丁格尔玫瑰图", group: "advanced", focus: "角度与半径含义、排序和面积感知风险" },
  { id: 44, name: "柱线目标带综合图", group: "composite", focus: "实际、趋势、目标区间和双轴边界" },
  { id: 45, name: "贡献桥接综合图", group: "composite", focus: "总差异、正负贡献与可核对桥接" },
  { id: 46, name: "双轴柱线图", group: "composite", focus: "两种单位、轴色对应与避免虚假相关" },
  { id: 47, name: "KPI—趋势—驱动拆解", group: "composite", focus: "驱动模块位于下半区，主要贡献值清晰对齐" },
  { id: 48, name: "同尺度小多图", group: "composite", focus: "共享尺度、统一标注和重点小图" },
];

function code(id) {
  return `VIZ-${String(id).padStart(2, "0")}`;
}

function title(text, subtext) {
  return {
    text,
    subtext,
    left: 12,
    top: 4,
    itemGap: 4,
    textStyle: { color: COLORS.ink, fontSize: 13, fontWeight: 700 },
    subtextStyle: { color: COLORS.muted, fontSize: 9, lineHeight: 13 },
  };
}

function grid(extra = {}) {
  return { left: 46, right: 22, top: 74, bottom: 38, containLabel: true, ...extra };
}

function categoryAxis(data, extra = {}) {
  return {
    type: "category",
    data,
    axisTick: { show: false },
    axisLine: { lineStyle: { color: COLORS.line } },
    axisLabel: { color: COLORS.muted, fontSize: 9, interval: 0 },
    ...extra,
  };
}

function valueAxis(name = "", extra = {}) {
  return {
    type: "value",
    name,
    nameTextStyle: { color: COLORS.muted, fontSize: 9, padding: [0, 0, 2, 0] },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: COLORS.muted, fontSize: 9 },
    splitLine: { lineStyle: { color: COLORS.grid, type: "dashed" } },
    ...extra,
  };
}

function baseOption(extra = {}) {
  return {
    animation: false,
    color: [COLORS.blue, COLORS.orange, COLORS.teal, COLORS.gray],
    textStyle: { fontFamily: "Microsoft YaHei, PingFang SC, sans-serif" },
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: "rgba(23,32,51,.94)",
      borderWidth: 0,
      textStyle: { color: "#fff", fontSize: 11 },
    },
    ...extra,
  };
}

function itemLabel(color = COLORS.ink) {
  return { show: true, color, fontSize: 9, fontWeight: 600 };
}

function money(v) {
  return `¥${Number(v).toLocaleString("zh-CN")}`;
}

function percent(v) {
  return `${Number(v).toFixed(1)}%`;
}

function option01() {
  const values = [138, 126, 108, 92, 78, 64];
  return baseOption({
    title: title("华东收入领先，较西南高 115%", "2026 Q2｜百万元｜按区域汇总"),
    grid: grid(),
    xAxis: categoryAxis(["华东", "华南", "华北", "华中", "西南", "西北"]),
    yAxis: valueAxis("百万元", { min: 0, max: 160 }),
    series: [{
      type: "bar",
      barWidth: "54%",
      data: values.map((v, i) => ({ value: v, itemStyle: { color: i === 0 ? COLORS.orange : COLORS.blue } })),
      label: { ...itemLabel(), position: "top", formatter: "{c}" },
    }],
  });
}

function option02() {
  const names = ["企业数据服务", "智能营销平台", "供应链解决方案", "客户成功服务", "培训与咨询"];
  const values = [286, 241, 198, 154, 118];
  return baseOption({
    title: title("企业数据服务贡献最高，占前五业务 28.7%", "2026 上半年｜收入：万元｜降序"),
    grid: grid({ left: 104, right: 42 }),
    xAxis: valueAxis("万元", { min: 0, max: 320 }),
    yAxis: categoryAxis(names.slice().reverse(), { inverse: false }),
    series: [{
      type: "bar",
      barWidth: 14,
      data: values.slice().reverse().map((v, i) => ({
        value: v,
        itemStyle: { color: i === values.length - 1 ? COLORS.orange : COLORS.blue },
      })),
      label: { ...itemLabel(), position: "right", formatter: "{c}" },
    }],
  });
}

function option03() {
  return baseOption({
    title: title("新方案在四个区域均提升转化，华南提升最大", "转化率｜百分点差异直接标注"),
    grid: grid(),
    legend: { top: 43, right: 10, itemWidth: 9, itemHeight: 9, textStyle: { fontSize: 9 } },
    xAxis: categoryAxis(["华东", "华南", "华北", "西南"]),
    yAxis: valueAxis("转化率", { min: 0, max: 24, axisLabel: { formatter: "{value}%", fontSize: 9 } }),
    series: [
      { name: "原方案", type: "bar", barWidth: 12, data: [15.2, 13.8, 14.6, 11.9], itemStyle: { color: COLORS.gray } },
      {
        name: "新方案",
        type: "bar",
        barWidth: 12,
        data: [18.4, 19.1, 17.2, 14.8],
        itemStyle: { color: COLORS.blue },
        label: { show: true, position: "top", color: COLORS.ink, fontSize: 8, formatter: (p) => `+${(p.value - [15.2, 13.8, 14.6, 11.9][p.dataIndex]).toFixed(1)}pp` },
      },
    ],
  });
}

function option04() {
  const a = [52, 61, 58, 68];
  const b = [31, 38, 42, 45];
  const c = [18, 20, 24, 27];
  const totals = a.map((v, i) => v + b[i] + c[i]);
  return baseOption({
    title: title("客户总量连续增长，企业客户贡献过半", "客户数：千户｜仅标总量和重点构成"),
    grid: grid(),
    legend: { top: 43, right: 8, itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 9 } },
    xAxis: categoryAxis(["Q1", "Q2", "Q3", "Q4"]),
    yAxis: valueAxis("千户", { min: 0, max: 160 }),
    series: [
      { name: "企业", type: "bar", stack: "total", data: a, itemStyle: { color: COLORS.blue } },
      { name: "中小商户", type: "bar", stack: "total", data: b, itemStyle: { color: COLORS.teal } },
      {
        name: "个人",
        type: "bar",
        stack: "total",
        data: c,
        itemStyle: { color: COLORS.gray },
        label: { show: true, position: "top", color: COLORS.ink, fontSize: 9, fontWeight: 700, formatter: (p) => totals[p.dataIndex] },
      },
    ],
  });
}

function option05() {
  const base = [58, 49, 63, 54];
  const growth = [27, 32, 22, 29];
  const other = base.map((v, i) => 100 - v - growth[i]);
  const n = [1280, 960, 1140, 860];
  return baseOption({
    title: title("华北续费结构最稳，新购占比仅 22.0%", "订单结构｜每组=100%｜括号为样本量"),
    grid: grid({ left: 66, right: 30 }),
    legend: { top: 43, right: 8, itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 9 } },
    xAxis: valueAxis("占比", { min: 0, max: 100, axisLabel: { formatter: "{value}%", fontSize: 9 } }),
    yAxis: categoryAxis(["华东", "华南", "华北", "西南"].map((x, i) => `${x}\nn=${n[i]}`), { axisLabel: { lineHeight: 12, fontSize: 8 } }),
    series: [
      { name: "续费", type: "bar", stack: "share", data: base, label: { show: true, position: "inside", color: "#fff", fontSize: 8, formatter: "{c}%" }, itemStyle: { color: COLORS.blue } },
      { name: "新购", type: "bar", stack: "share", data: growth, label: { show: true, position: "inside", color: "#fff", fontSize: 8, formatter: "{c}%" }, itemStyle: { color: COLORS.orange } },
      { name: "其他", type: "bar", stack: "share", data: other, itemStyle: { color: COLORS.gray } },
    ],
  });
}

function option06() {
  const months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"];
  const values = [82, 86, 91, 88, 96, 104, 101, 113];
  return baseOption({
    title: title("活跃用户总体上升，8 月创阶段新高", "月活跃用户：万人｜4 月活动切换形成短暂回落"),
    grid: grid({ right: 52 }),
    xAxis: categoryAxis(months),
    yAxis: valueAxis("万人", { min: 70, max: 120 }),
    series: [{
      name: "月活跃用户",
      type: "line",
      data: values,
      smooth: false,
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { color: COLORS.blue, width: 2.5 },
      itemStyle: { color: COLORS.blue },
      endLabel: { show: true, formatter: "113 万", color: COLORS.orange, fontSize: 10, fontWeight: 700 },
      labelLayout: { moveOverlap: "shiftY" },
      markPoint: {
        symbolSize: 38,
        data: [
          { coord: ["4月", 88], value: "活动\n切换", itemStyle: { color: COLORS.orange } },
          { type: "max", name: "峰值", label: { formatter: "峰值\n{c}" }, itemStyle: { color: COLORS.orange } },
        ],
        label: { color: "#fff", fontSize: 8 },
      },
    }],
  });
}

function option07() {
  const values = [42, 48, 55, 58, 72, 79, 91, 96];
  return baseOption({
    title: title("累计服务量在 5 月后明显加速", "月服务量：万次｜面积仅表示单一可加总指标"),
    grid: grid(),
    xAxis: categoryAxis(["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]),
    yAxis: valueAxis("万次", { min: 0, max: 110 }),
    series: [{
      type: "line",
      smooth: 0.25,
      data: values,
      symbol: "none",
      lineStyle: { color: COLORS.teal, width: 2.5 },
      areaStyle: { color: "rgba(21,155,131,.22)" },
      endLabel: { show: true, formatter: "96 万次", color: COLORS.teal, fontWeight: 700, fontSize: 9 },
      markLine: { symbol: ["none", "none"], data: [{ xAxis: "5月", label: { formatter: "增长加速", fontSize: 8 } }], lineStyle: { color: COLORS.orange, type: "dashed" } },
    }],
  });
}

function option08() {
  return baseOption({
    title: title("企业客户贡献近半收入", "2026 H1｜收入结构｜总计 ¥4,820 万"),
    legend: { show: false },
    series: [{
      type: "pie",
      radius: ["0%", "62%"],
      center: ["50%", "57%"],
      startAngle: 100,
      avoidLabelOverlap: true,
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      label: { color: COLORS.ink, fontSize: 9, formatter: "{b}\n{d}%" },
      labelLine: { length: 8, length2: 5 },
      data: [
        { value: 46, name: "企业客户", itemStyle: { color: COLORS.orange } },
        { value: 28, name: "中小商户", itemStyle: { color: COLORS.blue } },
        { value: 17, name: "个人客户", itemStyle: { color: COLORS.teal } },
        { value: 9, name: "其他", itemStyle: { color: COLORS.gray } },
      ],
    }],
  });
}

function option09() {
  return baseOption({
    title: title("续费收入占 62.0%，仍是收入基本盘", "2026 H1｜收入结构｜总计 ¥4,820 万"),
    graphic: [
      { type: "text", left: "center", top: "47%", style: { text: "¥4,820万", fill: COLORS.ink, font: "700 18px Microsoft YaHei", textAlign: "center" } },
      { type: "text", left: "center", top: "56%", style: { text: "总收入", fill: COLORS.muted, font: "10px Microsoft YaHei", textAlign: "center" } },
    ],
    series: [{
      type: "pie",
      radius: ["46%", "68%"],
      center: ["50%", "57%"],
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      label: { color: COLORS.ink, fontSize: 9, formatter: "{b} {d}%" },
      data: [
        { value: 62, name: "续费", itemStyle: { color: COLORS.blue } },
        { value: 24, name: "新购", itemStyle: { color: COLORS.orange } },
        { value: 14, name: "增购", itemStyle: { color: COLORS.teal } },
      ],
    }],
  });
}

function option10() {
  const bins = ["0–10", "10–20", "20–30", "30–40", "40–50", "50–60", "60–70", "70–80"];
  const counts = [4, 12, 29, 48, 55, 31, 14, 7];
  return baseOption({
    title: title("处理时长集中在 30–50 分钟，右侧存在长尾", "n=200｜箱宽 10 分钟｜均值 41.8 / 中位数 39.6"),
    grid: grid({ right: 28 }),
    xAxis: categoryAxis(bins, { name: "处理时长（分钟）", nameLocation: "middle", nameGap: 26, nameTextStyle: { fontSize: 9, color: COLORS.muted } }),
    yAxis: valueAxis("频数", { min: 0, max: 65 }),
    series: [{
      type: "bar",
      barCategoryGap: "0%",
      data: counts.map((v, i) => ({ value: v, itemStyle: { color: i >= 6 ? COLORS.orange : COLORS.blue, borderColor: "#fff", borderWidth: 0.5 } })),
      markLine: {
        symbol: ["none", "none"],
        label: { fontSize: 8 },
        data: [
          { xAxis: 3.96, name: "中位数", label: { formatter: "中位数 39.6" }, lineStyle: { color: COLORS.teal, type: "dashed" } },
          { xAxis: 4.18, name: "均值", label: { formatter: "均值 41.8" }, lineStyle: { color: COLORS.orange } },
        ],
      },
    }],
  });
}

function option11() {
  const names = ["企业", "中小商户", "个人", "其他"];
  const before = [64, 52, 38, 26];
  const after = [76, 61, 35, 21];
  return baseOption({
    title: title("企业与中小商户增长，个人和其他渠道回落", "2025 → 2026｜收入指数｜端点直接标注"),
    grid: grid({ left: 82, right: 78 }),
    xAxis: categoryAxis(["2025", "2026"], { boundaryGap: false }),
    yAxis: valueAxis("指数", { min: 15, max: 82 }),
    series: names.map((name, i) => ({
      name,
      type: "line",
      data: [
        {
          value: before[i],
          label: {
            show: true,
            position: "left",
            distance: 7,
            align: "right",
            color: COLORS.ink,
            fontSize: 8,
            formatter: `${name} ${before[i]}`,
          },
        },
        {
          value: after[i],
          label: {
            show: true,
            position: "right",
            distance: 7,
            align: "left",
            color: COLORS.ink,
            fontSize: 8,
            lineHeight: 11,
            formatter: `${after[i]}\n${after[i] - before[i] >= 0 ? "+" : ""}${after[i] - before[i]}`,
          },
        },
      ],
      symbolSize: 6,
      lineStyle: { width: i === 0 ? 3 : 1.5, color: i === 0 ? COLORS.orange : [COLORS.blue, COLORS.teal, COLORS.gray][i - 1] },
      itemStyle: { color: i === 0 ? COLORS.orange : [COLORS.blue, COLORS.teal, COLORS.gray][i - 1] },
      labelLayout: { moveOverlap: "shiftY" },
    })),
  });
}

function option12() {
  const cats = ["华东", "华南", "华北", "西南", "西北"];
  const rows = [[0, 68, 81], [1, 62, 76], [2, 71, 79], [3, 57, 69], [4, 54, 60]];
  return baseOption({
    title: title("新方案全面提升满意度，华南增幅最大", "满意度指数｜灰=原方案，蓝=新方案"),
    grid: grid({ left: 52, right: 54 }),
    xAxis: valueAxis("满意度", { min: 45, max: 90 }),
    yAxis: categoryAxis(cats, { inverse: true }),
    series: [{
      type: "custom",
      data: rows,
      renderItem(params, api) {
        const y = api.coord([api.value(1), api.value(0)])[1];
        const x1 = api.coord([api.value(1), api.value(0)])[0];
        const x2 = api.coord([api.value(2), api.value(0)])[0];
        return {
          type: "group",
          children: [
            { type: "line", shape: { x1, y1: y, x2, y2: y }, style: { stroke: COLORS.gray, lineWidth: 3 } },
            { type: "circle", shape: { cx: x1, cy: y, r: 5 }, style: { fill: COLORS.gray } },
            { type: "circle", shape: { cx: x2, cy: y, r: 6 }, style: { fill: params.dataIndex === 1 ? COLORS.orange : COLORS.blue } },
            { type: "text", style: { x: x2 + 8, y, text: `+${api.value(2) - api.value(1)}`, fill: params.dataIndex === 1 ? COLORS.orange : COLORS.ink, font: "700 9px Microsoft YaHei", verticalAlign: "middle" } },
          ],
        };
      },
    }],
  });
}

function option13() {
  const names = ["产品 A", "产品 B", "产品 C", "产品 D", "产品 E", "产品 F"];
  const vals = [92, 86, 84, 78, 73, 68];
  return baseOption({
    title: title("产品 A 满意度最高，前三名差距较小", "满意度指数｜点位比柱形更轻量"),
    grid: grid({ left: 62, right: 48 }),
    xAxis: valueAxis("指数", { min: 60, max: 100 }),
    yAxis: categoryAxis(names.slice().reverse()),
    series: [{
      type: "scatter",
      symbolSize: 11,
      data: vals.slice().reverse().map((v, i) => ({ value: v, itemStyle: { color: i === vals.length - 1 ? COLORS.orange : COLORS.blue } })),
      label: { ...itemLabel(), show: true, position: "right", formatter: "{c}" },
    }],
  });
}

function option14() {
  const names = ["企业数据", "智能营销", "供应链", "客户成功", "培训咨询", "其他"];
  const vals = [286, 241, 198, 154, 118, 72];
  return baseOption({
    title: title("企业数据业务领先，长尾业务不足头部三成", "收入：万元｜按值降序"),
    grid: grid({ left: 84, right: 44 }),
    xAxis: valueAxis("万元", { min: 0, max: 320 }),
    yAxis: categoryAxis(names.slice().reverse()),
    series: [
      {
        type: "bar",
        barWidth: 2,
        data: vals.slice().reverse(),
        itemStyle: { color: COLORS.gray },
        silent: true,
      },
      {
        type: "scatter",
        symbolSize: 10,
        data: vals.slice().reverse().map((v, i) => ({ value: v, itemStyle: { color: i === vals.length - 1 ? COLORS.orange : COLORS.blue } })),
        label: { show: true, position: "right", color: COLORS.ink, fontSize: 9, formatter: "{c}" },
      },
    ],
  });
}

function option15() {
  const filled = 63;
  const data = Array.from({ length: 100 }, (_, i) => [i % 10, 9 - Math.floor(i / 10), i < filled ? 1 : 0]);
  return baseOption({
    title: title("63.0% 用户在 7 日内完成首次关键行为", "100 格=100%｜橙色=已完成"),
    grid: grid({ left: 44, right: 44, top: 66, bottom: 28 }),
    xAxis: { type: "value", min: -0.7, max: 9.7, show: false },
    yAxis: { type: "value", min: -0.7, max: 9.7, show: false },
    graphic: [
      { type: "text", right: 16, top: 45, style: { text: "63.0%", fill: COLORS.orange, font: "700 18px Microsoft YaHei" } },
      { type: "text", right: 16, top: 67, style: { text: "n=1,240", fill: COLORS.muted, font: "9px Microsoft YaHei" } },
    ],
    series: [{
      type: "scatter",
      symbol: "roundRect",
      symbolSize: 14,
      data: data.map((d) => ({ value: d, itemStyle: { color: d[2] ? COLORS.orange : COLORS.grayLight } })),
    }],
  });
}

function option16() {
  return baseOption({
    title: title("华南客单价中位数最高，华北离散程度更大", "元｜箱体=P25–P75｜须=1.5×IQR｜圆点=统计异常"),
    grid: grid({ left: 44, right: 20 }),
    xAxis: categoryAxis(["华东\nn=120", "华南\nn=98", "华北\nn=112", "西南\nn=86"], { axisLabel: { fontSize: 8, lineHeight: 11 } }),
    yAxis: valueAxis("元", { min: 100, max: 520 }),
    series: [
      {
        name: "分布",
        type: "boxplot",
        data: [
          [180, 230, 282, 335, 410],
          { value: [205, 255, 315, 372, 458], itemStyle: { borderColor: COLORS.orange, color: COLORS.orangeSoft } },
          [145, 210, 270, 350, 480],
          [160, 205, 250, 305, 390],
        ],
        itemStyle: { color: COLORS.blueSoft, borderColor: COLORS.blue, borderWidth: 1.5 },
        tooltip: { formatter: (p) => `${p.name}<br/>下须 ${p.data[1]}<br/>P25 ${p.data[2]}<br/>中位数 ${p.data[3]}<br/>P75 ${p.data[4]}<br/>上须 ${p.data[5]}` },
      },
      {
        name: "统计异常",
        type: "scatter",
        symbolSize: 6,
        data: [[0, 468], [2, 505], [3, 435]],
        itemStyle: { color: COLORS.red },
      },
    ],
  });
}

function option17() {
  const points = [[2, 42], [3, 45], [4, 51], [5, 55], [6, 57], [7, 64], [8, 67], [9, 73], [10, 76], [11, 82], [12, 79], [13, 88]];
  return baseOption({
    title: title("使用频次与续费意愿呈中等正相关", "n=120｜虚线=线性趋势｜相关不代表因果"),
    grid: grid(),
    xAxis: valueAxis("月使用次数", { min: 0, max: 15 }),
    yAxis: valueAxis("续费意愿", { min: 35, max: 95 }),
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: 8,
        itemStyle: { color: COLORS.blue, opacity: 0.72 },
        markPoint: { symbolSize: 32, data: [{ coord: [12, 79], name: "高频未转化", value: "重点" }], label: { fontSize: 8 }, itemStyle: { color: COLORS.orange } },
      },
      {
        type: "line",
        data: [[2, 40], [13, 87]],
        showSymbol: false,
        silent: true,
        lineStyle: { color: COLORS.orange, type: "dashed", width: 1.5 },
      },
    ],
  });
}

function option18() {
  const data = [
    [76, 82, 680, "企业 A"], [62, 71, 430, "企业 B"], [84, 64, 520, "企业 C"],
    [55, 58, 280, "企业 D"], [69, 88, 760, "企业 E"], [47, 74, 210, "企业 F"],
  ];
  return baseOption({
    title: title("企业 E 兼具高增长与高利润，是优先投入对象", "横轴=增长率｜纵轴=利润率｜气泡面积=收入"),
    grid: grid({ right: 26 }),
    xAxis: valueAxis("增长指数", { min: 40, max: 90 }),
    yAxis: valueAxis("利润指数", { min: 50, max: 95 }),
    series: [{
      type: "scatter",
      data: data.map((d) => ({
        value: d,
        itemStyle: { color: d[3] === "企业 E" ? COLORS.orange : COLORS.blue, opacity: 0.72 },
      })),
      symbolSize: (d) => Math.sqrt(d[2]) * 1.25,
      label: { show: true, formatter: (p) => p.value[3], color: COLORS.ink, fontSize: 8, position: "top" },
    }],
  });
}

function option19() {
  const xs = ["周一", "周二", "周三", "周四", "周五"];
  const ys = ["上午", "中午", "下午", "晚间"];
  const vals = [
    [0, 0, 42], [1, 0, 51], [2, 0, 58], [3, 0, 62], [4, 0, 70],
    [0, 1, 55], [1, 1, 63], [2, 1, 69], [3, 1, 72], [4, 1, 78],
    [0, 2, 68], [1, 2, 74], [2, 2, 81], [3, 2, 86], [4, 2, 92],
    [0, 3, 49], [1, 3, 57], [2, 3, 66], [3, 3, 74], [4, 3, "-"],
  ];
  return baseOption({
    title: title("周五下午需求最高，周五晚间数据缺失", "工单量｜单色阶梯｜灰色=缺失，不等于 0"),
    grid: grid({ left: 52, right: 42, bottom: 52 }),
    xAxis: categoryAxis(xs),
    yAxis: categoryAxis(ys),
    visualMap: { min: 40, max: 95, calculable: false, orient: "horizontal", left: "center", bottom: 3, itemWidth: 8, itemHeight: 110, textStyle: { fontSize: 8 }, inRange: { color: ["#EDF3FF", "#2F6BFF"] } },
    series: [{
      type: "heatmap",
      data: vals.map((d) => d[2] === "-" ? { value: [d[0], d[1], 0], itemStyle: { color: COLORS.grayLight }, label: { formatter: "缺失" } } : d),
      label: { show: true, color: COLORS.ink, fontSize: 8, formatter: (p) => p.data.label ? "缺失" : p.value[2] },
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
    }],
  });
}

function option20() {
  return baseOption({
    title: title("方案 A 强在增长，方案 B 强在稳定与效率", "0–100 标准化分｜仅比较 2 个方案"),
    legend: { bottom: 4, textStyle: { fontSize: 9 }, itemWidth: 10, itemHeight: 8 },
    radar: {
      center: ["50%", "56%"],
      radius: "55%",
      splitNumber: 4,
      indicator: [
        { name: "增长", max: 100 }, { name: "利润", max: 100 }, { name: "效率", max: 100 },
        { name: "稳定", max: 100 }, { name: "体验", max: 100 },
      ],
      axisName: { color: COLORS.muted, fontSize: 9 },
      splitLine: { lineStyle: { color: COLORS.grid } },
      splitArea: { areaStyle: { color: ["#fff", COLORS.paper] } },
      axisLine: { lineStyle: { color: COLORS.line } },
    },
    series: [{
      type: "radar",
      data: [
        { value: [88, 74, 67, 62, 81], name: "方案 A", lineStyle: { color: COLORS.orange }, itemStyle: { color: COLORS.orange }, areaStyle: { color: "rgba(240,106,60,.13)" } },
        { value: [72, 78, 86, 89, 76], name: "方案 B", lineStyle: { color: COLORS.blue }, itemStyle: { color: COLORS.blue }, areaStyle: { color: "rgba(47,107,255,.10)" } },
      ],
    }],
  });
}

function option21() {
  const groups = [
    { name: "基础版", q1: 42, median: 51, q3: 61, vals: [30, 36, 42, 48, 54, 60, 66, 72], den: [0.08, 0.22, 0.56, 0.86, 0.72, 0.42, 0.18, 0.05], n: 120 },
    { name: "专业版", q1: 51, median: 63, q3: 72, vals: [35, 42, 49, 56, 63, 70, 77, 84], den: [0.04, 0.16, 0.42, 0.70, 0.92, 0.66, 0.27, 0.06], n: 96 },
    { name: "企业版", q1: 58, median: 69, q3: 79, vals: [41, 48, 55, 62, 69, 76, 83, 90], den: [0.05, 0.13, 0.30, 0.58, 0.88, 0.76, 0.34, 0.08], n: 84 },
  ];
  return baseOption({
    title: title("企业版使用深度整体更高，三组分布仍有重叠", "宽度=核密度，不代表样本量｜线=中位数 / P25–P75"),
    grid: grid({ left: 44, right: 20 }),
    xAxis: categoryAxis(groups.map((g) => `${g.name}\nn=${g.n}`), { axisLabel: { lineHeight: 11, fontSize: 8 } }),
    yAxis: valueAxis("使用深度", { min: 25, max: 95 }),
    series: [{
      type: "custom",
      data: groups.map((_, i) => [i]),
      renderItem(params, api) {
        const g = groups[params.dataIndex];
        const centerX = api.coord([params.dataIndex, g.median])[0];
        const band = api.size([1, 0])[0] * 0.34;
        const left = g.vals.map((v, i) => [centerX - g.den[i] * band, api.coord([params.dataIndex, v])[1]]);
        const right = g.vals.slice().reverse().map((v, ri) => {
          const i = g.vals.length - 1 - ri;
          return [centerX + g.den[i] * band, api.coord([params.dataIndex, v])[1]];
        });
        const q1y = api.coord([params.dataIndex, g.q1])[1];
        const q3y = api.coord([params.dataIndex, g.q3])[1];
        const medy = api.coord([params.dataIndex, g.median])[1];
        const color = params.dataIndex === 2 ? COLORS.orange : COLORS.blue;
        return {
          type: "group",
          children: [
            { type: "polygon", shape: { points: [...left, ...right] }, style: { fill: params.dataIndex === 2 ? "rgba(240,106,60,.28)" : "rgba(47,107,255,.22)", stroke: color, lineWidth: 1.2 } },
            { type: "line", shape: { x1: centerX, y1: q1y, x2: centerX, y2: q3y }, style: { stroke: COLORS.ink, lineWidth: 3 } },
            { type: "line", shape: { x1: centerX - 8, y1: medy, x2: centerX + 8, y2: medy }, style: { stroke: COLORS.ink, lineWidth: 2 } },
            { type: "text", style: { x: centerX + 10, y: medy, text: String(g.median), fill: COLORS.ink, font: "700 8px Microsoft YaHei", verticalAlign: "middle" } },
          ],
        };
      },
    }],
  });
}

function option22() {
  const groups = [
    { name: "一线", base: 3, vals: [0, 10, 20, 30, 40, 50, 60, 70, 80], den: [0, .08, .22, .58, .95, .70, .34, .10, 0] },
    { name: "新一线", base: 2, vals: [0, 10, 20, 30, 40, 50, 60, 70, 80], den: [0, .12, .38, .86, .78, .42, .18, .05, 0] },
    { name: "二线", base: 1, vals: [0, 10, 20, 30, 40, 50, 60, 70, 80], den: [0, .25, .70, .92, .52, .22, .07, .02, 0] },
    { name: "三线", base: 0, vals: [0, 10, 20, 30, 40, 50, 60, 70, 80], den: [0, .52, .96, .61, .24, .08, .02, 0, 0] },
  ];
  return baseOption({
    title: title("城市层级越高，薪资分布整体越向右移动", "月薪：千元｜同一带宽与横轴尺度"),
    graphic: [
      { type: "text", left: 13, top: 91, style: { text: "一线", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "text", left: 13, top: 140, style: { text: "新一线", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "text", left: 13, top: 190, style: { text: "二线", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "text", left: 13, top: 239, style: { text: "三线", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
    ],
    grid: grid({ left: 48, right: 20, bottom: 32 }),
    xAxis: valueAxis("月薪（千元）", { min: 0, max: 80 }),
    yAxis: valueAxis("", { min: -0.2, max: 3.8, interval: 1, axisLabel: { color: COLORS.muted, fontSize: 8, formatter: (v) => ({ 0: "三线", 1: "二线", 2: "新一线", 3: "一线" }[v] || "") }, splitLine: { show: false } }),
    series: [{
      type: "custom",
      data: groups.map((g) => [g.base]),
      renderItem(params, api) {
        const g = groups[params.dataIndex];
        const baseY = api.coord([0, g.base])[1];
        const pts = g.vals.map((v, i) => [api.coord([v, g.base])[0], baseY - g.den[i] * 34]);
        const poly = [[api.coord([0, g.base])[0], baseY], ...pts, [api.coord([80, g.base])[0], baseY]];
        return {
          type: "group",
          children: [
            { type: "polygon", shape: { points: poly }, style: { fill: params.dataIndex === 0 ? "rgba(240,106,60,.26)" : "rgba(47,107,255,.18)", stroke: params.dataIndex === 0 ? COLORS.orange : COLORS.blue, lineWidth: 1.1 } },
            { type: "line", shape: { x1: poly[0][0], y1: baseY, x2: poly[poly.length - 1][0], y2: baseY }, style: { stroke: COLORS.line } },
          ],
        };
      },
    }],
  });
}

function option23() {
  const data = [
    { value: [82, 74, 67, 91], name: "企业 A", lineStyle: { color: COLORS.orange, width: 3, opacity: 1 } },
    { value: [62, 81, 72, 68], name: "企业 B" },
    { value: [71, 58, 86, 73], name: "企业 C" },
    { value: [55, 69, 61, 79], name: "企业 D" },
    { value: [77, 63, 74, 66], name: "企业 E" },
  ];
  return baseOption({
    title: title("企业 A 增长和体验领先，但效率仍有提升空间", "各指标已标准化为 0–100 分｜橙色=重点企业"),
    parallel: { left: 42, right: 24, top: 70, bottom: 30, parallelAxisDefault: { type: "value", min: 40, max: 100, axisLabel: { fontSize: 8 }, nameTextStyle: { fontSize: 9, color: COLORS.ink }, splitLine: { lineStyle: { color: COLORS.grid } } } },
    parallelAxis: [
      { dim: 0, name: "增长" }, { dim: 1, name: "利润" }, { dim: 2, name: "效率" }, { dim: 3, name: "体验" },
    ],
    series: [{
      type: "parallel",
      lineStyle: { width: 1.2, opacity: 0.28, color: COLORS.blue },
      data,
    }],
  });
}

function option24() {
  const rows = [[0, 52, 47, 57], [1, 61, 55, 67], [2, 58, 50, 66], [3, 69, 64, 74]];
  return baseOption({
    title: title("方案 D 均值最高，四组 95% CI 仍有部分重叠", "点=均值｜线=95% 置信区间｜各组口径一致"),
    grid: grid({ left: 44, right: 24 }),
    xAxis: categoryAxis(["A\nn=80", "B\nn=76", "C\nn=68", "D\nn=84"], { axisLabel: { lineHeight: 11, fontSize: 8 } }),
    yAxis: valueAxis("指标均值", { min: 40, max: 80 }),
    series: [{
      type: "custom",
      data: rows,
      renderItem(params, api) {
        const x = api.coord([api.value(0), api.value(1)])[0];
        const y = api.coord([api.value(0), api.value(1)])[1];
        const low = api.coord([api.value(0), api.value(2)])[1];
        const high = api.coord([api.value(0), api.value(3)])[1];
        const color = params.dataIndex === 3 ? COLORS.orange : COLORS.blue;
        return {
          type: "group",
          children: [
            { type: "line", shape: { x1: x, y1: low, x2: x, y2: high }, style: { stroke: color, lineWidth: 1.5 } },
            { type: "line", shape: { x1: x - 6, y1: low, x2: x + 6, y2: low }, style: { stroke: color, lineWidth: 1.5 } },
            { type: "line", shape: { x1: x - 6, y1: high, x2: x + 6, y2: high }, style: { stroke: color, lineWidth: 1.5 } },
            { type: "circle", shape: { cx: x, cy: y, r: 5 }, style: { fill: color } },
            { type: "text", style: { x: x + 8, y, text: String(api.value(1)), fill: COLORS.ink, font: "700 8px Microsoft YaHei", verticalAlign: "middle" } },
          ],
        };
      },
    }],
  });
}

function option25() {
  const names = ["新客", "老客", "高频", "低频", "整体"];
  const rows = [[0, .18, .03, .33], [1, .12, -.02, .26], [2, .31, .12, .50], [3, .05, -.14, .24], [4, .16, .07, .25]];
  return baseOption({
    title: title("高频用户提升最明确；老客与低频区间跨越基线", "效应量｜95% CI｜无效应基线=0"),
    grid: grid({ left: 50, right: 88 }),
    xAxis: valueAxis("效应量", { min: -0.2, max: 0.6, axisLabel: { fontSize: 8, formatter: (v) => v.toFixed(1) } }),
    yAxis: categoryAxis(names, { inverse: true }),
    series: [
      {
        type: "custom",
        data: rows,
        renderItem(params, api) {
          const y = api.coord([api.value(1), api.value(0)])[1];
          const x = api.coord([api.value(1), api.value(0)])[0];
          const lo = api.coord([api.value(2), api.value(0)])[0];
          const hi = api.coord([api.value(3), api.value(0)])[0];
          const right = api.coord([0.59, api.value(0)])[0];
          const color = params.dataIndex === 2 ? COLORS.orange : COLORS.blue;
          return {
            type: "group",
            children: [
              { type: "line", shape: { x1: lo, y1: y, x2: hi, y2: y }, style: { stroke: color, lineWidth: 1.5 } },
              { type: "line", shape: { x1: lo, y1: y - 4, x2: lo, y2: y + 4 }, style: { stroke: color } },
              { type: "line", shape: { x1: hi, y1: y - 4, x2: hi, y2: y + 4 }, style: { stroke: color } },
              { type: "circle", shape: { cx: x, cy: y, r: 5 }, style: { fill: color } },
              { type: "text", style: { x: right + 6, y, text: `${api.value(1).toFixed(2)} [${api.value(2).toFixed(2)}, ${api.value(3).toFixed(2)}]`, fill: COLORS.ink, font: "8px Microsoft YaHei", verticalAlign: "middle" } },
            ],
          };
        },
      },
      {
        type: "scatter",
        data: [],
        markLine: { symbol: ["none", "none"], data: [{ xAxis: 0, label: { formatter: "无效应", fontSize: 8 } }], lineStyle: { color: COLORS.red, type: "dashed" } },
      },
    ],
  });
}

function option26() {
  const months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];
  const vals = [98, 101, 103, 99, 114, 104, 102, 97, 95, 87, 100, 102];
  return baseOption({
    title: title("过程总体稳定，但 5 月与 10 月出现统计超限", "单值控制图｜CL=100，UCL=110，LCL=90"),
    grid: grid({ right: 54 }),
    xAxis: categoryAxis(months, { axisLabel: { fontSize: 8 } }),
    yAxis: valueAxis("过程指标", { min: 82, max: 118 }),
    series: [
      {
        type: "line",
        data: vals,
        symbolSize: 5,
        lineStyle: { color: COLORS.blue, width: 2 },
        itemStyle: { color: COLORS.blue },
        markLine: {
          symbol: ["none", "none"],
          label: { position: "end", fontSize: 8 },
          data: [
            { yAxis: 110, name: "UCL", label: { formatter: "UCL 110" }, lineStyle: { color: COLORS.red, type: "dashed" } },
            { yAxis: 100, name: "CL", label: { formatter: "CL 100" }, lineStyle: { color: COLORS.teal } },
            { yAxis: 90, name: "LCL", label: { formatter: "LCL 90" }, lineStyle: { color: COLORS.red, type: "dashed" } },
          ],
        },
      },
      {
        type: "scatter",
        symbolSize: 10,
        data: [["5月", 114, "高于 UCL"], ["10月", 87, "低于 LCL"]],
        itemStyle: { color: COLORS.orange },
        label: { show: true, position: "top", color: COLORS.red, fontSize: 8, formatter: (p) => `${p.value[0]} ${p.value[1]}\n${p.value[2]}` },
      },
    ],
  });
}

function option27() {
  const cats = ["期初", "新客", "提价", "客户流失", "服务成本", "期末"];
  const base = [0, 100, 124, 120, 112, 0];
  const bars = [100, 24, 12, 16, 8, 112];
  const labels = ["100", "+24", "+12", "−16", "−8", "112"];
  return baseOption({
    title: title("新客和提价抵消流失与成本，利润净增 12 百万", "利润桥接｜百万元｜期初 100 → 期末 112"),
    grid: grid({ left: 40, right: 18 }),
    xAxis: categoryAxis(cats, { axisLabel: { fontSize: 8 } }),
    yAxis: valueAxis("百万元", { min: 0, max: 150 }),
    series: [
      { type: "bar", stack: "waterfall", silent: true, data: base, itemStyle: { color: "transparent" } },
      {
        type: "bar",
        stack: "waterfall",
        barWidth: 22,
        data: bars.map((v, i) => ({
          value: v,
          itemStyle: { color: i === 0 || i === 5 ? COLORS.blue : i < 3 ? COLORS.teal : COLORS.orange },
          label: { show: true, position: i === 3 || i === 4 ? "bottom" : "top", color: COLORS.ink, fontSize: 8, formatter: labels[i] },
        })),
      },
    ],
  });
}

function option28() {
  const names = ["响应慢", "权限问题", "数据错误", "页面卡顿", "功能缺失", "其他"];
  const values = [86, 54, 31, 18, 12, 9];
  const total = values.reduce((a, b) => a + b, 0);
  let running = 0;
  const cum = values.map((v) => {
    running += v;
    return +(running / total * 100).toFixed(1);
  });
  return baseOption({
    title: title("前三类问题贡献 81.4%，应优先治理响应与权限", "问题数｜累计阈值 80%｜真实集中度：3/6 类"),
    grid: grid({ right: 48 }),
    xAxis: categoryAxis(names, { axisLabel: { fontSize: 8, rotate: 24 } }),
    yAxis: [
      valueAxis("问题数", { min: 0, max: 100 }),
      valueAxis("累计占比", { min: 0, max: 100, position: "right", axisLabel: { formatter: "{value}%", fontSize: 8 }, splitLine: { show: false } }),
    ],
    series: [
      {
        type: "bar",
        barWidth: 18,
        data: values.map((v, i) => ({ value: v, itemStyle: { color: i < 3 ? COLORS.orange : COLORS.gray } })),
        label: { show: true, position: "top", color: COLORS.ink, fontSize: 8 },
      },
      {
        type: "line",
        yAxisIndex: 1,
        data: cum,
        symbolSize: 5,
        lineStyle: { color: COLORS.blue, width: 2 },
        itemStyle: { color: COLORS.blue },
        label: { show: true, formatter: (p) => p.dataIndex === 2 ? "81.4%\n3 项" : p.dataIndex === 5 ? "100%" : "", color: COLORS.ink, fontSize: 8 },
        markLine: { symbol: ["none", "none"], data: [{ yAxis: 80, label: { formatter: "80% 阈值", fontSize: 8 } }], lineStyle: { color: COLORS.red, type: "dashed" } },
      },
    ],
  });
}

function option29() {
  return baseOption({
    title: title("加入购物车前流失最大，较上一步减少 43.5%", "同一访客队列｜阶段数量在漏斗内，下降率统一放右侧"),
    graphic: [
      { type: "text", right: 10, top: 99, style: { text: "↓ 38.0%\n流失 3,800", fill: COLORS.muted, font: "8px Microsoft YaHei", lineHeight: 11 } },
      { type: "text", right: 10, top: 141, style: { text: "↓ 43.5%\n流失 2,700", fill: COLORS.orange, font: "700 8px Microsoft YaHei", lineHeight: 11 } },
      { type: "text", right: 10, top: 183, style: { text: "↓ 34.3%\n流失 1,200", fill: COLORS.muted, font: "8px Microsoft YaHei", lineHeight: 11 } },
      { type: "text", right: 10, top: 225, style: { text: "↓ 17.4%\n流失 400", fill: COLORS.muted, font: "8px Microsoft YaHei", lineHeight: 11 } },
    ],
    series: [{
      type: "funnel",
      left: "6%",
      top: 66,
      bottom: 18,
      width: "65%",
      minSize: "22%",
      maxSize: "100%",
      sort: "descending",
      gap: 3,
      label: { show: true, position: "inside", color: "#fff", fontSize: 9, formatter: (p) => `${p.name}\n${p.value.toLocaleString()}` },
      itemStyle: { borderColor: "#fff", borderWidth: 1 },
      data: [
        { value: 10000, name: "访问", itemStyle: { color: COLORS.blue } },
        { value: 6200, name: "查看详情", itemStyle: { color: "#5C84F5" } },
        { value: 3500, name: "加入购物车", itemStyle: { color: "#7F9FF2" } },
        { value: 2300, name: "发起支付", itemStyle: { color: COLORS.orange } },
        { value: 1900, name: "支付成功", itemStyle: { color: COLORS.teal } },
      ],
    }],
  });
}

function option30() {
  return baseOption({
    title: title("交付及时率达到 76%，仍低于 85% 目标", "差 <60｜中 60–80｜好 >80｜目标=85%"),
    graphic: [
      { type: "text", left: 20, top: 69, style: { text: "交付及时率", fill: COLORS.ink, font: "700 9px Microsoft YaHei" } },
      { type: "rect", left: 20, top: 88, shape: { width: 10, height: 8, r: 1 }, style: { fill: "#C2D0E8" } },
      { type: "text", left: 34, top: 86, style: { text: "差", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "rect", left: 58, top: 88, shape: { width: 10, height: 8, r: 1 }, style: { fill: "#D6DEE9" } },
      { type: "text", left: 72, top: 86, style: { text: "中", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "rect", left: 96, top: 88, shape: { width: 10, height: 8, r: 1 }, style: { fill: "#E6E9EE" } },
      { type: "text", left: 110, top: 86, style: { text: "好", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "rect", left: 141, top: 88, shape: { width: 14, height: 5, r: 1 }, style: { fill: COLORS.blue } },
      { type: "text", left: 160, top: 86, style: { text: "实际", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
      { type: "line", left: 205, top: 86, shape: { x1: 0, y1: 0, x2: 0, y2: 12 }, style: { stroke: COLORS.orange, lineWidth: 2, lineDash: [3, 2] } },
      { type: "text", left: 213, top: 86, style: { text: "目标", fill: COLORS.muted, font: "8px Microsoft YaHei" } },
    ],
    grid: grid({ left: 20, right: 20, top: 122, bottom: 58 }),
    xAxis: valueAxis("", { min: 0, max: 100, axisLabel: { formatter: "{value}%", fontSize: 8 } }),
    yAxis: categoryAxis([""], { axisLabel: { show: false } }),
    series: [
      { type: "bar", data: [100], barWidth: 36, itemStyle: { color: "#E6E9EE" }, silent: true },
      { type: "bar", data: [80], barWidth: 36, barGap: "-100%", itemStyle: { color: "#D6DEE9" }, silent: true },
      { type: "bar", data: [60], barWidth: 36, barGap: "-100%", itemStyle: { color: "#C2D0E8" }, silent: true },
      {
        type: "bar",
        data: [76],
        barWidth: 11,
        barGap: "-100%",
        itemStyle: { color: COLORS.blue },
        label: { show: true, position: "right", color: COLORS.ink, fontSize: 10, fontWeight: 700, formatter: "76%" },
        markLine: { symbol: ["none", "none"], data: [{ xAxis: 85, label: { formatter: "目标 85%", fontSize: 8 } }], lineStyle: { color: COLORS.orange, width: 2 } },
      },
    ],
  });
}

function option31() {
  return baseOption({
    title: title("目标完成率 78.0%，距目标仍差 7 个百分点", "单指标｜目标=85%｜状态=需关注"),
    series: [{
      type: "gauge",
      center: ["50%", "60%"],
      radius: "74%",
      min: 0,
      max: 100,
      startAngle: 210,
      endAngle: -30,
      progress: { show: true, width: 13, itemStyle: { color: COLORS.orange } },
      axisLine: { lineStyle: { width: 13, color: [[.6, "#E6E9EE"], [.85, "#CFD9EA"], [1, "#B8C9E7"]] } },
      axisTick: { show: false },
      splitLine: { length: 7, lineStyle: { color: "#9AA4B2", width: 1 } },
      axisLabel: { distance: 18, color: COLORS.muted, fontSize: 8 },
      pointer: { width: 4, length: "58%", itemStyle: { color: COLORS.ink } },
      anchor: { show: true, size: 8, itemStyle: { color: COLORS.ink } },
      detail: { valueAnimation: false, formatter: "{value}%", color: COLORS.ink, fontSize: 22, offsetCenter: [0, "38%"] },
      data: [{ value: 78 }],
      markPoint: { data: [{ value: 85 }] },
    }],
    graphic: [
      { type: "text", left: "72%", top: "39%", style: { text: "目标\n85%", fill: COLORS.orange, font: "700 9px Microsoft YaHei", textAlign: "center" } },
    ],
  });
}

function option32() {
  const days = Array.from({ length: 31 }, (_, i) => {
    const day = String(i + 1).padStart(2, "0");
    const value = 45 + ((i * 17) % 52);
    return [`2026-07-${day}`, value];
  });
  days[18][1] = 118;
  return baseOption({
    title: title("7 月 19 日活跃量达到峰值，周末整体偏低", "2026-07｜日活跃用户：千人｜连续日期无缺失"),
    visualMap: { min: 40, max: 120, orient: "horizontal", left: "center", bottom: 4, itemWidth: 8, itemHeight: 100, textStyle: { fontSize: 8 }, inRange: { color: ["#EDF3FF", "#2F6BFF"] } },
    calendar: {
      top: 78,
      left: 42,
      right: 18,
      bottom: 42,
      range: "2026-07",
      cellSize: ["auto", 24],
      dayLabel: { firstDay: 1, nameMap: ["日", "一", "二", "三", "四", "五", "六"], fontSize: 8, color: COLORS.muted },
      monthLabel: { show: false },
      yearLabel: { show: false },
      itemStyle: { borderWidth: 2, borderColor: "#fff" },
      splitLine: { show: false },
    },
    series: [{
      type: "heatmap",
      coordinateSystem: "calendar",
      data: days,
      label: { show: true, fontSize: 7, color: COLORS.ink, formatter: (p) => Number(p.value[0].slice(-2)) },
      markPoint: { data: [{ coord: ["2026-07-19", 118] }], symbol: "circle", symbolSize: 8, itemStyle: { color: COLORS.orange }, label: { show: false } },
    }],
  });
}

function option33() {
  const tasks = [
    { name: "需求确认", start: 0, end: 3, progress: 100 },
    { name: "数据准备", start: 2, end: 7, progress: 100 },
    { name: "分析建模", start: 6, end: 13, progress: 70 },
    { name: "报告制作", start: 11, end: 17, progress: 35 },
    { name: "评审交付", start: 16, end: 20, progress: 0 },
  ];
  return baseOption({
    title: title("分析建模已完成 70%，报告制作与其重叠推进", "项目周期：7/1–7/21｜虚线=今天 7/12"),
    grid: grid({ left: 76, right: 24 }),
    xAxis: valueAxis("7 月日期", { min: 0, max: 20, interval: 4, axisLabel: { fontSize: 8, formatter: (v) => `${v + 1}日` } }),
    yAxis: categoryAxis(tasks.map((t) => t.name), { inverse: true }),
    series: [{
      type: "custom",
      data: tasks.map((t, i) => [i, t.start, t.end, t.progress]),
      renderItem(params, api) {
        const y = api.coord([api.value(1), api.value(0)])[1];
        const x1 = api.coord([api.value(1), api.value(0)])[0];
        const x2 = api.coord([api.value(2), api.value(0)])[0];
        const done = x1 + (x2 - x1) * api.value(3) / 100;
        return {
          type: "group",
          children: [
            { type: "rect", shape: { x: x1, y: y - 8, width: x2 - x1, height: 16, r: 4 }, style: { fill: COLORS.grayLight } },
            { type: "rect", shape: { x: x1, y: y - 8, width: Math.max(0, done - x1), height: 16, r: 4 }, style: { fill: params.dataIndex === 2 ? COLORS.orange : COLORS.blue } },
            { type: "text", style: { x: x2 + 5, y, text: `${api.value(3)}%`, fill: COLORS.ink, font: "8px Microsoft YaHei", verticalAlign: "middle" } },
          ],
        };
      },
      markLine: { symbol: ["none", "none"], data: [{ xAxis: 11, label: { formatter: "今天", fontSize: 8 } }], lineStyle: { color: COLORS.red, type: "dashed" } },
    }],
  });
}

function option34() {
  const dates = ["7/1", "7/2", "7/3", "7/4", "7/5", "7/8", "7/9", "7/10", "7/11", "7/12"];
  const ohlc = [
    [102, 105, 100, 107], [105, 103, 101, 108], [103, 109, 102, 111], [109, 112, 107, 114], [112, 110, 108, 115],
    [110, 116, 109, 118], [116, 119, 114, 121], [119, 117, 115, 122], [117, 121, 116, 123], [121, 125, 120, 127],
  ];
  const volume = [32, 28, 41, 52, 35, 61, 58, 44, 67, 72];
  return baseOption({
    title: title("股价震荡上行，7/12 放量收于阶段高位", "OHLC 已校验｜红涨绿跌｜下方=成交量"),
    grid: [
      { left: 44, right: 18, top: 75, height: 134 },
      { left: 44, right: 18, top: 226, height: 41 },
    ],
    xAxis: [
      categoryAxis(dates, { gridIndex: 0, axisLabel: { show: false } }),
      categoryAxis(dates, { gridIndex: 1, axisLabel: { fontSize: 7 } }),
    ],
    yAxis: [
      valueAxis("价格", { gridIndex: 0, min: 96, max: 130, scale: true }),
      valueAxis("量", { gridIndex: 1, min: 0, max: 80, axisLabel: { fontSize: 7 }, splitLine: { show: false } }),
    ],
    series: [
      { type: "candlestick", data: ohlc, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: COLORS.red, color0: COLORS.green, borderColor: COLORS.red, borderColor0: COLORS.green } },
      { type: "bar", data: volume, xAxisIndex: 1, yAxisIndex: 1, barWidth: "55%", itemStyle: { color: (p) => ohlc[p.dataIndex][1] >= ohlc[p.dataIndex][0] ? COLORS.red : COLORS.green } },
    ],
  });
}

function option35() {
  const nodes = ["自然流量", "付费流量", "活动流量", "访问", "注册", "试用", "付费"];
  return baseOption({
    title: title("付费流量贡献最多注册，但自然流量付费转化更稳", "人数｜节点守恒｜仅强调主要路径"),
    series: [{
      type: "sankey",
      left: 18,
      right: 58,
      top: 70,
      bottom: 18,
      nodeWidth: 10,
      nodeGap: 10,
      layoutIterations: 24,
      data: nodes.map((name, i) => ({ name, itemStyle: { color: i === 1 || i === 6 ? COLORS.orange : i < 3 ? COLORS.blue : COLORS.teal } })),
      links: [
        { source: "自然流量", target: "访问", value: 480 },
        { source: "付费流量", target: "访问", value: 620 },
        { source: "活动流量", target: "访问", value: 300 },
        { source: "访问", target: "注册", value: 760 },
        { source: "访问", target: "试用", value: 420 },
        { source: "注册", target: "试用", value: 350 },
        { source: "注册", target: "付费", value: 160 },
        { source: "试用", target: "付费", value: 290 },
      ],
      lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.28 },
      label: { color: COLORS.ink, fontSize: 8 },
    }],
  });
}

function option36() {
  const dates = ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01"];
  const topics = {
    "AI 助手": [18, 22, 29, 36, 48, 57],
    "自动化": [28, 31, 34, 38, 35, 41],
    "数据治理": [42, 39, 35, 33, 31, 29],
  };
  const data = [];
  Object.entries(topics).forEach(([name, vals]) => vals.forEach((v, i) => data.push([dates[i], v, name])));
  return baseOption({
    title: title("AI 助手热度快速上升，6 月成为第一主题", "主题讨论量｜同一月度口径｜河流厚度=讨论量"),
    graphic: [
      { type: "text", left: 10, top: 112, style: { text: "AI 助手", fill: COLORS.blue, font: "700 8px Microsoft YaHei" } },
      { type: "text", left: 10, top: 160, style: { text: "自动化", fill: COLORS.orange, font: "700 8px Microsoft YaHei" } },
      { type: "text", left: 10, top: 208, style: { text: "数据治理", fill: COLORS.teal, font: "700 8px Microsoft YaHei" } },
      { type: "line", right: 54, top: 116, shape: { x1: 0, y1: 0, x2: 10, y2: 0 }, style: { stroke: COLORS.blue, lineWidth: 1 } },
      { type: "text", right: 8, top: 110, style: { text: "AI 助手 57", fill: COLORS.blue, font: "700 8px Microsoft YaHei" } },
      { type: "line", right: 54, top: 164, shape: { x1: 0, y1: 0, x2: 10, y2: 0 }, style: { stroke: COLORS.orange, lineWidth: 1 } },
      { type: "text", right: 8, top: 158, style: { text: "自动化 41", fill: COLORS.orange, font: "700 8px Microsoft YaHei" } },
      { type: "line", right: 54, top: 212, shape: { x1: 0, y1: 0, x2: 10, y2: 0 }, style: { stroke: COLORS.teal, lineWidth: 1 } },
      { type: "text", right: 8, top: 206, style: { text: "数据治理 29", fill: COLORS.teal, font: "700 8px Microsoft YaHei" } },
    ],
    singleAxis: {
      top: 78,
      bottom: 40,
      left: 62,
      right: 72,
      type: "time",
      axisLabel: { fontSize: 8, color: COLORS.muted, formatter: (value) => `${new Date(value).getMonth() + 1}月` },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLORS.line } },
    },
    series: [{
      type: "themeRiver",
      data,
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 0 } },
      itemStyle: { opacity: 0.82 },
    }],
  });
}

const BUSINESS_GEOJSON = {
  type: "FeatureCollection",
  features: [
    { type: "Feature", properties: { name: "西北区" }, geometry: { type: "Polygon", coordinates: [[[0, 7], [4, 8], [5, 5], [2, 4], [0, 7]]] } },
    { type: "Feature", properties: { name: "北区" }, geometry: { type: "Polygon", coordinates: [[[4, 8], [8, 8], [9, 6], [5, 5], [4, 8]]] } },
    { type: "Feature", properties: { name: "西区" }, geometry: { type: "Polygon", coordinates: [[[2, 4], [5, 5], [5, 2], [1, 1], [2, 4]]] } },
    { type: "Feature", properties: { name: "中区" }, geometry: { type: "Polygon", coordinates: [[[5, 5], [9, 6], [9, 3], [5, 2], [5, 5]]] } },
    { type: "Feature", properties: { name: "东区" }, geometry: { type: "Polygon", coordinates: [[[9, 6], [12, 5], [11, 2.5], [9, 3], [9, 6]]] } },
    { type: "Feature", properties: { name: "南区" }, geometry: { type: "Polygon", coordinates: [[[5, 2], [9, 3], [10, 0], [6, -1], [5, 2]]] } },
    { type: "Feature", properties: { name: "海岛区" }, geometry: { type: "Polygon", coordinates: [[[11, 1], [12, 1.3], [12.4, 0.2], [11.3, 0], [11, 1]]] } },
  ],
};

echarts.registerMap("business-regions", BUSINESS_GEOJSON);

function option37() {
  return baseOption({
    title: title("数据产品占业务规模 42%，其中企业数据最大", "面积=收入规模｜二级层级直接显示"),
    series: [{
      type: "treemap",
      left: 12,
      right: 12,
      top: 65,
      bottom: 12,
      roam: false,
      breadcrumb: { show: false },
      label: { show: true, color: "#fff", fontSize: 9, formatter: "{b}\n{c}" },
      upperLabel: { show: false },
      itemStyle: { borderColor: "#fff", borderWidth: 1, gapWidth: 1 },
      levels: [
        {},
        { itemStyle: { borderWidth: 2, gapWidth: 1 }, upperLabel: { show: false } },
        { colorSaturation: [0.3, 0.6], itemStyle: { borderWidth: 1, gapWidth: 1 } },
      ],
      data: [
        { name: "数据产品 42%", value: 42, itemStyle: { color: COLORS.blue }, children: [{ name: "企业数据", value: 24 }, { name: "行业洞察", value: 18 }] },
        { name: "营销产品 31%", value: 31, itemStyle: { color: COLORS.orange }, children: [{ name: "智能投放", value: 19 }, { name: "客户运营", value: 12 }] },
        { name: "服务 27%", value: 27, itemStyle: { color: COLORS.teal }, children: [{ name: "客户成功", value: 16 }, { name: "咨询培训", value: 11 }] },
      ],
    }],
  });
}

function option38() {
  return baseOption({
    title: title("企业客户是收入最大来源，续费构成核心路径", "内圈=客户类型｜外圈=收入类型｜父子总量一致"),
    series: [{
      type: "sunburst",
      center: ["50%", "57%"],
      radius: ["0%", "70%"],
      sort: null,
      nodeClick: false,
      label: { rotate: 0, fontSize: 8, color: COLORS.ink },
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      data: [
        { name: "企业 48", value: 48, itemStyle: { color: COLORS.blue }, children: [{ name: "续费 31", value: 31, itemStyle: { color: "#5C84F5" } }, { name: "新购 17", value: 17, itemStyle: { color: "#91ABF2" } }] },
        { name: "商户 32", value: 32, itemStyle: { color: COLORS.orange }, children: [{ name: "续费 18", value: 18, itemStyle: { color: "#F28C68" } }, { name: "新购 14", value: 14, itemStyle: { color: "#F6B49D" } }] },
        { name: "个人 20", value: 20, itemStyle: { color: COLORS.teal }, children: [{ name: "续费 12", value: 12, itemStyle: { color: "#49B29E" } }, { name: "新购 8", value: 8, itemStyle: { color: "#8BD1C3" } }] },
      ],
    }],
  });
}

function option39() {
  return baseOption({
    title: title("东区收入最高，海岛区数据缺失需单独核查", "虚拟业务分区｜分位数单色分级｜灰色=缺失"),
    visualMap: { min: 40, max: 150, left: 12, bottom: 10, itemWidth: 10, itemHeight: 72, text: ["高", "低"], textStyle: { fontSize: 8 }, inRange: { color: ["#E9F0FF", "#2F6BFF"] } },
    series: [{
      type: "map",
      map: "business-regions",
      left: 42,
      right: 16,
      top: 67,
      bottom: 14,
      roam: false,
      label: { show: true, fontSize: 8, color: COLORS.ink, formatter: (p) => p.value == null ? `${p.name}\n缺失` : `${p.name}\n${p.value}` },
      itemStyle: { borderColor: "#fff", borderWidth: 2, areaColor: COLORS.grayLight },
      emphasis: { disabled: true },
      data: [
        { name: "西北区", value: 55 }, { name: "北区", value: 96 }, { name: "西区", value: 48 },
        { name: "中区", value: 108 }, { name: "东区", value: 146, itemStyle: { borderColor: COLORS.orange, borderWidth: 3 } },
        { name: "南区", value: 121 }, { name: "海岛区", value: null, itemStyle: { areaColor: COLORS.gray } },
      ],
    }],
  });
}

function option40() {
  const coords = {
    "西北中心": [3.2, 6.3], "北区中心": [7.1, 6.7], "西区中心": [3.2, 2.8],
    "中区中心": [7.3, 3.8], "东区中心": [10.3, 4.4], "南区中心": [7.8, 1.2],
  };
  const values = [["西北中心", 42], ["北区中心", 78], ["西区中心", 35], ["中区中心", 96], ["东区中心", 138], ["南区中心", 112]];
  return baseOption({
    title: title("东区中心规模最大，符号面积约为西区中心四倍", "虚拟业务分区｜圆面积=客户数｜单位：千户"),
    geo: {
      map: "business-regions", left: 20, right: 20, top: 67, bottom: 12, roam: false,
      itemStyle: { areaColor: "#F0F3F7", borderColor: "#fff", borderWidth: 2 },
      label: { show: false }, emphasis: { disabled: true },
    },
    series: [{
      type: "scatter",
      coordinateSystem: "geo",
      data: values.map(([name, v]) => ({ name, value: [...coords[name], v], itemStyle: { color: name === "东区中心" ? COLORS.orange : COLORS.blue } })),
      symbolSize: (v) => Math.sqrt(v[2]) * 2.2,
      label: { show: true, position: "right", color: COLORS.ink, fontSize: 8, formatter: (p) => `${p.name}\n${p.value[2]}` },
    }],
  });
}

function option41() {
  const c = { "西北": [3.2, 6.3], "北区": [7.1, 6.7], "西区": [3.2, 2.8], "中区": [7.3, 3.8], "东区": [10.3, 4.4], "南区": [7.8, 1.2] };
  const flows = [["东区", "中区", 96], ["北区", "东区", 72], ["西北", "中区", 44], ["南区", "东区", 58], ["西区", "南区", 31]];
  return baseOption({
    title: title("东区是主要流入中心，最大通道来自中区", "虚拟业务分区｜线宽=流量｜箭头=方向"),
    geo: {
      map: "business-regions", left: 20, right: 20, top: 67, bottom: 12, roam: false,
      itemStyle: { areaColor: "#F0F3F7", borderColor: "#fff", borderWidth: 2 },
      emphasis: { disabled: true },
    },
    series: [
      {
        type: "lines",
        coordinateSystem: "geo",
        zlevel: 2,
        symbol: ["none", "arrow"],
        symbolSize: 7,
        lineStyle: { color: COLORS.blue, opacity: 0.55, curveness: 0.18 },
        data: flows.map(([from, to, v]) => ({ fromName: from, toName: to, value: v, coords: [c[from], c[to]], lineStyle: { width: Math.max(1.5, v / 25), color: v === 96 ? COLORS.orange : COLORS.blue } })),
      },
      {
        type: "effectScatter",
        coordinateSystem: "geo",
        showEffectOn: "emphasis",
        symbolSize: 7,
        data: Object.entries(c).map(([name, coord]) => ({ name, value: [...coord, 1] })),
        itemStyle: { color: COLORS.ink },
        label: { show: true, position: "right", color: COLORS.ink, fontSize: 8, formatter: "{b}" },
      },
    ],
  });
}

function option42() {
  const nodes = [
    { name: "核心客户", value: 34, symbolSize: 34, category: 0, x: 0, y: 0 },
    { name: "客户 A", value: 18, symbolSize: 22, category: 0, x: -70, y: -45 },
    { name: "客户 B", value: 16, symbolSize: 20, category: 0, x: 68, y: -48, label: { position: "left" } },
    { name: "渠道中心", value: 26, symbolSize: 28, category: 1, x: 0, y: 78 },
    { name: "渠道 C", value: 12, symbolSize: 17, category: 1, x: -75, y: 65 },
    { name: "渠道 D", value: 10, symbolSize: 15, category: 1, x: 78, y: 62, label: { position: "left" } },
    { name: "服务团队", value: 22, symbolSize: 25, category: 2, x: 0, y: -82 },
  ];
  const links = [
    ["核心客户", "客户 A", 5], ["核心客户", "客户 B", 4], ["核心客户", "渠道中心", 7],
    ["核心客户", "服务团队", 8], ["渠道中心", "渠道 C", 3], ["渠道中心", "渠道 D", 2],
    ["服务团队", "客户 A", 2], ["服务团队", "客户 B", 3],
  ];
  return baseOption({
    title: title("核心客户连接三个社群，是网络中的关键桥梁", "节点大小=连接度｜边宽=关系强度｜仅保留主要关系"),
    legend: { bottom: 2, data: ["客户", "渠道", "服务"], textStyle: { fontSize: 8 }, itemWidth: 9, itemHeight: 9 },
    series: [{
      type: "graph",
      layout: "none",
      left: 92,
      right: 92,
      top: 60,
      bottom: 42,
      roam: false,
      data: nodes,
      links: links.map(([source, target, value]) => ({ source, target, value, lineStyle: { width: value / 2, opacity: 0.35 } })),
      categories: [{ name: "客户", itemStyle: { color: COLORS.orange } }, { name: "渠道", itemStyle: { color: COLORS.blue } }, { name: "服务", itemStyle: { color: COLORS.teal } }],
      label: { show: true, position: "right", color: COLORS.ink, fontSize: 8 },
      lineStyle: { color: "#718096", curveness: 0.08 },
      emphasis: { disabled: true },
    }],
  });
}

function option43() {
  return baseOption({
    title: title("三季度投诉量最高，四季度明显回落", "半径=投诉量｜等角扇区｜面积感知可能夸大差异"),
    legend: { bottom: 4, textStyle: { fontSize: 8 }, itemWidth: 9, itemHeight: 9 },
    series: [{
      type: "pie",
      roseType: "radius",
      radius: ["18%", "68%"],
      center: ["50%", "55%"],
      startAngle: 90,
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      label: { color: COLORS.ink, fontSize: 8, formatter: "{b}\n{c}" },
      data: [
        { value: 42, name: "Q1", itemStyle: { color: "#AFC6FF" } },
        { value: 55, name: "Q2", itemStyle: { color: "#6F96F5" } },
        { value: 78, name: "Q3", itemStyle: { color: COLORS.orange } },
        { value: 48, name: "Q4", itemStyle: { color: COLORS.blue } },
      ],
    }],
  });
}

function option44() {
  const actual = [72, 78, 81, 69, 88, 94, 90, 102];
  const efficiency = [76, 79, 82, 78, 86, 91, 88, 93];
  return baseOption({
    title: title("6 月后实际量持续高位，效率重新回到目标带", "柱=实际量（左轴）｜线=效率（右轴）｜目标带=85%–95%"),
    grid: grid({ right: 48 }),
    legend: { show: false },
    xAxis: categoryAxis(["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"], { axisLabel: { fontSize: 8 } }),
    yAxis: [
      valueAxis("实际量（千）", { min: 0, max: 120, nameTextStyle: { color: COLORS.blue, fontSize: 8 } }),
      valueAxis("效率", { min: 65, max: 100, position: "right", nameTextStyle: { color: COLORS.orange, fontSize: 8 }, axisLabel: { formatter: "{value}%", color: COLORS.orange, fontSize: 8 }, splitLine: { show: false } }),
    ],
    series: [
      {
        name: "实际量",
        type: "bar",
        barWidth: 13,
        data: actual.map((v, i) => ({ value: v, itemStyle: { color: i === 3 ? COLORS.orange : COLORS.blue } })),
        label: { show: true, position: "top", color: COLORS.ink, fontSize: 7, formatter: (p) => p.dataIndex === 3 ? p.value : "" },
      },
      {
        name: "效率",
        type: "line",
        yAxisIndex: 1,
        data: efficiency,
        symbolSize: 4,
        lineStyle: { color: COLORS.teal, width: 2 },
        itemStyle: { color: COLORS.teal },
        endLabel: { show: true, formatter: "93%", color: COLORS.teal, fontSize: 8, fontWeight: 700 },
        markArea: { silent: true, itemStyle: { color: "rgba(21,155,131,.10)" }, label: { show: true, formatter: "目标带 85%–95%", position: "insideTop", color: COLORS.teal, fontSize: 7 }, data: [[{ yAxis: 85 }, { yAxis: 95 }]] },
      },
    ],
  });
}

function option45() {
  const cats = ["上期利润", "销量增长", "价格提升", "产品结构", "履约成本", "本期利润"];
  const base = [0, 100, 118, 111, 102, 0];
  const vals = [100, 18, 12, 7, 9, 102];
  const signs = ["100", "+18", "+12", "−7", "−9", "102"];
  return baseOption({
    title: title("增长贡献被结构与履约成本抵消，本期利润仅增 2", "百万元｜正贡献 +30 / 负贡献 −28｜桥接结果可核对"),
    graphic: [
      { type: "text", right: 13, top: 42, style: { text: "净变化 +2", fill: COLORS.orange, font: "700 10px Microsoft YaHei" } },
    ],
    grid: grid({ left: 42, right: 20 }),
    xAxis: categoryAxis(cats, { axisLabel: { fontSize: 7, rotate: 20 } }),
    yAxis: valueAxis("百万元", { min: 0, max: 145 }),
    series: [
      { type: "bar", stack: "bridge", data: base, silent: true, itemStyle: { color: "transparent" } },
      {
        type: "bar",
        stack: "bridge",
        barWidth: 19,
        data: vals.map((v, i) => ({
          value: v,
          itemStyle: { color: i === 0 || i === 5 ? COLORS.blue : i <= 2 ? COLORS.teal : COLORS.orange },
          label: { show: true, position: i === 3 || i === 4 ? "bottom" : "top", color: COLORS.ink, fontSize: 8, formatter: signs[i] },
        })),
      },
    ],
  });
}

function option46() {
  const orders = [82, 91, 96, 103, 110, 118, 126, 132];
  const price = [326, 318, 334, 329, 342, 351, 347, 362];
  return baseOption({
    title: title("订单量与客单价总体同升，但 7 月出现短暂背离", "柱=订单量（千单）｜线=客单价（元）｜两轴范围均公开"),
    grid: grid({ right: 50 }),
    legend: { show: false },
    xAxis: categoryAxis(["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"], { axisLabel: { fontSize: 8 } }),
    yAxis: [
      valueAxis("千单", { min: 0, max: 150, nameTextStyle: { color: COLORS.blue, fontSize: 8 }, axisLabel: { color: COLORS.blue, fontSize: 8 } }),
      valueAxis("元", { min: 280, max: 380, position: "right", nameTextStyle: { color: COLORS.orange, fontSize: 8 }, axisLabel: { color: COLORS.orange, fontSize: 8 }, splitLine: { show: false } }),
    ],
    series: [
      { name: "订单量", type: "bar", barWidth: 13, data: orders, itemStyle: { color: COLORS.blue } },
      {
        name: "客单价",
        type: "line",
        yAxisIndex: 1,
        data: price,
        symbolSize: 4,
        lineStyle: { color: COLORS.orange, width: 2 },
        itemStyle: { color: COLORS.orange },
        markPoint: {
          data: [
            { coord: ["7月", 347], value: "背离", symbolSize: 28, label: { fontSize: 7 }, itemStyle: { color: COLORS.orange } },
            { coord: ["8月", 362], value: "¥362", symbolSize: 6, label: { show: true, position: "left", offset: [-3, -10], formatter: "¥362", color: COLORS.orange, fontSize: 8, fontWeight: 700 }, itemStyle: { color: COLORS.orange } },
          ],
        },
      },
    ],
  });
}

function option47() {
  return baseOption({
    title: title("收入同比增长 12.4%，核心驱动来自企业客户", "2026 H1｜收入：百万元｜趋势与驱动口径一致"),
    graphic: [
      { type: "rect", left: 14, top: 58, shape: { width: 112, height: 64, r: 8 }, style: { fill: "#F3F6FB", stroke: COLORS.line } },
      { type: "text", left: 26, top: 67, style: { text: "当前收入", fill: COLORS.muted, font: "9px Microsoft YaHei" } },
      { type: "text", left: 25, top: 83, style: { text: "¥482M", fill: COLORS.ink, font: "700 22px Microsoft YaHei" } },
      { type: "text", left: 26, top: 109, style: { text: "同比 +12.4%｜高于目标 3.2%", fill: COLORS.orange, font: "700 8px Microsoft YaHei" } },
      { type: "text", left: 146, top: 62, style: { text: "趋势证据", fill: COLORS.muted, font: "700 9px Microsoft YaHei" } },
      { type: "text", left: 17, top: 184, style: { text: "驱动拆解", fill: COLORS.muted, font: "700 9px Microsoft YaHei" } },
    ],
    grid: [
      { left: 148, right: 18, top: 78, height: 76 },
      { left: 72, right: 70, top: 210, height: 60 },
    ],
    xAxis: [
      categoryAxis(["1月", "2月", "3月", "4月", "5月", "6月"], { gridIndex: 0, axisLabel: { fontSize: 7 } }),
      valueAxis("", { gridIndex: 1, min: -15, max: 35, axisLabel: { fontSize: 7 }, splitLine: { show: false } }),
    ],
    yAxis: [
      valueAxis("", { gridIndex: 0, min: 60, max: 95, axisLabel: { show: false }, splitLine: { lineStyle: { color: COLORS.grid } } }),
      categoryAxis(["企业客户", "中小商户", "个人客户", "成本变化"], { gridIndex: 1, inverse: true, axisLabel: { fontSize: 7 } }),
    ],
    series: [
      {
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: [68, 72, 75, 79, 83, 88],
        symbolSize: 4,
        lineStyle: { color: COLORS.blue, width: 2.5 },
        itemStyle: { color: COLORS.blue },
        endLabel: { show: true, formatter: "88M", color: COLORS.blue, fontSize: 8, fontWeight: 700 },
      },
      {
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        barWidth: 10,
        data: [31, 16, 8, -7].map((v, i) => ({
          value: v,
          itemStyle: { color: i === 0 ? COLORS.orange : v > 0 ? COLORS.blue : COLORS.gray },
          label: {
            show: true,
            position: v >= 0 ? "right" : "left",
            distance: 4,
            color: i === 0 ? COLORS.orange : COLORS.ink,
            fontSize: 7,
            fontWeight: i === 0 ? 700 : 400,
            formatter: `${v > 0 ? "+" : ""}${v}M${i === 0 ? " 核心驱动" : ""}`,
          },
        })),
        labelLayout: { moveOverlap: "shiftY" },
      },
    ],
  });
}

function option48() {
  const panels = [
    { name: "华东", data: [62, 66, 69, 72, 78, 82], color: COLORS.orange },
    { name: "华南", data: [58, 61, 65, 67, 71, 74], color: COLORS.blue },
    { name: "华北", data: [55, 59, 58, 64, 67, 70], color: COLORS.blue },
    { name: "西南", data: [48, 52, 55, 57, 60, 63], color: COLORS.blue },
  ];
  const grids = [
    { left: "10%", top: 84, width: "35%", height: 72 },
    { left: "57%", top: 84, width: "35%", height: 72 },
    { left: "10%", top: 190, width: "35%", height: 72 },
    { left: "57%", top: 190, width: "35%", height: 72 },
  ];
  return baseOption({
    title: title("四区域趋势同向，华东增速和最新值均最高", "月活跃用户：万｜四图共享 40–90 纵轴与同一时间范围"),
    graphic: panels.map((p, i) => ({
      type: "text",
      left: i % 2 === 0 ? "10%" : "57%",
      top: i < 2 ? 66 : 172,
      style: { text: `${p.name}｜最新 ${p.data[5]}`, fill: p.color, font: `700 8px Microsoft YaHei` },
    })),
    grid: grids,
    xAxis: panels.map((_, i) => categoryAxis(["1月", "2月", "3月", "4月", "5月", "6月"], { gridIndex: i, axisLabel: { show: i >= 2, fontSize: 6, interval: 1 } })),
    yAxis: panels.map((_, i) => valueAxis("", { gridIndex: i, min: 40, max: 90, axisLabel: { show: i % 2 === 0, fontSize: 6 }, splitLine: { lineStyle: { color: COLORS.grid } } })),
    series: panels.map((p, i) => ({
      type: "line",
      xAxisIndex: i,
      yAxisIndex: i,
      data: p.data,
      symbol: "none",
      lineStyle: { color: p.color, width: i === 0 ? 2.5 : 1.7 },
      areaStyle: i === 0 ? { color: "rgba(240,106,60,.08)" } : undefined,
      endLabel: i === 0 ? { show: true, formatter: "82", color: COLORS.orange, fontSize: 7 } : undefined,
    })),
  });
}

const OPTION_BUILDERS = {
  1: option01, 2: option02, 3: option03, 4: option04, 5: option05, 6: option06,
  7: option07, 8: option08, 9: option09, 10: option10, 11: option11, 12: option12,
  13: option13, 14: option14, 15: option15, 16: option16, 17: option17, 18: option18,
  19: option19, 20: option20, 21: option21, 22: option22, 23: option23, 24: option24,
  25: option25, 26: option26, 27: option27, 28: option28, 29: option29, 30: option30,
  31: option31, 32: option32, 33: option33, 34: option34, 35: option35, 36: option36,
  37: option37, 38: option38, 39: option39, 40: option40, 41: option41, 42: option42,
  43: option43, 44: option44, 45: option45, 46: option46, 47: option47, 48: option48,
};

const chartInstances = new Map();

function makeCard(card) {
  const article = document.createElement("article");
  article.className = "chart-card";
  article.dataset.group = card.group;
  article.id = code(card.id).toLowerCase();
  article.innerHTML = `
    <div class="card-head">
      <span class="card-index">${String(card.id).padStart(2, "0")}</span>
      <div>
        <h3 class="card-title">${card.name}</h3>
        <p class="card-family">${GROUP_LABELS[card.group]} · ${code(card.id)}</p>
      </div>
    </div>
    <div class="chart" role="img" aria-label="${card.name}示例图"></div>
    <div class="card-foot"><strong>检查重点：</strong>${card.focus}</div>
  `;
  return article;
}

function renderGallery() {
  const root = document.getElementById("gallery");
  CARDS.forEach((card) => root.appendChild(makeCard(card)));

  let rendered = 0;
  CARDS.forEach((card) => {
    const container = document.querySelector(`#${code(card.id).toLowerCase()} .chart`);
    try {
      const instance = echarts.init(container, null, { renderer: "canvas" });
      instance.setOption(OPTION_BUILDERS[card.id](), true);
      chartInstances.set(card.id, instance);
      rendered += 1;
    } catch (error) {
      container.className = "chart-error";
      container.textContent = `${code(card.id)} 渲染失败：${error.message}`;
      console.error(code(card.id), error);
    }
  });
  document.getElementById("rendered-count").textContent = String(rendered);

  const resizeObserver = new ResizeObserver(() => {
    chartInstances.forEach((instance) => instance.resize());
  });
  resizeObserver.observe(root);
}

function bindFilters() {
  const buttons = [...document.querySelectorAll(".filter")];
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => {
        item.classList.toggle("is-active", item === button);
        item.setAttribute("aria-pressed", item === button ? "true" : "false");
      });
      const selected = button.dataset.filter;
      document.querySelectorAll(".chart-card").forEach((card) => {
        card.hidden = selected !== "all" && card.dataset.group !== selected;
      });
      requestAnimationFrame(() => chartInstances.forEach((instance) => instance.resize()));
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderGallery();
  bindFilters();
});
