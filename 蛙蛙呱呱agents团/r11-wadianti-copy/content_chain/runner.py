# -*- coding: utf-8 -*-
"""内容链 runner：一条命令跑完 7 段，产出 7 个 JSON + final.md/html + chain_manifest.json。

manifest 记录每段 sha256、门禁结果与跨段一致性：
  - outline / draft / review / rewrite 的章节 id 必须一致；
  - research.claims 的数字集合必须覆盖 final 正文的全部数字；
  - 任一段门禁失败，整链退出码为 1，但工件仍落盘以便定位。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import draft as draft_stage
from . import final as final_stage
from . import outline as outline_stage
from . import research as research_stage
from . import review as review_stage
from . import rewrite as rewrite_stage
from . import topic as topic_stage
from .common import (FILES, THRESHOLDS, ck, claim_numbers, gate, now_iso,
                     read_json, sha256_file, write_json, write_text)


def run(brief_path: str, out_dir: str) -> Dict[str, Any]:
    brief = read_json(brief_path)
    os.makedirs(out_dir, exist_ok=True)

    t = topic_stage.build(brief)
    r = research_stage.build(t, brief)
    o = outline_stage.build(r, brief)
    d = draft_stage.build(o, r, brief)
    rv = review_stage.build(d)
    rq = rewrite_stage.build(d, rv, brief)
    text = final_stage.compose(d, rq, r, brief)
    fa = final_stage.audit(text, o, r, brief)

    staged = [("topic", t), ("research", r), ("outline", o), ("draft", d),
              ("review", rv), ("rewrite", rq), ("final", fa)]
    paths: Dict[str, str] = {}
    for name, artifact in staged:
        p = os.path.join(out_dir, FILES[name])
        write_json(p, artifact)
        paths[name] = p
    write_text(os.path.join(out_dir, "final.md"), text)
    html = final_stage.render_html(text, fa)
    write_text(os.path.join(out_dir, "final.html"), html)

    cross = cross_checks(t, r, o, d, rv, rq, fa, text)
    stages = []
    for name, _ in staged:
        p = paths[name]
        artifact = {"topic": t, "research": r, "outline": o, "draft": d,
                    "review": rv, "rewrite": rq, "final": fa}[name]
        stages.append({
            "stage": name,
            "file": os.path.basename(p),
            "sha256": sha256_file(p),
            "ok": bool((artifact.get("gate") or {}).get("ok")),
            "grade": (artifact.get("gate") or {}).get("grade"),
        })
    stage_gate_checks = [ck(s["ok"], "%s 门禁 %s" % (s["stage"], s["grade"]),
                            "manifest.stage." + s["stage"],
                            "CRITICAL" if not s["ok"] else "OK") for s in stages]
    manifest: Dict[str, Any] = {
        "artifact": "chain_manifest",
        "version": "1.0",
        "generated_at": now_iso(),
        "brief_path": os.path.abspath(brief_path),
        "brief_id": str(brief.get("brief_id") or ""),
        "out_dir": os.path.abspath(out_dir),
        "outputs": {
            "markdown": os.path.abspath(os.path.join(out_dir, "final.md")),
            "html": os.path.abspath(os.path.join(out_dir, "final.html")),
        },
        "thresholds": THRESHOLDS,
        "stages": stages,
        "cross_checks": cross,
        "gate": gate(stage_gate_checks + cross, "manifest"),
    }
    write_json(os.path.join(out_dir, "chain_manifest.json"), manifest)
    return manifest


def cross_checks(t: Dict[str, Any], r: Dict[str, Any], o: Dict[str, Any],
                 d: Dict[str, Any], rv: Dict[str, Any], rq: Dict[str, Any],
                 fa: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    t_id = str(t.get("selected", ""))
    ids = {"research": str(r.get("topic_id", "")), "outline": str(o.get("topic_id", "")),
           "draft": str(d.get("topic_id", "")), "review": str(rv.get("topic_id", "")),
           "rewrite": str(rq.get("topic_id", ""))}
    bad_topic = [k for k, v in ids.items() if v != t_id]
    checks.append(ck(not bad_topic, "topic 选择贯穿 7 段", "manifest.topic",
                     "CRITICAL" if bad_topic else "OK", offenders=bad_topic))

    chapters = {
        "outline": list(o.get("chapter_ids") or []),
        "draft": list(d.get("chapter_ids") or []),
        "review": list(rv.get("chapter_ids") or []),
        "rewrite": list(rq.get("chapter_ids") or []),
    }
    base = chapters["outline"]
    bad_ch = [k for k, v in chapters.items() if v != base]
    checks.append(ck(not bad_ch, "outline 章节 = draft / review / rewrite 章节",
                     "manifest.chapters", "CRITICAL" if bad_ch else "OK",
                     offenders=bad_ch, chapters=base))

    claims = claim_numbers(r) | set((fa.get("numbers") or {}).get("claims") or [])
    from .common import number_set
    final_nums = number_set(text)
    extra = sorted(final_nums - claims)
    checks.append(ck(not extra, "claims 数字覆盖 final 数字", "manifest.numbers",
                     "CRITICAL" if extra else "OK", offenders=extra,
                     final=sorted(final_nums), claims=sorted(claims)))

    low = [s.get("id") for s in (rq.get("sections") or [])
           if float(s.get("coverage") or 0) < 1.0]
    checks.append(ck(not low, "改写覆盖率全部 100%", "manifest.coverage",
                     "CRITICAL" if low else "OK", offenders=low))
    checks.append(ck(bool(fa.get("gate", {}).get("ok")), "final 终检通过",
                     "manifest.final_gate",
                     "CRITICAL" if not fa.get("gate", {}).get("ok") else "OK"))
    return checks


def audit_dir(out_dir: str) -> Dict[str, Any]:
    """对已落盘的链产物做独立复核，不重新生成。"""
    arts: Dict[str, Any] = {}
    missing = []
    for name, fname in FILES.items():
        p = os.path.join(out_dir, fname)
        if not os.path.isfile(p):
            missing.append(fname)
            continue
        arts[name] = read_json(p)
    md_path = os.path.join(out_dir, "final.md")
    text = ""
    if os.path.isfile(md_path):
        with open(md_path, encoding="utf-8") as f:
            text = f.read()
    else:
        missing.append("final.md")

    checks: List[Dict[str, Any]] = []
    checks.append(ck(not missing, "7 个 JSON 与 final.md 齐备", "audit.files",
                     "CRITICAL" if missing else "OK", offenders=missing))
    if missing:
        return {"artifact": "chain_audit", "ok": False, "gate": gate(checks, "audit")}
    for name, a in arts.items():
        ok = bool((a.get("gate") or {}).get("ok"))
        checks.append(ck(ok, "%s 门禁通过" % name, "audit." + name,
                         "CRITICAL" if not ok else "OK"))
    checks += cross_checks(arts["topic"], arts["research"], arts["outline"],
                           arts["draft"], arts["review"], arts["rewrite"],
                           arts["final"], text)
    return {"artifact": "chain_audit", "version": "1.0", "generated_at": now_iso(),
            "out_dir": os.path.abspath(out_dir), "gate": gate(checks, "audit")}
