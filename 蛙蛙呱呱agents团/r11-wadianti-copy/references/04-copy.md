# s04 文案与长文（article / script）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`bzwh321__article-director-public` 的 harness/article_validator.py
（终稿校验：错误累积、不 raise、区分 hard error 与 warning）。

## 一、方法论（什么时候用、核心口径）

这是 R11 最核心的「成品门禁」——一篇内容能不能进发布授权，由这里判定。
两个动作：
- `article`：校验文案终稿——正文字数下限、AI 味禁词（中文+英文）、结论先行
  （摘要段含具体数字）、必要结构（延伸阅读/后续阅读/延伸话题）。
- `script`：校验脚本类（对话/口播）——字数门槛取 article 的 0.5 倍，禁词同源。

核心红线：**AI 味套话是隐形减分项**。空转的起承转合（总而言之、综上所述、
值得注意的是、delve、tapestry 等）只稀释信息密度，命中即 BLOCKER；
字数不足、无结论先行、无延伸结构，任一即 BLOCKER。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`copy.min_chars`（800）、`copy.min_chars_longform`（2000）、
`copy.forbidden_zh`（26 个中文套话）、`copy.forbidden_en`（7 个英文词）、
`copy.soft_connectives`（首先/其次/因此等软连接，不拦截）、
`copy.required_sections`（延伸阅读/后续阅读/延伸话题）。

**正文校验规则**（article 用 min_chars，script 用 min_chars//2）：
- 首字符非 `#` → BLOCKER（必须以标题开头）。
- `clean_len(text)` < min_chars → BLOCKER（clean_len 去 Markdown 标记与空白后计数）。
- `_forbidden_hits` 命中（排除 soft_connectives）→ BLOCKER。
- 摘要/结论段（`摘要|总结|结论[：:](.+?)(\n\n|\Z)`）内无数字 → BLOCKER。
- 不含任一 required_sections → BLOCKER。

**输出键**：`char_count/profile/forbidden_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/article.json`：标题开头 + 摘要含「3 个月/42 篇/3 篇」数字 + 正文 1000+ 字
  + 延伸阅读 + 无禁词 → ok=true、char_count≥800、forbidden_count=0。
- `examples/script.json`：口播脚本，结论段含「3 个月」，字数≥400 → ok=true。
- 脏夹具 `article_dirty.json`：仅两行短文 → ok=false / exit 1。
- 脏夹具 `script_dirty.json`：含「说白了/值得我们深思」+ 太短 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **软连接词不能拦**：「首先/其次/因此」是正常逻辑连接词，若并入 forbidden_zh
  会把好文章全误杀，所以 `_forbidden_hits` 先 `soft` 排除再判。
- **英文禁词用词边界**：`delve` 用 `\b` 边界，否则 `delved`、`Delving` 里的子串
  也会命中；中文是字串匹配无此问题。
- **clean_len 要去 Markdown**：`#`、`-`、`|`、空格都计入 raw len 会虚高，
  与上游 article_validator 口径一致，去标记后才是「正文字数」。
- **结论先行判数字**：摘要段必须含 `\d`，防「结论：写作很重要」这类没信息量的
  空结论通过。
