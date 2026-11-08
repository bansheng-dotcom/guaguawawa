# 全栈交付闭环 优先级规则

1. 技术规格 → Schema → 功能切片 → 迁移，四步顺序固定。
2. spec 不过（boundary_ok=false）不进 Schema。
3. 后端服务未覆盖（e2e_coverage<1）不进迁移。
4. 迁移含不可逆操作且未授权，交付视为不完整。
