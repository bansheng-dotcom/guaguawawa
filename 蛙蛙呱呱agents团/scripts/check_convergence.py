#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/check_convergence.py —— 收敛门禁：同一件事不许被第二次新建。

每一条检查都对应一次真实返工（见 `交付/复盘-返工根因与项目规则-2026-11-18.md`）：

  S1 单一事实来源   experts.yaml 漂移 / 名册口径两套 / 图表类型两套
  S2 失败即失败     意图绑定被 except 吞掉 / 技能缺 ok 也算成功 / 无方法也算数据齐备 /
                    D 级来源不拦 / 缺 HTML 时质检层被跳过
  S3 工作区纪律     已跟踪文件从磁盘消失 / 仓根堆一次性脚本
  S4 文档可执行     README 与标准仍在教已下线命令
  S5 孤儿接线       声明了却没人调用的入口（chart_capabilities.render_chart / chart_plan.choose）

设计原则：
  * 只读，不改任何文件；不依赖第三方库（PyYAML 除外，与产线一致）。
  * 失败时给「违规 + 证据 + 修复动作」，不给分数。
  * 允许 `--baseline <json>` 冻结既有违规（只允许下降），用于老仓平滑接入。

用法：
    python scripts/check_convergence.py
    python scripts/check_convergence.py --json
    python scripts/check_convergence.py --baseline .convergence-baseline.json --write-baseline
退出码：0 全过（或未超过基线）；1 有新增违规。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
TEAM = ROOT.name
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROWS: List[Dict[str, Any]] = []


def hit(rule: str, msg: str, evidence: str, fix: str) -> None:
    ROWS.append({"rule": rule, "msg": msg, "evidence": evidence, "fix": fix})


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# S1 单一事实来源
# --------------------------------------------------------------------------- #
def s1_experts_drift() -> None:
    """experts.yaml 必须等于 gen_experts.build() 的渲染结果。"""
    try:
        from scripts import gen_experts as g
        want = "# 专家卡（由 scripts/gen_experts.py 生成，勿手改）\n" + g._yaml_dump(g.build()) + "\n"
    except Exception as exc:  # noqa: BLE001
        hit("S1", "专家卡无法重算（生成器坏了）", f"{type(exc).__name__}: {exc}",
            "修 scripts/gen_experts.py，再跑 --check")
        return
    disk = _read("configs/experts.yaml")
    if disk != want:
        # 找出第一处差异，避免只报「漂移」不说哪里
        a, b = disk.splitlines(), want.splitlines()
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        ev = f"configs/experts.yaml:{i + 1}\n  磁盘: {a[i] if i < len(a) else '(EOF)'}\n  重算: {b[i] if i < len(b) else '(EOF)'}"
        hit("S1", "configs/experts.yaml 与事实来源漂移（编排器读的是旧卡）", ev,
            "python scripts/gen_experts.py，并把 gen_experts.py --check 接进 CI")


def s1_roster_vs_experts() -> None:
    """名册的「能否进报告」必须与专家卡一致（现在两处各自硬编码）。"""
    from core import roster
    rb = roster.build()["roles"]
    try:
        import yaml
        ex = (yaml.safe_load(_read("configs/experts.yaml")) or {}).get("roles") or {}
    except Exception as exc:  # noqa: BLE001
        hit("S1", "专家卡不可读，无法比对名册", str(exc), "pip install pyyaml 后重跑")
        return
    diff = [f"{rid}: roster={r['enters_report']} experts={ex.get(rid, {}).get('enters_report')}"
            for rid, r in rb.items()
            if ex.get(rid) and bool(r["enters_report"]) != bool(ex[rid].get("enters_report"))]
    if diff:
        hit("S1", "名册与专家卡的「进报告」判定不一致", "；".join(diff[:6]),
            "把 enters_report 收敛到 core/base/registry.py 一处，其余生成")


def s1_membership_hardcoded() -> None:
    """enters_report 的硬编码集合只允许存在一处。"""
    a = _read("core/roster.py")
    b = _read("scripts/gen_experts.py")
    if '("r08", "r09", "r10", "r17")' in a and '{"r08", "r09", "r10", "r17"}' in b:
        hit("S1", "「谁不进报告」硬编码在两处（必然漂移）",
            "core/roster.py 与 scripts/gen_experts.py 各一份 r08/r09/r10/r17",
            "在 core/base/registry.py 给角色加 enters_report 字段，两处都读它")


