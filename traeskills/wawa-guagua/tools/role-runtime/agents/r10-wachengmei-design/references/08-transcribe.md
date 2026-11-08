# s08 转写与字幕素材（transcribe / transcribe·probe）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/user-research/SKILL.md
>


来源沉淀：`SYSTRAN__faster-whisper`（CTranslate2 高效转写，模型权重未内置）。

## 一、方法论（什么时候用、核心口径）

「模型权重未内置，转写能力必须如实降级」。两个动作：
- `transcribe`：校验转写任务单——model_size 白名单、source 非空、segments ≥1（每段
  start/end/text）、text 或 segments 至少其一非空。
- `probe`：探测本机 faster-whisper 能力，缺则如实 `status=blocked`。

核心红线：**转写结果必须落地**——`text` 或 `segments` 至少其一非空，否则「转了白转」；
probe 与 imaging/media 同理，是降级不是门禁。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`transcribe.model_sizes`（tiny/base/small/medium/large-v2/large-v3）、
`transcribe.segment_min`（1）。

**transcribe 校验规则**：
- `model_size` ∉ 白名单 → BLOCKER。
- `source` 空 → BLOCKER。
- `segments` 空，或任一段缺 start/end/text → BLOCKER。
- `text` 空且 `segments` 为空 → BLOCKER（输出完整性）。

**probe 语义**：`importlib.util.find_spec("faster_whisper")`；
`status = "ready" if fw else "blocked"`；`ok=true`、`verdict=PASS` 恒成立。

**输出键**：transcribe → `model_size/segment_count/source`；probe → `status/faster_whisper`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/transcribe.json`：model_size=small、source=episode-01.mp3、text 非空、
  2 段（各 start/end/text）→ ok=true、segment_count=2。
- `examples/transcribe_dirty.json`：model_size=huge（非法）、source 空、text 空、
  segments 空 → ok=false / exit 1。
- `transcribe probe` 恒 `ok=true`，无 faster-whisper 时 `status=blocked`。

## 四、实战踩坑（真拦下来的教训）

- **start/end 用数字不是字符串**：契约里 `_SEGMENT` 的 start/end 是 `_NUM`，
  校验时 `k not in seg` 判「键存在」，但还要看值非空（`str(seg.get(k)).strip()`），
  `0.0` 会被 `str(0.0)` 变成 "0.0" 非空，正确放行——别用 `bool(seg.get(k))`（0.0 会被误判空）。
- **输出完整性是「text 或 segments」的或**：`ok_out = bool(text) or len(segments) > 0`，
  转写可以只给整段 text 不给 segments，也可以只给 segments 不给 text，都算落地。
- **model_size 白名单含 large-v2/v3**：不是只有 tiny~large，别漏掉 large-v2/large-v3，
  否则合法的大模型请求被误拦。
- **probe 恒 ok=true**：模型权重「另行下载」是常态，缺 faster-whisper 只降级
  `status=blocked`，绝不返回 ok=false 假装「转写失败」。
