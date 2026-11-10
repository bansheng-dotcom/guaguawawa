# 模块J · 真实生图与视频提示词（Nano Banana Pro / MiniMax H3）

> 素材来源：Marketplace Skill `nano-banana-pro` v1.0.0（AI Hive OpenAPI 裸接口）
> 与 `h3-prompt-writing` v1.0.0（MiniMax H3 提示词规范）。
> 落地位置：`vendor/aihive/imagegen.py`、`references/h3/{base-en,ref-en}.txt`

过去 R10 的 `imagegen` 只产出**提示词**，不碰真实生成；这两个 Skill 正好补上「最后一步」，
但两者性质不同，融合方式也不同：

| 来源 | 性质 | 融合方式 | 对应技能 |
|---|---|---|---|
| nano-banana-pro | 要 API Key + 网络 + 扣费 | vendor 脚本 + 确定性外壳（探测/预览/守卫/解析） | `aihive` |
| h3-prompt-writing | 纯本地提示词规范 | 结构装配器 + 硬门禁 | `h3prompt` |

---

## 一、S12 `aihive`：真实生图（Nano Banana Pro）

固定模型 `public_model_nano_banana_pro`，**不换模型冒充**。本模块只做外壳，不自己发 HTTP。

```bash
python agent.py aihive probe                      # 探测脚本/依赖/Key，不联网
python agent.py aihive preview --prompt "..." --batch 2   # 只拼命令，脱敏
python agent.py aihive generate --prompt "..." --yes      # 真实调用（会扣费）
python agent.py aihive task --task-id <id> --yes          # 查已有任务
```

### 配置（三选一，优先级从高到低）

| 方式 | 示例 |
|---|---|
| 环境变量 | `AI_HIVE_API_KEY=sk-api-...`（可选 `AI_HIVE_BASE_URL`） |
| 配置文件 | `~/.ai-hive/config.json`：`{"api_key": "sk-api-...", "base_url": "..."}` |
| 上游交互式初始化 | `python vendor/aihive/imagegen.py init --skill-name nano-banana-pro` |

另可用 `AIHIVE_SCRIPT` 指向自备的上游脚本；默认用仓库内 `vendor/aihive/imagegen.py`。

### 安全纪律（比"能生成"更重要）

1. **默认只 preview**：真实调用必须 `--yes`，否则直接 blocked，**不发起任何网络请求**。
2. **缺 Key / 缺 requests → `status=blocked`**，绝不返回假图片、不假装成功。
3. **batch 上限 4**：超过要显式 `--allow-batch`，因为费用按倍增长。
4. **路由默认 COST_FIRST**；价格以脚本运行时查询的 `pricingSnapshot` 与实际扣费为准。
5. **超时不重复提交**：返回 `status=timeout`，保留 `taskId` 用 `aihive task` 继续查，
   避免重复扣费。
6. **Key 永不回显**：`preview` 只输出命令，不含密钥。

### 输出解析

生成成功后回传 `task_id`、落盘的 `files`（png/jpg/webp 路径）、`stdout_tail`。
产物默认在 `~/Downloads/AiHive/`，可用 `--output-dir` 指到项目目录。

---

## 二、S13 `h3prompt`：MiniMax H3 视频提示词

五种模式：`t2va`（文生）、`i2va`（首帧）、`fl2va`（首尾帧）、`l2va`（尾帧）、`ref2va`（全参考）。
字段名、段序、时间戳格式全部按上游规范生成，**不靠模型自由发挥**。

```bash
python agent.py h3prompt build --input spec.json --out prompt.txt
python agent.py h3prompt audit --input spec.json
```

### spec 结构（最小可用）

```json
{
  "mode": "i2va",
  "duration_sec": 6.0,
  "style": "Live-action, cinematic, soft window light",
  "references": [{"label": "Picture 1", "role": "first_frame", "shot": 1}],
  "shots": [
    {"start_sec": 0.0, "text": "the woman from <Picture 1> sits at a desk ..."},
    {"start_sec": 2.5, "text": "the camera cuts to a close-up ..., while she says: (S1) <d>[English] ...</d>"}
  ],
  "on_screen_text": ["营业中"],
  "soundscape": "A clock ticking, paper sliding on wood.",
  "music": "No non-diegetic music; room tone only."
}
```

`ref2va` 改为传 `sections`：`subject_definitions / summary / retention_analysis /
detailed_description / overall_soundscape / non_diegetic_music` 六段。

### 生成结果（base 模式）

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, soft window light. ...
[Shot 2] At 00:02.500, the camera cuts to a close-up ...

overall_soundscape: A clock ticking, paper sliding on wood.

non_diegetic_music: No non-diegetic music; room tone only.
```

### 硬门禁

| 规则 | 维度 |
|---|---|
| `mode ∈ {t2va,i2va,fl2va,l2va,ref2va}` | `h3.mode` |
| 时长 4–15 秒 | `h3.duration` |
| 首镜 `start_sec=0`，后续严格递增且 < duration | `h3.shot.first` / `monotonic` / `range` |
| 镜头文本非空，且不许手写时间戳（由渲染器生成） | `h3.shot.text` |
| `style` / `overall_soundscape` / `non_diegetic_music` 非空 | `h3.style` / `soundscape` / `music` |
| I2VA 需 `Picture 1`；FL2VA 需 `Picture 1`+`Picture 2`；L2VA 需 `Picture 1` | `h3.refs.required` |
| 参考标签格式 `Picture/Video/Audio N`，且 Ref2VA 的 `detailed_description` 必须全部引用 | `h3.refs.format` / `used` |
| 对白必须带语言标签 `<d>[English] ...</d>` 且前面有 `(S1)` 式说话人 | `h3.dialogue.*` |
| 屏幕文字必须用双引号原样出现 | `h3.on_screen_text` |

---

## 三、交给谁用

| 角色 | 用法 |
|---|---|
| **R10 蛙成美** | owner：真实出图、出提示词、九段式/五模式门禁 |
| **R08 蛙建成** | 落地页/详情页用 `aihive` 出的商品图，避免用占位图 |
| **R11 蛙点题** | 视频脚本由 `h3prompt` 装配成可投喂的提示词；口播/字幕保持原语言 |
| **R12 蛙引流** | 投放素材（KV/信息流/短视频）走 R10 的 `aihive` + `h3prompt`，不自己编画面 |

## 四、边界

- 真实出图需 **API Key + 网络 + 额度**；三者缺一即 `blocked`，不写"已生成"。
- 不虚构商品事实：提示词不得编造不存在的功能、材质、认证；屏幕文字交付前人工复核。
- 视频提示词是**给 H3 的输入**，不是成片；成片质量取决于模型与参考素材。
- 上游脚本与规范可能随 Marketplace 版本变化：`vendor/aihive/imagegen.py` 有改动时，
  以 `aihive probe` 与 `h3prompt audit` 回归为准。
