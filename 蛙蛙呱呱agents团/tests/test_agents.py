# -*- coding: utf-8 -*-
"""agents 域测试（合并自 6 个文件）。

源文件：
    test_ai_generation.py —— R10 生成类能力测试：AI Hive 生图适配（S12）与 MiniMax H3 提示词（S13）。
    test_brief_contract.py —— expert_brief v2 契约：七层、五门槛、18 条上限、卡不写验收。
    test_capabilities.py —— 自有能力目录测试：能力卡落地、可执行能力可解析、运行时不绑外部平台。
    test_capability_fusions.py —— 外部能力「真融合」回归：三个角色里可直接执行的技能（R11/R14/R15）。
    test_domain_pack.py —— 领域包与业务线编排：20 角色、行业匹配、任务编队、作战计划。
    test_skill_bridge.py —— 技能接入：领域方法必须落到现有技能，不能另起一套。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))
R10 = str(TEAM / "r10-wachengmei-design")
if R10 not in sys.path:
    sys.path.insert(0, R10)


import os
from types import SimpleNamespace
import pytest
from skills import s12_aihive, s13_h3prompt
import tempfile
from shared.knowledge import brief as B
from shared import capabilities as caps
import json
import subprocess
from core import domain_pack
from core import skill_bridge



# ====================================================================
# 合并自 test_ai_generation.py：R10 生成类能力测试：AI Hive 生图适配（S12）与 MiniMax H3 提示词（S13）。
# ====================================================================
# -*- coding: utf-8 -*-


def _t2va(**over):
    spec = {
        "mode": "t2va",
        "duration_sec": 8.0,
        "style": "Live-action, cinematic",
        "shots": [
            {"start_sec": 0.0, "text": "a wide shot frames a courier at the alley entrance."},
            {"start_sec": 3.5, "text": "the camera cuts to a close-up of a paper bag."},
        ],
        "soundscape": "Traffic hum, a bicycle bell, footsteps.",
        "music": "Sparse solo piano, unhurried.",
    }
    spec.update(over)
    return spec


def _build(spec):
    args = SimpleNamespace(action="build", input="x.json", out=None)
    checks, prompt, meta = s13_h3prompt._compose(spec)
    ok = all(c["ok"] for c in checks)
    return ok, checks, prompt, meta


# --------------------------------------------------------------------------- #
# H3 提示词
# --------------------------------------------------------------------------- #
def test_t2va_structure_and_timestamps():
    ok, checks, prompt, meta = _build(_t2va())
    assert ok, [c for c in checks if not c["ok"]]
    lines = prompt.splitlines()
    assert lines[0].startswith("integrated_multimodal_description: [Shot 1] ")
    assert "At 00:03.500" in prompt
    assert "overall_soundscape:" in prompt and "non_diegetic_music:" in prompt
    assert prompt.index("overall_soundscape:") < prompt.index("non_diegetic_music:")
    assert meta["shot_count"] == 2 and meta["duration_sec"] == 8.0


def test_i2va_requires_first_frame_instruction_and_label():
    # 没有参考标签 → 必须 FAIL
    ok, checks, _, _ = _build(_t2va(mode="i2va"))
    assert not ok
    assert any(c["dim"] == "h3.refs.required" for c in checks if not c["ok"])

    # 给了 <Picture 1> → PASS，且首行是关键帧指令
    ok2, checks2, prompt2, _ = _build(_t2va(
        mode="i2va",
        references=[{"label": "Picture 1", "role": "first_frame", "shot": 1}],
    ))
    assert ok2, [c for c in checks2 if not c["ok"]]
    assert prompt2.startswith("For the target video, at 0.00 seconds")


def test_fl2va_and_l2va_instruction_use_two_decimal_end():
    for mode in ("fl2va", "l2va"):
        spec = _t2va(mode=mode, references=[
            {"label": "Picture 1", "role": "first_frame", "shot": 1},
            {"label": "Picture 2", "role": "last_frame", "shot": 2},
        ])
        ok, checks, prompt, _ = _build(spec)
        assert ok, [c for c in checks if not c["ok"]]
        assert prompt.startswith("How the reference pictures align with the target video")
        assert "8.00-second" in prompt or "8.00" in prompt


@pytest.mark.parametrize("spec_patch", [
    {"duration_sec": 20.0},
    {"shots": []},
    {"soundscape": ""},
    {"music": ""},
    {"shots": [{"start_sec": 0.0, "text": "a shot"},
               {"start_sec": 0.0, "text": "another shot"}]},
])
def test_invalid_specs_fail(spec_patch):
    ok, checks, __, _ = _build(_t2va(**spec_patch))
    assert not ok
    assert any(not c["ok"] for c in checks)


def test_dialogue_requires_speaker_and_language_tag():
    spec = _t2va()
    spec["shots"][1]["text"] = "the close-up shows a letter, <d>[English] I get off here.</d>"
    ok, checks, __, _ = _build(spec)
    assert not ok
    assert any(c["dim"] == "h3.dialogue.speaker" for c in checks if not c["ok"])


def test_on_screen_text_must_be_quoted():
    spec = _t2va(on_screen_text=["营业中"])
    ok, checks, __, _ = _build(spec)
    assert not ok
    assert any(c["dim"] == "h3.on_screen_text" for c in checks if not c["ok"])


def test_ref2va_six_sections_in_order():
    spec = {
        "mode": "ref2va",
        "duration_sec": 10.0,
        "shots": [{"start_sec": 0.0, "text": "a shot"}],
        "references": [{"label": "Picture 1", "role": "subject"}],
        "sections": {
            "subject_definitions": "<Picture 1> defines the woman in a blue coat.",
            "summary": "A short walk becomes a conversation.",
            "retention_analysis": "<Picture 1> identity and coat color retained throughout.",
            "detailed_description": "[Shot 1] The woman from <Picture 1> walks...",
            "overall_soundscape": "Footsteps and wind.",
            "non_diegetic_music": "Warm strings, low mix.",
        },
    }
    ok, checks, prompt, _ = _build(spec)
    assert ok, [c for c in checks if not c["ok"]]
    order = [prompt.index(f"{k}:") for k in s13_h3prompt.REF2VA_SECTIONS]
    assert order == sorted(order)


# --------------------------------------------------------------------------- #
# AI Hive 生图适配
# --------------------------------------------------------------------------- #
def test_aihive_probe_reports_blocked_without_key(monkeypatch):
    monkeypatch.delenv("AI_HIVE_API_KEY", raising=False)
    monkeypatch.setenv("HOME", os.path.join(ROOT, ".nonexistent-home"))
    out = s12_aihive.run(SimpleNamespace(action="probe"))
    assert out["status"] in ("ready", "blocked")
    assert out["model"] == "public_model_nano_banana_pro"
    key_check = next(c for c in out["checks"] if c["dim"] == "aihive.key")
    assert key_check["ok"] is False


def test_aihive_preview_never_runs_and_caps_batch():
    ok_args = SimpleNamespace(action="preview", prompt="高级商业摄影风格", image=None,
                              batch=2, param=None, output_dir=None, routing="COST_FIRST")
    out = s12_aihive.run(ok_args)
    assert out["verdict"] == "PASS"
    assert out["model"] == "public_model_nano_banana_pro"
    assert "imagegen.py" in out["command"] and "--batch 2" in out["command"]

    too_big = SimpleNamespace(action="preview", prompt="x", image=None,
                              batch=9, param=None, output_dir=None, routing="COST_FIRST")
    out2 = s12_aihive.run(too_big)
    assert out2["verdict"] == "FAIL"


def test_aihive_generate_blocks_without_confirmation():
    args = SimpleNamespace(action="generate", prompt="x", image=None, batch=1,
                           param=None, output_dir=None, routing="COST_FIRST",
                           no_download=False, yes=False, allow_batch=False, timeout=5)
    out = s12_aihive.run(args)
    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert any(c["dim"] == "aihive.confirm" and not c["ok"] for c in out["checks"])


# ====================================================================
# 合并自 test_brief_contract.py：expert_brief v2 契约：七层、五门槛、18 条上限、卡不写验收。
# ====================================================================
# -*- coding: utf-8 -*-


def _card(task_type: str | None = None) -> dict:
    return {"task_id": "t-r06", "owner": "r06", "title": "测试卡",
            "goal": "测试 brief 契约", "question": "测试 brief 契约",
            "task_type": task_type, "skills": [], "non_goals": ["不编事实"]}


def test_build_covers_all_task_types():
    for task_type in B.TASK_LAYERS:
        eb = B.build_brief(_card(task_type), "r06")
        assert eb["task_type"] == task_type
        assert not B.validate_brief(eb, task_type), (task_type, eb)


def test_cap_18_and_parking_lot():
    eb = B.build_brief(_card("决策型"), "r06")
    assert len(eb["must_answer"]) <= B.MAX_MUST_ANSWER
    assert eb["parking_lot"], "决策型超过上限的部分应进 parking_lot"
    total = len(eb["must_answer"]) + len(eb["parking_lot"])
    assert total == 19, "被裁掉的问题不能凭空消失"


def test_five_gates_present():
    eb = B.build_brief(_card("诊断型"), "r06")
    for m in eb["must_answer"]:
        for key in ("answerable_by", "evidence", "owner",
                    "failure_impact", "check"):
            assert str(m.get(key) or "").strip(), (m["id"], key)
        assert m["answerable_by"] in B.ANSWERABLE


def test_card_must_not_carry_acceptance():
    eb = B.build_brief(_card("诊断型"), "r06")
    bad = {"brief_ref": "x", "brief_version": "v2", "acceptance": ["有图"]}
    assert B.validate_bundle(bad, eb), "卡写 acceptance 必须被拒收"
    ok = {"brief_ref": "x", "brief_version": "v2"}
    assert not B.validate_bundle(ok, eb)


def test_brief_rejects_facts():
    eb = B.build_brief(_card("诊断型"), "r06")
    dirty = dict(eb, standards=list(eb["standards"]) + ["市场规模 1200 亿元"])
    assert B.validate_brief(dirty, "诊断型")


def test_issue_bundle_without_project():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "cards" / "r06"
        res = B.issue_bundle(d, "r06", "t-r06", "测试")
        assert not res["problems"]
        assert (d / "bundle.json").is_file()
        assert res["bundle"]["card"]["brief_ref"].endswith("bundle.json#brief")


# ====================================================================
# 合并自 test_capabilities.py：自有能力目录测试：能力卡落地、可执行能力可解析、运行时不绑外部平台。
# ====================================================================
# -*- coding: utf-8 -*-


ROLES = {"r01", "r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09", "r10",
         "r11", "r12", "r13", "r14", "r15", "r16", "r17", "r18", "r19", "r20"}


def test_catalog_is_owned_and_complete():
    items = caps.all_caps()
    assert items, "能力目录为空"
    ids = [c["id"] for c in items]
    assert len(ids) == len(set(ids)), "能力 id 重复"
    for c in items:
        assert c["owner"] in ROLES, f"{c['id']} 的 owner 非法: {c['owner']}"
        for consumer in c["consumers"]:
            assert consumer in ROLES, f"{c['id']} 的消费者非法: {consumer}"
        assert c["kind"] in {"skill", "knowledge"}, f"{c['id']} kind 非法"
        assert c["rules"], f"{c['id']} 缺规则要点"
        assert c["summary"], f"{c['id']} 缺摘要"


def test_every_capability_has_card():
    missing = [c["id"] for c in caps.all_caps() if not os.path.isfile(caps.card_path(c))]
    assert not missing, f"缺能力卡：{missing}"


def test_no_external_dependencies_in_catalog():
    """目录里不允许出现外部平台路径/外链（MCP 是自有能力，不算外部平台）。"""
    text = open(caps.CATALOG_PATH, encoding="utf-8").read().lower()
    for forbidden in ("tra" + "e", "work" + "buddy", "http://", "https://"):
        assert forbidden not in text, f"能力目录残留外部痕迹：{forbidden}"


def test_executable_capabilities_point_to_real_skills():
    """每个可执行能力都要能落到「角色目录 + agent.py」，不写死名单。"""
    executable = [c for c in caps.all_caps() if c["entry"]]
    assert len(executable) >= 10, f"可执行能力过少（{len(executable)}），可能入口丢失"
    for cap in executable:
        role_dir = next((d for d in os.listdir(ROOT)
                         if d.startswith(cap["owner"] + "-")
                         and os.path.isdir(os.path.join(ROOT, d))), None)
        assert role_dir, f"{cap['id']} 的 owner 目录不存在: {cap['owner']}"
        assert os.path.isfile(os.path.join(ROOT, role_dir, "agent.py")), \
            f"{cap['id']} 缺 agent.py"
        # entry 有两种形态：技能（skill + actions）或脚本（script + actions）
        entry = cap["entry"] or {}
        target = entry.get("skill") or entry.get("script")
        assert target, f"{cap['id']} entry 既没有 skill 也没有 script"
        if entry.get("script"):
            assert os.path.isfile(os.path.join(ROOT, entry["script"])), \
                f"{cap['id']} 的脚本不存在: {entry['script']}"


def test_repository_has_no_platform_traces():
    """**运行时**代码不得绑外部平台（分发脚本与文档可以提到镜像，不算依赖）。"""
    tokens = ("tra" + "e", "work" + "buddy")
    runtime_roots = ["core", "shared", "configs", "styles", "templates"]
    hits = []
    for rel in runtime_roots:
        base_dir = os.path.join(ROOT, rel)
        if not os.path.isdir(base_dir):
            continue
        for base, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
            for name in files:
                if not name.endswith((".md", ".py", ".json", ".txt", ".yaml")):
                    continue
                path = os.path.join(base, name)
                try:
                    text = open(path, encoding="utf-8", errors="ignore").read().lower()
                except OSError:
                    continue
                if any(t in text for t in tokens):
                    hits.append(os.path.relpath(path, ROOT))
    # 角色自己的技能代码也属于运行时
    for role_dir in sorted(os.listdir(ROOT)):
        if not (role_dir.startswith("r") and role_dir[1:3].isdigit()
                and os.path.isdir(os.path.join(ROOT, role_dir))):
            continue
        for name in ("agent.py", "contracts.py", "harness.py"):
            p = os.path.join(ROOT, role_dir, name)
            if not os.path.isfile(p):
                continue
            text = open(p, encoding="utf-8", errors="ignore").read().lower()
            if any(t in text for t in tokens):
                hits.append(os.path.join(role_dir, name))
    assert not hits, f"运行时仍有平台痕迹：{hits[:10]}"


def test_stats_shape():
    s = caps.stats()
    items = caps.all_caps()
    assert s["count"] == len(items)
    assert s["executable"] == sum(1 for c in items if c["entry"])
    assert sum(s["by_role"].values()) == len(items)


# ====================================================================
# 合并自 test_capability_fusions.py：外部能力「真融合」回归：三个角色里可直接执行的技能（R11/R14/R15）。
# ====================================================================
# -*- coding: utf-8 -*-


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _run(role, args):
    proc = subprocess.run([sys.executable, "agent.py", *args],
                          cwd=os.path.join(ROOT, role), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("__AGENT_RESULT__")), "")
    assert line, f"{role} 未输出结果: {proc.stderr[-500:]}"
    return proc.returncode, json.loads(line.split(" ", 1)[1])


def _note(**over):
    p1 = "上个月我在景区做核销运营，第一周就踩坑：游客排队40分钟，核销率只有30%，现场3个窗口全堵死。"
    p2 = "我复盘了3轮，发现2个关键点：把核销码提前发到短信，把入园和核销合并成1步。改完第2周，核销率从30%涨到72%。"
    p3 = "这套方法在2个景区验证过，最小的一个只有1个窗口也能跑。你如果也在做景区运营，可以先从核销码前置这1步开始。"
    body = "\n\n".join([p1, p2, p3])
    pad = "\n\n我把每周数据都记在表里，连续记了8周，才敢说这个数字是稳定的。"
    while len(body) < 560:
        body += pad
    data = {"title": "景区核销2个月从30%干到72%", "body": body + "\n\n#AI辅助创作",
            "tags": ["景区运营", "核销率", "小红书运营", "文旅"],
            "core_keywords": ["景区", "核销"], "format_type": "story",
            "cta": "你更想先解决排队还是核销？评论区聊聊", "ai_assisted": True}
    data.update(over)
    return data


# --------------------------------------------------------------------------- #
# R11 · xhs
# --------------------------------------------------------------------------- #
def test_r11_note_passes_and_rejects_long_title(tmp_path):
    rc, out = _run("r11-wadianti-copy", ["xhs", "note", "--input", _write(tmp_path, "n.json", _note())])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    long_title = _note(title="这个标题写得太长了完全超过二十个字的硬性上限所以必须被拦截")
    rc2, out2 = _run("r11-wadianti-copy", ["xhs", "note", "--input", _write(tmp_path, "b.json", long_title)])
    assert out2["verdict"] == "FAIL"
    assert any(c["dim"] == "xhs.title.length" and not c["ok"] for c in out2["checks"])


def test_r11_compliance_blocks_blacklist_cta(tmp_path):
    bad = _note(cta="评论区扣1领取资料，帮你免费诊断", title="全网第一的景区核销秘籍")
    rc, out = _run("r11-wadianti-copy", ["xhs", "compliance", "--input", _write(tmp_path, "bad.json", bad)])
    assert out["verdict"] == "FAIL"
    dims = {c["dim"] for c in out["checks"] if not c["ok"]}
    assert {"xhs.cta.blacklist", "xhs.absolute"} <= dims
    rc2, ok = _run("r11-wadianti-copy", ["xhs", "compliance", "--input", _write(tmp_path, "ok.json", _note())])
    assert ok["verdict"] == "PASS", [c for c in ok["checks"] if not c["ok"]]


def test_r11_score_meets_seven_of_eight(tmp_path):
    rc, out = _run("r11-wadianti-copy", ["xhs", "score", "--input", _write(tmp_path, "s.json", _note())])
    assert out["passed"] >= 7, [c for c in out["checks"] if not c["ok"]]
    assert out["verdict"] == "PASS"
    assert out["ces_reference"]


# --------------------------------------------------------------------------- #
# R14 · selection
# --------------------------------------------------------------------------- #
def _sel(products):
    return {"products": products}


def _product(name, dims, hyp=True, risks=True):
    p = {"name": name, "dims": dims, "source_types": ["检索核实"]}
    if risks:
        p["risks"] = ["同质化"]
    if hyp:
        p["hypothesis"] = {"click_rate": "3%-5%", "cvr": "2%-3%",
                           "margin": "40%-50%", "verify_at": "上架 7 天"}
    return p


GOOD_DIMS = {"capacity": 4, "growth": 5, "entry": 3, "margin": 4, "supply": 4}
WEAK_DIMS = {"capacity": 4, "growth": 3, "entry": 2, "margin": 2, "supply": 2}


def test_r14_selection_normalizes_upstream_weights_and_ranks(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "score", "--input",
                                             _write(tmp_path, "s.json", _sel([
                                                 _product("便携水壶", GOOD_DIMS),
                                                 _product("露营桌", WEAK_DIMS)]))])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    assert out["ranked"][0]["name"] == "便携水壶"
    assert abs(sum(out["weights_used"].values()) - 100) < 0.5


def test_r14_selection_requires_hypothesis_for_recommended(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "score", "--input",
                                             _write(tmp_path, "s.json", _sel([
                                                 _product("便携水壶", GOOD_DIMS, hyp=False)]))])
    assert out["verdict"] == "FAIL"
    assert any(c["dim"] == "selection.hypothesis" and not c["ok"] for c in out["checks"])


def test_r14_profit_red_line(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "profit", "--input", _write(tmp_path, "p.json", {
        "price": 129, "cost": 40, "shipping": 8, "packaging": 2,
        "platform_fee_pct": 5, "ad_pct": 10, "return_rate_pct": 5})])
    assert out["verdict"] == "PASS" and out["margin_pct"] > 40
    rc2, low = _run("r14-wajiaoyi-commerce", ["selection", "profit", "--input", _write(tmp_path, "l.json", {
        "price": 100, "cost": 92})])
    assert low["verdict"] == "FAIL" and low["margin_pct"] < 15


# --------------------------------------------------------------------------- #
# R15 · tco
# --------------------------------------------------------------------------- #
def test_r15_landed_cost_math_and_ranking(tmp_path):
    quotes = {"annual_rate_pct": 6, "quotes": [
        {"supplier": "A", "unit_price": 12, "qty": 1000, "main_freight": 800,
         "insurance": 100, "duty_pct": 5, "lead_days": 35, "payment_terms_days": 30,
         "defects_pct": 1},
        {"supplier": "B", "unit_price": 11.5, "qty": 1000, "main_freight": 400,
         "insurance": 50, "duty_pct": 5, "lead_days": 75, "payment_terms_days": 60,
         "defects_pct": 3}]}
    rc, out = _run("r15-wagongying-erp", ["tco", "compare", "--input",
                                          _write(tmp_path, "t.json", quotes)])
    assert rc == 0 and out["verdict"] == "PASS"
    best = out["ranked"][0]
    assert best["supplier"] == "B"
    assert abs(best["effective_unit_cost"] - 13.04) < 0.05
    # 交期 75 天与不良率 3% 必须有告警
    assert any(c["sev"] == "WARN" and not c["ok"] for c in out["checks"])


def test_r15_lifecycle_requires_three_components(tmp_path):
    rc, out = _run("r15-wagongying-erp", ["tco", "lifecycle", "--input", _write(tmp_path, "l.json", {
        "acquisition": 120000, "implementation": 20000, "operation": 30000,
        "support": 10000, "residual": 15000})])
    assert out["verdict"] == "PASS" and out["tco"] == 165000
    rc2, thin = _run("r15-wagongying-erp", ["tco", "lifecycle", "--input", _write(tmp_path, "t.json", {
        "acquisition": 100, "main_freight": 10})])
    assert thin["verdict"] == "FAIL"
    assert any(c["dim"] == "tco.lifecycle_components" and not c["ok"] for c in thin["checks"])


# --------------------------------------------------------------------------- #
# R08 · deck
# --------------------------------------------------------------------------- #
def _deck(**over):
    slides = [
        {"title": "Q4 复盘", "message": "营收 +18%，利润只 +4%", "is_cover": True},
        {"title": "结论先行", "message": "增长来自复购", "bullets": ["复购 62%"]},
        {"title": "流量结构", "message": "自然流量升、转化降"},
        {"title": "履约成本", "message": "单均履约是最大漏点"},
        {"title": "三个动作", "message": "先修履约再加复购"},
        {"title": "验证方式", "message": "每项动作 4 周验证"},
        {"title": "下一步", "message": "本周定责任人", "is_closing": True},
    ]
    data = {"title": "2026 Q4 增长复盘", "slides": slides}
    data.update(over)
    return data


def test_r08_deck_plan_and_html(tmp_path):
    src = _write(tmp_path, "deck.json", _deck())
    rc, out = _run("r08-wajiancheng-mvp", ["deck", "plan", "--input", src])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    target = str(tmp_path / "deck.html")
    rc2, html_out = _run("r08-wajiancheng-mvp", ["deck", "html", "--input", src, "--out", target])
    assert html_out["verdict"] == "PASS", html_out.get("checks")
    body = open(target, encoding="utf-8").read()
    assert body.startswith("<!doctype html>") and "page-break-after" in body

    bad = _deck(slides=_deck()["slides"][:3])
    rc3, bad_out = _run("r08-wajiancheng-mvp", ["deck", "plan", "--input", _write(tmp_path, "bad.json", bad)])
    assert bad_out["verdict"] == "FAIL"


# --------------------------------------------------------------------------- #
# R10 · brandcheck
# --------------------------------------------------------------------------- #
def test_r10_brandcheck_against_design_md(tmp_path):
    good = {"colors": ["#0F172A", "#22D3EE"], "fonts": ["system-ui"],
            "text_pairs": [{"fg": "#F8FAFC", "bg": "#0F172A"}]}
    rc, out = _run("r10-wachengmei-design", ["brandcheck", "check",
                                             "--input", _write(tmp_path, "b.json", good)])
    assert out["verdict"] == "PASS", [c for c in out["checks"] if not c["ok"]]

    bad = {"colors": ["#FF00FF"], "fonts": ["Comic Sans"]}
    rc2, out2 = _run("r10-wachengmei-design", ["brandcheck", "check",
                                               "--input", _write(tmp_path, "bad.json", bad)])
    assert out2["verdict"] == "FAIL"
    dims = {c["dim"] for c in out2["checks"] if not c["ok"]}
    assert "brand.colors.known" in dims and "brand.fonts" in dims


# --------------------------------------------------------------------------- #
# R07 · prdguard / R08 · htmlreport / miniapp / R10 · imgops
# --------------------------------------------------------------------------- #
def _prd():
    return {
        "title": "会员券分层",
        "product_contract": {"user": "复购 2 次以上", "trigger": "订单完成 7 天",
                             "job": "把复购周期压到 21 天", "completion": "券核销并二次下单"},
        "p0_features": [
            {"name": "分层发券", "trigger": "订单完成 7 天", "rule": "按客单分 3 档",
             "result": "收到券", "state": "待核销", "source": "judgment"},
            {"name": "核销提醒", "trigger": "到期前 48h", "rule": "未核销推 1 次",
             "result": "推送成功", "state": "已提醒", "source": "evidence"},
        ],
        "non_goals": ["不做全场折扣", "不做新客首单"],
        "edge_cases": ["券库存不足降档", "通知失败重试 2 次"],
        "assumptions": ["21 天可达"], "open_questions": ["券成本上限"],
    }


def test_r07_prd_guard_and_render(tmp_path):
    src = _write(tmp_path, "prd.json", _prd())
    rc, out = _run("r07-wademing-pm", ["prdguard", "check", "--input", src])
    assert rc == 0 and out["ok"], [c for c in out["checks"] if not c["ok"]]
    target = str(tmp_path / "prd.md")
    rc2, out2 = _run("r07-wademing-pm", ["prdguard", "render", "--input", src, "--out", target])
    assert out2["ok"] and os.path.isfile(target)
    assert "产品契约" in open(target, encoding="utf-8").read()

    bad = _prd()
    bad["p0_features"][0].pop("state")
    bad["non_goals"] = ["只有一条"]
    rc3, out3 = _run("r07-wademing-pm", ["prdguard", "check", "--input",
                                         _write(tmp_path, "bad.json", bad)])
    assert not out3["ok"]


def test_r08_miniapp_scaffold(tmp_path):
    spec = {"name": "wawa-shop", "pages": [{"path": "pages/home/index", "title": "首页"},
                                           {"path": "pages/cart/index", "title": "购物车"}],
            "tabbar": [{"page": "pages/home/index"}, {"page": "pages/cart/index"}]}
    src = _write(tmp_path, "mini.json", spec)
    rc, out = _run("r08-wajiancheng-mvp", ["miniapp", "plan", "--input", src])
    assert out["verdict"] == "PASS"
    target = str(tmp_path / "app")
    rc2, out2 = _run("r08-wajiancheng-mvp", ["miniapp", "scaffold", "--input", src, "--out", target])
    assert out2["verdict"] == "PASS" and out2["file_count"] >= 9
    assert os.path.isfile(os.path.join(target, "package.json"))


def test_r10_imgops_resize_and_overwrite_guard(tmp_path):
    from PIL import Image
    src = tmp_path / "src.png"
    Image.new("RGB", (800, 600), (15, 23, 42)).save(src)
    out = str(tmp_path / "out.jpg")
    rc, data = _run("r10-wachengmei-design", ["imgops", "resize", "--input", str(src),
                                              "--out", out, "--width", "400"])
    assert data["verdict"] == "PASS" and data["width"] == 400
    rc2, bad = _run("r10-wachengmei-design", ["imgops", "resize", "--input", str(src),
                                              "--out", str(src), "--width", "100"])
    assert bad["verdict"] == "FAIL"
    assert any(c["dim"] == "img.overwrite" and not c["ok"] for c in bad["checks"])


def test_r08_office_xlsx_and_docx(tmp_path):
    xlsx_spec = {"sheets": [{"name": "汇总", "headers": ["渠道", "收入"],
                             "rows": [["自然", 1200], ["投放", 800]]}]}
    target = str(tmp_path / "out.xlsx")
    rc, out = _run("r08-wajiancheng-mvp", ["office", "xlsx", "--input",
                                           _write(tmp_path, "x.json", xlsx_spec), "--out", target])
    assert out["verdict"] == "PASS" and os.path.getsize(target) > 0

    docx_spec = {"title": "Q4 复盘", "sections": [
        {"heading": "结论", "paragraphs": ["复购是主因"], "bullets": ["复购 62%"]}]}
    target2 = str(tmp_path / "out.docx")
    rc2, out2 = _run("r08-wajiancheng-mvp", ["office", "docx", "--input",
                                             _write(tmp_path, "d.json", docx_spec), "--out", target2])
    assert out2["verdict"] == "PASS" and os.path.getsize(target2) > 0
    rc3, out3 = _run("r08-wajiancheng-mvp", ["office", "docx", "--input",
                                             _write(tmp_path, "d.json", docx_spec), "--out", target2])
    assert out3["verdict"] == "FAIL"


def test_e2e_task_routes_to_deck(tmp_path):
    """plan→run --task 的端到端：任务卡意图「幻灯片」必须路由到 deck。"""
    from core import protocol, workspace
    role = os.path.join(ROOT, "r08-wajiancheng-mvp")
    src = _write(tmp_path, "deck.json", _deck())
    ws = workspace.Workspace(os.path.join(ROOT, "workspace"))
    task = protocol.Task(title="做一份季度复盘幻灯片", owner="r08",
                         intent="帮我做一份季度复盘幻灯片", inputs=[protocol.Port(src, "data", note="")],
                         acceptance=["deck 门禁通过"])
    ws.create_task(task)
    rc, out = _run("r08-wajiancheng-mvp", ["run", "--task", task.task_id])
    assert out.get("skill") == "deck", out
    assert out.get("ok") is True, out


# ====================================================================
# 合并自 test_domain_pack.py：领域包与业务线编排：20 角色、行业匹配、任务编队、作战计划。
# ====================================================================
# -*- coding: utf-8 -*-


def test_twenty_role_packs_are_complete():
    roles = domain_pack.load_roles()
    assert len(roles) == 20
    for rid, r in roles.items():
        assert len(r["books"]) >= 5
        assert any(b["lang"] == "en" for b in r["books"])
        assert any(b["lang"] == "zh" for b in r["books"])
        assert len(r["methods"]) >= 6
        assert len(r["kpis"]) >= 6 and len(r["decisions"]) >= 4
        assert len(r["failure_modes"]) >= 4 and len(r["report_sections"]) >= 6


def test_industry_match_for_energy_retail():
    ind = domain_pack.match_industry("县域加油站非油业务增长")
    assert ind["name"].startswith("能源零售")
    assert "进站率" in "".join(ind["kpis"])


def test_task_force_for_gas_station():
    roles = domain_pack.load_roles()
    ind = domain_pack.match_industry("县域加油站非油业务增长")
    picked = domain_pack.score_roles("县域加油站非油业务增长", roles, ind)
    ids = {p["role"] for p in picked}
    assert {"r01", "r06", "r14", "r15"} <= ids
    assert len(picked) <= 5


def test_plan_contains_methods_and_design():
    p = domain_pack.plan("社区母婴连锁增长")
    assert p["industry"]["hypothesis"]
    methods = {m["method"] for m in p["analysis_design"]}
    assert {"decompose_mix_rate", "ab_proportion / ab_mean", "did_twfe + event_study + placebo"} <= methods
    md = domain_pack.to_markdown(p)
    for token in ("任务编队", "指标树", "分析设计", "三种情景", "90 天验证", "数据清单", "停止条件"):
        assert token in md
    # 不编项目数字：行业基准必须带「校准」
    assert "需校准" in md or "需按" in md


# ====================================================================
# 合并自 test_skill_bridge.py：技能接入：领域方法必须落到现有技能，不能另起一套。
# ====================================================================
# -*- coding: utf-8 -*-


def test_all_methods_have_landing():
    c = skill_bridge.coverage()
    assert c["total"] == 120
    assert not c["missing"], c["missing"]
    assert c["coverage_rate"] >= 0.95
    assert c["counts"]["exact"] >= 50
    assert c["counts"]["new"] <= 5


def test_statistics_methods_use_r06_skills():
    assert skill_bridge.info("r06", "DiD")["skill"] == "did"
    assert skill_bridge.info("r06", "DiD")["fit"] == "exact"
    assert skill_bridge.info("r06", "A/B 检验")["skill"] == "abtest"
    assert skill_bridge.info("r06", "弹性")["skill"] == "elasticity"
    assert skill_bridge.info("r06", "队列留存")["action"] == "cohort"


def test_supply_methods_use_r15_skills():
    assert skill_bridge.info("r15", "TCO")["skill"] == "tco"
    assert skill_bridge.info("r15", "安全库存")["skill"] == "safety-stock"


def test_two_new_methods_are_declared():
    new = [(r, m) for r, items in skill_bridge.skill_map()["roles"].items()
           for m, x in items.items() if x["fit"] == "new"]
    assert len(new) <= 5
    assert all(skill_bridge.info(r, m)["note"] for r, m in new)


def test_commands_are_real_cli():
    cmds = skill_bridge.commands("r06")
    assert any("call r06 -- did" in c for c in cmds)
    assert any("call r06 -- abtest" in c for c in cmds)
