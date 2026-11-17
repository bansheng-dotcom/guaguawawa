# -*- coding: utf-8 -*-
"""core/outcome_ledger —— 结果台账（P6）。

报告发出去之后，要能回答：这条判断后来对了吗？这个决定后来好吗？

最小闭环：

    add     登记一条 open 断言/预测（report_id + claim_id + prediction + decision + deadline）
    review  到期回填：hit / miss / partial / void + result
    summary 命中率、逾期待复核、即将到期

台账默认落在 `workspace/outcomes/ledger.json`（不进 git，属于运行态）。

用法：
    python -m core.outcome_ledger add --report-id RPT-... --claim-id structure \
      --prediction "6 个品类在涨、6 个在跌" --decision "哪些品类继续做" --deadline 2027-02-15
    python -m core.outcome_ledger review O-... --status hit --result "复盘：芒果/梨方向与判断一致"
    python -m core.outcome_ledger summary
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT.parent / "workspace" / "outcomes" / "ledger.json"

STATUSES = ("open", "hit", "miss", "partial", "void")


def _today() -> str:
    return date.today().isoformat()


def _path(path: Optional[str | Path]) -> Path:
    return Path(path) if path else DEFAULT_PATH


def load(path: Optional[str | Path] = None) -> Dict[str, Any]:
    p = _path(path)
    if not p.exists():
        return {"schema": "dsh.outcome_ledger/v1", "entries": []}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def save(data: Dict[str, Any], path: Optional[str | Path] = None) -> Path:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(str(s))
        return True
    except ValueError:
        return False


def add(report_id: str, claim_id: str, prediction: str, decision: str,
        deadline: str, path: Optional[str | Path] = None,
        kind: str = "claim") -> Dict[str, Any]:
    if not all([str(x).strip() for x in (report_id, claim_id, prediction, decision)]):
        raise ValueError("report_id / claim_id / prediction / decision 不能为空")
    if not _valid_date(deadline):
        raise ValueError(f"deadline 不是 YYYY-MM-DD：{deadline}")
    data = load(path)
    for e in data["entries"]:
        if (e.get("report_id") == report_id and e.get("claim_id") == claim_id
                and e.get("status") == "open"):
            return e
    entry = {
        "id": f"O-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6]}",
        "report_id": report_id,
        "claim_id": claim_id,
        "kind": kind,
        "prediction": prediction,
        "decision": decision,
        "deadline": deadline,
        "status": "open",
        "result": "",
        "recorded_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "reviewed_at": "",
    }
    data["entries"].append(entry)
    save(data, path)
    return entry


def review(entry_id: str, status: str, result: str,
           path: Optional[str | Path] = None) -> Dict[str, Any]:
    if status not in STATUSES or status == "open":
        raise ValueError(f"review status 只能是 hit/miss/partial/void：{status}")
    if not str(result or "").strip():
        raise ValueError("review 必须写 result：为什么算命中/失败")
    data = load(path)
    for e in data["entries"]:
        if e["id"] == entry_id:
            e["status"] = status
            e["result"] = str(result)
            e["reviewed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            save(data, path)
            return e
    raise KeyError(f"台账里没有 {entry_id}")


def list_entries(status: Optional[str] = None,
                 path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    es = load(path)["entries"]
    if status:
        es = [e for e in es if e.get("status") == status]
    return es


def summary(path: Optional[str | Path] = None, today: Optional[str] = None) -> Dict[str, Any]:
    es = load(path)["entries"]
    t = date.fromisoformat(today or _today())
    counts = {s: sum(1 for e in es if e.get("status") == s) for s in STATUSES}
    overdue = [e for e in es if e.get("status") == "open"
               and _valid_date(e.get("deadline", ""))
               and date.fromisoformat(e["deadline"]) < t]
    due_soon = [e for e in es if e.get("status") == "open"
                and _valid_date(e.get("deadline", ""))
                and t <= date.fromisoformat(e["deadline"]) <= t + timedelta(days=30)]
    judged = counts["hit"] + counts["miss"] + counts["partial"]
    return {
        "schema": "dsh.outcome_summary/v1",
        "total": len(es),
        **counts,
        "hit_rate": round(counts["hit"] / judged, 3) if judged else None,
        "overdue": len(overdue),
        "due_soon": len(due_soon),
        "overdue_ids": [e["id"] for e in overdue],
        "due_soon_ids": [e["id"] for e in due_soon],
        "as_of": t.isoformat(),
    }


def seed_from_trace(report_id: str, intent: str, trace: Dict[str, Any],
                    deadline: Optional[str] = None,
                    path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """把一份报告的 findings 登记成 open 预测，默认 90 天到期。"""
    ddl = deadline or (date.today() + timedelta(days=90)).isoformat()
    out = []
    for f in trace.get("findings") or []:
        key = str(f.get("key") or "")
        title = str(f.get("title") or key)
        if not key:
            continue
        out.append(add(report_id, key, title, intent, ddl, path=path))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="outcome_ledger",
                                 description="结果台账：登记预测 / 到期回填 / 命中率")
    ap.add_argument("--path", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--report-id", required=True)
    a.add_argument("--claim-id", required=True)
    a.add_argument("--prediction", required=True)
    a.add_argument("--decision", required=True)
    a.add_argument("--deadline", required=True)

    l = sub.add_parser("list")
    l.add_argument("--status", choices=STATUSES, default=None)

    r = sub.add_parser("review")
    r.add_argument("entry_id")
    r.add_argument("--status", choices=("hit", "miss", "partial", "void"), required=True)
    r.add_argument("--result", required=True)

    s = sub.add_parser("summary")
    s.add_argument("--today", default=None)

    sd = sub.add_parser("seed")
    sd.add_argument("--report-id", required=True)
    sd.add_argument("--intent", required=True)
    sd.add_argument("--trace", required=True)
    sd.add_argument("--deadline", default=None)

    args = ap.parse_args(argv)
    if args.cmd == "add":
        out: Any = add(args.report_id, args.claim_id, args.prediction, args.decision,
                       args.deadline, path=args.path)
    elif args.cmd == "list":
        out = list_entries(args.status, path=args.path)
    elif args.cmd == "review":
        out = review(args.entry_id, args.status, args.result, path=args.path)
    elif args.cmd == "summary":
        out = summary(path=args.path, today=args.today)
    else:
        trace = json.loads(Path(args.trace).read_text(encoding="utf-8-sig"))
        out = seed_from_trace(args.report_id, args.intent, trace,
                              deadline=args.deadline, path=args.path)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