def s1_chart_sets() -> None:
    """charts_pro 图型 / v1 注册表 / 选型配置 三者的图型集合必须自洽。"""
    from core.report_theme.charts_pro import spec as _pro
    from core.charts import chart_capabilities as cc
    v1 = set(cc.CATALOG_KEYS) if hasattr(cc, "CATALOG_KEYS") else {c.get("key") for c in cc.CATALOG}
    v2 = set(_pro.kinds()) | set(_pro.ALIASES)
    missing = sorted(v1 - v2)
    if missing:
        hit("S1", "v1 图型在 charts_pro 中缺别名", f"missing={missing}",
            "在 charts_pro/spec.py 的 ALIASES 补映射")
    try:
        import yaml
        doc = yaml.safe_load(_read("configs/chart_by_relation.yaml")) or {}
        allowed = {t for rel in (doc.get("relations") or {}).values() for t in (rel.get("allowed") or [])}
        bad = sorted(t for t in allowed if t not in v2)
        if bad:
            hit("S1", "选型配置引用了不存在的图型", f"chart_by_relation.yaml: {bad}",
                "删掉这些类型或补渲染器")
    except Exception as exc:  # noqa: BLE001
        hit("S1", "图表选型配置不可读", str(exc), "修 configs/chart_by_relation.yaml")


# --------------------------------------------------------------------------- #
# S2 失败即失败
# --------------------------------------------------------------------------- #
def s2_intent_fallback() -> None:
    """意图绑定失败不许 fallback 成「数据能算什么」。"""
    src = _read("core/decision_report.py")
    m = re.search(r"except ValueError:[\s\S]{0,400}?decision\.draft\(", src)
    if m:
        line = src[:m.start()].count("\n") + 1
        hit("S2", "意图绑定失败被降级：专家答不了 → 静默改用数据题库",
            f"core/decision_report.py:{line}",
            "删掉这段 fallback：draft_from_roster 抛错即整份失败（INTENT_UNBOUND）")


def s2_skill_ok_default() -> None:
    """技能没返回 ok 时不能默认成功。"""
    src = _read("core/analysis_methods.py")
    m = re.search(r'js\.get\("ok",\s*True\)', src)
    if m:
        line = src[:m.start()].count("\n") + 1
        hit("S2", "技能缺 ok 字段被当成成功（R06 从不输出 ok）",
            f"core/analysis_methods.py:{line}  js.get(\"ok\", True)",
            "改成 False，并让各角色 emit 统一写 ok；失败进 manifest.degraded")


def s2_readiness_no_methods() -> None:
    """没有数据方法 ≠ 数据齐备。"""
    src = _read("core/orchestrator.py")
    if '"no_methods": True' in src and '"readiness": 1.0' in src:
        line = src[:src.index('"readiness": 1.0')].count("\n") + 1
        hit("S2", "无方法的角色被当成 readiness=1.0，可出场但问不出问题",
            f"core/orchestrator.py:{line}",
            "无方法时 readiness=0 或单独 status=review_only，不参与数据题")


def s2_claim_gate_c2() -> None:
    """D 级来源必须拦（文档说拦，代码没拦）。"""
    src = _read("core/claims/claim_consistency.py")
    m = re.search(r"blocking\s*=\s*\(([\s\S]*?)\)", src)
    if m and "C2" not in m.group(1):
        line = src[:m.start()].count("\n") + 1
        hit("S2", "C2（D 级来源）只统计不拦截，与文档承诺不符",
            f"core/claims/claim_consistency.py:{line}",
            "把 issues['C2_d_only_numbers'] > 0 加进 blocking，或改文档别承诺")


def s2_gate_skip_layer() -> None:
    """缺 HTML 时质检层被跳过，仍可能 ok=true。"""
    src = _read("core/quality_gate.py")
    if "if html and Path(html).exists():" in src and "ok = bool(ran) and all" in src:
        line = src[:src.index("ok = bool(ran) and all")].count("\n") + 1
        hit("S2", "缺 HTML 时编辑/呈现两层被静默跳过，ok 仍可能为真",
            f"core/quality_gate.py:{line}",
            "缺层 = BLOCK（或 layer.ok=None 且 ok 要求三层齐全）")


# --------------------------------------------------------------------------- #
# S3 工作区纪律
# --------------------------------------------------------------------------- #
def s3_tracked_deleted() -> None:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "-c", "core.quotepath=false",
             "status", "--porcelain", "--", TEAM],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60).stdout
    except Exception as exc:  # noqa: BLE001
        hit("S3", "无法读取 git 状态", str(exc), "确认这是 git 仓库")
        return
    dels = [ln[3:] for ln in out.splitlines() if ln.startswith(" D")]
    if dels:
        hit("S3", "已跟踪文件从磁盘消失且未提交（无法在干净克隆里恢复）",
            f"{len(dels)} 个，例如 {dels[:3]}",
            "改删除为 git mv 到 _attic/ 并提交；或 git checkout -- 恢复")


def s3_root_scratch() -> None:
    scratch = sorted(p.name for p in REPO.glob("_*.py"))
    if scratch:
        hit("S3", "仓根堆了一次性脚本（复制粘贴的温床）",
            f"{len(scratch)} 个：{', '.join(scratch[:6])}",
            "移到 scripts/_oneoff/ 并加 --dry-run/幂等说明")


