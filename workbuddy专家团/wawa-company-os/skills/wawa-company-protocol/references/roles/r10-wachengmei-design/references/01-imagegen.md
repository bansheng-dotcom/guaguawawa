# s01 AI 生图与插画（imagegen / prompt·style·catalog）方法论
> 蒸馏自: 补充技能/01-当前能力域/nlr-2007__illustrations/SKILL.md
>
> 2026-11-11 重构：风格从「8 项闭合数组」升级为「10 core + 47 extended 注册表」（v1.1，共 57 条），
> 载体从 5 项扩到 12 项，新增 `text_policy` 与 `catalog`。


来源沉淀：`mae616__design-skills`（creative-coder）+ `nlr-2007__illustrations`（illustration/diagram/hybrid 三技能的 style locks 纪律）。

## 一、方法论（什么时候用、核心口径）

「把生图提示词从口头模板变成可审计的规格包」。三个动作：
- `prompt`：校验生图提示词包——载体合法、风格可解析、正/负向提示词均非空、
  style_locks ≥1 且不被负向提示词自我推翻、text_policy 合法、留白是否被正向声明。
- `style`：校验风格探索——风格可解析、composition ≥1 且每项非空字符串、
  palette 为 hex 色列表。
- `catalog`：生成能力目录——12 载体 × 57 风格的矩阵 + `catalog.html`，
  标出每条风格是 core/extended、已验证/已知失败/未跑基准。

核心红线（R10 视觉身份）：**提示词是资产不是草稿**。负向提示词若命中风格锁
（锁原文或其否定式「不X/无X」），说明自相矛盾，直接 BLOCKER。

## 二、可执行口径（与实现逐字对齐）

枚举分三处外置（验证链：`experience/*.json → _common.load_thresholds()/load_registry() → s01_imagegen`）：

| 出处 | 内容 | 语义 |
|---|---|---|
| `imagegen.output_media` | 12 项载体 | image / illustration / icon / poster / banner / packaging / mockup / ui-screen / infographic / pattern / comic / character-sheet |
| `imagegen.style_types` | 10 项 core 风格 | flat / line-art / gradient / duotone / watercolor / pixel / isometric / 3d / photo / collage |
| `experience/style_registry.json` | 57 条风格记录 | 10 core + 47 extended；每条带 aliases、render_style、recipe、text_policy、failure_modes、baseline |

另有 `output_media_extended`（social-card / thumbnail / sticker / sprite / dieline / storyboard，
命中记 WARN 不拦）、`text_policy_by_media`（poster/banner/infographic/ui-screen 等默认
`overlay-later`）、`image_sizes`（1:1→square_hd、4:3→landscape_4_3、3:4→portrait_4_3、16:9→landscape_16_9）。

`hard_limits`（v1.1 新增，8 条）记录**任何风格都绕不过**的结构限制（精确字体、CJK 字标、
真实商标、确定数字、角色一致性、多格一致、可编辑矢量、印刷规格），每条带兜底做法；
文字型载体（infographic / ui-screen / comic / character-sheet / packaging / mockup /
social-card / storyboard）在 `text_policy=none` 时给 `hard_limit=exact-typography` 的 WARN。
注册表另有 `sources` 字段记录风格与限制的外部依据。

**风格解析规则（三值门禁）**：
1. `style` 在 `style_types` 里 → core，`sev=OK`。
2. 不在 core 但命中注册表（id / 去前缀 id / 任一 alias，大小写不敏感）→ 解析出
   `render_style`（必为 core 之一），`sev=WARN`，放行并带出该风格的 `failure_modes`。
3. 两处都没有 → BLOCKER。
4. 注册表里 `render_style` 若不在 core 中 → 视为解析失败（防止注册表写错绕开门禁）。

**prompt 校验规则**：
- `media` 不在 `output_media` → BLOCKER 且短路返回（坏输入不再继续断言）。
- `style` 按上面三条解析；解析失败 → BLOCKER。
- `prompt` / `negative_prompt` 空 → BLOCKER。
- `style_locks` 空或非数组 → BLOCKER。
- 锁自洽：任一 lock 满足 `lock in negative` 或 `不{lock} in negative` 或 `无{lock} in negative` → BLOCKER。
- `text_policy` 不在枚举（none / overlay-later / render-attempt）→ BLOCKER；
  缺省取该风格的 `text_policy_default`，再缺省取 `none`。
