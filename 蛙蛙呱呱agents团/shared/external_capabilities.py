# -*- coding: utf-8 -*-
"""外部能力目录（26 个 Trae 插件 / WorkBuddy 技能）的加载、检索与就绪探测。

设计原则：
- **只登记与探测，不假装调用**：技能类（skill/multi）是提示词规范，R10 说明书式执行；
  MCP 类（meitu/volcengine/agent-earth/miniapp）需要 MCP 客户端，本团队 CLI 不直连。
- 入口文档已拷进各角色 `references/external/<id>/`，深层 references/ 与可执行脚本
  仍以 catalog 里的 `source` 为准。
- 探测只做本地事实：目录是否存在、文档是否落地、`node` 是否可用、相关环境变量是否配置；
  **不联网、不读密钥值**。
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
CATALOG_PATH = os.path.join(_HERE, "external_capabilities", "catalog.json")

ROLES = {
    "r01": "r01-waquanju-ceo", "r02": "r02-wapaibu-coo", "r03": "r03-washouxian-cfo",
    "r04": "r04-watiaoci-reviewer", "r05": "r05-washenyuan-research",
    "r06": "r06-wadeqing-analyst", "r07": "r07-wademing-pm", "r08": "r08-wajiancheng-mvp",
    "r09": "r09-wawenma-engineer", "r10": "r10-wachengmei-design",
    "r11": "r11-wadianti-copy", "r12": "r12-wayingliu-growth",
    "r13": "r13-wakecheng-csm", "r14": "r14-wajiaoyi-commerce",
    "r15": "r15-wagongying-erp", "r16": "r16-warenshi-hr",
    "r17": "r17-wazhiwang-automation", "r18": "r18-washucang-dataeng",
    "r19": "r19-wazhimo-ml", "r20": "r20-washouzhi-sre",
}

# MCP 能力所需的环境变量（只用于判断"是否配置"，不读取值）
ENV_HINTS: Dict[str, List[str]] = {
    "meitu-local-mcp": ["MEITU_OAUTH_ACCESS_TOKEN", "MEITU_MCP_CLIENT"],
    "volcengine-pro-dataset": ["X_HQD_API_KEY", "PRO_DATASET_API_KEY", "VOLC_PRO_DATASET_KEY"],
    "agent-earth": ["AGENT_EARTH_TOKEN", "AGENTEARTH_TOKEN"],
    "miniapp-builder": [],
}


def load_catalog(path: Optional[str] = None) -> Dict[str, Any]:
    p = path or CATALOG_PATH
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def all_caps() -> List[Dict[str, Any]]:
    return list(load_catalog().get("capabilities", []))


def get(cap_id: str) -> Optional[Dict[str, Any]]:
    for cap in all_caps():
        if cap["id"] == cap_id:
            return cap
    return None


def list_caps(role: Optional[str] = None, q: Optional[str] = None,
              kind: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for cap in all_caps():
        if role and cap["owner"] != role.lower() and role.lower() not in cap.get("consumers", []):
            continue
        if kind and cap["kind"] != kind:
            continue
        if q:
            hay = " ".join([cap["id"], cap["title"], " ".join(cap.get("triggers", []))]).lower()
            if q.lower() not in hay:
                continue
        out.append(cap)
    return out


def owned(role: str) -> List[Dict[str, Any]]:
    return [c for c in all_caps() if c["owner"] == role.lower()]


def docs_path(cap: Dict[str, Any]) -> str:
    return os.path.join(_REPO, cap["docs_dir"].replace("/", os.sep))


def probe(cap: Dict[str, Any]) -> Dict[str, Any]:
    """本地只读探测：目录 / 文档 / 运行时 / 环境变量。"""
    checks: List[Dict[str, Any]] = []

    def ck(ok: bool, msg: str, dim: str, required: bool = True) -> None:
        checks.append({"ok": bool(ok), "msg": msg, "dim": dim,
                       "sev": "OK" if ok else ("BLOCKER" if required else "WARN")})

    src = cap.get("source", "")
    ck(bool(src) and os.path.isdir(src), f"源目录存在（{src or '未登记'}）", "ext.source")

    dpath = docs_path(cap)
    doc_files = sum(len(files) for _r, _d, files in os.walk(dpath)) if os.path.isdir(dpath) else 0
    ck(doc_files > 0, f"入口文档已落地（{cap.get('docs_dir')}，{doc_files} 个文件）", "ext.docs")

    kind = cap.get("kind")
    if kind == "mcp":
        mcp_json = os.path.join(src, ".mcp.json")
        ck(os.path.isfile(mcp_json), ".mcp.json 存在", "ext.mcp_config")
        envs = ENV_HINTS.get(cap["id"], [])
        missing = [e for e in envs if not os.environ.get(e)]
        if envs:
            ck(not missing, f"环境变量已配置（缺 {missing or '无'}）", "ext.env", required=False)
        if cap.get("requires") == "mcp:node":
            ck(bool(shutil.which("node")), "node 可执行（本地 MCP 依赖）", "ext.node")
        ck(False, "MCP 需客户端接入（本 CLI 不直连，见 recipe）", "ext.client", required=False)

    blockers = [c for c in checks if not c["ok"] and c["sev"] == "BLOCKER"]
    warns = [c for c in checks if not c["ok"] and c["sev"] == "WARN"]
    status = "blocked" if blockers else ("partial" if warns else "ready")
    return {"id": cap["id"], "status": status, "checks": checks,
            "blockers": [c["msg"] for c in blockers], "warnings": [c["msg"] for c in warns]}


def recipe(cap: Dict[str, Any]) -> str:
    """返回可执行的接入/使用方式（MCP 返回脱敏配置片段）。"""
    if cap.get("kind") == "mcp":
        mcp_json = os.path.join(cap.get("source", ""), ".mcp.json")
        if os.path.isfile(mcp_json):
            try:
                with open(mcp_json, encoding="utf-8") as fh:
                    data = json.load(fh)
                text = json.dumps(data, ensure_ascii=False, indent=1)
                return ("# 需要 MCP 客户端（Trae / Claude Desktop 等）接入，本团队 CLI 不直连\n"
                        + text + "\n# 把 ${connector.*.ACCESS_TOKEN} 换成你环境里的实际凭据后再接入")
            except (OSError, ValueError) as exc:
                return f"MCP 配置读取失败：{exc}"
        return "MCP 配置缺失，请检查源目录 .mcp.json"
    skill_docs = [s["doc"] for s in cap.get("skills", [])]
    head = skill_docs[:5]
    lines = [f"# 读取 {cap['docs_dir']} 下的入口文档，按其中的 Workflow 执行："]
    lines += [f"#   - {d}" for d in head]
    if len(skill_docs) > len(head):
        lines.append(f"#   - ... 共 {len(skill_docs)} 个技能入口")
    if cap.get("source"):
        lines.append(f"# 深度 references / 脚本在源目录：{cap['source']}")
    return "\n".join(lines)


def stats() -> Dict[str, Any]:
    caps = all_caps()
    by_kind: Dict[str, int] = {}
    by_role: Dict[str, int] = {}
    for c in caps:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        by_role[c["owner"]] = by_role.get(c["owner"], 0) + 1
    return {"count": len(caps), "by_kind": by_kind, "by_role": dict(sorted(by_role.items()))}
