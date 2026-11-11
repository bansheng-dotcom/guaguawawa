# 电商设计师（ecommerce-designer）· v2.0.0

> 电商视觉设计稿输出引擎。把商品卖点翻译成可转化的视觉主张，一键产出主图矩阵、详情页分屏脚本、版式色彩字体系统、AI 出图提示词与全平台像素级规格清单，并强制通过广告法极限词合规闸门。**兼具反向诊断能力与单变量验证能力。**

---

## 一、这个技能解决什么

电商视觉的痛点从来不是"不会画图"，而是四件事没人一次做全：

1. **图好看但不转化**——没有转化职责、没有点击理由、五张主图互相重复。
2. **上线就被打回**——尺寸不对、体积超限、文字面积超标（牛皮癣）、被平台压缩裁切。
3. **文案踩法条**——"全网最低""顶级""根治"一写就违法，罚款上限可达 200 万元。
4. **改完不知道有没有变好**——凭经验改图，说不清为什么改、也说不清改完是否有效。

本技能用四条能力对位解决：**转化型视觉主张引擎 / 规格·合规双闸门 / 源文件与迭代响应协议 / 诊断与验证闭环**。

## 二、包结构

```
ecommerce-designer/
├── SKILL.md                         # 技能主指令（九步流水线 + 三种运行模式）
├── README.md                        # 本文件
├── references/                      # 知识资产 17 件（按需读取）
│   ├── platform-spec-matrix.md          全平台视觉规格矩阵（12 渠道 × 8 版位）
│   ├── ad-law-compliance.md             广告法合规与极限词处置（九大类 + 三档替换 + 执法案例）
│   ├── conversion-visual-method.md      转化型视觉方法论（0.8 秒预算 / 12 屏曲线 / 10 条洞察）
│   ├── layout-typography-system.md      版式·色彩·字体系统（含字体商用授权清单）
│   ├── prompt-library-imagegen.md       AI 出图提示词库（七段结构 + 负面词库）
│   ├── deliverable-and-iteration.md     交付八件套 + 源文件规范 + 修改响应协议
│   ├── compliance-and-labeling.md       内容安全与 AI 生成标识合规层
│   ├── quality-rubric.md                100 分制质量终审细则（七维度）
│   ├── trend-radar-2026.md              电商视觉趋势雷达（2026 六大结构性变化）  ★v2 新增
│   ├── category-playbooks-30.md         30 类目视觉打法手册                        ★v2 新增
│   ├── copywriting-formulas.md          文案公式库（主图 12 + 详情 20 + 促销 15） ★v2 新增
│   ├── detail-page-modules.md           详情页 36 模块库 + 8 套行业装配模板        ★v2 新增
│   ├── diagnosis-engine.md              设计稿诊断与改版优先级引擎                ★v2 新增
│   ├── ab-test-designer.md              A/B 测试设计器（样本量 + 判定规则）        ★v2 新增
│   ├── source-whitelist.md              联网检索与时效核验 SOP                    ★v2 新增
│   ├── faq-and-troubleshooting.md       40 例高频卡点处置                        ★v2 新增
│   └── changelog.md                     版本与月度进化记录
├── scripts/                         # 零第三方依赖脚本 10 个（均含 --self-test）
│   ├── spec_query.py                    规格查询（12 渠道 × 8 版位）
│   ├── adlaw_scan.py                    极限词扫描（9 大类 314 词 + 13 条平台红线）
│   ├── design_audit.py                  方案自检（26 项）                          ★v2 升级
│   ├── quality_score.py                 100 分制终审门禁（7 维度）                 ★v2 升级
│   ├── library_index.py                 资源库索引与口径一致性核验                ★v2 升级
│   ├── monthly_evolution.py             每月 1 号自动进化（五轮标准动作 + 版本递增）★v2 升级
│   ├── render_spec.py                   八件套交付骨架一键产出                    ★v2 新增
│   ├── diagnose.py                      设计稿诊断（20 项体检 → 分级 → 优先级）    ★v2 新增
│   ├── ab_plan.py                       A/B 测试计划与样本量估算                  ★v2 新增
│   └── web_research.py                  联网检索计划生成与结论落盘                ★v2 新增
├── templates/                       # 交付模板 6 件
│   ├── design-brief.md                  需求简报 + 十维画布 + 关键假设清单
│   ├── main-image-plan.md               主图矩阵方案表（5+N，每张十项）
│   ├── detail-page-storyboard.md        详情页 12 屏脚本
│   ├── delivery-manifest.md             交付清单 + 源文件规范 + 修改响应表
│   ├── diagnosis-report.md              设计稿诊断报告                        ★v2 新增
│   └── ab-test-plan.md                  A/B 测试计划                          ★v2 新增
└── assets/                          # 案例配图（设计规范参考卡）
```