- 留白未正向声明 → WARN（不拦）：`text_policy=none` 且 prompt 含留白意图词
  （space for / empty space / 留白 / 标题位…）但没有任何空场声明
  （flat solid / pure color field / no lettering / do not invent…）。

**style 校验规则**：
- 风格解析同 prompt；core 记 OK，extended 记 WARN。
- `composition` ≥1 且每项非空；`palette` 每项 `is_hex_color`。

**输出键**：prompt → `media/style/resolved_style/style_level/text_policy/lock_count/warning_count/grade`；
style → `style/resolved_style/style_level/comp_count/palette`；catalog → `styles_total/core/extended/verified/failed/unverified/media/combinations/artifacts`。

`verdict` 仍只有 PASS/FAIL（契约枚举不变）；三值语义放在 `grade`：
`PASS` / `PASS_WITH_WARNING`（有 WARN 无 BLOCKER）/ `FAIL`。

## 三、为什么是「解析 + 降级」而不是「把 43 种都塞进白名单」

- 43 项全进 `style_types`，core 语义会被冲淡：任何新名字都成了「硬校验可交付」，
  门禁变成投票器而不是闸门。
- 加一个风格要同步数组 + `run_tests.py` 断言 + 4 份镜像，成本高到没人愿意加
  （历史上 `len(style_types) == 8` 就是一道明文的扩展禁令）。
- 现状：新增风格 = 在 `style_registry.json` 加一条 + 跑基准，**不碰任何 .py**。

## 四、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/prompt.json`：media=illustration、style=line-art、正负向非空、3 条 style_locks
  且负向不含锁 → ok=true、lock_count=3、verdict=PASS。
- `examples/style.json`：style=flat、composition 3 项、palette 3 个 hex → ok=true、verdict=PASS。
- 脏夹具 `prompt_dirty.json`：prompt/negative/style_locks 全空 → ok=false / exit 1。
- 脏夹具 `style_dirty.json`：composition=[] + palette=["red"]（非法 hex）→ ok=false / exit 1。
- 扩展风格：`style=risograph` → `resolved_style=duotone`、grade=PASS_WITH_WARNING、
  带出 2 条已知失败模式；`style=赛博朋克`（中文别名）→ `gradient`。
- 未登记风格：`style=vaporwave` → ok=false（注册表里没有，不猜）。
- experimental（跑挂降级）：允许出现在 `prompt` 文本层，出现在 `style` 字段 → BLOCKER。
- 准入判据 `_admission()`：`seeds≥3 且 pass≥2` → core；`seeds<3` → extended；
  `seeds≥3 且 pass<2` → experimental；`seeds=0` → extended（软放行、未验证）。
- `admit`：只报不改，当前报出 10 条 core 证据不足（都是 seeds=1，未达 3 seed）。
- `catalog` 四态：`verified`（客观检查 + ≥2 seed）/ `sampled`（有样张未达门槛）/
  `failed`（0 过）/ `unverified`（未跑）；当前 0 / 15 / 1 / 27。
- `pack`：生成 57 风格 × 3 seed = **171 条**可直接喂渲染器的提示词包
  （`workspace/pack/prompts/*.json` + `MANIFEST.json`），不含生图调用。
- `score --dir`：对已有图做客观评分——占位图检测（灰度标准差 <8）、`palette_c90`
  （90% 像素落在多少 8 阶色桶）、尺寸/画幅；输出 `score_report.json`。
  在 2026-11-11 的 10 张真实样张上跑：10/10 识别为真实图、0 张占位。
- 载体分级：`media=social-card`（extended）→ WARN 放行；`media=video` → BLOCKER。
- `generate --dry-run`：不调用任何引擎，只输出「最终会发出去的 prompt / 负向 / 尺寸 /
  文字策略 / 已知失败模式」，落盘到 `workspace/dryrun/`。
  无引擎时这是唯一诚实的产出——不是占位图，是待确认的规格。
  实测：`style=brutalist`（1920×1080）→ `flat / landscape_16_9 / overlay-later`，
  366 ms 返回，`engine_used=none (dry-run)`。
- `compose`：确定性出提示词——只读注册表，不调 LLM、不调引擎。
  实测 `3d-food + packaging + 1600×1200` → `landscape_4_3`、`overlay-later`，
  输出 `workspace/prompts/<style>.md` 与 `.json`，Prompt/Negative 两段可直接复制。
  这是「没有接生图软件、只想拿提示词」时该走的主路径。
  **必须给业务主体**（`subject` / `need` / `concept` 之一）：缺了直接 FAIL 并给示例，
  不再静默产出「有风格没内容」的空模板。支持 `--need "一句话需求"`，
  以及 `scene` / `props` / `mood` / `must_include` / `avoid` 业务字段按序拼入。
  未指定 `style` 时按 `flat` 出，并在结果里标 `style_defaulted=true`。
