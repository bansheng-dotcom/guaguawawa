# S01 成品盘点与三级证据链
> 蒸馏自: 补充技能/01-当前能力域/open-gsd__gsd-core/skills/validate-artifact/SKILL.md
>


## 方法论（来源 harness-engineering / evidence）

评审的前提是「评的东西真的存在」。两步走：

1. **inventory 盘点**：把声称交付的物料列成清单，逐项核存在性；
2. **verify 证据链**：存在 ≠ 有效，按三级证据链逐级深挖——
   - **L1_EXISTS**：文件/路径存在；
   - **L2_SUBSTANTIVE**：有实质内容，不是 stub（占位/待办/空实现）；
   - **L3_WIRED**：被真实接线（被引用、被注册、被测试调用），不是孤儿文件。

stub 是最常见反模式：看起来交付了，实际是 `TODO` / `pass` /
`raise NotImplementedError` / 测试 `.skip`。

## 可执行口径

- inventory：物料路径按「原样 → 输入所在目录 → agent 目录」三级 resolve；
  **required 缺失 → CRITICAL FAIL（verdict=BLOCKED）**；
  可选缺失 → INFO（ok=True，不阻断）——别把可选项拉红。
- verify 串行三级，级别名外置在 `artifact.levels`（L1→L2→L3），不要手拼枚举；
- stub 扫描的标记清单全部外置：
  - 注释类：`artifact.stub_markers`
  - 代码类：`artifact.stub_code_patterns`
  - 测试跳过类：`artifact.test_skip_markers`
  - 最小文件字节数：`artifact.min_file_bytes`
- 内容优先级：**content 声明 > 磁盘读取 > exists 声明**——
  允许把内容内联在输入里评，但声明了 content 就不再读磁盘。

## 已验证算例

- `examples/artifact_inventory.json`：2 存在 + 1 可选缺失 → COMPLETE；
- `examples/artifact_inventory_dirty.json`：required 缺失 → BLOCKED；
- `examples/artifact_verify.json` / `artifact_verify_dirty.json`：
  干净件三级全过；脏件在 L2 被 stub 标记拦下。

## 实战踩坑

- 枚举拼写曾错写成 `L2_SUBSTIVE`，校验永远差一级——
  级别名一律读 `artifact.levels`，不在代码/文档里手写第二份；
- 可选物料缺失曾把整个 inventory 拉红（ok=False）——
  required / optional 必须分流定级，可选项缺失只提示不阻断。
