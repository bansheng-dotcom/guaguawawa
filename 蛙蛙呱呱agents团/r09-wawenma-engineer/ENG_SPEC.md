# 工业级代码工程规范账本 (Engineering Specification Ledger - ENG_SPEC.md)
> 角色代号：R09 蛙稳码（代码工程官）  
> 版本：v1.0.0 (SSOT - Single Source of Truth)  
> 适用范围：蛙蛙呱呱 agents 团代码生成、技术规格评审、数据库设计、全栈切片、测试覆盖、性能调优与 CI/CD 交付

---

## 一、 核心质量底线与硬指标 (Non-Negotiable Thresholds)

| 维度 | 指标项 | 警戒线 (Warning) | 阻断线 (Hard Redline) | 检验引擎 / 判据 |
| :--- | :--- | :--- | :--- | :--- |
| **单测覆盖率** | 行覆盖率 (Line Coverage) | `< 85%` | `< 80%` | pytest-cov / AST 静态分析 |
| **测试跳过率** | 测试跳过数 (Skipped Tests) | `> 0` | `> 0` (严禁伪造通过) | T11 对抗评审 / test_skipped 门禁 |
| **圈复杂度** | 函数圈复杂度 (Cyclomatic Complexity) | `> 10` | `> 15` | radon / EngineeringRuntimeEngine |
| **P99 延迟** | 接口服务响应耗时 (P99 Latency) | `> 200ms` | `> 500ms` | 性能剖析基线 / debug_refactor |
| **破坏性操作** | 线上迁移回滚步骤 (Rollback Steps) | `< 1` | `0` (无回滚必阻断) | ops_migration / irreversible 门禁 |
| **安全密钥** | 依赖漏洞与密钥泄露 (Leaked Keys/CVE) | Medium CVE | High/Critical CVE 或硬编码密钥 | ops_security / 密钥探针 |

---

## 二、 八维工程能力规范矩阵 (8-Domain Engineering Matrix)

### 1. 技术规格与架构 (Spec & Architecture)
- 拓扑定义：必须显式声明单体 (monolith)、分层 (layered) 或微服务 (microservices) 拓扑结构。
- 模块边界：服务连线必须形成闭环 DAG，禁止悬挂孤立节点或未声明输入输出的黑盒模块。

### 2. 数据库与 API 契约 (Database Schema & API Contracts)
- 数据库 Schema：所有表必须具有主键约束（UUID 或自增 BigInt），核心查询列必须配备明确索引。
- API 契约：必须具备 RESTful 规范动词与唯一路由，必须显式定义错误码映射 (Error Codes)。

### 3. 前后端全栈切片 (Fullstack Feature Slice)
- 垂直切片：UI 组件与后端服务必须显式连线绑定，端到端调用覆盖率达到 100%。
- 认证与权限：受保护路由 (Protected Routes) 必须绑定认证中间件 (如 JWT/OAuth2)，边界清晰。

### 4. 跨端生产工程 (Cross-Platform Engineering)
- 目标平台：构建矩阵必须覆盖 Android / iOS / Web 等目标容器，全矩阵编译通过。
- 状态管理：状态流转与平台差异必须文档化明确。

### 5. 测试与浏览器验证 (Testing & Browser Verification)
- 测试分层：单元测试 (Unit) + 集成测试 (Integration) + 端到端测试 (E2E) 三层金字塔。
- 关键路径：核心转化漏斗（登录/注册/下单）必须录制真实浏览器 Trace，Flaky 率必须为 0。

### 6. 调试性能重构 (Debug & Performance Refactoring)
- 根因定位：必须包含复现步骤 (Reproduction Steps) 与根本原因分析。
- 测试保护：性能重构必须在已有回归测试套件保护下完成，重构前后热点响应耗时劣化率 `< 0%`。

### 7. 迁移 CI/CD 安全 (Ops Migration & Security)
- 数据迁移：必须提供幂等迁移脚本与一键可逆回滚计划 (Rollback Plan)。
- 依赖审计：严禁引入已知 High/Critical 漏洞，严禁在代码仓中提交敏感 AccessKey/Secret。

### 8. 特殊技术载体 (Special Artifacts)
- MCP 服务：符合 Model Context Protocol 标准传输（如 stdio），工具声明与实现完全一致。
- Godot 载体：场景节点引用与脚本绑定完整，无断链资源。
