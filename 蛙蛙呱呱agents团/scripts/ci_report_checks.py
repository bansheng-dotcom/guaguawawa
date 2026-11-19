# -*- coding: utf-8 -*-
"""CI 闸门：唯一报告产线（2026-11-15 收敛后）。

按顺序验下面几件事，全部围绕「一条产线、一份报告」：
  [1] 20 个角色入口可用（执行角色还在，只是不再出报告）
  [2] 分支 A（单角色）从真实 result 出一份报告，且过门禁
  [3] 分支 B（跨角色）从两份 result 出一份报告，且过门禁
  [4] 角色侧已无报告引擎（静态扫描：没人再 import 被删除的产线模块）
  [5] 图表能力 48/48 不退化
  [10] 48 型图表经报告管线嵌入：v2 不回退、无双标题、卡框口径齐备
  [13] 交付稿风格：禁斜体、标题/表头禁衬线体
  [14] 开工前契约：四个纲领各跑一遍，契约不成立就不许出报告
  [15] 报告线单测：数据台/方法库/纲领/成稿（缺样本的用例自动 skip，不装绿也不装红）

样本目录缺失算「环境未就绪」，单独列出、不计入失败——否则红灯常年亮着，
真正的代码回归会被噪音淹没。

旧的 [1] spec/[2][3] contract/[4] legacy/[7] substance 五项已随产线一起删除。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "workspace" / "_ci_report_flow"
PIPE = ROOT.parent / "内蒙古水果三城调研_2026-11-16_pipeline"

DEAD_MODULES = (
    "report_pipeline", "report_engine", "report_generator",
    "kernel_report_adapter", "report_modules", "report_blueprint",
    "corpus_analysis", "enhanced_report_renderer", "report_kernel.layers",
    "report_kernel.spec", "report_kernel.aggregate",
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    fails: list[str] = []
    # 环境未就绪（样本目录/外部依赖缺失）与代码回归必须分开：
    # 混在一起会让红灯常年亮着，真正的回归被噪音淹没。
    env: list[str] = []

    # [1] 20 角色入口
    rc, out = run([sys.executable, "guagua.py", "check"])
    tail = [l for l in out.strip().splitlines() if "通过" in l]
    print(f"[1] roles check rc={rc} :: {tail[-1] if tail else out.strip()[-60:]}")
    if rc:
        fails.append("roles")

    # [2] run-line：v11 唯一入口（一条命令）；下面两个只差意图，用来证明同一数据不同问题
    out_a = OUT / "a"
    rc, out = run([sys.executable, "guagua.py", "report", "run-line",
                   "--intent", "内蒙古三城水果市场调研",
                   "--dir", str(PIPE), "--out", str(out_a),
                   "--layout", "paper",
                   "--quote-mode", "off"])
    print(f"[2] run-line(调研) rc={rc}")
    if rc:
        fails.append("flow-A")
        print("   ", out.strip()[:200])
    rc, out = run([sys.executable, "scripts/check_report_flow.py",
                   "--dir", str(out_a)])
    print(f"[2] gate(调研) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("gate-A")

    # [3] run-line：换意图必须换内容（P2 之前 hash 会相同，这里先只验能跑）
    out_b = OUT / "b"
    rc, out = run([sys.executable, "guagua.py", "report", "run-line",
                   "--intent", "内蒙古三城水果经营分析",
                   "--dir", str(PIPE), "--out", str(out_b),
                   "--layout", "paper",
                   "--quote-mode", "off"])
    print(f"[3] run-line(经营) rc={rc}")
    if rc:
        fails.append("flow-B")
        print("   ", out.strip()[:200])
    rc, out = run([sys.executable, "scripts/check_report_flow.py",
                   "--dir", str(out_b)])
    print(f"[3] gate(经营) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("gate-B")

    # [3b] 报告只有一份，且出具人是 R01；决策契约可审计、binding 达标
    man = out_b / "manifest.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        dec = m.get("decision") or {}
        qs = dec.get("questions") or []
        binding = (dec.get("binding") or {}).get("binding")
        one = (m.get("producer") == "r01" and len(qs) >= 3
               and (m.get("gates") or {}).get("binding") == "pass"
               and m.get("ok"))
        print(f"[3b] manifest producer={m.get('producer')} questions={len(qs)} "
              f"binding={binding} ok={m.get('ok')}")
        if not one:
            fails.append("manifest")
    else:
        print("[3b] manifest 缺失")
        fails.append("manifest")

    # [4] 角色侧无报告引擎
    pat = re.compile(r"^\s*(?:from|import)\s+\S*(?:" +
                     "|".join(re.escape(x) for x in DEAD_MODULES) + r")", re.M)
    bad = []
    for p in list(ROOT.glob("r*/agent.py")) + list(ROOT.glob("core/*.py")) + \
            list(ROOT.glob("shared/*.py")):
        if pat.search(p.read_text(encoding="utf-8", errors="replace")):
            bad.append(str(p.relative_to(ROOT)))
    print(f"[4] role-side report engine imports: {len(bad)} {bad[:3]}")
    if bad:
        fails.append("dual-engine")

    # [5] 图表能力
    rc, out = run([sys.executable, "-m", "core.chart_capabilities", "--check"])
    print(f"[5] charts rc={rc} :: {out.strip().splitlines()[-1] if out.strip() else ''}")
    if rc:
        fails.append("charts")

    # [6] v7 深度线：区域市场调研（带来源事实表）+ 九条门禁 + 反模板门禁
    out_v7 = OUT / "v7_market"
    src_v7 = ROOT.parent / "家居百货内蒙调研_2026-11-15"
    if not src_v7.exists():
        print(f"[6] SKIP(v7-market) :: 缺样本目录 {src_v7.name}")
        env.append("v7-sample-missing")
    else:
        rc, out = run([sys.executable, "guagua.py", "report", "run-line",
                       "--intent", "内蒙古家居百货市场调研",
                       "--dir", str(src_v7),
                       "--layout", "paper",
                       "--out", str(out_v7)])
        print(f"[6] flow(v7-market) rc={rc}")
        if rc:
            fails.append("flow-v7")
            print("   ", out.strip()[:200])
        rc, out = run([sys.executable, "scripts/check_report_flow.py",
                       "--dir", str(out_v7)])
        print(f"[6] gate(v7) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
        if rc:
            fails.append("gate-v7")
        rc, out = run([sys.executable, "-m", "core.report_quality",
                       str(out_v7 / "report.html")])
        print(f"[6] depth(v7) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
        if rc:
            fails.append("depth-v7")

    # [7] 学习层：Move 卡片必须可校验（来源/反例/代码落点/回归）
    rc, out = run([sys.executable, "scripts/check_move_cards.py"])
    tail7 = [l for l in out.strip().splitlines() if "PASS" in l]
    print(f"[7] move cards rc={rc} :: {tail7[-1] if tail7 else out.strip()[-60:]}")
    if rc:
        fails.append("move-cards")

    # [8] 领域层：20 角色领域包完整（书/方法/指标/决策/误判/章节）
    rc, out = run([sys.executable, "scripts/check_role_packs.py"])
    tail8 = [l for l in out.strip().splitlines() if "PASS；" in l]
    print(f"[8] role packs rc={rc} :: {tail8[-1] if tail8 else out.strip()[-60:]}")
    if rc:
        fails.append("role-packs")

    # [9] 接入层：120 条领域方法必须落到现有技能，或显式标成新增
    rc, out = run([sys.executable, "scripts/check_skill_integration.py"])
    tail9 = [l for l in out.strip().splitlines() if "方法 " in l]
    print(f"[9] skill integration rc={rc} :: {tail9[0] if tail9 else out.strip()[-60:]}")
    if rc:
        fails.append("skill-integration")

    # [10] 图表嵌入：48 型走报告渲染管线，v2 不回退、无双标题、卡框口径齐备
    rc, out = run([sys.executable, "scripts/check_chart_report_embed.py"])
    print(f"[10] chart embed rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("chart-embed")

    # [11] 报告质量内核：契约/规格/一致性/序列/交付门禁的自检
    rc, out = run([sys.executable, "-m", "core.report_kernel", "self-test"])
    print(f"[11] report kernel rc={rc} :: {out.strip().splitlines()[-1] if out.strip() else ''}")
    if rc:
        fails.append("report-kernel")

    # [12] 报告质量内核单测：交付门禁正反样例、规格推断、冲突拦截
    rc, out = run([sys.executable, "-m", "pytest", "tests/test_report_kernel.py", "-q"])
    tail12 = [l for l in out.strip().splitlines() if "passed" in l or "failed" in l]
    print(f"[12] report kernel tests rc={rc} :: {tail12[-1] if tail12 else out.strip()[-60:]}")
    if rc:
        fails.append("report-kernel-tests")

    # [13] 风格门禁：交付稿禁斜体、标题/表头禁衬线体（出处 REPORT-STANDARD §四）
    for tag, d in (("A", out_a), ("B", out_b)) + ((("v7", out_v7),) if out_v7.exists() else ()):
        if not d.exists():
            continue
        rc, out = run([sys.executable, "scripts/check_report_style.py", "--dir", str(d)])
        tail13 = [l for l in out.strip().splitlines() if "合计" in l]
        print(f"[13] style({tag}) rc={rc} :: {tail13[-1] if tail13 else out.strip()[-60:]}")
        if rc:
            fails.append(f"style-{tag}")

    # [14] 决策契约：3 个意图各跑一遍，证明「问题先于证据」且 binding 可审计
    src_fruit = PIPE
    if not src_fruit.exists():
        print(f"[14] SKIP(decision) :: 缺样本目录 {src_fruit.name}")
        env.append("fruit-sample-missing")
    else:
        for tag, intent in (("market", "内蒙古三城水果市场调研"),
                            ("ops", "内蒙古三城水果经营分析"),
                            ("risk", "内蒙古三城水果：停采换源与止损")):
            out_c = OUT / f"decision_{tag}"
            rc, out = run([sys.executable, "guagua.py", "report", "run-line",
                           "--intent", intent,
                           "--dir", str(src_fruit), "--out", str(out_c),
                           "--layout", "paper",
                           "--quote-mode", "off",
                           "--audience", "水果品类经营负责人"])
            dec = out_c / "decision.json"
            bind = out_c / "binding.json"
            c: dict = {}
            b: dict = {}
            if dec.exists():
                c = json.loads(dec.read_text(encoding="utf-8"))
            if bind.exists():
                b = json.loads(bind.read_text(encoding="utf-8"))
            qs = c.get("questions") or []
            fields_ok = (3 <= len(qs) <= 5
                         and all(q.get("comparison") and q.get("chart")
                                 and q.get("falsifier") for q in qs)
                         and b.get("declared") == len(qs)
                         and isinstance(b.get("binding"), (int, float)))
            print(f"[14] decision({tag}) rc={rc} questions={len(qs)} "
                  f"binding={b.get('binding')} fields={'OK' if fields_ok else 'MISSING'}")
            if rc or not fields_ok:
                fails.append(f"decision-{tag}")
                print("   ", out.strip()[-200:])

    # [15] 报告线单测：缺样本的用例已改为 skip，绿灯只代表代码没回归
    rc, out = run([sys.executable, "-m", "pytest",
                   "tests/test_report_flow.py", "tests/test_report_flow_opt.py",
                   "tests/test_decision_report.py", "tests/test_report_sections.py",
                   "tests/test_orchestrator.py", "-q"])
    tail15 = [l for l in out.strip().splitlines() if "passed" in l or "failed" in l]
    print(f"[15] line tests rc={rc} :: {tail15[-1] if tail15 else out.strip()[-60:]}")
    if rc:
        fails.append("line-tests")

    # [16] 语义层审计：六项悬空边必须全为 0（P4 起这是硬门禁，不许只记录）
    rc, out = run([sys.executable, "-m", "core.report_model", "--audit"])
    line16 = next((l for l in out.splitlines() if '"issues"' in l), "")
    print(f"[16] report model rc={rc} :: {'六项悬空边全为 0' if rc == 0 else '仍有悬空边'}")
    if rc:
        fails.append("report-model")

    # [17] 呈现层：斜体 / 打印规则 / 对比度 / 字阶 / 图四件套
    rc, out = run([sys.executable, "scripts/check_report_presentation.py",
                   "--dir", str(out_b)])
    print(f"[17] presentation rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("presentation")

    # [18] 死代码：每个 .py 必须有引用者（import / 脚本调用 / 文档）。
    # 判据是「说不出谁在用就删」，不是「看着像没用就删」。
    rc, out = run([sys.executable, "scripts/check_dead_code.py", "--check"])
    print(f"[18] dead-code rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("dead-code")
        print(out)

    # [19] 收敛门禁（2026-11-19 接入）：同一件事不许第二次新建。
    # 既有违规冻结在 .convergence-baseline.json（只允许下降）；新增违规直接红。
    rc, out = run([sys.executable, "scripts/check_convergence.py",
                   "--baseline", ".convergence-baseline.json"])
    tail19 = [l for l in out.strip().splitlines() if "PASS" in l or "FAIL" in l]
    print(f"[19] convergence rc={rc} :: {tail19[-1] if tail19 else out.strip()[:80]}")
    if rc:
        fails.append("convergence")
        print(out)

    # [20] 专家卡漂移：experts.yaml 必须等于生成器重算结果（防 phantom 方法让专家永远 blocked）
    rc, out = run([sys.executable, "scripts/gen_experts.py", "--check"])
    print(f"[20] experts-drift rc={rc} :: {out.strip().splitlines()[-1] if out.strip() else ''}")
    if rc:
        fails.append("experts-drift")

    # [21] 默认版式 flow：同一份输入用默认 layout 出一份，验「连续流 + 文笔门禁记录」。
    #      版式回归基线仍走 paper（上面 [2][3][6][14] 显式钉住），这里只验默认入口没坏。
    out_f = OUT / "flow_default"
    rc, out = run([sys.executable, "guagua.py", "report", "run-line",
                   "--intent", "内蒙古三城水果市场调研",
                   "--dir", str(PIPE), "--out", str(out_f),
                   "--layout", "flow",
                   "--quote-mode", "off"])
    html_f = out_f / "report.html"
    man_f = out_f / "manifest.json"
    flow_ok = False
    if html_f.exists() and man_f.exists():
        h = html_f.read_text(encoding="utf-8", errors="replace")
        m = json.loads(man_f.read_text(encoding="utf-8"))
        flow_ok = ("flow-block" in h and 'class="page ' not in h
                   and "flow_gate" in m and bool(m.get("files", {}).get("html")))
    print(f"[21] flow-render rc={rc} :: flow={'OK' if flow_ok else 'MISSING'}")
    if rc or not flow_ok:
        fails.append("flow-render")
        print("   ", out.strip()[-200:])

    # [22] 项目化 flow：模板复制即用；并验 --prose-hard 真的会拦（先证后文闭环）
    import shutil
    tmpl = ROOT / "templates" / "flow-report"
    proj = OUT / "flow_project"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    shutil.copytree(tmpl, proj)
    rc, out = run([sys.executable, "guagua.py", "report", "flow",
                   "--project", str(proj), "--out", str(proj / "out"),
                   "--pdf", "--no-specs", "--no-prose-hard"])
    h = proj / "out" / "report.html"
    p = proj / "out" / "report.pdf"
    ok22 = rc == 0 and h.exists() and p.exists()
    # 硬门禁：同一份短报告加 --prose-hard 必须判 BLOCK，且 manifest 与退出码一致
    rc_h, _ = run([sys.executable, "guagua.py", "report", "flow",
                   "--project", str(proj), "--out", str(proj / "out_hard"),
                   "--no-specs", "--prose-hard"])
    man_h = proj / "out_hard" / "flow_manifest.json"
    hard_ok = False
    if man_h.exists():
        mh = json.loads(man_h.read_text(encoding="utf-8"))
        hard_ok = (bool(mh.get("ok")) == (rc_h == 0)) and mh.get("prose_hard") is True
    print(f"[22] flow-project rc={rc} :: html={h.exists()} pdf={p.exists()} "
          f"prose-hard rc={rc_h} consistent={hard_ok}")
    if not ok22 or not hard_ok:
        fails.append("flow-project")
        print("   ", out.strip()[-200:])

    # [23] 门禁统一：r04 的页数必须读 PDF 实际页数（flow 没有 class="page" 也能判）
    covd = OUT / "flow_project" / "coverage"
    covd.mkdir(parents=True, exist_ok=True)
    (covd / "task_frame.json").write_text(json.dumps(
        {"units": [{"id": "U1", "name": "示例"}],
         "dimensions": [{"id": "D1", "name": "数据"}], "maps": []},
        ensure_ascii=False), encoding="utf-8")
    (covd / "coverage_plan.json").write_text(json.dumps(
        {"core_units": ["U1"], "depth": {"U1": "deep"}, "page_floor": 5,
         "cells": [{"unit": "U1", "dimension": "D1", "status": "verified",
                    "sources": ["S1"]}], "charts": []},
        ensure_ascii=False), encoding="utf-8")
    (covd / "source_ledger.json").write_text(json.dumps(
        {"sources": [{"id": "S1", "url": "https://example.com", "quote": "x"}]},
        ensure_ascii=False), encoding="utf-8")
    r04_json = covd / "r04_gate.json"
    run([sys.executable, "-m", "core.r04_audit",
         "--frame", str(covd / "task_frame.json"),
         "--plan", str(covd / "coverage_plan.json"),
         "--sources", str(covd / "source_ledger.json"),
         "--html", str(OUT / "flow_project" / "out" / "report.html"),
         "--pdf", str(OUT / "flow_project" / "out" / "report.pdf"),
         "--min-pages", "5", "--json", str(r04_json)])
    ok23 = False
    det: dict = {}
    if r04_json.exists():
        g = json.loads(r04_json.read_text(encoding="utf-8"))
        lay = next((l for l in g.get("layers") or [] if l["layer"] == "layout"), {})
        det = lay.get("detail") or {}
        ok23 = (det.get("source") == "pdf" and det.get("pages", 0) >= 5
                and bool(lay.get("ok")))
    print(f"[23] gate-unify :: pdf-pages={det.get('pages')} source={det.get('source')}")
    if not ok23:
        fails.append("gate-unify")

    if env:
        print(f"\n环境未就绪（不计入失败）：{', '.join(env)}")
    print(f"\n=== {'FAIL: ' + ','.join(fails) if fails else 'ALL PASS'} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
