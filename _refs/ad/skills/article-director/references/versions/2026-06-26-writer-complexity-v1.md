# Writer Complexity v1

日期：2026-06-26

## 背景

writer v3 引入上下文窗口、reader-use-contract、argument-spine 和长逻辑门禁后，单节推理完整性提升，但文章复杂度上升。用户确认新的产品方向：writer 不追求一次写到最终短稿，而是写出可裁剪初稿，后置 editor 负责压缩复杂度。

## 变更

- writer-controller 从固定 2-3 轮决策日志改为默认 1 轮、最多 2 轮。
- reader-use-contract 增加 `reasoning_depth` 与 `compressible_items`，用于区分 light / medium / deep 推理深度。
- writer-section 不再强制每节至少一个长推理段；只在机制、边界、方法、核心争议或关键判断中保留必要推理。
- argument-spine 从“长逻辑写作要求”改为“推理深度与压缩标记”，要求区分 `must_keep` 与 `compressible`。
- argument-flow gate 将“缺长推理段”降级为 warning，继续阻断连续短气口导致的观点串联。
- narrative-smoother 与 style-harmonizer 改为保留必要推理并压缩过长解释。

## 非目标

- 不移除 writer-controller。
- 不改变 workflow 拓扑。
- 不改 `cognitive-style-guide.md`。
- 不降低 article-review 对逻辑跳步的敏感度。

## 验收

- Python 语法检查通过。
- `validate_argument_flow.py` 对 4 段 light-depth 临时稿不再因缺少长推理段失败，只输出 warning。
