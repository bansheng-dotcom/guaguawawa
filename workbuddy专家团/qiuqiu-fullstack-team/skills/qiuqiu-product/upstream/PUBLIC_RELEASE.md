# Public Release Boundary

这个仓库是 `product-manager` Skill 的公开分发版，仓库名为 `product-manager-agent-project-public`。

## 保留内容

- `SKILL.md`、`AGENTS.md` 和平台元数据。
- 产品管理方法库、workflow、模板和验证门禁。
- 经验 RAG 的模型、规则、空索引和脱敏模板。
- 可公开复用的用户档案示例。

## 排除内容

- 固定服务对象的真实档案和原话。
- 真实项目经验卡、内部需求编号、业务数据和报告。
- 本机绝对路径、登录态、密钥、Cookie、Token 和凭据。
- 私有仓库 Git 历史。

## 本地个性化

- 用户档案写入 `user/profile.md`。
- 项目经验写入 `experience/projects/`。
- 临时经验写入 `experience/inbox/`。

上述本地路径均由 `.gitignore` 保护。若要贡献可复用经验，请先脱敏、泛化并补充适用边界，再通过独立分支提交。

## 同步规则

公开版从私有版更新时，先复制已提交快照，再重复执行隐私扫描和结构验证；禁止直接复用私有仓库 Git 历史或把私有分支设为公开。
