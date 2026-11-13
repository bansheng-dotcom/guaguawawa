# s06 修图与图像工程（imaging / edit·probe）方法论
> 蒸馏自: 补充技能/01-当前能力域/python-pillow__Pillow/SKILL.md
>


来源沉淀：`python-pillow__Pillow` + `opencv__opencv` + `danielgatis__rembg`（裸库形态）。

## 一、方法论（什么时候用、核心口径）

「重依赖如实降级，不假装会」。两个动作：
- `edit`：校验图像工程任务单——operations 白名单、source 格式白名单、overwrite ∈ never/suffix。
- `probe`：探测本机 Pillow/OpenCV/rembg 能力，缺库如实 `status=blocked`。

核心红线：**probe 是降级不是门禁**——`ok=true` 恒成立，缺库只反映在 `status=blocked`
与 `next` 提示上；`edit` 校验的是「任务单规格」，与「本机有没有库」解耦。防不可逆覆盖：
`overwrite` 只允许 never/suffix。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`imaging.operations`（resize/crop/rotate/convert/compress/flip/grayscale）、
`imaging.allowed_formats`（jpg/jpeg/png/webp/bmp/tiff）、`imaging.overwrite`（never/suffix）。

**edit 校验规则**：
- `operations` 空，或任一不在白名单 → BLOCKER。
- `source` 扩展名不在 allowed_formats → BLOCKER。
- `overwrite` ∉ {never, suffix} → BLOCKER。

**probe 语义**：`importlib.util.find_spec` 探测 PIL/cv2/rembg；
`status = "ready" if pillow else "blocked"`；`ok=true`、`verdict=PASS` 恒成立。

**输出键**：edit → `operation_count/source`；probe → `status/pillow/opencv/rembg`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/edit.json`：operations=[resize, compress]、source=hero.png、overwrite=never → ok=true。
- `examples/edit_dirty.json`：operations=[explode]（非法）、source=hero.psd（非法格式）、
  overwrite=always（非法）→ ok=false / exit 1。
- `imaging probe` 恒 `ok=true`，缺库时 `status=blocked` 且 `next` 提示如实降级。

## 四、实战踩坑（真拦下来的教训）

- **probe 不要返回 ok=false**：缺 Pillow 是「能力降级」不是「任务单错误」，
  若把 probe 做成门禁，编排器会把「本机没装库」误判成「设计失败」。
- **格式白名单用扩展名**：`source.rsplit(".", 1)[-1].lower()` 取扩展名，空字符串
  （无点）会被 `in allowed_formats` 正确拒绝，别在无点路径上抛 IndexError。
- **overwrite 三态不是布尔**：`never`（拒绝覆盖）、`suffix`（另存带后缀）、`always`
  （危险，不放行）——用集合白名单 `in ("never","suffix")`，别用 `bool(overwrite)`。
- **探测用 find_spec 不用 import**：`import PIL` 若库损坏会抛异常导致进程崩溃，
  `find_spec` 只查「能否找到」，安全。