- `engines`：列出 8 个可接引擎与各自的接入开关（`COMFYUI_URL` / `SD_WEBUI_URL` / `FOOOCUS_URL` / `SILICONFLOW_API_KEY` / `OPENAI_API_KEY` / `DASHSCOPE_API_KEY` / `ZHIPUAI_API_KEY` / `MIDJOURNEY_API_KEY`），接任意一个后 `generate` 自动切真实出图。
- **默认走提示词路线**：`generate` 在无引擎时**自动降级为 `compose`**（返回 `degraded=true`
  与可粘贴 prompt），不再让人在菜单里选、也不落占位图。
- **设计参考库（31 套）**：`references/design-library/` 存了 Linear / Apple / Notion / Stripe /
  Framer 等真实产品的 DESIGN.md，`imagegen refs` 可检索（名称/关键词/配色/氛围/字体）。
  `compose --ref linear` 会把该设计系统的配色与氛围注入 prompt。
  来源：`awesome-design-md`（VoltAgent 整理，Google Stitch DESIGN.md 格式）。
  R10 **不会自己上网逛设计站**——参考库是可离线检索、可 `--rebuild` 重建的固定素材，
  新增设计只要把 .md 丢进 `design-library/`。
- **灵感检索（39 站）**：`imagegen inspire --need "..." [--category packaging] [--fetch]`
  返回站点清单、检索词、该看什么、版权档位（free-asset / inspiration-only /
  licensed-only）与 `prompt_seed`。`--fetch` 只抓公开 HTML 的 title/description/og:image，
  先查 robots.txt；登录墙站点只给链接。版权硬规则：只借鉴配色/排版/氛围，
  禁止复刻构图、图形、角色、文案。详见 `docs/R10-灵感检索与版权.md`。
- **兜底气质分档**：`_expert_fallback` 的收尾按四档给不同 tail 与 lighting
  （摄影 / 3D 渲染 / 海报 / 插画），负向分三层（风格专属 + 通用质量 + 文字）；
  `text_policy=render-attempt` 时**不加**文字负向（原先写死 `text, logos` 会和
  「允许渲染文字」自相矛盾），`overlay-later` 时正向补一句留白。
  `edit --style` 也可指定风格，不再写死 `commercial-photography`。
- `imagegen` 不带 action 时仍输出 5 条路径（TTY 可交互，非 TTY 返回 `route_menu` JSON），
  但推荐项固定为「1. 只要提示词」。
- **mock 引擎一律拒绝**：`MockFallbackEngine` 带 `is_mock=True`；`generate` / `edit` /
  `--explore` 三条产出路径一旦只选到它，直接返回 `blocked=True, verdict=FAIL`，
  不写任何产物。实测：`edit` 不留遮罩文件（0 个新文件）、`explore` 返回空列表、
  `generate` 直接调管线也是 `0 new files`。

## 五、实战踩坑（真拦下来的教训）

- **media 非法要短路**：media 一旦不在白名单，后面的 style/prompt 校验无意义，
  直接 return FAIL，避免对坏输入继续做无谓断言。
- **锁自洽是核心，别只查「存在」**：`不{lock}` 与 `无{lock}` 的否定式也要查，
  否则「负向写『非黑白黄三色』、锁写『#111111/#FFC21A 双色』」这种隐性矛盾会漏。
- **palette 每个都要 `is_hex_color`**：`#red`、`red`、`"blue"` 都不是合法 hex，
  别用「以 # 开头」的弱判断。
- **负向提示词 ≥1 是门禁**：生图质量靠负向约束兜底，空负向提示词直接 BLOCKER，
  不是「建议项」。
- **负向写 `text` 挡不住文字（实测 4/4 失败）**：`Duobraid`（05）、`Pyunttentt Oy eafingır`（03）、
  伪中文（06）、`Duoto`（A6）都出现在负向含 text/watermark 的提示词里。
  所以留白必须**正向声明成纯色空场**，这条落成 `imagegen.negative_space` 的 WARN。
- **pixel 在 core 里也不等于能兑现**：07 实测 90% 像素落在 893 个色桶，
  硬边与限定色板均未达成；注册表把 `style.pixel` 的 baseline 记为 `pass=0` 并登记失败模式，
  不因为「它在白名单里」就假装通过。
