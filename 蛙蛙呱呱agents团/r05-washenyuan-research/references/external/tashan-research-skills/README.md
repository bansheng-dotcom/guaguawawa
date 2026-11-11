# 他山科研 Skills

面向 TRAE 的科研 Skills 插件包，覆盖文献调研、研究构思、实验设计、数据分析、成果写作与论文审查等科研环节。

## 包内容

- `.trae-plugin/plugin.json`：TRAE 插件清单。
- `skills/`：原始 `skills.zip` 中的全部 Skill 与配套脚本、模板、参考资料和资源文件。
- `assets/icon.webp`：来自合作方提交 Wiki 的市场展示图标。

原始 ZIP 实际包含 20 个顶层 Skill 入口；合作方市场说明使用“18 项高频科研 Skills”口径。本包完整保留 20 个入口，没有据此擅自删减能力。其中原目录 `find-science-skills-mcp/` 已修正为 `find-science-skills/`，使目录名与 `SKILL.md` frontmatter 及原索引一致。

## 能力与连接配置

这是一个纯 Skills 插件包，不声明统一 MCP 或 Connector。部分 Skill 会按各自说明调用外部服务、命令行工具或本地运行时；相关依赖、环境变量和使用限制以对应 Skill 目录内的说明为准。包内不包含真实 token、secret、private key 或用户凭据。

## 市场信息

- 发布方：国科大他山
- 官网：https://tashan.ac.cn/homepage/
- 上架地区：中国版 + 国际版
- 市场分类：开发工具、效率提升
- 支持系统：macOS、Windows

## 许可证与第三方内容

各 Skill 的许可证和第三方声明按其目录内现有文件保留。本转换没有为缺少统一许可证声明的内容补造许可证；正式上架前应由发布方确认整包授权范围及所有第三方依赖的再分发条件。

## 来源

本包由合作方提供的 `skills.zip` 转换，并参考 TRAE Plugin 对外接入模板和法智插件包的目录组织方式生成。法智的法律 Skills、MCP 地址、Connector 和认证配置未包含在本包中。
