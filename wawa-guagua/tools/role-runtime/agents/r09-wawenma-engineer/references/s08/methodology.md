# s08 特殊技术载体（special）方法论

来源沉淀：`godotengine__godot-demo-projects`（Godot 可加载脚本）+ MCP 工程 Agent 工作流
（`open-gsd__gsd-core`）。

## 一、方法论（什么时候用、核心口径）

特殊载体回答「非 Web 工程怎么落地」。两个动作：
- `mcp`：MCP 工具服务——transport 枚举、工具命名、manifest 与工具清单一致。
- `godot`：Godot 可加载脚本——project_config 在、场景挂载的脚本必须存在。

核心红线：**manifest 与 tools 不一致 = 工具服务不可发现**；
**场景挂载不存在的脚本 = 加载即崩**。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

MCP 传输方式外置：`special.mcp_transports`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s08_special.mcp/godot`）

**mcp 校验规则**：
- transport 不在枚举 → `special:transport` CRITICAL。
- tools 为空 → `special:tools` CRITICAL。
- 工具缺 name → `special:tool_name` HIGH。
- manifest.tools 与工具清单不一致 → `special:manifest` HIGH。

**godot 校验规则**：
- project_config 为空 → `special:project_config` CRITICAL。
- scenes 为空 → `special:scenes` CRITICAL。
- 场景挂载的 script 不存在于 scripts → `special:scene_script` HIGH。

**输出键**：mcp → `transport / tool_count / verdict / next`；
godot → `scene_count / script_count / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/special_mcp.json`（stdio + 2 工具 + manifest 一致）：tool_count=2，verdict=PASS。
`examples/special_godot.json`（2 场景 2 脚本）：scene_count=2，script_count=2，verdict=PASS。
脏夹具 `special_mcp_dirty.json`：transport 非法+manifest 不一致 → ok=false；
`special_godot_dirty.json`：空 project_config+悬空脚本 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **manifest 一致性要做集合对拍**：不能只查「工具都在」，
  还要查「manifest 多列了不存在的工具」，否则工具服务发现会失败。
- **Godot 脚本引用是加载期错误**：脚本路径写错在运行时才崩，
  确定性门禁必须在交付前拦下悬空 script。
