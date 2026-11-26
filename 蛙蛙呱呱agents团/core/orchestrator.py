# -*- coding: utf-8 -*-
"""core/orchestrator —— 专家编排：谁出场，由「你的问题」决定，不由「数据里有什么」决定。

问题（改造前）：
    报告的问题由 `decision.draft(intent, mounted)` 从「数据能算什么」里反推，
    所以「问招聘、只有水果数据」会出一份水果报告，binding=1.0、门禁全绿。
    这不是文案错误，是**编排层缺失**：系统里没有任何地方把「意图」映射到「专家」。

本模块做四件事：

1. `plan(intent, ...)`：意图 → 域 → 候选专家 → 数据齐备度 → roster / blocked；
2. 硬规矩（写死在代码里，不靠提示词）：
     - 意图相关度低于阈值 → 该专家不许出场；
     - 该专家 `needs` 的 required 能力缺一项 → 它只能交 BLOCKED，写明缺什么；
     - **意图命中的最强专家若全部 BLOCKED → 整份报告失败（INTENT_UNBOUND），
       不许退回「用能算的东西出报告」**；
     - 完全没有专家命中 → 数据驱动兜底（data_shape 模式），并在 `decisions.json` 里标记。
3. `readiness(experts, plan_obj)`：用方法挂载计划反推每个专家「数据够不够」；
4. `summary(decisions)`：给 manifest / 报告末节用的一行人话。

数据来源：`configs/experts.yaml`（由 `scripts/gen_experts.py` 生成，单一事实来源）。

用法：
    python -m core.orchestrator --intent "招聘编制与组织设计" --dir <项目>
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPERTS_PATH = ROOT / "configs" / "experts.yaml"
SCHEMA = "dsh.orchestrator/v1"

# 意图相关度阈值：低于它，该专家不许出场（0.30 来自「一个强触发词即可入选」的实测）
MIN_RELEVANCE = 0.30
# 数据齐备度阈值：低于它，专家只能交 BLOCKED
MIN_READINESS = 0.50
# 一次最多几位专家（超过会稀释报告，且成本陡增）
MAX_ROSTER = 5


# --------------------------------------------------------------------------- #
# 读专家卡（极简 YAML：只解析本仓库生成的格式，不引入 PyYAML 依赖）
# --------------------------------------------------------------------------- #
def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """解析 gen_experts.py 生成的 YAML 子集：嵌套 dict / list / 标量。"""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    pos = 0

    def _indent(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    def _scalar(s: str) -> Any:
        s = s.strip()
        if s in ("null", "~", ""):
            return None
        if s in ("true", "True"):
            return True
        if s in ("false", "False"):
            return False
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('\\"', '"')
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def _parse(base: int) -> Any:
        nonlocal pos
        out: Any = None
        while pos < len(lines):
            ln = lines[pos]
            ind = _indent(ln)
            if ind < base:
                break
            body = ln.strip()
            if body.startswith("- "):
                if out is None:
                    out = []
                item = body[2:].strip()
                pos += 1
                if item.endswith(":") or item == "":
                    child = _parse(ind + 1)
                    out.append(child if child is not None else {})
                else:
                    out.append(_scalar(item))
                continue
            if ":" not in body:
                pos += 1
                continue
            key, _, rest = body.partition(":")
            key = key.strip().strip('"')
            rest = rest.strip()
            if out is None:
                out = {}
            pos += 1
            if rest == "":
                child = _parse(ind + 1)
                out[key] = child if child is not None else {}
            elif rest in ("{}", "[]"):
                out[key] = {} if rest == "{}" else []
            else:
                out[key] = _scalar(rest)
        return out

    res = _parse(0)
    return res if isinstance(res, dict) else {}


def load_experts(path: Optional[Path] = None) -> Dict[str, Any]:
    """读 `configs/experts.yaml`。用 PyYAML（与 gen_agent_packs.py 同一依赖）。"""
    p = Path(path or EXPERTS_PATH)
    if not p.exists():
        raise FileNotFoundError(
            f"缺少专家卡 {p.name}：先跑 python scripts/gen_experts.py")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - 环境缺依赖时给明确指引
        raise RuntimeError(
            "读专家卡需要 PyYAML（gen_agent_packs.py 也依赖它）：pip install pyyaml") from exc
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not data.get("roles"):
        raise ValueError(f"{p.name} 结构不对：缺 roles")
    return data


# --------------------------------------------------------------------------- #
# 相关度
# --------------------------------------------------------------------------- #
def _hit(intent: str, word: str) -> bool:
    w = str(word).strip()
    if not w:
        return False
    if w.isascii():
        return re.search(re.escape(w.lower()), intent.lower()) is not None
    return w in intent


def _idf(experts: Dict[str, Any]) -> Dict[str, float]:
    """触发词的区分度：出现在越多角色里，权重越低。"""
    n = max(1, len(experts))
    df: Dict[str, int] = {}
    for e in experts.values():
        for w in set(e.get("triggers") or []):
            df[w] = df.get(w, 0) + 1
    return {w: math.log(1 + n / (1 + c)) for w, c in df.items()}


def relevance(intent: str, expert: Dict[str, Any], idf: Dict[str, float]) -> Dict[str, Any]:
    """意图相关度 = 域命中 + 域词 + 标签 + 触发词（按 IDF 加权），归一到 0–1。

    权重排序：业务域词 > 域描述 / 动作标签 > 技能触发词。
    业务域词（domain_triggers）是「这句话属于哪个领域」的人话表述，最能判域。
    """
    hits: List[Tuple[str, float, str]] = []
    dom = str(expert.get("domain") or "")
    if dom and _hit(intent, dom):
        hits.append((dom, 2.0, "domain"))
    for w in (expert.get("domain_triggers") or []):
        if _hit(intent, w):
            hits.append((w, idf.get(w, 1.5) * 1.2, "domain_word"))
    for lb in (expert.get("labels") or []):
        if _hit(intent, lb):
            hits.append((lb, 1.5, "label"))
    for w in (expert.get("triggers") or []):
        if _hit(intent, w):
            hits.append((w, idf.get(w, 1.0), "trigger"))
    for d in (expert.get("domains") or []):
        if _hit(intent, d):
            hits.append((d, 1.2, "capability"))

    # 归一：得分 / (得分 + 2)，保证 1 个强命中≈0.5，多个命中趋近 1
    raw = sum(w for _, w, _ in hits)
    score = raw / (raw + 2.0) if raw > 0 else 0.0
    return {"score": round(score, 3), "hits": [h for h, _, _ in hits],
            "kinds": sorted({k for _, _, k in hits})}


def refused(intent: str, expert: Dict[str, Any]) -> List[str]:
    """该专家明确声明「不答」的域被命中 → 提前否决。"""
    return [w for w in (expert.get("refuses") or []) if _hit(intent, w)]


# --------------------------------------------------------------------------- #
# 数据齐备度
# --------------------------------------------------------------------------- #
def readiness(expert: Dict[str, Any], plan_obj: Dict[str, Any]) -> Dict[str, Any]:
    """用方法挂载计划反推：这个专家的方法有几个能跑、缺什么能力。

    `plan_obj` 来自 `core.methods.plan()`：mounted / skipped（带 missing）。
    没有方法的角色（评审/研究类）按「不依赖数据方法」处理，readiness=1。
    """
    keys = list(expert.get("methods") or [])
    if not keys:
        # 没有可进报告的方法 = 这份数据题它答不了（只能评审/人工交付）。
        # 2026-11-19 体检：原来给 1.0 会让 r11/r19/r03 被选进数据 roster，
        # 随后由 decision_report 静默回退数据题库 —— 问文案出水果报告。
        return {"readiness": 0.0, "mounted": [], "skipped": [], "missing": [],
                "no_methods": True}
    mounted = {m["key"] for m in (plan_obj.get("mounted") or [])}
    skipped = {s["key"]: list(s.get("missing") or []) for s in (plan_obj.get("skipped") or [])}
    ok = [k for k in keys if k in mounted]
    bad = [k for k in keys if k in skipped and k not in mounted]
    missing: List[str] = []
    for k in bad:
        for m in skipped.get(k, []):
            if m not in missing:
                missing.append(m)
    r = len(ok) / len(keys) if keys else 1.0
    return {"readiness": round(r, 3), "mounted": ok, "skipped": bad,
            "missing": missing, "no_methods": False}


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def plan(intent: str, experts: Optional[Dict[str, Any]] = None,
         method_plan: Optional[Dict[str, Any]] = None,
         min_relevance: float = MIN_RELEVANCE,
         min_readiness: float = MIN_READINESS) -> Dict[str, Any]:
    """意图 → 域 → 专家名单。返回 roster / blocked / mode / reason。

    mode:
        intent    意图命中了专家，按意图出场（正常路径）
        data      没有任何专家命中意图，退回「数据能算什么」（标记 auto）
        unbound   意图命中的专家全部答不了 → 整份报告失败
    """
    ex = (experts or load_experts()).get("roles") or {}
    idf = _idf(ex)
    rows: List[Dict[str, Any]] = []
    for rid, e in ex.items():
        if not e.get("enters_report", True):
            continue
        rel = relevance(intent, e, idf)
        ref = refused(intent, e)
        ready = readiness(e, method_plan or {})
        row = {
            "role": rid, "name": e.get("name"), "title": e.get("title"),
            "domain": e.get("domain"),
            "methods": list(e.get("methods") or []),
            "produces": list(e.get("produces") or []),
            "relevance": rel["score"], "hits": rel["hits"], "kinds": rel["kinds"],
            "refuses_hit": ref,
            "readiness": ready["readiness"],
            "methods_mounted": ready["mounted"], "methods_skipped": ready["skipped"],
            "missing": ready["missing"], "no_methods": ready["no_methods"],
        }
        # 三态：selected / blocked / excluded
        if ref:
            row["status"] = "excluded"
            row["why"] = f"明确不答：{'、'.join(ref)}"
        elif rel["score"] < min_relevance:
            row["status"] = "excluded"
            row["why"] = f"意图相关度 {rel['score']} < {min_relevance}"
        elif ready["no_methods"]:
            row["status"] = "blocked"
            row["review_only"] = True
            row["why"] = "该角色没有可进报告的方法（只能评审/人工交付）"
        elif ready["readiness"] < min_readiness:
            row["status"] = "blocked"
            row["why"] = (f"数据齐备度 {ready['readiness']} < {min_readiness}；"
                          f"缺 {'、'.join(ready['missing']) or '关键数据'}")
        else:
            row["status"] = "selected"
            row["why"] = f"相关度 {rel['score']}，数据齐备度 {ready['readiness']}"
        rows.append(row)

    rows.sort(key=lambda r: (-r["relevance"], -r["readiness"], r["role"]))
    roster = [r for r in rows if r["status"] == "selected"][:MAX_ROSTER]
    blocked = [r for r in rows if r["status"] == "blocked"]
    excluded = [r for r in rows if r["status"] == "excluded"]

    if roster:
        mode, reason = "intent", f"意图命中 {len(roster)} 位专家"
    elif blocked:
        mode = "unbound"
        miss = sorted({m for r in blocked for m in r["missing"]})
        if miss:
            reason = "意图命中的专家都答不了：缺 " + "、".join(miss)
        elif all(r.get("review_only") for r in blocked):
            reason = ("意图命中的专家只能评审/人工交付，没有可进报告的作答方法："
                      + "、".join(f"{r['role']} {r['name']}" for r in blocked))
        else:
            reason = "意图命中的专家都答不了：缺 可进报告的数据"
    else:
        mode, reason = "data", "没有任何专家命中意图，退回数据驱动（auto）"

    return {
        "schema": SCHEMA,
        "intent": intent,
        "mode": mode,
        "reason": reason,
        "min_relevance": min_relevance,
        "min_readiness": min_readiness,
        "roster": roster,
        "blocked": blocked,
        "excluded": excluded,
        "rows": rows,
    }


def summary(decisions: Dict[str, Any]) -> str:
    """一行人话，给 manifest / 报告末节用。"""
    mode = decisions.get("mode")
    if mode == "intent":
        names = "、".join(f"{r['role']} {r['name']}" for r in decisions.get("roster") or [])
        return f"专家编排：{len(decisions.get('roster') or [])} 位出场（{names}）"
    if mode == "unbound":
        return f"专家编排：意图无法落地——{decisions.get('reason')}"
    return f"专家编排：{decisions.get('reason')}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="orchestrator",
                                 description="专家编排：意图 → 域 → 名单（不产报告）")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--dir", default=None, help="项目目录；给了就算数据齐备度")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    method_plan = None
    if a.dir:
        from core.data import analysis_desk
        from core import analysis_methods, methods
        desk = analysis_desk.scan(a.dir)
        views = analysis_methods.build_views(desk)
        prof = analysis_desk.profile(desk)
        method_plan = methods.plan(desk, views, prof, "analysis")

    d = plan(a.intent, method_plan=method_plan)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print(f"mode = {d['mode']}  ({d['reason']})")
        for r in d["roster"]:
            print(f"  [selected] {r['role']} {r['name']:<4} rel={r['relevance']} "
                  f"ready={r['readiness']}  {r['domain']}")
        for r in d["blocked"]:
            print(f"  [blocked ] {r['role']} {r['name']:<4} {r['why']}")
        for r in d["excluded"][:5]:
            print(f"  [excluded] {r['role']} {r['name']:<4} {r['why']}")
    return 0 if d["mode"] in ("intent", "data") else 1


if __name__ == "__main__":
    raise SystemExit(main())
