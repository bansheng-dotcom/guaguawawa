---
name: meitu-audio-generate
description: Generate background music or songs via the meitu-local MCP `audio-music-generate` (instrumental BGM 30-120s) and `audio-song-generate` (songs with vocals or strong rhythm) tools. Use when the user explicitly asks to generate pure instrumental/BGM or a full song; for media/video/dubbing background or soundtracks.
---

# 配乐 / 歌曲生成（audio-music-generate / audio-song-generate）

生成纯音乐 BGM 或带人声完整歌曲，服务于视频/口播/直播背景、氛围与情绪渲染。

## 工具（`meitu-local` MCP Server）

- **`audio-music-generate`** — 生成无歌词纯音乐/BGM（30–120 秒）。
- **`audio-song-generate`** — 生成带人声的完整歌曲，或强节奏/全编曲纯音乐成品。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查；绝不索取 AK/SK。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。
- 仅在用户明确要求生成纯音乐/BGM 或歌曲/音频成品时触发；普通音乐讨论不触发。

## Prompt 维度（把空泛词改写为可执行声音 brief）

按序给出：**用途 → 风格/类型 → 情绪 → BPM/速度 → 主要乐器/声音元素 → 音色 → 质感 → 编配密度 → 空间感 → 时长 → 是否人声/歌词语言**。

- 纯 BGM（视频/口播/直播背景）：`audio-music-generate`，无歌词纯音乐。
- 歌曲：`audio-song-generate`，带人声或强节奏全编曲；提供或确认风格与歌词参数。

### 五大扩展维度（禁止只写笼统流派名）

- **音色（Timbre）**：明亮/暗色、温暖/冷感、粗粝/丝滑、颗粒感/空气感、模拟味/数字感、木质/金属/玻璃/合成器质地。例：`温暖偏模拟味的合成器音色`。
- **质感（Texture）**：干/湿、紧/松、硬/软、厚/薄、压缩感强/动态保留多、平滑/毛边/失真感。例：`鼓组干而紧，瞬态明确`。
- **编配（Arrangement）**：稀疏/中等/饱满、主旋律突出/氛围优先/节奏优先、低频占比轻/中/重、是否要 build-up/drop/breakdown。例：`前半段稀疏，后半段逐步加层，不要堆满编制`。
- **空间（Space）**：贴脸/近景/中景/远景、房间感/大厅感/影院感/梦境感、立体声窄/中等/开阔、残响短/中/长。例：`主体靠前，背景拉开空间纵深，主旋律保持居中聚焦`。
- **人声（Vocal，仅歌曲/hook/jingle 时写）**：贴耳/飘逸/梦幻/冷淡/颗粒感、清亮/沙哑/少年感/成熟感、独唱/和声铺底/合唱感。例：`女声贴耳、轻梦幻，副歌轻薄和声，不做大合唱`。

### 空泛词改写映射

| 用户说法 | 改写方向 |
|---|---|
| “高级感” | 少量元素、温暖模拟味、动态保留、空间开阔但克制 |
| “电影感” | 低频稳、层次递进、空间纵深、情绪弧线明确 |
| “网感” | 节奏点更鲜明、记忆点前置、音色直接、hook 更快 |
| “治愈” | 温暖、轻柔、留白多、中慢速、旋律平顺 |
| “炸” | 低频更重、瞬态更强、能量快速抬升（仍写清粗粝/电子/工业） |

## 工作流

1. 确认用途与风格/情绪/时长，是否要人声歌词。
2. 选工具，按上述维度组装可执行声音 brief，调用。
3. 交付音频 URL/文件，说明参数与规格。

## 输出规范

- 标注风格、情绪、BPM、音色/质感/编配/空间要点、是否人声/语种及时长。
- 禁止：写 DAW 工程参数、dB/EQ 数值、版权/商用安全承诺；不自动打开/购买任何音乐服务。画面与视频剪辑指令不写入音乐 prompt。