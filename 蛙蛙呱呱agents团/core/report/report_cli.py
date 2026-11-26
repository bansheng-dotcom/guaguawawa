# -*- coding: utf-8 -*-
"""report CLI —— 唯一报告产线入口（v10）。

主入口：
    report build   问题树 → coverage → v9 → 报告（唯一出报告入口）
    report check   验一份成品报告
    report gaps    看项目的 quote 缺口
    report charts  48 型图表能力盘点
    report capabilities / plan  诊断

v11 起已删除 run / build / decide / produce / pack 过渡别名；
`report "指令" …` 与 `report run-line …` 都走同一条主链。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cmd_capabilities(args) -> int:
    """角色适配层：20 角色 / 195 技能，哪些能进报告、输出什么 claim。"""
    from core import report_roles
    if getattr(args, "graph", False) or getattr(args, "graph_write", None):
        from core import capability_graph
        g = capability_graph.build()
        if getattr(args, "graph_write", None):
            p = capability_graph.write(args.graph_write)
            print(f"graph: {p}")
        if getattr(args, "graph", False):
            print(json.dumps(g["counts"], ensure_ascii=False, indent=1))
        return 0
    cat = report_roles.classify()
    if args.write:
        p = report_roles.write_catalog(cat)
        print(f"catalog: {p}")
    if args.json:
        print(json.dumps(cat, ensure_ascii=False, indent=1)[:12000])
        return 0
    c = cat["counts"]
    print(f"角色 {c['roles']} / 技能 {c['skills']} / 动作 {c['actions']}；"
          f"可进报告 {c['eligible_skills']} 技能 / {c['eligible_actions']} 动作")
    for r in report_roles.coverage_table(cat):
        print(f"  {r['role']} {r['name']:<4} 技能 {r['eligible']:>2}/{r['skills']:<2}"
              f" 动作 {r['eligible_actions']:>2}/{r['actions']:<2} "
              f"{'进报告' if r['enters'] else '不进报告'}")
    return 0


def cmd_plan(args) -> int:
    """只看挂载计划：这个方法会不会被数据挂上、缺哪个能力。"""
    from core import analysis_desk, analysis_methods, methods, report_thesis
    desk = analysis_desk.scan(args.dir)
    views = analysis_methods.build_views(desk)
    prof = analysis_desk.profile(desk)
    th = args.thesis or report_thesis.infer(args.intent or "分析", prof)
    p = methods.plan(desk, views, prof, th)
    p["inferred_thesis"] = th
    print(json.dumps(p, ensure_ascii=False, indent=1)[:12000])
    return 0


def cmd_plan_report(args) -> int:
    """一句话 → 专业研究方案（不产报告）：告诉 agent 该查什么、按什么等级收证据。"""
    from core import research_protocol
    p = research_protocol.plan(args.intent, project_dir=getattr(args, "dir", None),
                               has_files=bool(getattr(args, "dir", None)))
    out = getattr(args, "out", None)
    if out:
        from pathlib import Path
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "research_plan.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        (Path(out) / "research_brief.md").write_text(
            research_protocol.to_markdown(p), encoding="utf-8")
    print(json.dumps({"data_lane": p["data_lane"],
                      "what_to_research": p["what_to_research"],
                      "claim_fields": [c["field"] for c in p["claim_contract"]],
                      "report_parts": [s["part"] for s in p["report_shape"]],
                      "out": out or "(仅预览)"}, ensure_ascii=False, indent=1))
    return 0


def cmd_clarify(args) -> int:
    """接任务先对齐意图：出一张澄清卡（不拆卡、不发卡）。"""
    from core import report_clarify
    answers = list(getattr(args, "answer", None) or [])
    if answers and not args.dir:
        print(json.dumps({"ok": False, "error": "--answer 需要 --dir"}, ensure_ascii=False))
        return 2
    if answers:
        # 会话里问完把答案交回来：C1=… C2=… ；写入后自动确认（需用户原话）
        res = report_clarify.answer(
            args.dir, answers,
            by=str(getattr(args, "by", "user") or "user"),
            user_said=str(getattr(args, "user_said", "") or ""))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res.get("ok") else 2
    if getattr(args, "confirm", False):
        if not args.dir:
            print(json.dumps({"ok": False, "error": "--confirm 需要 --dir"}, ensure_ascii=False))
            return 2
        res = report_clarify.confirm(
            args.dir, by="user",
            user_said=str(getattr(args, "user_said", "") or ""))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res.get("ok") else 2
    if not (args.intent and args.out):
        print(json.dumps({"ok": False, "error": "需要 --intent 与 --out"}, ensure_ascii=False))
        return 2
    res = report_clarify.write(args.intent, args.out, force=bool(args.force))
    try:
        from core import intake
        res["intake"] = intake.start(args.out, args.intent)
        # 12 问由 R01 在对话里问用户；这里把问题一并吐给调用方，避免“让用户填表”
        res["ask_user"] = intake.QUESTIONS
    except Exception as exc:  # noqa: BLE001
        res["intake"] = {"ok": False, "error": str(exc)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 1


def cmd_intake(args) -> int:
    """R01 接活：12 问的填写与查看（SOP v5）。"""
    from core import intake
    if getattr(args, "show", False):
        import json as _j
        p = Path(args.dir)
        data = _j.loads((p / "intake.json").read_text(encoding="utf-8-sig")) if (p / "intake.json").is_file() else {}
        print(_j.dumps({"questions": intake.QUESTIONS,
                        "answers": data.get("answers") or {},
                        "status": data.get("status"),
                        "min_answers": intake.MIN_ANSWERS},
                       ensure_ascii=False, indent=1))
        return 0
    if not getattr(args, "answer", None):
        print(json.dumps({"ok": False, "error": "需要 --answer I1=… 或 --show"},
                         ensure_ascii=False))
        return 2
    res = intake.answer(args.dir, args.answer,
                        by=str(getattr(args, "by", "user") or "user"))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 2


def cmd_brief(args) -> int:
    """发任务卡。两种用法：

    A 老路径（不拆卡）：report brief --intent … --out …
    B 新路径（先澄清、再审映射、再发卡）：
        report brief --dir <项目> --plan            出映射表（draft）
        report brief --dir <项目> --plan --confirm  确认并发卡（带 nonce）
    """
    from core import dispatch, report_dispatch
    if getattr(args, "plan", False) or getattr(args, "dir", None) \
            or getattr(args, "project", None):
        base = args.dir or args.out or getattr(args, "project", None)
        if not base:
            print(json.dumps({"ok": False, "error": "需要 --dir <项目>"}, ensure_ascii=False))
            return 2
        if getattr(args, "plan", False):
            # SOP v5：--confirm = 用户给 brief 签字（接活 12 问的确认动作）
            if getattr(args, "confirm", False):
                from core import intake
                if not getattr(args, "ack_cards", False):
                    print(json.dumps({
                        "ok": False, "stage": "card_ack",
                        "error": "还没让用户看卡：确认前必须把卡片清单给用户过目",
                        "hint": "先跑 report brief --dir <项目> --plan（会打印卡片清单），"
                                "用户点头后再加 --confirm --ack-cards "
                                "--user-said \"用户原话\"",
                    }, ensure_ascii=False, indent=1))
                    return 2
                if (Path(base) / "intake.json").is_file():
                    sg = intake.sign_brief(
                        base, by="user",
                        user_said=str(getattr(args, "user_said", "") or ""))
                    if not sg.get("ok"):
                        print(json.dumps({"ok": False, "error": sg.get("error")},
                                         ensure_ascii=False, indent=1))
                        return 2
            res = report_dispatch.write_plan(base, confirm=bool(args.confirm))
            # 用户过卡留痕：确认时把卡片清单与时间写进 plan.json
            if getattr(args, "confirm", False):
                try:
                    import datetime as _dt
                    _pp = Path(base) / "plan.json"
                    _pl = json.loads(_pp.read_text(encoding="utf-8-sig"))
                    _pl["acknowledged_at"] = _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    _pl["acknowledged_by"] = "user"
                    _pp.write_text(json.dumps(_pl, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
                except Exception:  # noqa: BLE001
                    pass
            # v1.5：拆卡 SOP 进产线。--plan 即生成五轴并判 S7 门禁；
            # 门禁不过，--confirm 一律不发卡。
            from core import card_issue
            spec = card_issue.prepare(Path(base), intent=str(res.get("intent") or ""))
            res["card_spec"] = {"ok": spec.get("ok"),
                                "counts": spec.get("counts"),
                                "gates": spec.get("gates")}
            if not spec.get("ok"):
                res["ok"] = False
                # 2026-11-23 修：前置门禁（clarify/intake）早退时不产出
                # plan/pre_issue_gates.json，原来却提示"去看那个文件"，误导。
                if spec.get("error"):
                    res["hint"] = "拆卡前置未过（%s）：%s" % (
                        spec.get("stage") or "?", spec.get("error"))
                elif (Path(base) / "plan" / "pre_issue_gates.json").is_file():
                    res["hint"] = "拆卡门禁未过；看 plan/pre_issue_gates.json，改完重跑"
                else:
                    res["hint"] = "拆卡未产出工件；先确认 clarify 已确认、intake 已签"
                print(json.dumps(res, ensure_ascii=False, indent=1))
                return 2
            # 没确认时把卡片清单摊给用户看（2026-11-22）：不发卡、不执行，
            # 等用户点头后再 --confirm --ack-cards。
            if not getattr(args, "confirm", False):
                try:
                    cj = json.loads((Path(base) / "plan" / "cards.json")
                                    .read_text(encoding="utf-8-sig"))
                    res["cards_preview"] = [
                        {"qid": c.get("qid"), "owner": c.get("owner"),
                         "cells": len(c.get("cells") or [])}
                        for c in (cj.get("cards") or [])]
                except Exception:  # noqa: BLE001
                    res["cards_preview"] = []
                res["ask_user"] = ("以上是拆卡清单（问句→负责人→格子数）。"
                                   "确认后加 --confirm --ack-cards "
                                   "--user-said \"用户原话\" 才会发卡。")
            if args.confirm:
                # 审完即发：确认映射与发卡是同一次动作，避免"确认了但没发"
                res = {**res, "issued": report_dispatch.issue(base)}
                if not res["issued"].get("ok"):
                    print(json.dumps(res, ensure_ascii=False, indent=1))
                    return 2
                try:
                    from core import grid_attach
                    res["grid"] = grid_attach.attach_cards(Path(base))
                except Exception as exc:  # noqa: BLE001
                    res["grid"] = {"ok": False, "why": str(exc)}
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0 if res.get("ok") else 2
        res = report_dispatch.issue(base)
        if res.get("ok"):
            try:
                from core import grid_attach
                res["grid"] = grid_attach.attach_cards(Path(base))
            except Exception as exc:  # noqa: BLE001
                res["grid"] = {"ok": False, "why": str(exc)}
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res.get("ok") else 2
    only = [x.strip() for x in (args.only or "").split(",") if x.strip()] or None
    if not (args.intent and args.out):
        print(json.dumps({"ok": False,
                          "error": "老路径需要 --intent 与 --out；"
                                   "新路径用 --dir（先 clarify 再 --plan）"},
                         ensure_ascii=False))
        return 2
    # v1.5：老路径也走拆卡 SOP。但 2026-11-22 起不再自动补澄清：
    # 没有用户确认过的 clarify.json，一律不发卡。
    cl = Path(args.out) / "clarify.json"
    if not cl.is_file():
        print(json.dumps({
            "ok": False, "stage": "clarify_required",
            "error": "老路径不再自动补澄清卡：没有 clarify.json 就不发卡",
            "hint": "先 report clarify --intent \"…\" --out <项目>，把 12 问问给用户，"
                    "拿到 --user-said 后再 --confirm",
        }, ensure_ascii=False, indent=1))
        return 2
    try:
        _cl = json.loads(cl.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        _cl = {}
    if _cl.get("status") != "confirmed" or str(_cl.get("confirmed_by") or "") != "user":
        print(json.dumps({
            "ok": False, "stage": "clarify_required",
            "error": "澄清卡未由用户确认（需要 status=confirmed、confirmed_by=user）",
            "hint": "把 12 问问给用户，再用 clarify --confirm --user-said \"原话\"",
        }, ensure_ascii=False, indent=1))
        return 2
    from core import card_issue
    res = card_issue.bootstrap(Path(args.out), args.intent, only)
    res["mode"] = "legacy+card_spec"
    res["note"] = "老路径已并入拆卡门禁：五轴不过不发卡"
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 2


def cmd_exchange(args) -> int:
    """卡间协商：把 needs 投到对方 INBOX，并汇总闭环状态。"""
    from core import report_exchange
    base = args.dir
    res = report_exchange.route(base)
    md = report_exchange.render_md(base)
    p = Path(base) / "exchange.md"
    p.write_text(md, encoding="utf-8")
    print(json.dumps({**res, "ledger": str(p)}, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 1


def cmd_probe(args) -> int:
    """探源与可行性探测（SUPPLY-SOP v7.2）。

    两段发卡的第一段：
        report probe --dir <项目> --issue     → 发探源卡给 r18（只查源，不采数）
        report probe --dir <项目>             → 跑探测，生成 plan/supply.json
        report probe --dir <项目> --degrade   → 探测 + 把无数据的格子标 unavailable
    """
    from core import card_issue, card_probe

    base = str(args.dir)
    if getattr(args, "issue", False):
        res = card_issue.prepare_probe_cards(Path(base))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res.get("ok") else 1

    mode = "degrade" if getattr(args, "degrade", False) else "report"
    res = card_probe.probe(base, mode=mode)
    slim = {k: v for k, v in (res or {}).items()
            if k not in ("cell_state", "gates", "draft", "unavailable_demands",
                         "supply_demands")}
    slim["supply_demands"] = [
        {kk: d.get(kk) for kk in ("measure", "level", "matched_source",
                                  "cell_count", "missing", "why")}
        for d in (res.get("supply_demands") or [])
    ]
    slim["unavailable"] = [u.get("measure")
                           for u in (res.get("unavailable_demands") or [])]
    print(json.dumps(slim, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 1


def cmd_preflight(args) -> int:
    """拆卡线预检：clarify/plan/issued/claims/nonce/来源/语义层七项。"""
    import importlib.util
    sp = ROOT / "scripts" / "preflight.py"
    spec = importlib.util.spec_from_file_location("dsh_preflight", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    r = mod.run(args.dir, int(getattr(args, "min_sources", 50) or 50))
    for c in r["checks"]:
        print(("[OK]   " if c["ok"] else "[FAIL] ") + f'{c["id"]} {c["msg"]}')
    print("PASS" if r["ok"] else "FAIL")
    return 0 if r["ok"] else 1


def cmd_collect(args) -> int:
    """收卡：验 quote/来源/覆盖 → 合并 → 缺口清单 → 编译 → 过闸 → 渲染。

    证据门禁（2026-11-19，2026-11-20 收紧）：每条 source 必须 url/date/quote；
    `--min-sources` 按**唯一 URL** 计数（默认 50，`--min-sources 0` 关闭）；
    `--verify-quotes` 联网逐条回抓，`--strict-quotes` 时未核过的来源直接失败。

    降级必须显式授权：想关回抓或关严格，得同时给 `--allow-degraded`，
    否则直接报错退出——过去一条 `--no-strict-quotes` 就能让 40% 未核来源
    静默过关，产物上还看不出降级。
    """
    from core import dispatch, paths, project as project_mod
    verify = bool(getattr(args, "verify_quotes", True))
    strict = bool(getattr(args, "strict_quotes", True))
    allow_degraded = bool(getattr(args, "allow_degraded", False))
    if (not verify or not strict) and not allow_degraded:
        print(json.dumps({
            "ok": False, "stage": "evidence_gate",
            "error": "关闭回抓或关闭严格核验属于降级，必须显式加 --allow-degraded；"
                     "降级会写进 manifest.quotes.degraded，产物会标出来",
            "requested": {"verify_quotes": verify, "strict_quotes": strict}},
            ensure_ascii=False, indent=1))
        return 2
    paths.assert_writable(args.out, allow_runtime=True)
    proj = project_mod.load(getattr(args, "project", None) or args.dir)
    merged, problems = dispatch.collect(
        args.dir,
        require_all=not getattr(args, "allow_partial", False),
        min_sources=int(getattr(args, "min_sources", 0) or 0),
        verify_quotes=verify,
        strict_verify=strict and verify,
        intent=str(getattr(args, "intent", "") or ""),
        allow_open_needs=bool(getattr(args, "allow_open_needs", False)),
        allow_legacy=bool(getattr(args, "allow_legacy", False)),
        project=proj)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cov = merged.get("coverage") or {}
    ev = merged.get("evidence") or {}
    gaps = merged.get("gaps") or {}
    (out / "gaps.json").write_text(json.dumps(
        {"coverage": cov, "evidence": ev, "gaps": gaps,
         "source_verify": merged.get("source_verify") or {}},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if merged.get("source_verify"):
        (out / "source_verify.json").write_text(json.dumps(
            merged["source_verify"], ensure_ascii=False, indent=2),
            encoding="utf-8")
    if cov:
        print(f"[coverage] 发卡 {cov['expected']} / 收卡 {cov['delivered']}"
              f"（{cov['rate']:.0%}）；缺 " + ("、".join(cov["missing"]) or "无"),
              file=sys.stderr)
    if ev:
        print(f"[evidence] 来源 {ev['sources']}（字段齐 {ev['sources_fields_ok']}，"
              f"quote 率 {ev['quote_rate']:.0%}）；数字 {ev['numbers']} / 节 {ev['sections']}",
              file=sys.stderr)
    if gaps:
        print(f"[gaps] 缺单元×维度 {gaps.get('missing_count', 0)}；"
              f"估算 {gaps.get('estimated_count', 0)}；"
              f"缺地图 " + ("、".join(gaps.get("maps_missing") or []) or "无"),
              file=sys.stderr)
    if problems:
        print(json.dumps({"ok": False, "problems": problems[:12],
                          "coverage": cov, "evidence": ev, "gaps": gaps},
                         ensure_ascii=False, indent=1))
        return 2
    merged_path = out / "claims_merged.json"
    merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    cov_dir = Path(args.dir) / "coverage"
    if cov_dir.is_dir():
        rows = [{"id": s.get("file"), "title": s.get("title"),
                 "org": s.get("org"), "url": s.get("url"), "date": s.get("date"),
                 "grade": s.get("grade"), "quote": s.get("quote")}
                for s in (merged.get("sources") or [])]
        (cov_dir / "source_ledger.json").write_text(json.dumps(
            {"sources": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "claims": str(merged_path),
                      "out": str(out), "coverage": cov, "evidence": ev,
                      "gaps": gaps}, ensure_ascii=False, indent=1))
    return 0


def cmd_research(args) -> int:
    """并行调研：发卡 → 写提示词 → 并行执行 →（可选）收卡。

    执行器由 --worker-cmd 或 GUAGUA_WORKER_CMD 提供；不给时只出计划与 PROMPT.md。
    """
    import os
    from core import parallel_research, card_issue

    only = [x.strip() for x in (getattr(args, "only", "") or "").split(",") if x.strip()] or None
    base = Path(args.out)
    base.mkdir(parents=True, exist_ok=True)
    # v1.5：并行调研也走拆卡门禁；缺语义层直接拒。
    boot = card_issue.bootstrap(base, args.intent, only)
    if not boot.get("ok"):
        print(json.dumps(boot, ensure_ascii=False, indent=1))
        return 2
    brief = {"cards": [{"role": c["role"]} for c in boot.get("cards") or []]}
    worker = (getattr(args, "worker_cmd", None)
              or os.environ.get("GUAGUA_WORKER_CMD") or None)
    res = parallel_research.run(str(base), worker, args.workers,
                                args.timeout, only)
    if res.get("mode") == "plan" and not worker:
        print(json.dumps({"ok": True, "mode": "plan", "cards": brief["cards"],
                          "plan": str(base / "research_plan.json"),
                          "hint": res.get("hint")}, ensure_ascii=False, indent=1))
        return 0
    if not res.get("ok"):
        print(json.dumps({"ok": False, "mode": res.get("mode"),
                          "roles": res.get("roles"),
                          "run": str(base / "research_run.json")},
                         ensure_ascii=False, indent=1))
        return 1
    if not getattr(args, "collect", False):
        print(json.dumps({"ok": True, "mode": "worker",
                          "roles": len(res.get("roles") or []),
                          "run": str(base / "research_run.json")},
                         ensure_ascii=False, indent=1))
        return 0
    return cmd_collect(argparse.Namespace(
        dir=str(base), out=str(base / "out"),
        intent=str(getattr(args, "intent", "") or ""),
        allow_partial=bool(getattr(args, "allow_partial", False)),
        min_sources=int(getattr(args, "min_sources", 50)),
        verify_quotes=bool(getattr(args, "verify_quotes", True)),
        strict_quotes=bool(getattr(args, "strict_quotes", True)),
        allow_degraded=bool(getattr(args, "allow_degraded", False))))


def cmd_run_line(args) -> int:
    """v11 唯一入口（P1：转发实现）：一条命令 + 四种输入。"""
    from core import report_line
    # v12：--claims 一步到位：编译（含交叉质询）→ 过闸 → 渲染。
    # 这样「智能体交一份 claims.json」就是完整交付动作，不用记两个命令。
    claims_path = getattr(args, "claims", None)
    source = getattr(args, "source", None)
    if source == "cards" and not claims_path:
        print(json.dumps({
            "ok": False, "stage": "source",
            "error": "--source cards 需要同时给 --claims <claims_merged.json>",
            "hint": "先 report collect 收卡，再 run-line --source cards --claims ..."
        }, ensure_ascii=False, indent=1))
        return 2
    if source == "data" and claims_path:
        print(json.dumps({
            "ok": False, "stage": "source",
            "error": "--source data 与 --claims 冲突：数据型不读收卡产物",
            "hint": "取卡走 --source cards；取项目数据去掉 --claims"
        }, ensure_ascii=False, indent=1))
        return 2
    if str(getattr(args, "layout", "flow")) != "flow":
        print(json.dumps({
            "ok": False, "error": "paper 文档线已下线（2026-11-21）：只保留 flow",
            "hint": "去掉 --layout paper；需要分页由导出器做"}, ensure_ascii=False))
        return 2
    if claims_path:
        import subprocess
        import sys as _sys
        from pathlib import Path as _P
        cp = _P(claims_path)
        try:
            _c = json.loads(cp.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "stage": "claims",
                              "error": f"claims 读不了：{exc}"},
                             ensure_ascii=False))
            return 2
        # 2026-11-22 起：只有「收卡产物」才能直接渲染。收卡产物带 dispatch
        # （nonce 校验结果）或 coverage（发卡/收卡对账）；手写 claims 没有这两样，
        # 必须显式 --solo-claims --allow-solo，并按唯一 URL 过来源门槛。
        is_card_output = bool((_c.get("dispatch") or {}).get("issued")) \
            or bool((_c.get("coverage") or {}).get("delivered"))
        if not is_card_output:
            if not (bool(getattr(args, "solo_claims", False))
                    and bool(getattr(args, "allow_solo", False))):
                print(json.dumps({
                    "ok": False, "stage": "dispatch_gate",
                    "error": "这份 claims 不是收卡产物（缺 dispatch/coverage 凭证），"
                             "拆卡线被跳过",
                    "hint": "走拆卡：report clarify → brief --plan --confirm → "
                            "子智能体按 nonce 交 claims → report collect → "
                            "run-line --claims out/claims_merged.json；"
                            "确需单人稿请用 --solo-claims --allow-solo（会标降级）"
                }, ensure_ascii=False, indent=1))
                return 2
            urls = {str(s.get("url")).strip()
                    for s in (_c.get("sources") or []) if s.get("url")}
            need = int(getattr(args, "min_sources", 50) or 0)
            if need and len(urls) < need:
                print(json.dumps({
                    "ok": False, "stage": "evidence_gate",
                    "error": f"单人稿唯一来源 {len(urls)} 条，低于门槛 {need}",
                    "hint": "补采到 50 条唯一 URL，或 --min-sources 0 显式关闭"
                }, ensure_ascii=False, indent=1))
                return 2
            mode_p = _P(args.out) / "input_mode.json"
            mode_p.parent.mkdir(parents=True, exist_ok=True)
            mode_p.write_text(json.dumps({
                "schema": "dsh.report.input_mode/v1", "mode": "solo",
                "solo": True, "degraded": ["solo_no_dispatch"],
                "sources": len(urls), "claims": str(cp),
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            print("[degraded] 单人稿：未拆卡、未收卡；产物已标 solo_no_dispatch",
                  file=sys.stderr)
        comp = _P(__file__).resolve().parents[2] / "scripts" / "compile_agent_report.py"
        proc = subprocess.run([_sys.executable, str(comp), str(claims_path),
                               "--out", str(_P(args.out) / "_compiled")],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            print((proc.stdout or proc.stderr or "").strip() or f"compile rc={proc.returncode}")
            return proc.returncode
        args.evidence = str(_P(args.out) / "_compiled" / "evidence_pack.json")
        args.draft = str(_P(args.out) / "_compiled" / "draft_sections.json")
    try:
        res = report_line.build(
            intent=args.intent, project_dir=args.dir, out_dir=args.out,
            input_path=getattr(args, "input", None),
            research=getattr(args, "research", False),
            audience=args.audience, theme=args.theme, pdf=args.pdf,
            quote_mode=args.quote_mode, min_binding=args.min_binding,
            evidence_path=getattr(args, "evidence", None),
            draft_path=getattr(args, "draft", None),
            layout=getattr(args, "layout", "flow"),
            prose_hard=bool(getattr(args, "prose_hard", False)),
            gate_hard=bool(getattr(args, "gate_hard", True)))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    # S5: gate (4 gates). block mode fails report; warn mode records only.
    if res.get("ok") and getattr(args, "dir", None):
        _contract = _P(args.out) / "contract.json"
        if _contract.exists():
            import subprocess as _sp
            _gate = _P(__file__).resolve().parents[2] / "scripts" / "check_gates.py"
            _gp = _sp.run([sys.executable, str(_gate), "--project", str(args.dir), "--report", str(_contract)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            try:
                _gres = json.loads(_gp.stdout or "{}")
                if not _gres.get("ok") and _gres.get("mode") == "block":
                    res = {**res, "ok": False, "gate": _gres}
                elif not _gres.get("ok"):
                    res = {**res, "gate_warn": _gres}
            except json.JSONDecodeError:
                pass
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_flow(args) -> int:
    """项目化 flow 报告：facts.py + charts.py（+ 可选 prose_specs.py）。

    2026-11-23 更正：这条路径是「**项目代码放项目文件夹**」的正确实现——
    facts.py / charts.py / prose_specs.py 都从 `--project` 目录加载，
    core/ 只提供引擎，不含任何项目内容。之前误判为「重复渲染器」并删除，
    导致项目代码没有家、只能往 core/ 塞；已恢复。
    """
    from core import flow_report
    from core.report_layout import default_layout
    layout = "paper" if getattr(args, "paper", False) else (args.layout or default_layout())
    try:
        res = flow_report.build(args.project, args.out, pdf=args.pdf,
                                layout=layout,
                                use_specs=not getattr(args, "no_specs", False),
                                author_first=bool(getattr(args, "author_first", False)),
                                prose_hard=bool(getattr(args, "prose_hard", False)),
                                gate_hard=bool(getattr(args, "gate_hard", False)))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_check(args) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_report_flow import check_html
    r = check_html(args.html)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


def cmd_charts(args) -> int:
    from core.chart_capabilities import check, CATALOG
    r = check()
    print(json.dumps({"ok": r["ok"], "count": r["count"], "items": CATALOG},
                     ensure_ascii=False) if args.json
          else f"图表能力：{r['count']}/48，渲染器 {r['renderers']}/48，ok={r['ok']}")
    return 0 if r["ok"] else 1


def cmd_gaps(args) -> int:
    """看项目的 quote gap 清单（诊断，不产报告）。"""
    p = Path(args.project) / "data" / "quote_gaps.json"
    if not p.exists():
        print(json.dumps({"ok": False, "error": f"没有 {p}"}, ensure_ascii=False))
        return 2
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    print(json.dumps(data, ensure_ascii=False, indent=2)[:12000])
    return 0 if int(data.get("unverified") or 0) == 0 else 1


def cmd_attest(args) -> int:
    """交付口径：只从 manifest 与产物取证，不接受任何自由措辞。

    2026-11-20 那次，模型在收尾里写「报告已完成并通过全部门禁验证」，
    而同一份产物的 source_verify.ok 是 false。结论必须由机器回填。
    """
    out = Path(args.out)
    man_p = out / "manifest.json"
    if not man_p.is_file():
        print(f"[attest] FAIL 没有 {man_p}：先跑产线")
        return 2
    m = json.loads(man_p.read_text(encoding="utf-8-sig"))
    flow = ((m.get("gate") or {}).get("flow") or {})
    ev = m.get("evidence") or {}
    q = m.get("quotes") or {}
    files = m.get("files") or {}
    verdict = flow.get("verdict") or "UNKNOWN"
    viol = flow.get("violations") or []
    sha = str(flow.get("gate_sha256") or "")[:12]
    degraded = list(m.get("degraded") or [])
    min_src = ev.get("min_sources")
    lines = [
        f"门禁：{verdict}（判据 {len(viol)} 条违规；门禁指纹 {sha or '未记录'}）",
        f"来源：登记 {ev.get('files', 0)} 条 / 唯一 {ev.get('unique_sources', 0)} 条"
        f"（门槛 {'-' if min_src is None else min_src}，"
        f"口径 {ev.get('min_sources_scope') or '-'}）",
        f"核验：{q.get('verified', '-')}/{q.get('total', '-')} 逐字命中"
        if q.get("total") else "核验：本次未执行（见降级清单）",
        "交付：" + "、".join(
            f"{k.upper()}{'✓' if files.get(k) else '✗'}"
            for k in ("html", "md", "pdf")),
        "降级：" + ("、".join(degraded) if degraded else "无"),
    ]
    q = m.get("questions") or {}
    if q.get("must"):
        claimed = len([x for x in q["must"] if x not in (q.get("unanswered") or [])])
        lines.append(f"问题对账：必答 {len(q['must'])} 问 / 正文认领 {claimed} 问"
                     + (f"；未答 {'、'.join(q['unanswered'])}"
                        if q.get("unanswered") else "；无未答"))
    ex = m.get("exchange") or {}
    if (ex.get("counts") or {}).get("total"):
        c = ex["counts"]
        lines.append(f"卡间协商：{c['total']} 条（回答 {c['answered']} / "
                     f"拒绝 {c['declined']} / 未闭环 {c['open']}）")
    if viol:
        lines.append("违规：" + "；".join(v.get("id", "?") for v in viol[:8]))
    print("\n".join(lines))
    if args.json:
        print(json.dumps({"verdict": verdict, "violations": viol,
                          "evidence": ev, "quotes": q,
                          "degraded": degraded,
                          "files": {k: bool(files.get(k))
                                    for k in ("html", "md", "pdf")}},
                         ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


def main(argv=None) -> int:
    from core.report_flow import THEMES, DEFAULT_THEME
    ap = argparse.ArgumentParser(prog="guagua report",
                                 description="唯一报告产线：一条命令 + 四种输入（v11）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rl = sub.add_parser("run-line", help="v11 唯一入口（P1 转发）：一条命令 + 四种输入")
    rl.add_argument("--intent", required=True, help="你的指令/问题")
    rl.add_argument("--dir", default=None, help="数据项目目录（数据型）")
    rl.add_argument("--input", default=None, help="单份文档（评审型，P2 接入）")
    rl.add_argument("--research", action="store_true", help="联网采集型（P2/P3 接入）")
    rl.add_argument("--out", required=True)
    rl.add_argument("--project", default=None,
                    help="项目资产根（默认 GUAGUA_PROJECT 或 <repo>/projects）")
    rl.add_argument("--audience", default="业务负责人")
    rl.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    rl.add_argument("--layout", default="flow",
                    help="只支持 flow（paper 文档线 2026-11-21 下线）")
    rl.add_argument("--prose-hard", dest="prose_hard", action="store_true", default=True,
                    help="文笔/字数门禁纳入 BLOCK（默认开，2026-11-21 起）")
    rl.add_argument("--no-prose-hard", dest="prose_hard", action="store_false",
                    help="文笔只记分不拦（薄稿会带 prose_soft 降级标记）")
    rl.add_argument("--gate-hard", dest="gate_hard", action="store_true", default=True,
                    help="流程门禁不过就判失败（默认开）")
    rl.add_argument("--no-gate-hard", dest="gate_hard", action="store_false",
                    help="流程门禁只记录，不判失败（排障用，产物会标 degraded）")
    rl.add_argument("--pdf", action="store_true")
    rl.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="off")
    rl.add_argument("--min-binding", type=float, default=0.8)
    rl.add_argument("--evidence", default=None, help="证据包 JSON（智能体写稿路径）")
    rl.add_argument("--draft", default=None, help="章节稿 JSON（智能体写稿路径）")
    rl.add_argument("--claims", default=None,
                    help="收卡产物 claims_merged.json：一步完成 编译+质询+过闸+渲染")
    rl.add_argument("--source", choices=("data", "cards"), default=None,
                    help="取数来源：data=报告层直接算（L3）；cards=收卡后编译（L4，需 --claims）")
    rl.add_argument("--solo-claims", dest="solo_claims", action="store_true",
                    help="单人稿：跳过拆卡直写 claims（必须同时给 --allow-solo，标降级）")
    rl.add_argument("--allow-solo", dest="allow_solo", action="store_true",
                    help="显式授权单人稿；未拆卡、未收卡的 claims 一律拒收")
    rl.add_argument("--min-sources", type=int, default=50,
                    help="单人稿唯一来源下限（默认 50；收卡产物以 collect 的门槛为准）")
    rl.add_argument("--decision", default=None,
                    help="决策契约 JSON；缺省读 <dir>/data/decision.json，再缺省按出场专家起草")
    rl.set_defaults(func=cmd_run_line)

    # v11 / P5：build / decide / produce / pack / research / run 六个名字全部删除。
    # 唯一入口 = `report "指令" --dir … --out …`（也接受 `report run-line …` 写法）。

    fl = sub.add_parser("flow", help="项目化 flow 报告：facts + charts（+ 可选 prose_specs）")
    fl.add_argument("--project", required=True, help="项目目录（含 facts.py / charts.py）")
    fl.add_argument("--out", required=True)
    fl.add_argument("--pdf", action="store_true")
    fl.add_argument("--layout", choices=("flow", "paper"), default=None)
    fl.add_argument("--paper", action="store_true", help="等价 --layout paper")
    fl.add_argument("--prose-hard", dest="prose_hard", action="store_true",
                    default=True, help="文笔门禁纳入 BLOCK（默认开）")
    fl.add_argument("--no-prose-hard", dest="prose_hard", action="store_false",
                    help="文笔只记分，不拦")
    fl.add_argument("--gate-hard", dest="gate_hard", action="store_true",
                    default=True, help="有 coverage/ 三件套时，r04 五项不过就 BLOCK（默认开）")
    fl.add_argument("--no-gate-hard", dest="gate_hard", action="store_false",
                    help="r04 只记录，不拦")
    fl.add_argument("--no-specs", action="store_true", help="不跑 prose_specs 生成")
    fl.add_argument("--author-first", action="store_true",
                    help="人工正文优先：校验 prose_specs 11 字段，但不生成正文")
    fl.set_defaults(func=cmd_flow)

    c = sub.add_parser("check", help="验一份成品报告")
    c.add_argument("--html", required=True)
    c.set_defaults(func=cmd_check)

    at = sub.add_parser("attest", help="交付口径：从 manifest 回填门禁/来源/核验结论")
    at.add_argument("--out", required=True, help="报告产物目录（含 manifest.json）")
    at.add_argument("--json", action="store_true")
    at.set_defaults(func=cmd_attest)

    ch = sub.add_parser("charts", help="48 型图表能力盘点")
    ch.add_argument("--json", action="store_true")
    ch.set_defaults(func=cmd_charts)

    cp = sub.add_parser("capabilities", help="角色适配层：20 角色 / 195 技能的入报资格与 claim")
    cp.add_argument("--json", action="store_true")
    cp.add_argument("--write", action="store_true", help="写 configs/report_capabilities.json")
    cp.add_argument("--graph", action="store_true", help="角色 × 问题 × 能力 × 状态图")
    cp.add_argument("--graph-write", default=None, help="把能力图写到指定 JSON")
    cp.set_defaults(func=cmd_capabilities)

    pl = sub.add_parser("plan", help="只看方法挂载计划（不执行、不出报告）")
    pl.add_argument("--dir", required=True)
    pl.add_argument("--intent", default=None)
    pl.add_argument("--thesis", default=None,
                    help="research / operations / remediation / chain / forecast / growth / "
                         "product / support / people / sre / marketing / sku / store")
    pl.set_defaults(func=cmd_plan)

    # v12：一句话 → 专业研究方案。这一步替代「让用户自己定义研究问题」。
    rp = sub.add_parser("research-plan",
                        help="一句话 → 专业研究方案（8 个模块 / 专家 / 数据通道），不产报告")
    rp.add_argument("--intent", required=True)
    rp.add_argument("--dir", default=None, help="已给数据目录则 data_lane=given")
    rp.add_argument("--out", default=None)
    rp.set_defaults(func=cmd_plan_report)

    g = sub.add_parser("gaps", help="看项目的 quote gap 清单（不产报告）")
    g.add_argument("--project", required=True)
    g.set_defaults(func=cmd_gaps)

    bf = sub.add_parser("brief", help="发任务卡：老路径（不拆卡）或 澄清→映射→发卡")
    bf.add_argument("--intent", default=None, help="老路径：总任务")
    bf.add_argument("--out", default=None, help="老路径：项目目录")
    bf.add_argument("--project", default=None,
                    help="项目资产根（默认 GUAGUA_PROJECT 或 <repo>/projects）")
    bf.add_argument("--only", default=None, help="老路径：只发给这些角色，逗号分隔")
    bf.add_argument("--dir", default=None, help="新路径：已确认 clarify.json 的项目目录")
    bf.add_argument("--plan", action="store_true",
                    help="新路径：先出「问题→角色」映射表（draft）")
    bf.add_argument("--confirm", action="store_true",
                    help="新路径：确认映射并直接发卡（每卡带 nonce）")
    bf.add_argument("--ack-cards", dest="ack_cards", action="store_true",
                    help="用户已看过卡片清单；不加就不许 --confirm 发卡")
    bf.add_argument("--user-said", dest="user_said", default="",
                    help="用户对目标/卡片的一句原话；签 brief 必填")
    bf.set_defaults(func=cmd_brief)

    cf = sub.add_parser("clarify", help="接任务先对齐意图：出澄清卡 / 确认澄清卡")
    cf.add_argument("--intent", default=None)
    cf.add_argument("--out", default=None)
    cf.add_argument("--dir", default=None, help="已有项目目录（配合 --confirm）")
    cf.add_argument("--confirm", action="store_true", help="把 clarify.json 标为已确认")
    cf.add_argument("--answer", action="append", default=None,
                    metavar="C1=答案", help="回答澄清卡里的 confirm 项（可多次），写完自动确认")
    cf.add_argument("--force", action="store_true", help="覆盖已有 clarify.json")
    cf.add_argument("--by", choices=("user", "agent"), default="user",
                    help="答案是谁给的（默认 user；agent 代答不算确认）")
    cf.add_argument("--user-said", dest="user_said", default="",
                    help="用户确认目标的一句原话；缺了不确认")
    cf.set_defaults(func=cmd_clarify)

    it = sub.add_parser("intake", help="R01 接活 12 问（SOP v5）：填写或查看")
    it.add_argument("--dir", required=True)
    it.add_argument("--answer", action="append", default=None, metavar="I1=答案")
    it.add_argument("--by", choices=("user", "agent"), default="user",
                    help="答案是谁给的（默认 user；agent 代答不算用户确认）")
    it.add_argument("--show", action="store_true")
    it.set_defaults(func=cmd_intake)

    ex = sub.add_parser("exchange", help="卡间协商：路由 needs / INBOX / 闭环台账")
    ex.add_argument("--dir", required=True, help="项目目录（含 cards/）")
    ex.set_defaults(func=cmd_exchange)

    # 探源（SUPPLY-SOP v7.2）：两段发卡的第一段——先查源，再发采集卡
    pb = sub.add_parser("probe", help="探源与可行性探测：发探源卡(r18) / 生成供给方案")
    pb.add_argument("--dir", required=True, help="项目目录")
    pb.add_argument("--issue", action="store_true",
                    help="只发探源卡给 r18（不跑探测）")
    pb.add_argument("--degrade", action="store_true",
                    help="探测后把无数据的格子标 unavailable")
    pb.set_defaults(func=cmd_probe)

    pf = sub.add_parser("preflight", help="拆卡线预检：7 项不过就不进收卡/渲染")
    pf.add_argument("--dir", required=True)
    pf.add_argument("--min-sources", type=int, default=50)
    pf.set_defaults(func=cmd_preflight)

    cl = sub.add_parser("collect", help="收各角色 claims → 合并 → 过闸 → 出报告")
    cl.add_argument("--dir", required=True)
    cl.add_argument("--out", required=True)
    cl.add_argument("--project", default=None,
                    help="项目资产根（默认 GUAGUA_PROJECT 或 <repo>/projects）；"
                         "缺省时用 --dir")
    cl.add_argument("--intent", default="", help="报告标题/意图；缺省沿用卡里的 meta")
    cl.add_argument("--pdf", action="store_true")
    cl.add_argument("--allow-partial", action="store_true",
                    help="允许部分专家缺席仍出报告（默认缺卡即失败）")
    cl.add_argument("--min-sources", type=int, default=50,
                    help="唯一来源条数下限（默认 50；传 0 关闭）")
    cl.add_argument("--verify-quotes", dest="verify_quotes", action="store_true",
                    default=True, help="联网逐条回抓 url（默认开）")
    cl.add_argument("--no-verify-quotes", dest="verify_quotes", action="store_false",
                    help="关闭联网回抓，只查字段（降级，需同时给 --allow-degraded）")
    cl.add_argument("--strict-quotes", dest="strict_quotes", action="store_true",
                    default=True, help="未核过的来源直接失败（默认开）")
    cl.add_argument("--no-strict-quotes", dest="strict_quotes", action="store_false",
                    help="未核过只告警（降级，需同时给 --allow-degraded）")
    cl.add_argument("--allow-degraded", action="store_true",
                    help="显式授权降级；降级会写进 manifest.quotes.degraded")
    cl.add_argument("--allow-open-needs", action="store_true",
                    help="允许卡间协商有未闭环的 need（默认不闭环就拒收）")
    cl.add_argument("--allow-legacy", action="store_true",
                    help="放行没有 issued.json 的老卡（降级，会写进 manifest.degraded）")
    cl.set_defaults(func=cmd_collect)

    rs = sub.add_parser("research", help="并行调研：发卡 → 提示词 → 并行执行 → 可选收卡")
    rs.add_argument("--intent", required=True)
    rs.add_argument("--out", required=True)
    rs.add_argument("--project", default=None,
                    help="项目资产根（默认 GUAGUA_PROJECT 或 <repo>/projects）")
    rs.add_argument("--only", default=None, help="只跑这些角色，逗号分隔")
    rs.add_argument("--worker-cmd", default=None,
                    help="外部执行器命令；占位符 {role}/{card_dir}/{prompt}/{claims}")
    rs.add_argument("--workers", type=int, default=8, help="并行度（默认 8）")
    rs.add_argument("--timeout", type=int, default=1800, help="单卡超时秒数")
    rs.add_argument("--collect", action="store_true", help="跑完后立即收卡（只产证据）")
    rs.add_argument("--allow-partial", action="store_true", help="允许缺卡")
    rs.add_argument("--min-sources", type=int, default=50)
    rs.add_argument("--no-verify-quotes", dest="verify_quotes", action="store_false",
                    default=True)
    rs.add_argument("--no-strict-quotes", dest="strict_quotes", action="store_false",
                    default=True)
    rs.add_argument("--allow-degraded", action="store_true",
                    help="显式授权降级；降级会写进 manifest.quotes.degraded")
    rs.set_defaults(func=cmd_research)

    argv = list(sys.argv[1:] if argv is None else argv)
    # v11 唯一入口：`report "指令" --dir …` 等价于 `report run-line --intent "指令" …`
    # 判断依据是「第一个 token 不是已注册子命令」——这样不用记子命令名。
    known = {"run-line", "check", "charts", "capabilities", "plan", "gaps",
             "research-plan", "brief", "collect", "research", "flow", "attest",
             "clarify", "exchange", "intake", "preflight", "probe",
             "-h", "--help"}
    if argv and argv[0] not in known:
        rest = argv
        argv = ["run-line", "--intent", rest[0], *rest[1:]]

    args = ap.parse_args(argv)
    # 边界守卫：写盘命令的目标目录不能指向专家团；允许写运行临时根（兼容旧路径），
    # 但项目资产应写到 --project 指向的项目根。
    from core import paths
    if getattr(args.func, "__name__", "") in {
            "cmd_run_line", "cmd_brief", "cmd_collect", "cmd_research",
            "cmd_plan_report", "cmd_clarify", "cmd_intake", "cmd_flow"}:
        targets = [t for t in (getattr(args, "out", None),
                               getattr(args, "project", None)) if t]
        for t in targets:
            try:
                paths.assert_writable(t, allow_runtime=True)
            except paths.BoundaryError as exc:
                print(f"[report] {exc}", file=sys.stderr)
                return 2
    try:
        return args.func(args)
    except ValueError as exc:
        if isinstance(exc, paths.BoundaryError):
            print(f"[report] {exc}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
