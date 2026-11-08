# s07 多平台适配（adapt / publish）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`bzwh321__article-director-public`（多平台改写纪律）+ R11「对外发布需授权」红线。

## 一、方法论（什么时候用、核心口径）

同一篇内容发到不同平台，不能复制粘贴——各平台的语气、长度、标签规则都不同。
两个动作：
- `adapt`：校验平台改写——platform 在白名单，title/length_limit/tone_shift/hashtags
  齐备（hashtags 为列表）。
- `publish`：校验发布清单——items 逐条含 platform/url/status/authorized，
  且 **authorized 必须为 true**（对外发布需授权，机器判据）。

核心红线：**写和发分开**。内容可以写、可以改写，但能不能发、发到哪、由谁拍板，
必须逐条显式声明 authorized=true；任一条未授权即 FAIL。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`platform.platforms`（8 个平台）、`platform.adapt_required`（5 字段）、
`platform.publish_required`（platform/url/status/authorized）。

**adapt 校验规则**：
- platform 不在 8 平台白名单 → BLOCKER（短路）。
- title/length_limit/tone_shift 任一空 → BLOCKER。
- hashtags 非列表 → BLOCKER。

**publish 校验规则**：
- items 非列表或为空 → BLOCKER（item_count=0）。
- 任一条目缺 platform/url/status/authorized → BLOCKER。
- 任一条目 `authorized is not True` → BLOCKER（对外发布需授权）。

**输出键**：adapt → `platform`；publish → `item_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/adapt.json`：platform=小红书、hashtags 3 条、length_limit/tone_shift 齐备
  → ok=true。
- `examples/publish.json`：2 条（微信公众号/小红书），authorized 均为 true
  → ok=true、item_count=2。
- 脏夹具 `adapt_dirty.json`：platform=论坛（不在白名单）→ ok=false / exit 1。
- 脏夹具 `publish_dirty.json`：authorized=false → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **authorized 用 `is not True` 判**：不能写 `if not authorized`——那会把「缺失」和
  「false」都拦（其实都该拦），但 `is not True` 更精确：只有字面 true 才放行，
  字符串 "true"、1、缺失统统拦，堵死「用字符串糊弄授权」的漏洞。
- **hashtags 是列表**：小红书/抖音的标签天然是多值，判 `isinstance(list)`，
  空列表也拦（空标签等于没做平台适配）。
- **platform 白名单短路**：平台非法直接返回，别继续判字段，与 brief/hook 一致。
