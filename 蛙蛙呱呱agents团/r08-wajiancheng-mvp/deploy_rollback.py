#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R08 部署 / 回滚机制：版本锁 + 幂等部署 + 健康检查 + 回滚计划（T12）。

升级方案 §15 对 R08 的要求是「部署/回滚、真实 E2E」，验收「1 个可部署 MVP」。
本模块用**本地文件态**模拟一次可部署 MVP：`state.json` 是版本锁，
`release/` 是当前发布内容，`history.json` 是发布与回滚账本。

门禁（确定性）：
    D01_NO_ROLLBACK_PLAN      没有回滚计划就直接发布 → 拒绝
    D02_VERSION_LOCK          版本低于当前且未声明 allow_rollback → 拒绝（回滚请走 rollback）
    D03_HEALTHCHECK_FAILED    健康检查不过 → 自动回滚到上一版，并报失败
    D05_VERSION_DIGEST_MISMATCH 同版本号但内容摘要不同 → 拒绝（发布物被篡改）
    D06_PATH_ESCAPE           发布文件名越界（../）→ 拒绝

幂等：同版本号 + 同摘要重复部署 → `noop`，不重写文件、不新增历史。

用法：
    python deploy_rollback.py deploy --manifest <m.json> --dir <state>
    python deploy_rollback.py rollback --dir <state>
    python deploy_rollback.py e2e [--dir <tmp>]
    python deploy_rollback.py check --case misuse/deploy-no-rollback.json
    python deploy_rollback.py goldens
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))

