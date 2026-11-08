# s07 视频与音频处理（media / media·probe）方法论
> 蒸馏自: 补充技能/01-当前能力域/danielgatis__rembg/SKILL.md
>


来源沉淀：`FFmpeg__FFmpeg`（libavcodec/libavfilter 工具箱，外部二进制形态）。

## 一、方法论（什么时候用、核心口径）

「ffmpeg 是外部二进制，命令规格与执行能力分开校验」。两个动作：
- `media`：校验媒体处理任务单——operations 白名单、target.container/audio 白名单、
  缩放偶数规则（H.264 硬要求）、overwrite ∈ never/suffix。
- `probe`：探测本机 ffmpeg/ffprobe，缺则如实 `status=blocked`。

核心红线：**缩放尺寸必须是偶数**（H.264 编码要求宽高为偶数）；`probe` 与 imaging 同理，
是降级不是门禁；防覆盖：`overwrite` 只允许 never/suffix。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`media.operations`（transcode/cut/concat/extract_audio/fade/scale/add_watermark）、
`media.container_formats`（mp4/webm/mov/mkv）、`media.audio_formats`（mp3/aac/wav/ogg/m4a）。

**media 校验规则**：
- `operations` 空或任一非法 → BLOCKER。
- `source` 空 → BLOCKER。
- `target.container` ∉ 白名单 → BLOCKER；`target.audio` 非空且 ∉ 白名单 → BLOCKER。
- `scale.width/height` 非整数或任一为奇数 → BLOCKER（无 scale 则跳过）。
- `overwrite` ∉ {never, suffix} → BLOCKER。

**probe 语义**：`shutil.which("ffmpeg"/"ffprobe")`；`status = "ready" if ffmpeg else "blocked"`；
`ok=true`、`verdict=PASS` 恒成立。

**输出键**：media → `operation_count/source`；probe → `status/ffmpeg/ffprobe`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/media.json`：operations=[transcode, scale]、source=input.mov、
  container=mp4、audio=aac、scale 1920×1080（偶数）、overwrite=suffix → ok=true。
- `examples/media_dirty.json`：operations=[explode]、source 空、container=avi（非法）、
  audio=flac（非法）、scale 1921×1079（奇数）、overwrite=always → ok=false / exit 1。
- `media probe` 恒 `ok=true`，无 ffmpeg 时 `status=blocked`。

## 四、实战踩坑（真拦下来的教训）

- **偶数规则是 `% 2 == 0`**：1921 是奇数、1079 是奇数，两者都要 `w % 2 == 0 and h % 2 == 0`；
  别只判「是整数」，奇数整数照样会让 H.264 编码失败。
- **audio 允许为空**：纯视频任务可能不指定 audio，`ok_a = not audio or audio in whitelist`
  ——空是合法的，但给了就必须在白名单内。
- **scale 是可选的**：没有 scale 字段或 scale 为空 dict 时跳过偶数检查，
  `scale_ok = True` 默认放行，别在缺 scale 时报「尺寸非法」。
- **probe 用 shutil.which**：Windows 下 ffmpeg 可能是 ffmpeg.exe，`which` 能正确找到；
  直接 `subprocess.run(["ffmpeg","-version"])` 会因找不到二进制抛 FileNotFoundError。
