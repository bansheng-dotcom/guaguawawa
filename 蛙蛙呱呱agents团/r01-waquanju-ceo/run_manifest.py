#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 报告级运行账本（run-manifest）：把每一步决策与工件钉死在账本上。

为什么需要它（升级方案 §15 Tier C）：
    R01 是唯一报告作者，但此前只有「运行日志」（skill/action/exit_code），
    无法回答「这份经营决策包里的每个工件是谁在哪个阶段产出、输入是什么、
    决策理由是什么、不可逆动作有没有签名位、文件有没有被手改」。
    本模块把一次经营决策产线写成一条**可复核的账本**：

        stage（阶段） ─ inputs（上游工件） ─ outputs（工件 + sha256）
                      └ decision（阶段决策） ─ signoff（签名位）

门禁（确定性，失败即拒绝）：
    M00_SCHEMA           账本版本不对
    M01_STAGE_ORDER      阶段序号不连续 / 重复 / 乱序
    M02_MISSING_SHA256   工件缺 sha256（账本无法防篡改）
    M03_MISSING_DECISION 阶段没有决策（只有动作没有判断）
    M04_UNTRACEABLE_INPUT 输入工件不由任何更早阶段产出（追不到来源）
    M05_HASH_MISMATCH    磁盘工件与账本 sha256 不一致（被手改）
    M06_MISSING_SIGNOFF  不可逆阶段没有签名位 / 未签字
    M07_DUPLICATE_ARTIFACT 同一工件名被两个阶段重复登记
    M08_ARTIFACT_MISSING 账本登记的工件在磁盘上不存在

用法：
    python run_manifest.py verify --file golden/run-manifest.json [--dir golden/artifacts]
    python run_manifest.py trace  --file golden/run-manifest.json
    python run_manifest.py check  --case misuse/manifest-missing-sha.json
    python run_manifest.py goldens            # 重建 golden/*.html + 账本
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "guagua.run-manifest/v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ERRORS = {
    "M00_SCHEMA": "账本 schema 不是 " + SCHEMA,
    "M01_STAGE_ORDER": "阶段序号必须从 1 连续递增且不重复",
    "M02_MISSING_SHA256": "工件缺 sha256，账本无法防篡改",
    "M03_MISSING_DECISION": "阶段没有决策（只记录动作不算账本）",
    "M04_UNTRACEABLE_INPUT": "输入工件不由任何更早阶段产出，追不到来源",
    "M05_HASH_MISMATCH": "磁盘工件 sha256 与账本不一致（可能被手改）",
    "M06_MISSING_SIGNOFF": "不可逆阶段缺签名位或未签字",
    "M07_DUPLICATE_ARTIFACT": "同一工件名被重复登记",
    "M08_ARTIFACT_MISSING": "账本登记的工件在磁盘上不存在",
}


# --------------------------------------------------------------------------- #
# 哈希与基础读写
# --------------------------------------------------------------------------- #
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --------------------------------------------------------------------------- #
# 账本构建 / 校验 / 追踪
# --------------------------------------------------------------------------- #
def make_stage(seq: int, stage: str, inputs: List[str], outputs: List[Dict[str, Any]],
               decision: str, owner: str = "r01",
               irreversible: bool = False,
               signoff: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"seq": seq, "stage": stage, "owner": owner, "inputs": list(inputs),
            "outputs": list(outputs), "decision": decision,
            "irreversible": bool(irreversible),
            "signoff": signoff or {"required": bool(irreversible),
                                   "by": None, "at": None}}


def build_manifest(run_id: str, title: str, stages: List[Dict[str, Any]],
                   created: str = "2026-11-27", role: str = "r01") -> Dict[str, Any]:
    return {"schema": SCHEMA, "run_id": run_id, "role": role, "title": title,
            "created": created, "stages": sorted(stages, key=lambda s: s["seq"])}


