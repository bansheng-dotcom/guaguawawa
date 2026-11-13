# s03 前端后端全栈（fullstack）方法论

来源沉淀：`KarmenLoop__fullstack-web-delivery` + `Jeffallan__claude-skills`（flutter-expert 全栈口径）。

## 一、方法论（什么时候用、核心口径）

全栈回答「一个功能从前端到后端跑通没有」。两个动作：
- `feature`：端到端功能切片——前端组件与后端服务成对连线，后端服务必须被覆盖。
- `auth`：认证——auth_method 白名单，受保护路由必须存在于 routes。

核心红线：**后端服务没有被任何前端组件调用 = 功能没跑通**，e2e_coverage 必须 1.0。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

认证方式外置：`fullstack.auth_methods`；最低组件/服务数 `fullstack.min_components/min_services`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s03_fullstack.feature/auth`）

**feature 校验规则**：
- frontend/backend 数量低于下限 → `fullstack:components/services` CRITICAL。
- wiring 引用不存在的组件/服务 → `fullstack:wiring_comp/wiring_svc` HIGH。
- 后端服务未被覆盖 → `fullstack:e2e_coverage` HIGH。
- e2e_coverage = 被覆盖服务数 / 服务总数。

**auth 校验规则**：
- auth_method 不在白名单 → `fullstack:auth_method` CRITICAL。
- 受保护路由不在 routes → `fullstack:protected_route` HIGH。
- routes 为空 → `fullstack:routes` CRITICAL。

**输出键**：feature → `component_count / service_count / e2e_coverage / verdict / next`；
auth → `auth_method / route_count / protected_count / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/fullstack_feature.json`（2 组件 2 服务）：e2e_coverage=1.0，verdict=PASS。
`examples/fullstack_auth.json`（3 路由 2 受保护）：auth_method=jwt，protected_count=2，verdict=PASS。
脏夹具 `fullstack_feature_dirty.json`：服务未被覆盖 → e2e_coverage<1.0，ok=false；
`fullstack_auth_dirty.json`：auth_method 非法+悬空受保护路由 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **e2e_coverage 是「跑通」的代理指标**：组件和服务都存在但没连线，功能照样是死的。
  必须把未覆盖服务显式列为 HIGH，而非只看数量。
- **auth_method 白名单防拍脑袋**：sso/magic-link 等要进白名单必须先有实现方案，避免契约空转。
