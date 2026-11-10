---
name: r10-wachengmei-design
description: 视觉设计官角色技能。本地支持确定性校验和媒体文件存在性/MIME/尺寸检查；图像生成、转码、转写及外部发布未接入时属于 simulated 或 blocked。
---

# R10 蛙成美 · 视觉设计官
> 蒸馏自: 补充技能/01-当前能力域/mae616__design-skills/SKILL.md
>


把能力全景里的 **8 个能力域各自做成一个独立技能模块**（`skills/s01..s08`），
由一个薄调度器 `agent.py` 统一分发。每个技能都是纯标准库、独立可测的单元，
把「视觉设计官的提示词/工作流」转成**确定性校验 + 门禁**，返回可 JSON 化的结果。
对 Pillow/OpenCV/rembg、ffmpeg、faster-whisper 等重依赖，一律**门禁探测 + 如实降级**
（本机缺库则 `status=blocked`，不假装会）。

## Quick Start

```bash
python agent.py local-media-check --input ./asset.png # 本地媒体文件存在性/MIME/尺寸检查
python agent.py demo                          # 生成示例工件(prompt/logo/vi/screen)

python agent.py imagegen prompt --input examples/prompt.json   # S01 生图提示词包
python agent.py imagegen style --input examples/style.json     # S01 风格探索
python agent.py logo logo --input examples/logo.json           # S02 Logo 设计包
python agent.py logo favicon --input examples/favicon.json     # S02 图标变体
python agent.py uiux screen --input examples/screen.json       # S03 屏幕设计
python agent.py uiux ux --input examples/ux.json               # S03 可用性评估
python agent.py brand vi --input examples/vi.json              # S04 品牌视觉身份
python agent.py brand token --input examples/token.json        # S04 设计令牌
python agent.py motion motion --input examples/motion.json     # S05 动效规格
python agent.py motion prototype --input examples/prototype.json # S05 交互原型
python agent.py imaging edit --input examples/edit.json        # S06 图像工程任务单
python agent.py imaging probe                                 # S06 重依赖探测
python agent.py media media --input examples/media.json        # S07 媒体处理任务单
python agent.py media probe                                   # S07 ffmpeg 探测
python agent.py transcribe transcribe --input examples/transcribe.json  # S08 转写任务单
python agent.py transcribe probe                              # S08 faster-whisper 探测
python agent.py render poster --input examples/poster.json    # S09 宣传图契约 → SVG
python agent.py render theme --name tech-blue                 # S09 主题色板
python agent.py designsys list --category devtools            # S11 设计系统库：按分类查
python agent.py designsys recommend --project ai              # S11 按项目类型推荐 3~5 套
python agent.py designsys show --brand linear.app             # S11 看色板/字体/组件
python agent.py designsys apply --brand linear.app --out DESIGNS/linear  # S11 落盘
python agent.py designsys audit --brand claude                # S11 九段式门禁
python agent.py aihive probe                                  # S12 真实生图：探测 Key/依赖
python agent.py aihive preview --prompt "高级商业摄影风格" --batch 2   # S12 只拼命令
python agent.py aihive generate --prompt "..." --yes          # S12 真实调用（会扣费）
python agent.py h3prompt build --input h3_spec.json --out prompt.txt  # S13 H3 提示词
python agent.py h3prompt audit --input h3_spec.json           # S13 提示词门禁

python agent.py contract list                               # T6 8 技能机器可读契约
python agent.py contract validate --skill logo --action logo --output r.json
python agent.py review --result r.json --skill logo --action logo   # T7 对抗评审
python agent.py case list                                    # T8 案例库
python agent.py case validate --case logo-rebrand
python agent.py harness logo --input examples/logo.json      # 确定性验证器(硬门禁)
python agent.py harness verify --logo examples/logo.json --vi examples/vi.json
python agent.py run --task <task_id>                        # 协作入口
```

## 能力域 → 技能模块

| # | 能力域 | 子命令 | 真实执行的动作 | 整合自 |
|---|---|---|---|---|
| S01 | AI生图插画 | `imagegen prompt/style` | media/style 枚举 + 正负向提示词 + 风格锁自洽 | mae616 design-skills + nlr-2007 illustrations |
| S02 | Logo图标VI | `logo logo/favicon` | mark_type 白名单 + 尺寸测试阶梯 + 单色/16px + 对比度 | kaankiziltug logo-design + jgerton brand-toolkit |
| S03 | 产品UI/UX | `uiux screen/ux` | 目标/分区≥3/组件带状态/五态覆盖/a11y 三底线 | mae616 ui-designer/a11y/usability |
| S04 | 品牌VI令牌 | `brand vi/token` | 3 方向 Stylescape + 反陈词滥调 + 三类 token | jgerton brand-toolkit + mae616 token |
| S05 | 交互原型动效 | `motion motion/prototype` | 人格白名单 + 时长区间 + 加减速 + 减少动效 | LottieFiles motion-design + mae616 |
| S06 | 修图图像工程 | `imaging edit/probe` | 操作/格式白名单 + 防覆盖 + Pillow/cv2/rembg 探测 | Pillow + opencv + rembg |
| S07 | 视频音频处理 | `media media/probe` | 容器/音频白名单 + 缩放偶数 + ffmpeg 探测 | FFmpeg |
| S08 | 转写字幕 | `transcribe transcribe/probe` | 模型尺寸白名单 + 段列表 + faster-whisper 探测 | SYSTRAN faster-whisper |
| S09 | 数据视觉营销物料 | `render poster/theme` | 宣传图契约 → 确定性 SVG（主题色板 + 参数化几何体） | 生成层（对齐第九节「LLM 生成，Python 关笼子」） |
| S11 | 品牌设计系统库 | `designsys list/recommend/show/apply/audit` | 31 套品牌 DESIGN.md：检索 → 按项目类型推荐 → 落盘 DESIGN.md + design_tokens.json → 九段式门禁 | awesome-design-md（Google Stitch DESIGN.md 格式） |
| S12 | 真实生图（AI Hive） | `aihive probe/preview/generate/task` | Nano Banana Pro 裸接口外壳：探测 → 拼命令 → 扣费前确认 → 真实调用 → 解析 taskId/落盘文件 | Marketplace Skill nano-banana-pro |
| S13 | H3 视频提示词 | `h3prompt build/audit` | T2VA/I2VA/FL2VA/L2VA/Ref2VA 结构装配 + 时长/时间戳/参考标签/对白/屏幕文字硬门禁 | Marketplace Skill h3-prompt-writing |

