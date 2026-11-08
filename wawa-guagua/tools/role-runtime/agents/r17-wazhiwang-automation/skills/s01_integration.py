# -*- coding: utf-8 -*-
"""S01 SaaS/API 集成 —— 能力域 1。

整合自 n8n-io__n8n 的 workflow-builder / instance-awareness skills：
  - 自动化工作流的节点/连接/触发器结构校验（node 引用完整性、无悬空边）
  - 凭据选择与「禁明文密钥」门禁（secret 不得出现在 source）

关键立场：**集成工程师装配管道，但不发明业务规则、不硬编码凭据**。本门禁只做
确定性结构校验：节点齐备 + 触发器合法 + 连接引用完整 + 无明文密钥。业务字段
与规则来自上游业务角色的已确认输入（rules/fields），本角色不替其决定。

动作：
  workflow    工作流源码结构 + 凭据引用校验
  credential  凭据选择/服务选择 + 明文密钥禁词校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "integration"
DESC = "SaaS/API 集成：workflow/credential"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("workflow", help="校验自动化工作流节点/连接/触发器结构")
    a.add_argument("--input", required=True)
    b = act.add_parser("credential", help="校验凭据选择并拦截明文密钥")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "workflow":
        return _validate_workflow(data)
    if args.action == "credential":
        return _validate_credential(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _scan_secrets(obj: Any, keys: List[str]) -> List[str]:
    """递归扫描参数对象，返回命中的明文密钥键名（去重）。"""
    hits: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and v.strip():
                hits.append(k)
            hits.extend(_scan_secrets(v, keys))
    elif isinstance(obj, list):
        for x in obj:
            hits.extend(_scan_secrets(x, keys))
    return sorted(set(hits))


# --------------------------------------------------------------------------- #
def _validate_workflow(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["integration"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", node_count=0, trigger_count=0)

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return c.result([_ck(False, "nodes 必须是非空列表", "workflow.nodes")],
                        ok=False, verdict="FAIL", node_count=0, trigger_count=0)

    checks.append(_ck(len(nodes) <= th["max_nodes"],
                      f"节点数 {len(nodes)} ≤ 上限 {th['max_nodes']}",
                      "workflow.size"))

    # 每个节点必须有非空 name + type；name 唯一
    names: List[str] = []
    bad_node: List[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            bad_node.append("(非对象)")
            continue
        nm = n.get("name")
        nt = n.get("type")
        if not nm or not nt:
            bad_node.append(nm or "(缺名)")
            continue
        names.append(nm)
    checks.append(_ck(not bad_node, f"节点 name/type 齐备（异常 {bad_node or '无'}）",
                      "workflow.node_required"))

    dup = sorted({x for x in names if names.count(x) > 1})
    checks.append(_ck(not dup, f"节点名唯一（重复 {dup or '无'}）",
                      "workflow.node_unique"))

    # 触发器：至少 1 个以 Trigger 结尾或 type 命中白名单
    trigger_types = th["trigger_types"]
    triggers = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nt = str(n.get("type") or "")
        if nt.endswith("Trigger") or nt in trigger_types:
            triggers.append(n.get("name"))
    checks.append(_ck(bool(triggers),
                      f"至少 1 个触发器（找到 {len(triggers)}）", "workflow.trigger"))

    # 连接引用完整性：connections 里引用的节点必须存在，无悬空边
    conns = data.get("connections") or {}
    known = set(names)
    dangling: List[str] = []
    if isinstance(conns, dict):
        for src, out in conns.items():
            if src not in known:
                dangling.append(f"源:{src}")
            for group in (out.get("main") or []) if isinstance(out, dict) else []:
                for link in (group or []):
                    tgt = link.get("node") if isinstance(link, dict) else link
                    if tgt not in known:
                        dangling.append(f"目标:{tgt}")
    checks.append(_ck(not dangling,
                      f"连接引用完整（悬空 {sorted(set(dangling)) or '无'}）",
                      "workflow.connections"))

    # 凭据禁明文：参数里出现 secret 类键名（且非空字符串）
    secret_keys = th["credential_secret_keys"]
    secrets: List[str] = []
    for n in nodes:
        if isinstance(n, dict):
            secrets.extend(_scan_secrets(n.get("parameters") or {}, secret_keys))
            secrets.extend(_scan_secrets(n.get("credentials") or {}, secret_keys))
    secrets = sorted(set(secrets))
    checks.append(_ck(not secrets,
                      f"无明文密钥（命中 {secrets or '无'}）", "workflow.no_secret"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        node_count=len(nodes), trigger_count=len(triggers),
        dangling_edges=len(set(dangling)),
        narrative=f"工作流 {data.get('name', '?')}：{len(nodes)} 节点 / "
                  f"{len(triggers)} 触发器 / 悬空边 {len(set(dangling))}")


# --------------------------------------------------------------------------- #
def _validate_credential(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["integration"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", credential_count=0,
                        unresolved_count=0)

    creds = data.get("credentials")
    if not isinstance(creds, list) or not creds:
        return c.result([_ck(False, "credentials 必须是非空列表", "credential.list")],
                        ok=False, verdict="FAIL", credential_count=0,
                        unresolved_count=0)

    checks.append(_ck(True, f"凭据 {len(creds)} 个", "credential.count"))

    # 每个凭据必须声明 credential_type（不允许匿名默认兜底）
    missing = [x.get("name", "?") for x in creds
               if not (isinstance(x, dict) and x.get("credential_type"))]
    checks.append(_ck(not missing,
                      f"每个凭据声明 credential_type（缺 {missing or '无'}）",
                      "credential.type"))

    # 未解析占位符：newCredential() 语义——值为占位符字符串视为已引用、非明文
    unresolved = [x.get("name", "?") for x in creds
                  if isinstance(x, dict) and x.get("unresolved") is True]
    checks.append(_ck(not unresolved,
                      f"无未解析凭据（未解析 {unresolved or '无'}）",
                      "credential.resolved"))

    # 凭据禁明文：任何凭据体里出现 secret 类键名
    secret_keys = th["credential_secret_keys"]
    secrets: List[str] = []
    for x in creds:
        if isinstance(x, dict):
            secrets.extend(_scan_secrets(x.get("data") or {}, secret_keys))
    secrets = sorted(set(secrets))
    checks.append(_ck(not secrets,
                      f"凭据无明文密钥（命中 {secrets or '无'}）",
                      "credential.no_secret"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        credential_count=len(creds), unresolved_count=len(unresolved),
        narrative=f"凭据 {len(creds)} 个，未解析 {len(unresolved)}，"
                  f"明文命中 {len(secrets)}")