## 三、快速上手

```
用户：帮我的保温杯做一版淘宝主图 + 详情页，客单价 129，主打 48 小时保温
技能：一键起八件套骨架 → 十维解码 → 联网校准规格与竞品 → 视觉主张锻造
      → 主图矩阵 → 详情页 12 屏装配 → 设计系统令牌 → 出图提示词
      → 合规闸门 → 交付与迭代响应

用户：我这个详情页转化不好，帮我看看问题出在哪
技能：走 Diagnose 模式 → 20 项体检 → 分级 + P0/P1/P2 优先级 + 12 类病症处方
      → 输出前 3 项改版建议与归因假设

用户：改完之后怎么知道有没有变好
技能：走 Verify 模式 → 单变量 A/B 计划（含样本量估算、护栏指标、判定规则）
```

## 四、脚本用法

```bash
# 规格查询
python scripts/spec_query.py --platform taobao --slot main
python scripts/spec_query.py --list

# 文案合规扫描（九大类 + 平台红线）
python scripts/adlaw_scan.py --text "全网最低价，顶级品质"
python scripts/adlaw_scan.py --file 主图文案.md --out 合规报告.md --strict

# 方案自检（26 项）
python scripts/design_audit.py --file 设计稿方案.md --out 自检报告.md

# 100 分制终审（≥95 才交付）
python scripts/quality_score.py --file 设计稿方案.md

# 八件套交付骨架一键产出
python scripts/render_spec.py --product 保温杯 --platform 淘宝 --out ./交付物

# 设计稿诊断
python scripts/diagnose.py --demo
python scripts/diagnose.py --file 体检表.md --out 诊断报告.md

# A/B 测试计划与样本量
python scripts/ab_plan.py --baseline 0.05 --lift 0.2 --daily-traffic 1000
python scripts/ab_plan.py --table

# 联网检索计划
python scripts/web_research.py --plan --platform taobao --category 保温杯

# 资源库核验
python scripts/library_index.py --audit

# 月度进化（五轮标准动作 + 版本递增）
python scripts/monthly_evolution.py --check
python scripts/monthly_evolution.py --plan
python scripts/monthly_evolution.py --bump minor --note "升级要点"
```

全部脚本仅依赖 Python 标准库，Windows / macOS / Linux 通用。

## 五、质量门禁（七维度，满分 100）

| 维度 | 满分 | 一票否决 |
|---|---|---|
| A 交付合规 | 13 | 极限词未替换 / 伪造资质 / 未授权素材 / 缺 AI 标识 |
| B 需求契合 | 18 | — |
| C 领域深度 | 18 | — |
| D 转化力 | 18 | — |
| E 可执行性 | 12 | — |
| F 交付完整 | 9 | — |
| G 时效与溯源 | 12 | — |
| **合计** | **100** | **≥95 才准交付** |

## 六、月度自动进化（五轮标准动作）

`scripts/monthly_evolution.py` 支持每月 1 号 0–1 点执行，`--plan` 可查看完整五轮动作：

1. **规格与合规时效同步** —— 重新联网核验规格与监管口径
2. **趋势雷达刷新** —— 保持设计决策的时效锚不落后
3. **类目打法与文案公式扩容** —— 每轮至少 +3 类目 / +3 公式
4. **脚本与门禁能力升级** —— 全脚本自检 + 端到端验收
5. **资产与交付形态扩容** —— 交付三查 + 打包 + 安装 + 存档

当前知识截止：**2026-09**。版本递增用 `--bump patch|minor|major`（自动递增 SKILL.md 版本号并落账）。

## 七、边界与合规

- 不做品牌 VI 全体系、印刷包装、UI 界面设计。
- 不承诺具体销量 / 转化率数字，只给可验证假设与单变量测试方案。
- 不生成伪造资质、盗用素材、虚假宣传、违法违规内容。
- 产出含 AI 生成内容，已内置显式标识话术与隐式元数据声明（依据《人工智能生成合成内容标识办法》，2025-09-01 施行）。
- 主图位须为真实拍摄；AI 生成图用于次级位、场景位与详情页。
- 所有文案交付前须通过极限词扫描；正式发布前请按目标平台当期规则复核。

## 八、版本

v2.0.0（2026-09-15）五轮极致升级。变更记录见 `references/changelog.md`。