def verify_manifest(manifest: Dict[str, Any],
                    root: Optional[str] = None) -> Dict[str, Any]:
    """逐条核对账本；root 非空时同时重算磁盘工件 sha256。"""
    v: List[Dict[str, str]] = []

    def bad(code: str, detail: str) -> None:
        v.append({"code": code, "msg": ERRORS[code], "detail": detail})

    if manifest.get("schema") != SCHEMA:
        bad("M00_SCHEMA", str(manifest.get("schema")))

    stages = sorted(manifest.get("stages") or [], key=lambda s: s.get("seq", 0))
    seqs = [s.get("seq") for s in stages]
    if seqs != list(range(1, len(stages) + 1)):
        bad("M01_STAGE_ORDER", str(seqs))

    produced: Dict[str, int] = {}
    for st in stages:
        seq = st.get("seq")
        if not str(st.get("decision") or "").strip():
            bad("M03_MISSING_DECISION", f"stage {seq} {st.get('stage')}")
        for name in st.get("inputs") or []:
            if name not in produced:
                bad("M04_UNTRACEABLE_INPUT",
                    f"stage {seq} 输入 {name} 未由更早阶段产出")
        for art in st.get("outputs") or []:
            name = str(art.get("name") or "")
            digest = str(art.get("sha256") or "")
            if not HEX64.match(digest):
                bad("M02_MISSING_SHA256", f"stage {seq} 工件 {name or '?'}")
            if name in produced:
                bad("M07_DUPLICATE_ARTIFACT", f"{name} @ stage {produced[name]}&{seq}")
            produced[name] = seq
            if root:
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    bad("M08_ARTIFACT_MISSING", f"{name}")
                else:
                    real = sha256_file(path)
                    if HEX64.match(digest) and real != digest:
                        bad("M05_HASH_MISMATCH", f"{name}: {digest[:12]} != {real[:12]}")
        if st.get("irreversible"):
            so = st.get("signoff") or {}
            if not so.get("required") or not str(so.get("by") or "").strip():
                bad("M06_MISSING_SIGNOFF", f"stage {seq} {st.get('stage')}")

    return {"ok": not v, "violations": v, "stages": len(stages),
            "artifacts": len(produced), "trace": trace_steps(manifest)}


