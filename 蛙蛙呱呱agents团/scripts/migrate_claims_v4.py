# -*- coding: utf-8 -*-
"""把旧 claims（sections 长文）迁移成 v4 判断单元，再交给 flow 渲染。

用法：
    python scripts/migrate_claims_map.py --project <项目> [--claims <旧合并稿>]

产出：<项目>/out/claims_map.json（含 claims + 由映射层生成的 sections）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.claims import claims as claims_map  # noqa: E402  P5-4：映射层已并入 claims


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _clean(t: str) -> str:
    t = re.sub(r"^【[^】]{1,6}】", "", str(t or "").strip())
    t = re.sub(r"^[一二三四五六七八九十]+、", "", t)
    return t.strip()


def _first_sentence(t: str, n: int = 80) -> str:
    head, sep, _ = _clean(t).partition("。")
    out = (head + "。") if sep else _clean(t)
    return out if len(out) <= n else out[: n - 2] + "…"


def _blocks(sec: dict):
    fact = mech = rebut = act = ""
    for r in sec.get("reading") or []:
        txt = str(r.get("text") or "")
        st = str(r.get("strong") or "")
        key = "事实" if "事实" in st else ("机理" if "机理" in st else
                                       ("反例" if "反例" in st else
                                        ("所以" if "所以" in st else "")))
        if not key:
            if "【事实】" in txt:
                key = "事实"
            elif "【机理】" in txt:
                key = "机理"
            elif "【反例】" in txt:
                key = "反例"
            elif txt.startswith("所以"):
                key = "所以"
        if key == "事实" and not fact:
            fact = txt
        elif key == "机理" and not mech:
            mech = txt
        elif key == "反例" and not rebut:
            rebut = txt
        elif key == "所以" and not act:
            act = txt
    return fact, mech, rebut, act


def _dedupe(text: str, seen: set) -> str:
    """迁移时去掉跨节重复句：旧稿里同一句口径会反复出现。"""
    parts = re.split(r"(?<=[。！？；])", str(text or ""))
    out = []
    for p in parts:
        k = re.sub(r"\s+", "", p)[:60]
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(p)
    return "".join(out).strip()


def migrate(project: Path, claims_path: Path) -> dict:
    old = _load(claims_path, {}) or {}
    clarify = _load(project / "clarify.json") or _load(project / "out" / "clarify.json") or {}
    must = {a["id"] for a in clarify.get("asks") or [] if a.get("must")}
    nums = {str(n.get("id")): n for n in old.get("numbers") or []}
    claims = []
    seen: set = set()
    for i, sec in enumerate(old.get("sections") or [], 1):
        fact, mech, rebut, act = _blocks(sec)
        fact, mech, rebut, act = (_dedupe(fact, seen), _dedupe(mech, seen),
                                  _dedupe(rebut, seen), _dedupe(act, seen))
        rows = []
        ch = sec.get("chart") or {}
        unit = str(ch.get("unit_meta") or "")
        # 旧图原样保留（它当初过了校验）；refs 用本节 refs
        for b in (ch.get("bars") or ch.get("items") or ch.get("points") or []):
            if b.get("value") is None:
                continue
            try:
                v = float(b["value"])
            except (TypeError, ValueError):
                continue
            rows.append({"label": str(b.get("label")), "value": v})
        if len(rows) < 2:
            rows = []
            for ref in sec.get("refs") or []:
                n = nums.get(str(ref))
                if not n or n.get("value") in (None, ""):
                    continue
                try:
                    v = float(n["value"])
                except (TypeError, ValueError):
                    continue
                unit = unit or str(n.get("unit") or "")
                lab = re.sub(r"^(全国|中国|北京|内蒙古|全区)", "", str(n.get("name") or ""))
                rows.append({"label": lab[:18], "value": v})
                if len(rows) >= 6:
                    break
        if len(rows) < 2:
            continue
        answers = [a for a in (sec.get("answers") or []) if a]
        if not answers:
            m = re.match(r"^\s*(Q\d+)", str(sec.get("question") or ""))
            if m:
                answers = [m.group(1)]
        tier = "main" if (set(answers) & must) else "support"
        findings = claims_map.detect(rows, str(ch.get("unit_meta") or ""))
        claim_text = _first_sentence(fact or sec.get("title") or "")
        if not re.search(r"\d", claim_text):
            claim_text = _first_sentence(sec.get("title") or claim_text)
        claims.append({
            "id": f"C{i}", "qid": (answers[0] if answers else ""),
            "answers": answers,
            "tier": tier,
            "claim": claim_text,
            "question": str(sec.get("question") or ""),
            "rows": rows,
            "encoding": {"mark": "bar", "x": "value", "y": "label"},
            "unit": str(ch.get("unit_meta") or unit or ""),
            "findings": findings,
            "warrant": _clean(mech) or "待补机理",
            "rebuttal": _clean(rebut),
            "qualifier": str(sec.get("boundary") or ""),
            "action": _clean(act),
            "refs": sec.get("refs") or [],
            "falsifier": str(sec.get("falsifier") or
                             "若关键数字偏离 20% 或口径变化，本节结论作废"),
            "legacy": True,
        })
    stand = next((c["claim"] for c in claims if re.search(r"\d", c["claim"])), "")
    doc = {"numbers": old.get("numbers") or [], "sources": old.get("sources") or [],
           "meta": old.get("meta") or {}, "claims": claims, "standfirst": stand,
           "boundaries": [f"{c['id']}: {c['qualifier']}" for c in claims if c.get("qualifier")]
           or ["旧稿迁移：边界待补"]}
    secs = claims_map.build_sections(doc)
    # 第二遍：跨节去重（门禁按归一化句子算重复，这里同口径处理）
    seen2: set = set()
    for sec in secs:
        for rd in sec.get("reading") or []:
            parts = re.split(r"(?<=[。！？；])", str(rd.get("text") or ""))
            keep = []
            for part in parts:
                key = re.sub(r"[\d\s%．.，,、；;：:（）()]", "", part)[:60]
                if not key or key in seen2:
                    continue
                seen2.add(key)
                keep.append(part)
            rd["text"] = "".join(keep).strip()
    doc["sections"] = secs
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--claims", default="")
    a = ap.parse_args()
    project = Path(a.project)
    src = Path(a.claims) if a.claims else (project / "out" / "claims_merged.json")
    doc = migrate(project, src)
    out = project / "out" / "claims_map.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    errs = claims_map.validate_v4(doc["claims"])
    print(json.dumps({"ok": True, "claims": len(doc["claims"]),
                      "main": sum(1 for c in doc["claims"] if c["tier"] == "main"),
                      "support": sum(1 for c in doc["claims"] if c["tier"] == "support"),
                      "sections": len(doc["sections"]),
                      "errors": errs[:8], "out": str(out)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
