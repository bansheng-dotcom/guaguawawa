# -*- coding: utf-8 -*-
"""咨询项目工作簿：状态机 + 门禁 + 产物落盘（零依赖）。"""
from __future__ import annotations

import json
from pathlib import Path

from . import checks
from .stages import STAGES, STAGE_BY_ID, next_stage

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT / "projects" / "consulting"


class WorkbookError(RuntimeError):
    pass


def project_dir(eid: str) -> Path:
    d = PROJECTS / eid
    d.mkdir(parents=True, exist_ok=True)
    return d


def path_of(eid: str) -> Path:
    return project_dir(eid) / "workbook.json"


def load(eid: str) -> dict:
    p = path_of(eid)
    if not p.exists():
        raise WorkbookError(f"项目 {eid} 不存在，先 start")
    return json.loads(p.read_text(encoding="utf-8"))


def save(eid: str, data: dict) -> None:
    path_of(eid).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def start(eid: str, client: str, decision: str, partner: str = "r01",
          lead: str = "r05", deadline: str = "") -> dict:
    if path_of(eid).exists():
        raise WorkbookError(f"项目 {eid} 已存在")
    data = {
        "engagement": {"id": eid, "client": client, "decision": decision,
                       "partner": partner, "lead": lead, "deadline": deadline},
        "current_stage": 1,
        "stages": {str(s["id"]): {"status": "in_progress", "payload": None,
                                  "signed_by": None, "errors": []} for s in STAGES},
        "log": [],
    }
    save(eid, data)
    return data


def submit(eid: str, stage: int, payload: dict) -> dict:
    data = load(eid)
    if stage != data["current_stage"]:
        raise WorkbookError(f"当前阶段是 {data['current_stage']}，不能提交阶段 {stage}")
    errors = checks.check(stage, payload)
    rec = data["stages"][str(stage)]
    rec["payload"] = payload
    rec["errors"] = errors
    rec["status"] = "rejected" if errors else "done"
    data["log"].append({"action": "submit", "stage": stage, "errors": errors})
    save(eid, data)
    # 产物落盘（无论是否通过，都留痕）
    d = project_dir(eid)
    safe = STAGE_BY_ID[stage]["name"].replace("/", "-")
    (d / f"0{stage}-{safe}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"stage": stage, "ok": not errors, "errors": errors}


def sign(eid: str, stage: int, by: str) -> dict:
    data = load(eid)
    rec = data["stages"][str(stage)]
    if rec["status"] != "done":
        raise WorkbookError(f"阶段 {stage} 未通过，不能签字")
    reviewer = STAGE_BY_ID[stage]["reviewer"]
    if by not in (reviewer, "r01"):
        raise WorkbookError(f"阶段 {stage} 的评审人是 {reviewer}（或 r01），不是 {by}")
    rec["signed_by"] = by
    data["log"].append({"action": "sign", "stage": stage, "by": by})
    save(eid, data)
    return {"stage": stage, "signed_by": by}


def advance(eid: str) -> dict:
    data = load(eid)
    cur = data["current_stage"]
    rec = data["stages"][str(cur)]
    if rec["status"] != "done":
        raise WorkbookError(f"阶段 {cur} 未通过（{rec['errors']}）")
    if not rec["signed_by"]:
        raise WorkbookError(f"阶段 {cur} 未签字，不能进下一阶段")
    if cur >= 8:
        data["status"] = "completed"
        save(eid, data)
        return {"status": "completed", "stage": 8}
    data["current_stage"] = next_stage(cur)
    data["stages"][str(data["current_stage"])]["status"] = "in_progress"
    data["log"].append({"action": "advance", "from": cur, "to": data["current_stage"]})
    save(eid, data)
    return {"status": "advanced", "stage": data["current_stage"]}


def status(eid: str) -> list[dict]:
    data = load(eid)
    rows = []
    for s in STAGES:
        rec = data["stages"][str(s["id"])]
        rows.append({"stage": s["id"], "name": s["name"],
                     "status": rec["status"], "signed_by": rec["signed_by"],
                     "errors": rec["errors"]})
    return rows


def render_md(eid: str) -> str:
    data = load(eid)
    eng = data["engagement"]
    lines = [f"# 咨询工作簿 · {eng['id']}", "",
             f"- 客户：{eng['client']}", f"- 决策：{eng['decision']}",
             f"- partner：{eng['partner']} / lead：{eng['lead']}",
             f"- 截止：{eng['deadline'] or '—'}", "", "| 阶段 | 名称 | 状态 | 签字 |", "|---|---|---|---|"]
    for s in STAGES:
        rec = data["stages"][str(s["id"])]
        lines.append(f"| {s['id']} | {s['name']} | {rec['status']} | {rec['signed_by'] or '—'} |")
    lines += ["", "## 各阶段产物", ""]
    for s in STAGES:
        rec = data["stages"][str(s["id"])]
        if rec["payload"]:
            lines.append(f"### 阶段 {s['id']} · {s['name']}")
            lines.append("```json")
            lines.append(json.dumps(rec["payload"], ensure_ascii=False, indent=1))
            lines.append("```")
    out = project_dir(eid) / "workbook.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)
