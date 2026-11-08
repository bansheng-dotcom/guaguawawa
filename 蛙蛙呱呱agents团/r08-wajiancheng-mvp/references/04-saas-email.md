# s04 SaaS 与邮件脚手架（saas / email）方法论
> 蒸馏自: 补充技能/01-当前能力域/duncan-buildroom__freeskills/email-writer/SKILL.md
>


来源沉淀：`makerskills`（saas-starter / email-scaffold）。

## 一、方法论（什么时候用、核心口径）

「把多页 SaaS 或邮件流程快速搭出可演示骨架」。两个动作：
- `saas`：校验 SaaS 脚手架——pages ≥2、routes 每项 path+page、auth 合法、
  入口点明确。
- `email`：校验邮件脚手架——templates 每项 name/subject/body、preview_text 非空、
  unsubscribe_link 非空。

核心红线（R08 实现型身份）：**骨架止于可演示**。鉴权只做形态选择（session/jwt/oauth/
email-link/none），不实现 token 轮换、限流、防重放等生产安全工程——那是 R09/R20 的边界。
邮件侧的唯一硬合规线：**退订链接必须存在**（无退订 = 骚扰邮件，直接 BLOCKER）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

页面下限、鉴权类型全部外置：`saas.pages_min`、`saas.auth_types`（验证链：
`experience/thresholds.json → _common.load_thresholds() → s04_saas._validate_saas/
_validate_email`）。

**saas 校验规则**：
- `pages` 条数 < 2 → `saas.pages` BLOCKER（单页不算 SaaS 骨架）。
- `routes` 为空 → `saas.routes` BLOCKER；每项缺 path / page → `saas.route.{k}` BLOCKER。
- `auth` 不在 5 类（session/jwt/oauth/email-link/none）→ `saas.auth` BLOCKER。
- `entry_point` 为空 → `saas.entry_point` BLOCKER。

**email 校验规则**：
- `templates` 为空 → `email.templates` BLOCKER；每项缺 name / subject / body →
  `email.template.{k}` BLOCKER。
- `preview_text` 为空 → `email.preview_text` BLOCKER。
- `unsubscribe_link` 为空 → `email.unsubscribe_link` BLOCKER（合规底线）。

**输出键**：saas → `page_count / verdict / next`；email → `template_count / verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/saas.json`：pages 2 条、routes 2 条 path+page 齐、auth=none、
  entry_point=app.py → ok=true、page_count=2、verdict=PASS。
- `examples/email.json`：welcome 模板 + preview_text + unsubscribe_link →
  ok=true、template_count=1、verdict=PASS。
- 脏夹具 `saas_dirty.json`：pages 仅 1 条 → ok=false / exit 1。
- 脏夹具 `email_dirty.json`：缺 unsubscribe_link → ok=false / exit 1（合规线拦下）。

## 四、实战踩坑（真拦下来的教训）

- **routes 与 pages 的计数是两套口径**：pages 查条数下限（≥2），routes 查每项结构
  （path+page 非空）。曾出现 pages 3 条但 routes=[] 的产出——页面无法被访问，等价于
  没有页面；两个检查必须分开，缺一不可。
- **auth 大小写归一**：`"OAuth"` 必须先 lower 再进白名单，否则合法值被误拦。
  与 s01 的 risk_type、s02 的 stack 是同一条教训（r06 踩过）。
- **email 的 subject 与 body 缺一不可**：只有 name 的模板是「未完成的草稿」，
  门禁必须拦——这是「邮件脚手架」与「邮件清单」的分界。
- **preview_text 不是可选**：收件箱里 preview 决定打开率，缺失意味着流程未完成；
  它与 unsubscribe_link 一起构成 email 的完整性底线，二者任一为空都是 BLOCKER。
