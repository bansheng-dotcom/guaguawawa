# 出图批次运行手册（pipeline-runbook）

> manifest 模板 · 命名规范 · 失败分类 · 成本表 · 6 组 BAD/GOOD。版本：v1

---

## 一、manifest.json 模板（每批一份，必须落盘）

```json
{
  "batch_id": "20261111_coffee",
  "created_at": "2026-11-11T16:30:00+08:00",
  "tool": {
    "name": "<外部生成工具名，如 nano-banana-pro>",
    "model": "<模型标识>",
    "version": "<工具有版本就写，没有写 unknown>"
  },
  "budget": {
    "unit_cost": 0.0,
    "planned_versions": 16,
    "cap": 0.0,
    "spent": 0.0,
    "stop_line": "80%"
  },
  "items": [
    {
      "seq": 1,
      "usage": "taobao_main",
      "spec": {"ratio": "1:1", "pixels": "2400x2400", "text_area": "top 1/5"},
      "selling_point": "静音 ≤45dB",
      "subject_variant": "深灰",
      "versions": 4,
      "acceptance": "主体占 70%，右上留文字位",
      "candidates": [
        {"file": "01_main_dark_v1_1101.png", "seed": 1101,
         "cost": 0.0, "spec_gate": "pass", "reject": null},
        {"file": "01_main_dark_v2_1102.png", "seed": 1102,
         "cost": 0.0, "spec_gate": "rejected:spec", "reject": "1024x1024 非 2400"}
      ],
      "retries": [
        {"reason": "随机性·六指", "action": "换 seed 重试", "n": 1}
      ],
      "selected": null
    }
  ],
  "notes": "本批第一轮，prompt 尚未验证可复现"
}
```

**字段纪律**：
- `seed` 必填（没有 seed 用工具的可复现标识替代，如 request_id）；
- `reject` 用固定前缀：`rejected:spec` / `rejected:channel` / `rejected:residue` / `rejected:brand`；
- `retries[].action` 只能是 `换 seed 重试` 或 `改 prompt`（二选一，便于事后统计）。

---

## 二、命名规范

```
<序号两位>_<用途>_<主体变体>_v<版本号>_<seed>.<ext>
01_main_dark_v3_88123.png
02_detail_material_v1_4411.png
03_xhs_cover_lifestyle_v2_9902.png
```

| 段 | 必填 | 说明 |
|---|---|---|
| 序号 | ✅ | 与 manifest 的 `seq` 对应 |
| 用途 | ✅ | `main` / `detail` / `xhs_cover` / `ad` |
| 主体变体 | ✅ | `dark` / `white` / `lifestyle` |
| 版本 | ✅ | `v1..vN` |
| seed | ✅ | 数字或工具标识 |
| 扩展名 | ✅ | 与通道匹配（RGBA 用 png） |

**禁用**：`1.png`、`最终版.png`、`最终版2.png`、`新建文件夹 (3)`。

---

## 三、版数档位表

| 档 | 版数 | 何时用 | 依据 |
|---|---|---|---|
| 试水 | 4 | 新主体/新风格/prompt 未验证 | 4 版才能看出稳定性 |
| 正式 | 8 | prompt 已验证可复现 | 求挑出最优 |
| A/B | 每向 4 | 两个方向对比 | 各向样本量对等 |
| 补数 | 2 | 已有 1 版合格，补备选 | 只需备选 |

**上限**：单批总版数 **≤ 8 × 张数**。超了说明在用数量掩盖 prompt 问题。

---

## 四、成本表与止损

```
批次预算 = 单版成本 × 计划总版数 × 1.2（重试余量）
```

| 阶段 | 阈值 | 动作 |
|---|---|---|
| 正常 | <60% 预算 | 继续 |
| 预警 | ≥60% | 检查是否在重复无效重试 |
| **暂停** | **≥80%** | **停止出图，汇报给人，由人决定** |
| 硬停 | ≥100% | 立即停，不出一版 |

**单卡止损**：同一任务卡连续重试 **>2 次**仍不合格 → 停止，进失败分类。

> 止损线的意义不是省钱，是**逼你在第 3 次之前想清楚 prompt**。

---

## 五、失败分类表（本手册最有用的表）

