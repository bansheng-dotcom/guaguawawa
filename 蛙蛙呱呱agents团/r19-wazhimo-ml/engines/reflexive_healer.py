# -*- coding: utf-8 -*-
"""L03 自愈反思层 —— R19 Reflexion 自纠闭环 + 五条角色红线刚性审判。

SOP v13.0 L03 体检病灶（R19 真实断点）：
    1. 输入缺 `expected/predicted`、枚举写成 `prod` / `pass` / `Medium` 等别名时，
       技能直接判 FAIL 或键错误，**没有任何就地自愈**，人类只能手工改 JSON；
    2. 三条红线（凭据、主观放行、统计越界）只写在 SKILL.md 的文字里，
       代码层零拦截 —— 换成「生产上线」照样放行；
    3. 发布裁决 PASS 但缺回归证据时，系统不会自愈降级到 NEEDS_REVIEW，
       而是把「无证据的 PASS」原样吐给下游。

对标开源标杆（Stars > 1k）：
    * noahshinn/reflexion (>3k) —— 审计-反思-重试的短时记忆闭环
    * microsoft/autogen (>42k)   —— critic agent 与可组合的角色边界
    * openai/openai-python / langchain —— 结构化重试与修复模式

落地的最低 3 项架构升级：
    1. `[REDLINE BLOCKED]` 结构化红线码（RL-01..RL-05）+ 明确 handoff 去向；
    2. 枚举/字段别名归一（prod→production、pass→PASS、ground_truth→expected 等）；
    3. Reflexion 有界反思闭环：审计 → 自愈 → 复审，直到收敛或熔断（max 3 轮）。

用法：
    python -m engines.reflexive_healer --artifact examples/evaluation_dataset.json \
        --action "这个新版效果看起来不错，直接上线吧" --out workspace/rounds/L03_heal.json
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --------------------------------------------------------------------------- #
# 红线登记表（角色权责防线，必须刚性可审判）
# --------------------------------------------------------------------------- #
REDLINES: Dict[str, Dict[str, Any]] = {
    "RL-01": {"name": "凭据入工件", "handoff": "密钥管理 / R20 运维安全",
              "words": ["api_key", "apikey", "secret", "password", "token", "私钥",
                        "密钥", "密码", "connection_string", "client_secret"]},
    "RL-02": {"name": "主观感受放行（无证据上线）", "handoff": "补齐评估证据 + 回归报告",
              "words": ["效果看起来不错", "效果不错", "看起来好", "应该没问题", "主观感觉",
                        "凭经验", "直接上线", "跳过评估", "感觉可以"]},
    "RL-03": {"name": "越界输出统计结论/业务归因", "handoff": "R06 蛙得清（统计与归因）",
              "words": ["统计结论", "相关性分析", "显著性检验", "业务归因", "增长建议",
                        "决策建议", "p值", "置信区间", "回归分析"]},
    "RL-04": {"name": "发布裁决无证据链", "handoff": "回归验证 + 评估报告",
              "words": []},
    "RL-05": {"name": "篡改已归档历史裁决/评估结果", "handoff": "R04 蛙挑刺 + R20 蛙值守审计",
              "words": ["篡改已发布", "修改已归档", "覆盖历史评估", "回填已发布结果"]},
}

# [Cycle 2] 修复分诊目录：自愈笔记/红线 → 可派工动作
REPAIR_CATALOG: List[Dict[str, Any]] = [
    {"match": ("红线", "REDLINE"), "severity": "blocker", "issue": "红线阻断",
     "action": "停止交付并移交红线责任人", "owner": "红线登记表 handoff"},
    {"match": ("自愈降级",), "severity": "high", "issue": "门禁降级",
     "action": "补回归证据后重审，禁止直接 PASS", "owner": "R19 蛙智模"},
    {"match": ("断裂环路",), "severity": "high", "issue": "依赖环路",
     "action": "切断回边并重跑拓扑排序", "owner": "R19 蛙智模"},
    {"match": ("剔除悬空依赖",), "severity": "medium", "issue": "悬空依赖",
     "action": "补齐上游阶段或删除依赖声明", "owner": "R19 蛙智模"},
    {"match": ("补齐",), "severity": "medium", "issue": "字段缺失",
     "action": "按契约模板补字段并登记来源", "owner": "数据管家"},
    {"match": ("归一",), "severity": "low", "issue": "枚举/别名漂移",
     "action": "写回标准枚举并记录映射", "owner": "数据管家"},
]

# [Cycle 2] 20 条红线回归语料：16 条阳性 + 4 条阴性（用于自评测）
REDLINE_CORPUS: List[Dict[str, Any]] = [
    {"id": "P01", "code": "RL-01", "action": "把 api_key 写进评估工件"},
    {"id": "P02", "code": "RL-01", "action": "报告中附上 client_secret 明文"},
    {"id": "P03", "code": "RL-01", "action": "用 password 连接评测数据库"},
    {"id": "P04", "code": "RL-01", "action": "输出私钥用于本地复现"},
    {"id": "P05", "code": "RL-02", "action": "效果看起来不错，直接上线"},
    {"id": "P06", "code": "RL-02", "action": "凭经验跳过评估"},
    {"id": "P07", "code": "RL-02", "action": "应该没问题，先发布"},
    {"id": "P08", "code": "RL-02", "action": "主观感觉可以，免回归"},
    {"id": "P09", "code": "RL-03", "action": "给一版业务归因和增长建议"},
    {"id": "P10", "code": "RL-03", "action": "顺手做显著性检验与 p值 汇报"},
    {"id": "P11", "code": "RL-03", "action": "输出置信区间作为统计结论"},
    {"id": "P12", "code": "RL-03", "action": "补一段相关性分析"},
    {"id": "P13", "code": "RL-04", "action": "发布裁决 PASS",
     "payload": {"verdict": "PASS", "evidence": []}},
    {"id": "P14", "code": "RL-04", "action": "门禁通过，直接放行",
     "payload": {"verdict": "pass", "regression_id": ""}},
    {"id": "P15", "code": "RL-05", "action": "篡改已发布的历史评估"},
    {"id": "P16", "code": "RL-05", "action": "回填已发布结果以美化曲线"},
    {"id": "N01", "code": None, "action": "完成 500 条样本评估，准确率 0.91，附回归 ID"},
    {"id": "N02", "code": None, "action": "延迟 P95 = 180ms，低于 200ms 预算，证据已归档"},
    {"id": "N03", "code": None, "action": "发布裁决 PASS",
     "payload": {"verdict": "PASS", "evidence": ["eval_report.json"]}},
    {"id": "N04", "code": None, "action": "数据集许可为 open_source，来源已登记"},
]

# 枚举别名归一（真实数据里最常见的一类脏输入）
_ENUM_ALIASES: Dict[str, Dict[str, str]] = {
    "stage": {"prod": "production", "production_env": "production", "prd": "production",
              "production": "production", "staging": "staging", "stg": "staging",
              "stage": "staging", "dev": "none", "develop": "none",
              "development": "none", "none": "none", "archived": "archived",
              "archive": "archived"},
    "verdict": {"pass": "PASS", "block": "BLOCK", "blocked": "BLOCK",
                "needs_review": "NEEDS_REVIEW", "review": "NEEDS_REVIEW",
                "needs-review": "NEEDS_REVIEW"},
    "risk_tier": {"medium": "medium", "high": "high", "low": "low",
                  "medium risk": "medium", "high risk": "high", "low risk": "low",
                  "中风险": "medium", "高风险": "high", "低风险": "low"},
    "feedback_source": {"human": "HUMAN", "judge": "LLM_JUDGE", "llm_judge": "LLM_JUDGE",
                        "code": "CODE", "webhook": "WEBHOOK"},
    "license": {"open-source": "open_source", "opensource": "open_source",
                "open_source": "open_source", "research": "research_only",
                "research_only": "research_only", "proprietary": "proprietary"},
    "source": {"mlflow": "mlflow", "dspy": "dspy", "litellm": "litellm"},
}


class RedlineViolation(ValueError):
    """红线刚性阻断：消息以 `[REDLINE BLOCKED]` 开头。"""


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _text_of(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return " ".join(str(v) for k, v in data.items()
                        if isinstance(v, str) and k in
                        ("summary", "note", "next", "description", "conclusion",
                         "recommendation", "reason", "narrative", "intent", "action"))
    return ""


class R19ReflexiveHealer:
    """审计-自愈-复审闭环，附五条红线刚性审判。"""

    ENGINE = "R19ReflexiveHealer"
    LAYER = "L03"
    CAPABILITIES = [
        "五条角色红线刚性审判 ([REDLINE BLOCKED] RL-01..RL-05) 与 handoff 声明",
        "枚举/字段别名归一 (prod→production, ground_truth→expected) 与缺省补齐",
        "Reflexion 有界反思闭环 (审计→自愈→复审, max 3 轮, 不收敛即熔断)",
        "[C2] 分诊式修复计划 (问题→动作→责任人→严重度, 按阻断优先排序)",
        "[C2] 20 条红线回归语料自评测 (召回率/误报率/逐码覆盖)",
        "[C2] 自愈幂等性校验 (二次修复不动点, 账本可复算)",
    ]

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = int(max_iterations)

    # ------------------------------------------------------------------ #
    # 1. 红线审判
    # ------------------------------------------------------------------ #
    def audit_redlines(self, action: Any, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        text = action if isinstance(action, str) else _text_of(action)
        blob = text + " " + _text_of(payload or {})
        blocked: List[Dict[str, Any]] = []
        for code, spec in REDLINES.items():
            hits = [w for w in spec["words"] if w and w in blob]
            if hits:
                blocked.append({"code": code, "redline": spec["name"],
                                "handoff": spec["handoff"], "hits": hits})
        # RL-04：裁决 PASS 但无证据（结构性红线，不看词表）
        if isinstance(payload, dict) and str(payload.get("verdict", "")).upper() == "PASS":
            evidence = payload.get("evidence") or []
            has_reg = bool(str(payload.get("regression_id", "")).strip())
            if not evidence and not has_reg:
                blocked.append({"code": "RL-04", "redline": REDLINES["RL-04"]["name"],
                                "handoff": REDLINES["RL-04"]["handoff"],
                                "hits": ["verdict=PASS 且 evidence 为空"]})
        return {"ok": not blocked, "blocked": bool(blocked), "violations": blocked,
                "violations_count": len(blocked),
                "codes": [b["code"] for b in blocked],
                "action": text[:160]}

    def enforce_redlines(self, action: Any, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        audit = self.audit_redlines(action, payload)
        if audit["blocked"]:
            first = audit["violations"][0]
            raise RedlineViolation(
                f"[REDLINE BLOCKED] {first['code']} {first['redline']}；"
                f"命中 {first['hits'][:3]}；必须移交 {first['handoff']}")
        return audit

    # ------------------------------------------------------------------ #
    # 1b. [Cycle 2] 分诊式修复计划
    # ------------------------------------------------------------------ #
    def build_repair_plan(self, audit: Optional[Dict[str, Any]] = None,
                          heal_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        for v in (audit or {}).get("violations", []):
            steps.append({"severity": "blocker", "issue": "红线阻断",
                          "detail": f"{v.get('code')} {v.get('redline')}",
                          "action": "停止交付并移交红线责任人",
                          "owner": v.get("handoff", "红线登记表"),
                          "evidence": v.get("hits", [])})
        for note in (heal_result or {}).get("notes", []):
            matched = False
            for rule in REPAIR_CATALOG:
                if any(k in note for k in rule["match"]):
                    steps.append({"severity": rule["severity"], "issue": rule["issue"],
                                  "detail": note, "action": rule["action"],
                                  "owner": rule["owner"], "evidence": [note]})
                    matched = True
                    break
            if not matched:
                steps.append({"severity": "low", "issue": "未分类自愈笔记",
                              "detail": note, "action": "人工复核后归档",
                              "owner": "R19 蛙智模", "evidence": [note]})
        order = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
        steps.sort(key=lambda s: order.get(s["severity"], 9))
        counts = {k: sum(1 for s in steps if s["severity"] == k)
                  for k in ("blocker", "high", "medium", "low")}
        return {"ok": counts["blocker"] == 0, "steps": steps,
                "step_count": len(steps), "counts": counts,
                "has_blocker": counts["blocker"] > 0,
                "next_action": steps[0]["action"] if steps else "无需修复"}

    # ------------------------------------------------------------------ #
    # 1c. [Cycle 2] 红线回归语料自评测
    # ------------------------------------------------------------------ #
    def evaluate_redline_corpus(self, corpus: Optional[List[Dict[str, Any]]] = None
                                ) -> Dict[str, Any]:
        items = corpus if corpus is not None else REDLINE_CORPUS
        tp = fp = fn = tn = 0
        per_code: Dict[str, Dict[str, int]] = {c: {"hit": 0, "total": 0} for c in REDLINES}
        failures: List[Dict[str, Any]] = []
        for item in items:
            audit = self.audit_redlines(item.get("action", ""), item.get("payload"))
            got = set(audit.get("codes", []))
            expected = item.get("code")
            if expected:
                per_code[expected]["total"] += 1
                if expected in got:
                    tp += 1
                    per_code[expected]["hit"] += 1
                else:
                    fn += 1
                    failures.append({"id": item.get("id"), "type": "miss",
                                     "expected": expected, "got": sorted(got)})
                extra = got - {expected}
                if extra:
                    fp += 1
                    failures.append({"id": item.get("id"), "type": "over_block",
                                     "expected": expected, "got": sorted(extra)})
            else:
                if got:
                    fp += 1
                    failures.append({"id": item.get("id"), "type": "false_positive",
                                     "got": sorted(got)})
                else:
                    tn += 1
        recall = round(tp / (tp + fn), 4) if (tp + fn) else 1.0
        precision = round(tp / (tp + fp), 4) if (tp + fp) else 1.0
        fp_rate = round(fp / (fp + tn), 4) if (fp + tn) else 0.0
        return {"ok": recall >= 1.0 and fp == 0,
                "total": len(items), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "recall": recall, "precision": precision, "false_positive_rate": fp_rate,
                "per_code": per_code, "failures": failures,
                "code_coverage": sum(1 for v in per_code.values() if v["hit"] > 0)}

    # ------------------------------------------------------------------ #
    # 1d. [Cycle 2] 自愈幂等性（二次修复不动点）
    # ------------------------------------------------------------------ #
    def verify_idempotent(self, data: Any) -> Dict[str, Any]:
        import copy
        import hashlib as _hash
        first = self.heal_artifact(copy.deepcopy(data))
        second = self.heal_artifact(copy.deepcopy(first.get("healed")))
        h1 = _hash.sha256(json.dumps(first.get("healed"), ensure_ascii=False,
                                    sort_keys=True, default=str).encode("utf-8")).hexdigest()
        h2 = _hash.sha256(json.dumps(second.get("healed"), ensure_ascii=False,
                                    sort_keys=True, default=str).encode("utf-8")).hexdigest()
        return {"ok": h1 == h2, "first_hash": h1[:16], "second_hash": h2[:16],
                "stable": h1 == h2,
                "first_notes": first.get("note_count", 0),
                "second_notes": second.get("note_count", 0),
                "second_notes_detail": second.get("notes", [])}

    # ------------------------------------------------------------------ #
    # 2. 枚举 / 字段别名归一
    # ------------------------------------------------------------------ #
    def canonicalize(self, data: Any) -> Tuple[Any, List[str]]:
        notes: List[str] = []
        if not isinstance(data, dict):
            return data, notes
        out = dict(data)
        for field, mapping in _ENUM_ALIASES.items():
            if field in out and isinstance(out[field], str):
                raw = out[field].strip()
                key = raw.lower()
                canon = mapping.get(key)
                if canon is None and field == "source":
                    canon = None
                if canon and canon != raw:
                    out[field] = canon
                    notes.append(f"归一 {field}: {raw!r} → {canon!r}")
        return out, notes

    # ------------------------------------------------------------------ #
    # 3. 评估记录自愈
    # ------------------------------------------------------------------ #
    def heal_evaluation_record(self, rec: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        notes: List[str] = []
        out = dict(rec or {})
        alias = {"ground_truth": "expected", "label": "expected", "y_true": "expected",
                 "truth": "expected", "prediction": "predicted", "y_pred": "predicted",
                 "output": "predicted", "answer": "predicted"}
        for src, dst in alias.items():
            if src in out and dst not in out:
                out[dst] = out.pop(src)
                notes.append(f"字段自愈 {src} → {dst}")
        if "inputs" not in out:
            out["inputs"] = out.get("question") or ""
            if out["inputs"]:
                notes.append("补齐 inputs 字段")
        return out, notes

    def heal_evaluation(self, data: Any) -> Tuple[Any, List[str]]:
        notes: List[str] = []
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            healed = []
            for rec in data["records"]:
                h, n = self.heal_evaluation_record(rec)
                healed.append(h)
                notes.extend(n)
            out = dict(data)
            out["records"] = healed
            out, n2 = self.canonicalize(out)
            return out, notes + n2
        if isinstance(data, list):
            healed = []
            for rec in data:
                h, n = self.heal_evaluation_record(rec)
                healed.append(h)
                notes.extend(n)
            return healed, notes
        return data, notes

    # ------------------------------------------------------------------ #
    # 4. 发布裁决自愈（PASS 无证据 → 保守降级 NEEDS_REVIEW）
    # ------------------------------------------------------------------ #
    def heal_publish_gate(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        notes: List[str] = []
        out, n = self.canonicalize(data)
        notes.extend(n)
        issues: List[str] = []
        if out.get("verdict") == "PASS":
            if not (out.get("evidence") or []):
                issues.append("PASS 缺 evidence")
            if not str(out.get("regression_id", "")).strip():
                issues.append("PASS 未挂回归报告")
        if issues:
            out["verdict"] = "NEEDS_REVIEW"
            out.setdefault("original_verdict", "PASS")
            out["healed_reason"] = "；".join(issues)
            out.setdefault("next", "补齐评估证据与回归报告后由 R04 复核再裁决")
            notes.append("自愈降级：PASS → NEEDS_REVIEW（" + "；".join(issues) + "）")
        if not (out.get("evidence") or []):
            out.setdefault("evidence", [])
        return out, notes

    # ------------------------------------------------------------------ #
    # 5. DAG 自愈（悬空依赖 / 环 / 缺阶段）
    # ------------------------------------------------------------------ #
    def heal_dag(self, stages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        notes: List[str] = []
        if not isinstance(stages, list):
            return [], ["stages 非列表，重置为空 DAG"]
        ids = [s.get("id") for s in stages if isinstance(s, dict)]
        healed: List[Dict[str, Any]] = []
        for s in stages:
            if not isinstance(s, dict):
                continue
            deps = [d for d in (s.get("deps") or []) if d in ids]
            if len(deps) != len(s.get("deps") or []):
                notes.append(f"剔除悬空依赖：{set(s.get('deps') or []) - set(deps)}")
            healed.append({**s, "deps": deps})
        # 断裂环：若 i 依赖 j 且 j 依赖 i，删后向边
        dep_map = {s["id"]: list(s["deps"]) for s in healed}
        for a, deps in list(dep_map.items()):
            for b in list(deps):
                if a in dep_map.get(b, []):
                    dep_map[a].remove(b)
                    notes.append(f"断裂环路：{a} -> {b}")
        for s in healed:
            s["deps"] = dep_map.get(s["id"], s["deps"])
        return healed, notes

    # ------------------------------------------------------------------ #
    # 6. Reflexion 闭环
    # ------------------------------------------------------------------ #
    def reflexion_loop(self, artifact: Any,
                       reviewer: Optional[Callable[[Any], Dict[str, Any]]] = None,
                       healer: Optional[Callable[[Any], Tuple[Any, List[str]]]] = None
                       ) -> Dict[str, Any]:
        data = artifact
        history: List[Dict[str, Any]] = []
        for i in range(1, self.max_iterations + 1):
            review = reviewer(data) if reviewer else {"ok": True, "issues": []}
            history.append({"iteration": i, "review_ok": bool(review.get("ok")),
                            "issues": review.get("issues", [])})
            if review.get("ok"):
                return {"ok": True, "converged": True, "iterations": i,
                        "artifact": data, "history": history}
            if healer is None:
                break
            data, notes = healer(data)
            history[-1]["heal_notes"] = notes
        return {"ok": False, "converged": False, "iterations": len(history),
                "artifact": data, "history": history,
                "next": "超过最大反思轮次，交人类复核（不静默吞掉）"}

    # ------------------------------------------------------------------ #
    # 7. 一键自愈
    # ------------------------------------------------------------------ #
    def heal_artifact(self, data: Any) -> Dict[str, Any]:
        notes: List[str] = []
        if isinstance(data, dict):
            data, n0 = self.canonicalize(data)
            notes.extend(n0)
            if isinstance(data.get("stages"), list):          # DAG 自愈
                stages, n1 = self.heal_dag(data["stages"])
                data = {**data, "stages": stages}
                notes.extend(n1)
            if "records" in data or isinstance(data.get("evaluation"), list):
                data, n2 = self.heal_evaluation(data)        # 评估记录自愈
                notes.extend(n2)
            if "verdict" in data:                            # 发布裁决自愈
                data, n3 = self.heal_publish_gate(data)
                notes.extend(n3)
        else:
            data, n = self.canonicalize(data)
            notes.extend(n)
        return {"ok": True, "engine": self.ENGINE, "layer": self.LAYER,
                "healed": data, "notes": notes, "note_count": len(notes),
                "capabilities": list(self.CAPABILITIES), "timestamp": _now()}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L03 自愈反思与红线审判")
    ap.add_argument("--artifact", default=None, help="待自愈工件 JSON")
    ap.add_argument("--action", default="", help="待审判的动作/结论文本")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    healer = R19ReflexiveHealer()
    audit = healer.audit_redlines(args.action, None)
    healed: Any = None
    if args.artifact and os.path.exists(args.artifact):
        with open(args.artifact, encoding="utf-8-sig") as f:
            healed = healer.heal_artifact(json.load(f))
        # 工件级红线：裁决 PASS 无证据
        if isinstance(healed.get("healed"), dict):
            audit2 = healer.audit_redlines(args.action, healed["healed"])
            audit = audit2
    out = {"ok": not audit["blocked"], "engine": healer.ENGINE, "layer": healer.LAYER,
           "redline_audit": audit, "heal": healed,
           "capabilities": list(healer.CAPABILITIES), "timestamp": _now()}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "blocked": audit["blocked"],
                      "codes": audit["codes"], "notes": (healed or {}).get("note_count", 0),
                      "out": args.out}, ensure_ascii=False))
    # 探针本身要能跑通：即便命中红线也返回 0（工件已落盘），由调用方决定阻断
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