def trace_steps(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把账本摊平为「每一步」：阶段 → 输入 → 工件 → 决策 → 签名。"""
    out = []
    for st in sorted(manifest.get("stages") or [], key=lambda s: s.get("seq", 0)):
        out.append({
            "seq": st.get("seq"), "stage": st.get("stage"),
            "owner": st.get("owner"),
            "inputs": list(st.get("inputs") or []),
            "outputs": [{"name": a.get("name"), "sha256": a.get("sha256"),
                         "bytes": a.get("bytes")} for a in (st.get("outputs") or [])],
            "decision": st.get("decision"),
            "signed": bool((st.get("signoff") or {}).get("by")),
        })
    return out


def find_stage(manifest: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for st in manifest.get("stages") or []:
        for art in st.get("outputs") or []:
            if art.get("name") == name:
                return st
    return None


# --------------------------------------------------------------------------- #
# 误用样本：在黄金账本上做一次确定性篡改，验证门禁确实拦得住
# --------------------------------------------------------------------------- #
MUTATIONS = ("drop_sha", "break_trace", "drop_signoff", "reorder", "drop_decision")


def apply_mutations(manifest: Dict[str, Any], mutations: List[str]) -> Dict[str, Any]:
    m = json.loads(json.dumps(manifest))  # 深拷贝
    stages = m["stages"]
    for mut in mutations:
        if mut == "drop_sha":
            st = next(s for s in stages if len(s.get("outputs") or []) > 1)
            st["outputs"][1]["sha256"] = ""
        elif mut == "break_trace":
            st = next(s for s in stages if s["seq"] == 2)
            st["inputs"] = list(st["inputs"]) + ["board.json"]
        elif mut == "drop_signoff":
            st = next(s for s in stages if s.get("irreversible"))
            st["signoff"] = {"required": True, "by": None, "at": None}
        elif mut == "reorder":
            stages[1]["seq"] = stages[2]["seq"]
        elif mut == "drop_decision":
            stages[2]["decision"] = "  "
    return m


def check_case(path: str) -> Dict[str, Any]:
    spec = load_json(path)
    src = os.path.join(HERE, spec.get("source", "golden/run-manifest.json"))
    manifest = load_json(src)
    manifest = apply_mutations(manifest, spec.get("mutations") or [])
    out = verify_manifest(manifest)
    expect = set(spec.get("expect") or [])
    got = {x["code"] for x in out["violations"]}
    out.update({"case_id": spec.get("case_id"), "expect": sorted(expect),
                "hit": sorted(expect & got), "rejected": not out["ok"],
                "as_expected": bool(expect) and expect <= got})
    return out


# --------------------------------------------------------------------------- #
# 页面渲染（内联 CSS / A4 / 单主题 / 标题不跳级 / 表格带表头）
# --------------------------------------------------------------------------- #
def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
@page {{ size: A4; margin: 18mm; }}
:root {{ --paper:#ffffff; --ink:#111827; --muted:#4b5563; --faint:#6b7280; --line:#d1d5db; --accent:#0f766e; --accent-soft:#f0fdfa; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:32px 20px; background:var(--paper); color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; font-size:15px; }}
.sheet {{ max-width:920px; margin:0 auto; }}
h1 {{ font-size:28px; line-height:1.35; margin:0 0 6px; }}
h2 {{ font-size:20px; line-height:1.4; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--accent); }}
h3 {{ font-size:16px; line-height:1.45; margin:18px 0 8px; color:var(--accent); }}
p, li, td, th {{ font-size:14px; }}
.meta {{ font-size:12px; color:var(--muted); margin:0 0 18px; }}
.tag {{ display:inline-block; font-size:12px; padding:1px 8px; border-radius:4px; background:var(--accent-soft); color:var(--accent); }}
table {{ width:100%; border-collapse:collapse; margin:10px 0 16px; }}
thead th {{ background:var(--accent-soft); color:var(--ink); text-align:left; font-size:12.5px; }}
th, td {{ border:1px solid var(--line); padding:6px 8px; vertical-align:top; }}
code {{ font-size:12px; color:var(--muted); word-break:break-all; }}
.block {{ background:#f9fafb; border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; border-radius:4px; }}
figure, .block, section, tr {{ break-inside: avoid; }}
.fig-card {{ border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:12px 0; }}
.fig-sub {{ font-size:13px; color:var(--ink); margin:0 0 4px; }}
.fig-src, .fig-unit {{ font-size:12px; color:var(--muted); }}
</style>
</head>
<body data-theme="light">
<main class="sheet">
{body}
</main>
</body>
</html>
"""


def _short(digest: str) -> str:
    return (digest or "—")[:12]


def render_manifest_html(manifest: Dict[str, Any], verify: Dict[str, Any]) -> str:
    rows = []
    for st in trace_steps(manifest):
        arts = "".join(
            f"<div>{a['name']} · <code>{_short(a['sha256'])}</code></div>"
            for a in st["outputs"])
        rows.append(
            f"<tr><td>{st['seq']}</td><td>{st['stage']}</td>"
            f"<td>{'、'.join(st['inputs']) or '（起点）'}</td>"
            f"<td>{arts}</td><td>{st['decision']}</td>"
            f"<td>{'已签' if st['signed'] else '未要求'}</td></tr>")
    status = "PASS" if verify["ok"] else "FAIL"
    body = f"""
<h1>运行账本 · {manifest['title']}</h1>
<p class="meta">run_id {manifest['run_id']} ｜ 角色 {manifest['role']} ｜ 账本日期 {manifest['created']} ｜
门禁 <span class="tag">{status}</span> ｜ 阶段 {verify['stages']} ｜ 工件 {verify['artifacts']}</p>
<h2>1. 账本结论</h2>
<div class="block">每条阶段都登记了输入、工件 sha256、阶段决策与签名位；任一项缺失即拒绝出包。
本账本校验结果：{status}，违规 {len(verify['violations'])} 条。</div>
<h2>2. 逐步追踪</h2>
<table>
<thead><tr><th>序号</th><th>阶段</th><th>输入</th><th>工件（sha256 前 12 位）</th><th>阶段决策</th><th>签名</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<h2>3. 门禁明细</h2>
<table>
<thead><tr><th>错误码</th><th>含义</th><th>后果</th></tr></thead>
<tbody>
<tr><td>M02_MISSING_SHA256</td><td>工件缺哈希</td><td>拒绝签收</td></tr>
<tr><td>M04_UNTRACEABLE_INPUT</td><td>输入早于产出或不存在</td><td>拒绝签收</td></tr>
<tr><td>M05_HASH_MISMATCH</td><td>磁盘工件被手改</td><td>拒绝签收并回滚</td></tr>
<tr><td>M06_MISSING_SIGNOFF</td><td>不可逆动作未签字</td><td>升级创始人</td></tr>
</tbody>
</table>
<h3>3.1 复核方式</h3>
<p>运行 <code>python run_manifest.py verify --file golden/run-manifest.json --dir golden/artifacts</code>，
会重算每个工件 sha256；任何文件被改动都会以 M05 失败。</p>
"""
    return _page("运行账本 · " + manifest["title"], body)


def render_decision_pack_html(manifest: Dict[str, Any], verify: Dict[str, Any]) -> str:
    rows = []
    for st in manifest["stages"]:
        rows.append(f"<tr><td>{st['stage']}</td><td>{st['decision']}</td>"
                    f"<td>{'是' if st.get('irreversible') else '否'}</td></tr>")
    signed = [st for st in manifest["stages"] if st.get("irreversible")]
    so = (signed[0].get("signoff") if signed else {}) or {}
    body = f"""
<h1>经营决策包 · {manifest['title']}</h1>
<p class="meta">run_id {manifest['run_id']} ｜ 出具 R01 蛙全局 ｜ 账本校验 {"PASS" if verify['ok'] else "FAIL"} ｜
不可逆阶段签名 {so.get('by') or '—'} @ {so.get('at') or '—'}</p>
<h2>1. 结论先行</h2>
<div class="block">维持 99 元自助档，削减 12% 低效投放，供应链改双供应商；预计 6 周回补毛利率 2.4pt。
代价是短期新客增速下降 8%，用灰度对照验证。</div>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：预算再平衡前后毛利率与获客成本（示意口径，非真实财务数）</figcaption>
  <table>
    <thead><tr><th>指标</th><th>再平衡前</th><th>再平衡后（目标）</th></tr></thead>
    <tbody><tr><td>毛利率</td><td>38.6%</td><td>41.0%</td></tr>
    <tr><td>获客成本 CAC</td><td>186 元</td><td>171 元</td></tr></tbody>
  </table>
  <div class="fig-src">来源：财务周报（内部），2026-11-24</div>
  <div class="fig-unit">单位：百分比 / 人民币元；零线为 0pt 毛利变化基准</div>
</figure>
<h2>2. 决策链</h2>
<table>
<thead><tr><th>阶段</th><th>阶段决策</th><th>不可逆</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<h2>3. 工件与可追性</h2>
<table>
<thead><tr><th>工件</th><th>产出阶段</th><th>sha256 前 12 位</th></tr></thead>
<tbody>{''.join(f"<tr><td>{a['name']}</td><td>{st['stage']}</td><td><code>{_short(a['sha256'])}</code></td></tr>" for st in manifest['stages'] for a in st.get('outputs') or [])}</tbody>
</table>
<h2>4. 边界与未决</h2>
<p>本包不回答竞品是否跟进降价；6 周灰度未结束前，毛利率改善只能算目标值，不写成事实。</p>
"""
    return _page("经营决策包 · " + manifest["title"], body)


# --------------------------------------------------------------------------- #
# 黄金成品：真实跑一遍账本产线，落盘工件 + 两份 HTML
# --------------------------------------------------------------------------- #
_STAGES = [
    (1, "intent", [], ["brief.json"],
     "确认问题：毛利率连续两季下滑 3.1pt，决策用途是预算再平衡", False),
    (2, "decompose", ["artifacts/brief.json"], ["taskcard.json"],
     "拆 4 张任务卡：定价 / 投放 / 供应链 / 人效，单一 owner", False),
    (3, "decide", ["artifacts/taskcard.json"], ["decision_card.json"],
     "维持 99 元档 + 削减 12% 投放；可逆性=难逆，需灰度回滚计划", False),
    (4, "redteam", ["artifacts/decision_card.json"], ["redteam.json"],
     "三评委 2 GO 1 PAUSE：补 6 周灰度对照后再全量", False),
    (5, "companyos", ["artifacts/redteam.json"], ["companyos.json"],
     "回补目标写进 Rocks，周会用红黄绿追踪", False),
    (6, "decisionlog", ["artifacts/companyos.json"], ["decisionlog.json"],
     "决策留痕并锁 60 天冷却，禁止重提旧方案", False),
    (7, "boardroom", ["artifacts/decisionlog.json"], ["board.json"],
     "上报董事会：请求 6 周灰度授权（不可逆动资金）", True),
    (8, "deliver", ["artifacts/board.json"], ["decision-pack.html", "交付回执.txt"],
     "打包交付：决策包 + 账本 + 回执，交 R04 复核", False),
]


def build_goldens(base_dir: Optional[str] = None) -> Dict[str, Any]:
    base = base_dir or os.path.join(HERE, "golden")
    art_dir = os.path.join(base, "artifacts")
    os.makedirs(art_dir, exist_ok=True)

    # 1) 真实工件：从 examples 复制（确定性、无联网），缺失时用最小占位
    sources = {"brief.json": "brief.json", "decision_card.json": "decision_card.json",
               "redteam.json": "redteam.json", "companyos.json": "companyos.json",
               "decisionlog.json": "decisionlog.json", "board.json": "board.json"}
    for dst, src in sources.items():
        sp = os.path.join(HERE, "examples", src)
        data = load_json(sp) if os.path.isfile(sp) else {"source": src}
        write_json(os.path.join(art_dir, dst), data)
    write_json(os.path.join(art_dir, "taskcard.json"), {
        "goal": "Q4 预算再平衡：毛利率回补 2.4pt",
        "owner": "r01", "wave": 1,
        "tasks": [{"owner": "r03", "goal": "定价与毛利测算"},
                  {"owner": "r12", "goal": "投放预算削减 12% 方案"},
                  {"owner": "r15", "goal": "双供应商替代"}]})
    write_text(os.path.join(art_dir, "交付回执.txt"),
               "R01 经营决策包交付回执\n签收：R04 蛙挑刺\n日期：2026-11-27\n")

    # 2) 决策包页面（作为交付工件，先落盘再登记哈希）
    manifest = build_manifest("R01-20261127-Q4BUDGET", "Q4 预算再平衡决策包", [])
    pack_html = render_decision_pack_html(
        build_manifest("R01-20261127-Q4BUDGET", "Q4 预算再平衡决策包",
                       [make_stage(seq, stage, inputs, _outputs_of(art_dir, outs),
                                   decision, irreversible=irr,
                                   signoff={"required": True, "by": "创始人",
                                            "at": "2026-11-27"} if irr else None)
                        for seq, stage, inputs, outs, decision, irr in _STAGES]),
        {"ok": True})
    write_text(os.path.join(base, "decision-pack.html"), pack_html)

    # 3) 正式账本（决策包已落盘，哈希可算）
    stages = [make_stage(seq, stage, inputs, _outputs_of(art_dir, outs, base),
                         decision, irreversible=irr,
                         signoff={"required": True, "by": "创始人",
                                  "at": "2026-11-27"} if irr else None)
              for seq, stage, inputs, outs, decision, irr in _STAGES]
    manifest = build_manifest("R01-20261127-Q4BUDGET", "Q4 预算再平衡决策包", stages)
    verify = verify_manifest(manifest, root=base)
    write_json(os.path.join(base, "run-manifest.json"), manifest)
    write_text(os.path.join(base, "run-manifest.html"),
               render_manifest_html(manifest, verify))
    return {"manifest": manifest, "verify": verify,
            "decision_pack": os.path.join(base, "decision-pack.html"),
            "run_manifest": os.path.join(base, "run-manifest.html")}


def _outputs_of(art_dir: str, names: List[str], base: Optional[str] = None) -> List[Dict[str, Any]]:
    """把工件登记为「相对账本根」的路径：examples 复制的在 artifacts/ 下，页面在根。"""
    out = []
    for name in names:
        if base:
            path = os.path.join(base, name)
            if os.path.isfile(path):
                out.append({"name": name, "sha256": sha256_file(path),
                            "bytes": os.path.getsize(path)})
                continue
        path = os.path.join(art_dir, name)
        if os.path.isfile(path):
            out.append({"name": "artifacts/" + name, "sha256": sha256_file(path),
                        "bytes": os.path.getsize(path)})
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="run_manifest.py", description="R01 运行账本")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--file", required=True)
    v.add_argument("--dir", default=None)
    t = sub.add_parser("trace")
    t.add_argument("--file", required=True)
    c = sub.add_parser("check")
    c.add_argument("--case", required=True)
    sub.add_parser("goldens")
    a = ap.parse_args(argv)

    if a.cmd == "goldens":
        out = build_goldens()
        print(json.dumps({"ok": out["verify"]["ok"],
                          "decision_pack": out["decision_pack"],
                          "run_manifest": out["run_manifest"],
                          "violations": out["verify"]["violations"]},
                         ensure_ascii=False, indent=2))
        return 0 if out["verify"]["ok"] else 1
    if a.cmd == "verify":
        out = verify_manifest(load_json(a.file), root=a.dir)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "trace":
        steps = trace_steps(load_json(a.file))
        print(json.dumps({"steps": steps, "count": len(steps)}, ensure_ascii=False, indent=2))
        return 0
    out = check_case(a.case)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["as_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