| 现象 | 归因 | 动作 | 不许做的事 |
|---|---|---|---|
| 偶发畸变、多余手指 | 随机性 | 换 seed 重试（≤2 次） | 改 prompt |
| 构图每版都漂 | 构图段太虚 | 改 prompt：写角度 + 占比 | 反复换 seed |
| 主体材质/颜色每版都错 | 主体段太虚 | 改 prompt：写材质 + 色值 | 加版数 |
| 尺寸/比例不对 | 规格没写进 prompt | 改 prompt 第 6 段 | 后处理裁 |
| 有文字/水印残留 | 负向词缺失 | 改 prompt：补负向 | 再生成碰运气 |
| 都合规但都不好 | 方向或版数 | 加版数 / 换方向 | 硬挑 |
| 规格对但主体被切 | 占比过大 | 改 prompt：降占比 | 后处理补边 |

**判据**：任何一次"再来一次"，都要能填上这张表的**归因**列。填不上 = 你在碰运气。

---

## 六、规格闸（出图后立刻跑，不等人看）

```bash
# 1 规格与通道
python agent.py imgops info --input 20261111_coffee/01_main_dark_v1_1101.png

# 2 品牌色（需要产物描述 json）
python agent.py brandcheck check --input prod.json --design DESIGN.md
```

| 闸 | 不符时的 reject 标记 |
|---|---|
| 比例/像素 | `rejected:spec` |
| 通道（RGBA→JPG 透明变黑） | `rejected:channel` |
| 负向残留（人工抽看） | `rejected:residue` |
| 品牌色越界 | `rejected:brand` |

**纪律**：被 reject 的版本**不进候选池**，但**文件不删**（留档证明出过，用于成本核对）。

---

## 七、6 组 BAD/GOOD

| # | 场景 | ❌ | ✅ |
|---|---|---|---|
| 1 | 重试策略 | 同一 prompt 重试 12 次 | 2 次后改「构图段写 45° 俯视 + 占 70%」 |
| 2 | 版数 | 所有图都出 8 版 | 试水 4 版，验证可复现后再上 8 版 |
| 3 | 命名 | `1.png` `2.png` | `01_main_dark_v1_1101.png` |
| 4 | 预算 | 出完再看花了多少 | 先写上限，80% 暂停 |
| 5 | 事后追溯 | 「上次用的啥参数忘了」 | manifest 有 seed 与 prompt 版本 |
| 6 | 规格错 | 出 1024 再裁成 1:1 | prompt 第 6 段写 1:1 + 2400×2400 |

---

## 八、一次真实批次的完整顺序

```
1. 定任务卡（每张图一行六项）
2. 定版数（按风险档）→ 算总版数，核 ≤8×张数
3. 写预算上限 → 算 80% 止损线
4. 写 prompt（见 image-prompt-structure 六段）
5. 建批次目录 + 空 manifest.json
6. 出 4 版（试水）→ 跑规格闸 → 填 manifest.candidates
7. 若 ≥2 版过硬门 → 交 image-candidate-selection 筛选
   若 <2 版 → 进失败分类 → 改 prompt 或提版数 → 回 6
8. 筛选定主选/备选 → 写入 manifest.selected
9. 主选进 image-ops 后处理 → 交付
10. 归档 manifest + 落选原因分类（回灌下一轮）
```

---

## 九、与相邻卡的分工

| 环节 | 归谁 |
|---|---|
| 要几张、每张说什么卖点 | `ecommerce-designer` |
| 怎么描述（六段 prompt） | `image-prompt-structure` |
| **出几版、预算、重试、落盘**（本卡） | `image-gen-pipeline` |
| 多版挑哪张 | `image-candidate-selection` |
| 裁切压缩加水印 | `image-ops` |
| 单张好不好看 | `visual-hierarchy` |

---

## 十、来源

- 批次编排、预算止损与失败分类：本团队工程实践（借用软件交付里的"重试 vs 修复"判断逻辑）
- 版数档位（4/8/2）：与 `image-candidate-selection` 的"4 版抽检"口径对齐
- manifest 字段设计：参考构建产物台账（seed/参数/成本/淘汰原因）常见做法
- 外部工具形态参考：`nano-banana-pro`（封装 AI Hive OpenAPI、含价格快照与任务轮询）——
  **本卡刻意不复制其调用实现**，因为团队 55 个包保持零依赖离线可跑