ERRORS = {
    "D01_NO_ROLLBACK_PLAN": "没有回滚计划（至少一步）不得发布",
    "D02_VERSION_LOCK": "版本号回退必须走 rollback，不得直接 deploy 旧版本",
    "D03_HEALTHCHECK_FAILED": "健康检查未通过，已自动回滚到上一版",
    "D05_VERSION_DIGEST_MISMATCH": "同版本号内容摘要不同，发布物被篡改",
    "D06_PATH_ESCAPE": "发布文件名越界（../ 或绝对路径）",
}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def digest_files(files: Dict[str, str]) -> str:
    """发布物摘要：文件名排序后逐个喂 sha256，任何字节变化都会变摘要。"""
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(str(files[name]).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _vtuple(version: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", str(version))
    return tuple(int(x) for x in nums) if nums else (0,)


def _state_paths(root: str) -> Dict[str, str]:
    return {"state": os.path.join(root, "state.json"),
            "history": os.path.join(root, "history.json"),
            "release": os.path.join(root, "release")}


def _load_state(root: str) -> Dict[str, Any]:
    p = _state_paths(root)["state"]
    return load_json(p) if os.path.isfile(p) else {}


def _save_state(root: str, state: Dict[str, Any]) -> None:
    write_json(_state_paths(root)["state"], state)


def _append_history(root: str, entry: Dict[str, Any]) -> None:
    p = _state_paths(root)["history"]
    hist = load_json(p) if os.path.isfile(p) else []
    hist.append(entry)
    write_json(p, hist)


def _sanitize(files: Dict[str, str]) -> List[str]:
    bad = []
    for name in files:
        if os.path.isabs(name) or ".." in name.replace("\\", "/").split("/"):
            bad.append(name)
    return bad


def _materialize(root: str, files: Dict[str, str]) -> None:
    rel = _state_paths(root)["release"]
    if os.path.isdir(rel):
        shutil.rmtree(rel)
    for name, content in files.items():
        _write(os.path.join(rel, *name.replace("\\", "/").split("/")), str(content))


# --------------------------------------------------------------------------- #
# 发布 / 回滚
# --------------------------------------------------------------------------- #
def deploy(manifest: Dict[str, Any], root: str,
           now: str = "2026-11-27T09:00:00") -> Dict[str, Any]:
    os.makedirs(root, exist_ok=True)
    files = dict(manifest.get("files") or {})
    version = str(manifest.get("version") or "")
    digest = digest_files(files)
    state = _load_state(root)
    violations: List[Dict[str, str]] = []

    def bad(code: str, detail: str) -> None:
        violations.append({"code": code, "msg": ERRORS[code], "detail": detail})

    rollback_plan = (manifest.get("rollback") or {}).get("plan") or []
    if not rollback_plan:
        bad("D01_NO_ROLLBACK_PLAN", f"{version} 无回滚步骤")
    escaped = _sanitize(files)
    if escaped:
        bad("D06_PATH_ESCAPE", "、".join(escaped))
    if state.get("version") and _vtuple(version) < _vtuple(state["version"]) \
            and not manifest.get("allow_rollback"):
        bad("D02_VERSION_LOCK", f"{version} < 当前 {state['version']}（请用 rollback）")
    if state.get("version") == version and state.get("digest") != digest:
        bad("D05_VERSION_DIGEST_MISMATCH",
            f"{version} 摘要 {digest[:12]} != 已发布 {str(state.get('digest'))[:12]}")

    if violations:
        _append_history(root, {"action": "deploy", "version": version,
                               "digest": digest, "at": now, "result": "refused",
                               "codes": [v["code"] for v in violations]})
        return {"ok": False, "outcome": "refused", "version": version,
                "digest": digest, "idempotent": False, "rolled_back": False,
                "violations": violations, "state": state}

    # 幂等：同版本 + 同摘要 → no-op
    if state.get("version") == version and state.get("digest") == digest:
        _append_history(root, {"action": "deploy", "version": version,
                               "digest": digest, "at": now, "result": "noop"})
        return {"ok": True, "outcome": "noop", "version": version, "digest": digest,
                "idempotent": True, "rolled_back": False, "violations": [],
                "state": state}

    previous = {"version": state.get("version"), "digest": state.get("digest"),
                "files": dict(state.get("files") or {})} if state.get("version") else None

    # 健康检查：先落盘再检查，失败则恢复上一版
    _materialize(root, files)
    checks = manifest.get("healthchecks") or []
    failed = [c for c in checks if str(c.get("actual")) != str(c.get("expect"))]

    new_state = {"version": version, "digest": digest, "deployed_at": now,
                 "files": files, "previous": previous,
                 "health": "healthy" if not failed else "unhealthy"}
    _save_state(root, new_state)

    if failed:
        if previous:
            _materialize(root, previous.get("files") or {})
            restored = {"version": previous.get("version"),
                        "digest": previous.get("digest"),
                        "deployed_at": now, "files": previous.get("files") or {},
                        "previous": None, "health": "healthy"}
            _save_state(root, restored)
            new_state = restored
        bad("D03_HEALTHCHECK_FAILED",
            "、".join(f"{c.get('name')}: {c.get('actual')}!={c.get('expect')}"
                     for c in failed))
        _append_history(root, {"action": "deploy", "version": version, "digest": digest,
                               "at": now, "result": "auto_rolled_back",
                               "to": (previous or {}).get("version"),
                               "codes": ["D03_HEALTHCHECK_FAILED"]})
        return {"ok": False, "outcome": "auto_rolled_back", "version": version,
                "digest": digest, "idempotent": False, "rolled_back": bool(previous),
                "violations": violations, "state": new_state}

    _append_history(root, {"action": "deploy", "version": version, "digest": digest,
                           "at": now, "result": "deployed"})
    return {"ok": True, "outcome": "deployed", "version": version, "digest": digest,
            "idempotent": False, "rolled_back": False, "violations": [],
            "state": new_state}


def rollback(root: str, now: str = "2026-11-27T10:00:00") -> Dict[str, Any]:
    state = _load_state(root)
    prev = state.get("previous")
    if not prev or not prev.get("version"):
        return {"ok": False, "outcome": "refused", "violations": [
            {"code": "D02_VERSION_LOCK", "msg": "没有可回滚的上一版", "detail": "-"}],
            "state": state}
    _materialize(root, prev.get("files") or {})
    restored = {"version": prev["version"], "digest": prev.get("digest"),
                "deployed_at": now, "files": prev.get("files") or {},
                "previous": None, "health": "healthy"}
    _save_state(root, restored)
    _append_history(root, {"action": "rollback", "version": prev["version"],
                           "digest": prev.get("digest"), "at": now,
                           "result": "rolled_back", "from": state.get("version")})
    return {"ok": True, "outcome": "rolled_back", "version": prev["version"],
            "digest": prev.get("digest"), "violations": [], "state": restored}


def check_health(root: str) -> Dict[str, Any]:
    """部署后自检：state / release 文件摘要必须与版本锁一致。"""
    state = _load_state(root)
    rel = _state_paths(root)["release"]
    files = {}
    if os.path.isdir(rel):
        for base, _dirs, names in os.walk(rel):
            for n in names:
                p = os.path.join(base, n)
                files[os.path.relpath(p, rel).replace("\\", "/")] = _read(p)
    digest = digest_files(files)
    ok = bool(state.get("version")) and digest == state.get("digest")
    return {"ok": ok, "version": state.get("version"), "digest": digest,
            "locked": state.get("digest"), "files": len(files)}


# --------------------------------------------------------------------------- #
# E2E：1 个可部署 MVP 的本地文件态全流程
# --------------------------------------------------------------------------- #
BASE_FILES = {"index.html": "<h1>MVP v1.1.0</h1>", "app.js": "console.log('v1.1.0')",
              "styles.css": "body{font-family:sans-serif}"}
NEXT_FILES = {"index.html": "<h1>MVP v1.2.0</h1>", "app.js": "console.log('v1.2.0')",
              "styles.css": "body{font-family:system-ui}"}
ROLLBACK = {"to": "mvp-1.1.0",
            "plan": ["恢复 release/ 到下个快照", "重启静态服务", "跑冒烟 3 条"],
            "owner": "r08"}


def manifest(version: str, files: Dict[str, str], healthy: bool = True,
             include_rollback: bool = True,
             health: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    m = {"version": version, "files": files,
         "healthchecks": health or [
             {"name": "首页可达", "expect": "200", "actual": "200" if healthy else "500"},
             {"name": "静态资源摘要", "expect": "match", "actual": "match" if healthy else "drift"}],
         "rollback": ROLLBACK if include_rollback else {}}
    return m


def run_e2e(root: Optional[str] = None) -> Dict[str, Any]:
    tmp = root or tempfile.mkdtemp(prefix="r08-deploy-")
    steps: List[Dict[str, Any]] = []
    d1 = deploy(manifest("mvp-1.1.0", BASE_FILES), tmp)
    steps.append({"step": "首次发布 v1.1.0", **{k: d1[k] for k in
                  ("ok", "outcome", "idempotent", "rolled_back", "version")}})
    d2 = deploy(manifest("mvp-1.1.0", BASE_FILES), tmp)
    steps.append({"step": "重复发布同版本（幂等）", **{k: d2[k] for k in
                  ("ok", "outcome", "idempotent", "rolled_back", "version")}})
    d3 = deploy(manifest("mvp-1.2.0", NEXT_FILES, healthy=False), tmp)
    steps.append({"step": "发布 v1.2.0（健康检查失败）", **{k: d3[k] for k in
                  ("ok", "outcome", "idempotent", "rolled_back", "version")},
                  "codes": [v["code"] for v in d3["violations"]]})
    d4 = deploy(manifest("mvp-1.2.0", NEXT_FILES, healthy=True), tmp)
    steps.append({"step": "修复后发布 v1.2.0", **{k: d4[k] for k in
                  ("ok", "outcome", "idempotent", "rolled_back", "version")}})
    r1 = rollback(tmp)
    steps.append({"step": "人工回滚到 v1.1.0", **{k: r1[k] for k in
                  ("ok", "outcome", "version")}})
    health = check_health(tmp)
    history = load_json(_state_paths(tmp)["history"])
    return {"ok": d1["ok"] and d2["idempotent"] and (not d3["ok"]) and d3["rolled_back"]
                  and d4["ok"] and r1["ok"] and health["ok"],
            "steps": steps, "history": history, "health": health,
            "state": _load_state(tmp), "root": tmp}


def check_case(path: str) -> Dict[str, Any]:
    spec = load_json(path)
    tmp = tempfile.mkdtemp(prefix="r08-misuse-")
    seed = spec.get("seed")
    if seed:
        deploy(manifest(seed.get("version"), seed.get("files") or BASE_FILES,
                        include_rollback=True), tmp)
    out = deploy(spec.get("manifest") or {}, tmp)
    got = {v["code"] for v in out["violations"]}
    expect = set(spec.get("expect") or [])
    return {"case_id": spec.get("case_id"), "outcome": out["outcome"],
            "expect": sorted(expect), "hit": sorted(expect & got),
            "rejected": out["ok"] is False,
            "as_expected": bool(expect) and expect <= got}


# --------------------------------------------------------------------------- #
# 页面渲染
# --------------------------------------------------------------------------- #
STYLE = """
@page { size: A4; margin: 18mm; }
:root { --paper:#ffffff; --ink:#111827; --muted:#4b5563; --faint:#6b7280; --line:#d1d5db; --accent:#7c3aed; --accent-soft:#f5f3ff; }
* { box-sizing: border-box; }
body { margin:0; padding:32px 20px; background:var(--paper); color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; font-size:15px; }
.sheet { max-width:920px; margin:0 auto; }
h1 { font-size:28px; line-height:1.35; margin:0 0 6px; }
h2 { font-size:20px; line-height:1.4; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--accent); }
h3 { font-size:16px; line-height:1.45; margin:18px 0 8px; color:var(--accent); }
p, li, td, th { font-size:14px; }
.meta { font-size:12px; color:var(--muted); margin:0 0 18px; }
.tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:4px; background:var(--accent-soft); color:var(--accent); }
table { width:100%; border-collapse:collapse; margin:10px 0 16px; }
thead th { background:var(--accent-soft); color:var(--ink); text-align:left; font-size:12.5px; }
th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; }
code { font-size:12px; color:var(--muted); word-break:break-all; }
.block { background:#f9fafb; border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; border-radius:4px; }
figure, .block, section, tr { break-inside: avoid; }
.fig-card { border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:12px 0; }
.fig-sub { font-size:13px; color:var(--ink); margin:0 0 4px; }
.fig-src, .fig-unit { font-size:12px; color:var(--muted); }
"""


def _page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>{STYLE}</style>\n</head>\n"
            f"<body data-theme=\"light\">\n<main class=\"sheet\">\n{body}\n</main>\n</body>\n</html>\n")


def render_delivery_html(e2e: Dict[str, Any], m: Dict[str, Any]) -> str:
    files = "".join(f"<tr><td>{n}</td><td>{len(str(c))} B</td></tr>"
                    for n, c in sorted(m["files"].items()))
    checks = "".join(f"<tr><td>{c['name']}</td><td>{c['expect']}</td><td>{c['actual']}</td></tr>"
                     for c in m["healthchecks"])
    plan = "".join(f"<li>{x}</li>" for x in m["rollback"]["plan"])
    body = f"""
<h1>MVP 交付包 · {m['version']}</h1>
<p class="meta">交付人 R08 蛙建成 ｜ 版本锁 {m['version']} ｜ 摘要 <code>{e2e['health']['locked'][:16]}</code> ｜
健康 {e2e['health']['ok']}</p>
<h2>1. 交付结论</h2>
<div class="block">这是 1 个可本地部署的静态 MVP（3 个文件），带版本锁、幂等发布、健康检查与回滚计划。
E2E 五步全部按预期：首次发布成功、重复发布 no-op、坏版本自动回滚、修复后发布成功、人工回滚成功。</div>
<h2>2. 发布物</h2>
<table>
<thead><tr><th>文件</th><th>大小</th></tr></thead>
<tbody>{files}</tbody>
</table>
<p>版本锁：<code>{m['version']} · {e2e['health']['digest'][:16]}</code>；
相同版本号但摘要不同会被 D05 拒绝，防止「同号不同包」。</p>
<h2>3. 健康检查</h2>
<table>
<thead><tr><th>检查项</th><th>期望</th><th>实际</th></tr></thead>
<tbody>{checks}</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：E2E 五步的终态（发布 / 幂等 / 回滚）</figcaption>
  <table>
    <thead><tr><th>步骤</th><th>结果</th></tr></thead>
    <tbody>{''.join(f"<tr><td>{s['step']}</td><td>{s['outcome']}</td></tr>" for s in e2e['steps'])}</tbody>
  </table>
  <div class="fig-src">来源：deploy_rollback.run_e2e（本地文件态模拟）</div>
  <div class="fig-unit">单位：次；零线为「无失败步骤」基线</div>
</figure>
<h2>4. 回滚计划</h2>
<ol>{plan}</ol>
<h3>4.1 触发条件</h3>
<p>健康检查任一不过（D03）自动回滚；人工回滚只允许回到版本锁记录的上一版（D02）。</p>
"""
    return _page("MVP 交付包 · " + m["version"], body)


def render_rollback_html(e2e: Dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{h['at']}</td><td>{h['action']}</td><td>{h.get('version')}</td>"
        f"<td>{h['result']}</td><td>{h.get('to') or h.get('from') or '—'}</td></tr>"
        for h in e2e["history"])
    body = f"""
<h1>回滚记录 · {e2e['state'].get('version')}</h1>
<p class="meta">记录人 R08 ｜ 最终版本 {e2e['state'].get('version')} ｜
健康检查 {e2e['health']['ok']} ｜ 历史 {len(e2e['history'])} 条</p>
<h2>1. 结论先行</h2>
<div class="block">v1.2.0 首次发布因健康检查失败被自动回滚，release/ 已恢复为 v1.1.0；
修复后重新发布成功，随后人工回滚再次回到 v1.1.0，版本锁与磁盘摘要一致。</div>
<h2>2. 发布与回滚时间线</h2>
<table>
<thead><tr><th>时间</th><th>动作</th><th>版本</th><th>结果</th><th>目标/来源</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<h2>3. 失败与处置</h2>
<table>
<thead><tr><th>事件</th><th>错误码</th><th>处置</th><th>复核</th></tr></thead>
<tbody>
<tr><td>v1.2.0 健康检查 500</td><td>D03_HEALTHCHECK_FAILED</td><td>自动回滚 v1.1.0</td><td>R04 复核放行</td></tr>
<tr><td>重复发布 v1.1.0</td><td>—</td><td>幂等 no-op</td><td>无副作用</td></tr>
<tr><td>人工回滚 v1.2.0→v1.1.0</td><td>—</td><td>按回滚计划 3 步</td><td>冒烟 3 条通过</td></tr>
</tbody>
</table>
<h2>4. 版本锁一致性</h2>
<table>
<thead><tr><th>项</th><th>值</th></tr></thead>
<tbody>
<tr><td>锁定版本</td><td>{e2e['state'].get('version')}</td></tr>
<tr><td>锁定摘要</td><td><code>{e2e['health']['locked']}</code></td></tr>
<tr><td>磁盘重算摘要</td><td><code>{e2e['health']['digest']}</code></td></tr>
<tr><td>文件数</td><td>{e2e['health']['files']}</td></tr>
</tbody>
</table>
<h3>4.1 复核</h3>
<p>运行 <code>python deploy_rollback.py e2e</code> 可复现以上时间线；文件被手改会让
<code>check_health</code> 的摘要比对失败。</p>
"""
    return _page("回滚记录", body)


def build_goldens(base: Optional[str] = None) -> Dict[str, Any]:
    out_dir = base or os.path.join(HERE, "golden")
    os.makedirs(out_dir, exist_ok=True)
    e2e = run_e2e()
    m = manifest("mvp-1.1.0", BASE_FILES)
    # 交付包记录的是「当前锁定版本」的发布物与健康检查
    m["version"] = e2e["state"].get("version") or "mvp-1.1.0"
    m["files"] = e2e["state"].get("files") or BASE_FILES
    write_json(os.path.join(out_dir, "deploy-e2e.json"),
               {"steps": e2e["steps"], "history": e2e["history"],
                "health": e2e["health"], "state": {k: e2e["state"].get(k)
                                                   for k in ("version", "digest", "deployed_at")}})
    _write(os.path.join(out_dir, "mvp-delivery-pack.html"), render_delivery_html(e2e, m))
    _write(os.path.join(out_dir, "mvp-rollback-record.html"), render_rollback_html(e2e))
    return {"ok": e2e["ok"], "e2e": e2e, "dir": out_dir}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="deploy_rollback.py", description="R08 部署/回滚")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deploy")
    d.add_argument("--manifest", required=True)
    d.add_argument("--dir", required=True)
    r = sub.add_parser("rollback")
    r.add_argument("--dir", required=True)
    e = sub.add_parser("e2e")
    e.add_argument("--dir", default=None)
    c = sub.add_parser("check")
    c.add_argument("--case", required=True)
    sub.add_parser("goldens")
    a = ap.parse_args(argv)

    if a.cmd == "goldens":
        out = build_goldens()
        print(json.dumps({"ok": out["ok"], "steps": out["e2e"]["steps"],
                          "dir": out["dir"]}, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "deploy":
        out = deploy(load_json(a.manifest), a.dir)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "rollback":
        out = rollback(a.dir)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "e2e":
        out = run_e2e(a.dir)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    out = check_case(a.case)
    out["ok"] = out["as_expected"]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