# --------------------------------------------------------------------------- #
# S4 文档可执行
# --------------------------------------------------------------------------- #
RETIRED = [
    (r"report\s+(produce|decide|build|pack|research)(?=\s|$)", "已下线的 report 子命令"),
    (r"--lens\b", "已删除的参数 --lens"),
    (r"--thesis\b", "已删除的参数 --thesis"),
    (r"report\s+run\s+--results", "已删除的 --results 用法"),
]
DOCS = ["README.md", "REPORT-STANDARD.md", "REPORT-BRIDGE-GUIDE.md",
        "docs/REPORT-LINES.md", "AGENTS.md", "使用指南.md"]


def s4_stale_docs() -> None:
    bad = []
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        head = "\n".join(lines[:15])
        # 整篇声明「以下为历史对照」的文档不按现行命令校验（但仍应在文首标明）
        if "历史" in head and ("对照" in head or "保留" in head):
            continue
        for i, line in enumerate(lines, 1):
            prev = lines[i - 2] if i >= 2 else ""
            # 「说明它已下线」的行不算违规；只有教人照着执行才算
            if any(w in line + prev for w in ("删除", "退役", "下线", "历史", "不再生效", "兼容")):
                continue
            whys = [why for pat, why in RETIRED if re.search(pat, line)]
            for why in dict.fromkeys(whys):
                bad.append(f"{rel}:{i} {why}")
    if bad:
        hit("S4", "文档仍在教已下线命令（照做必失败）", "；".join(bad[:8]),
            "改成 report \"指令\" --dir … --out …；或在行尾标「已下线」")


def s4b_ci_retired_commands() -> None:
    """CI 脚本不得调用已删除的 report 子命令（否则绿灯是假绿）。"""
    bad = []
    for p in (ROOT / "scripts").glob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"report"\s*,\s*"(decide|build|produce|pack|research)"', txt):
            bad.append(f"{p.name}:{txt[:m.start()].count(chr(10)) + 1} report {m.group(1)}")
    if bad:
        hit("S4", "CI/脚本仍在调已删除的 report 子命令（会被当 intent 吞掉）",
            "；".join(bad[:6]),
            "改成 report \"指令\" --dir … --out …；并让未知子命令报错，不要静默当 intent")


# --------------------------------------------------------------------------- #
# S5 孤儿接线
# --------------------------------------------------------------------------- #
def s5_orphans() -> None:
    py = [p for p in ROOT.rglob("*.py") if "_attic" not in p.parts and "site-packages" not in p.parts]
    hits = []
    for name, pat in (("chart_capabilities.render_chart", r"chart_capabilities\.render_chart\s*\("),
                      ("chart_plan.choose", r"chart_plan\.choose\s*\(")):
        callers = []
        for p in py:
            txt = p.read_text(encoding="utf-8", errors="replace")
            if re.search(pat, txt):
                callers.append(p.relative_to(ROOT).as_posix())
        if not callers:
            hits.append(name)
    if hits:
        hit("S5", "声明了入口但全仓零调用（死接线）", "、".join(hits),
            "接进产线或删除；不要再留「以后会用」的入口")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
CHECKS = [s1_experts_drift, s1_roster_vs_experts, s1_membership_hardcoded,
          s1_chart_sets, s2_intent_fallback, s2_skill_ok_default,
          s2_readiness_no_methods, s2_claim_gate_c2, s2_gate_skip_layer,
          s3_tracked_deleted, s3_root_scratch, s4_stale_docs,
          s4b_ci_retired_commands, s5_orphans]


def run() -> Dict[str, Any]:
    for fn in CHECKS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001  检查器自身失败也要看得见
            hit("CHECK", f"{fn.__name__} 执行失败", f"{type(exc).__name__}: {exc}",
                "修检查器；否则这条规则等于没接")
    return {"schema": "dsh.convergence/v1", "ok": not ROWS, "violations": ROWS,
            "count": len(ROWS)}


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="check_convergence",
                                 description="收敛门禁：防同一件事第二次被新建")
    ap.add_argument("--json", default=None)
    ap.add_argument("--baseline", default=None, help="基线 JSON：只允许违规数下降")
    ap.add_argument("--write-baseline", action="store_true")
    a = ap.parse_args(argv)

    res = run()
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    if a.baseline and a.write_baseline:
        Path(a.baseline).write_text(json.dumps({"count": res["count"]}, indent=2),
                                    encoding="utf-8")
        print(f"baseline written: {a.baseline} ({res['count']})")
        return 0

    print(f"收敛门禁 · {len(CHECKS)} 项检查 · 违规 {res['count']}")
    for v in res["violations"]:
        print(f"\n[{v['rule']}] {v['msg']}")
        print(f"  证据：{v['evidence']}")
        print(f"  修复：{v['fix']}")

    if a.baseline and Path(a.baseline).exists():
        base = json.loads(Path(a.baseline).read_text(encoding="utf-8")).get("count", 0)
        if res["count"] > base:
            print(f"\nFAIL：违规 {res['count']} > 基线 {base}（新增 {res['count'] - base}）")
            return 1
        print(f"\nPASS：违规 {res['count']} ≤ 基线 {base}")
        return 0
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
