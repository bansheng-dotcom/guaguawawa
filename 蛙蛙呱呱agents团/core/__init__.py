"""蛙式一人公司 —— 20 个本地 Agent 的协作底座。

本包提供跨角色协作的最小内核，纯 Python 标准库，无第三方依赖：
    protocol  —— 交接合同（端口 / 任务卡 / 事件）的数据结构
    workspace —— 共享工作区（事件流 + 任务卡 + 文件锁）
    registry  —— 20 个角色的注册表（能力、端口、集成来源）
    runner    —— 以子进程方式调用其它 Agent

设计原则（源自 Anthropic《Building effective agents》与《Multi-agent
coordination patterns》）：
    1. 简单可组合，不做重型框架；
    2. 协作用「编排器(Orchestrator) + 共享工作区(Shared-State)」；
    3. 交接靠明确的 input/output 端口契约，而非口头约定；
    4. 一切带终止条件，避免死循环。
"""

__all__ = ["protocol", "workspace", "registry", "runner", "artifact_registry", "approvals", "report_bridge"]