## 协作契约

- **inputs**：`brand_brief`（品牌简报）、`content`（待加工内容）。
- **outputs**：`visual_assets`（视觉资产）、`vi`（视觉身份）。
- 结果以一行 `__AGENT_RESULT__ {json}` 输出，供编排器以子进程方式消费。
- 协作入口 `run --task` 按**意图关键词 → 技能+动作**确定性路由（见 `_INTENT_ROUTES`），
  产物 `{skill}.json` 与 `design_report.md` 写回 `workspace/artifacts/{task_id}/`。

## 关键纪律（保留自 reference，校验环不丢）

1. 枚举白名单外置：media/style/mark_type/personality/model_size/操作/格式 全部从
   `experience/thresholds.json` 读，改口径不改代码（T9）。
2. 重依赖如实降级：Pillow/OpenCV/rembg、ffmpeg、faster-whisper 一律走 `probe`
   探测，缺库返回 `status=blocked`，绝不 `ok=false` 假装执行（探测非门禁）。
3. 视觉质量可度量：对比度用 WCAG 公式算（`_common.contrast`），logo 主/次色 ≥3.0，
   UI a11y 三底线（键盘可达/焦点可见/对比度达标）任一缺即 FAIL。
4. 反陈词滥调：品牌 VI narrative 出现「因为蓝色代表信任」「看起来专业」「显得高端」即 FAIL。
5. 防不可逆覆盖：imaging/media 的 `overwrite` 只允许 never/suffix，杜绝覆盖源文件。
6. 吐多少由契约锁死：`contract validate` 用 JSON Schema 校验每次产出，不符即 FAIL。
7. 空泛/占位拦截：`review` 点名「待定/TODO/占位」无具体产物 → FAIL。
8. 不越界：出现「高可用/灾备/CI-CD/GPU 集群」且未声明 handoff → scope_creep FAIL。

## 边界

R10 产出视觉资产与设计规格；真实前端代码实现交 R09；数据口径与可视化交 R06；
整篇文案与品牌语调定稿交 R11；模型权重、素材授权、字体/肖像权与 FFmpeg 许可组合
需单独确认；不替 R04 做独立验收。

「生成层」纪律（S09 render）：营销物料版式由确定性 SVG 渲染器产出（主题色板 + 参数化
几何体），**不假装会画照片级产品图**——那交给 `imagegen prompt` 产提示词、由真实生图
模型生成。两条路各司其职：`render` 出「版式正确但不真实」的矢量稿，`imagegen prompt`
出「能直投模型」的提示词。

「真实生成」纪律（S12 aihive / S13 h3prompt）：
- `aihive` 真实出图需要 **API Key + 网络 + 额度**，缺一即 `status=blocked`；`generate` 必须
  `--yes`，batch > 4 需 `--allow-batch`；超时只保留 `taskId`，不重复提交（避免重复扣费）。
- `h3prompt` 产出的是**给 MiniMax H3 的提示词**，不是成片；时长/时间戳/参考标签/对白/
  屏幕文字全部走确定性门禁，失败即 FAIL，不允许"差不多"。
- 两者都不得虚构商品事实（功能、材质、认证、价格）；屏幕文字交付前必须人工复核。

## 详细参考（11 个模块）

- [模块A AI 生图与插画](references/01-imagegen.md)
- [模块B Logo 与图标](references/02-logo.md)
- [模块C 产品 UI/UX](references/03-uiux.md)
- [模块D 品牌 VI 与设计令牌](references/04-brand-token.md)
- [模块E 交互原型与动效](references/05-motion.md)
- [模块F 修图与图像工程](references/06-imaging.md)
- [模块I 品牌设计系统库（31 套 DESIGN.md）](references/09-design-systems.md)
- [模块J 真实生图与视频提示词（Nano Banana Pro / MiniMax H3）](references/10-ai-generation.md)
- [模块G 视频与音频处理](references/07-media.md)
- [模块H 转写与字幕](references/08-transcribe.md)
