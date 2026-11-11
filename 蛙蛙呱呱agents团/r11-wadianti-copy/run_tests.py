#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R11 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 8 技能（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / plan / demo / run_task /
重依赖探测(probe 恒 ok=true 如实降级)。

用法：
    python run_tests.py          # 全量
    python run_tests.py --verbose
"""
from __future__ import annotations

import argparse
import copy
import json
import os

import subprocess
import sys
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
for p in (HERE, AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

from skills import (s01_topic, s02_seo, s03_hook, s04_copy,  # noqa: E402
                    s05_voice, s06_pr, s07_platform, s08_localize)
from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases  # noqa: E402
import harness  # noqa: E402
import verify_loop  # noqa: E402


class T:
    def __init__(self, verbose=False):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.verbose = verbose

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  ok  {name}")
        else:
            self.failed += 1
            self.errors.append((name, detail))
            print(f"FAIL  {name}" + (f"  -> {detail}" if detail else ""))

    def section(self, title):
        print(f"\n== {title} ==")


def run_agent(*args):
    """运行 agent.py 并解析 __AGENT_RESULT__。返回 (exit_code, dict)。"""
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    out = proc.stdout
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": out[-4000:], "_stderr": proc.stderr[-2000:]}


def _ex(name):
    return os.path.join(HERE, "examples", name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("9 个技能", len(m.get("skills", [])) == 9, str(len(m.get("skills", []))))
    t.check("角色 r11", m.get("role") == "r11")
    t.check("输入端口 topic/audience",
            m.get("inputs") == ["topic", "audience"])
    t.check("输出端口 content_draft/publish_list",
            m.get("outputs") == ["content_draft", "publish_list"])

    t.section("S01 内容策略与选题")
    brief = c.load_json(_ex("brief.json"))
    r = s01_topic._validate_brief(brief)
    t.check("brief 干净通过", r["ok"])
    t.check("brief topic_count=1", r["topic_count"] == 1)
    t.check("brief 渠道非法短路拦截",
            not s01_topic._validate_brief(
                {"audience": "a", "pain_point": "p", "channel": "论坛",
                 "differentiator": "用固定流水线"})["ok"])
    t.check("brief 差异点空泛拦截",
            not s01_topic._validate_brief(
                {"audience": "a", "pain_point": "p", "channel": "公众号",
                 "differentiator": "更好"})["ok"])
    plan = c.load_json(_ex("plan.json"))
    r = s01_topic._validate_plan(plan)
    t.check("plan 干净通过", r["ok"])
    t.check("plan item_count=2", r["item_count"] == 2)
    t.check("plan 非法 status 拦截",
            not s01_topic._validate_plan(
                {"items": [{"topic": "t", "owner": "o", "due": "d",
                            "status": "todo"}]})["ok"])

    t.section("S02 SEO/AEO 与搜索发现")
    keyword = c.load_json(_ex("keyword.json"))
    r = s02_seo._validate_keyword(keyword)
    t.check("keyword 干净通过", r["ok"])
    t.check("keyword intent 非法拦截",
            not s02_seo._validate_keyword(
                {"primary": "p", "longtail": "l", "intent": "branding",
                 "difficulty": "medium", "aeo_opportunity": "a"})["ok"])
    audit = c.load_json(_ex("audit.json"))
    r = s02_seo._validate_audit(audit)
    t.check("audit 干净通过", r["ok"], str(r.get("checks")))
    t.check("audit h2_count>=2", r["h2_count"] >= 2)
    t.check("audit external_links>=3", r["external_links"] >= 3)
    t.check("audit 外链不足拦截",
            not s02_seo._validate_audit(
                {"content": "# 标题\n\n## 小节\n\n只有一个 [链接](https://a.com)"})["ok"])

    t.section("S03 钩子、提纲与立场")
    hook = c.load_json(_ex("hook.json"))
    r = s03_hook._validate_hook(hook)
    t.check("hook 干净通过", r["ok"])
    t.check("hook title_count=3", r["title_count"] == 3)
    t.check("hook 类型非法拦截",
            not s03_hook._validate_hook(
                {"hook_type": "玄学", "titles": ["a", "b", "c"]})["ok"])
    outline = c.load_json(_ex("outline.json"))
    r = s03_hook._validate_outline(outline)
    t.check("outline 干净通过", r["ok"])
    t.check("outline h2_count>=3", r["h2_count"] >= 3)
    t.check("outline 边界不替读者拍板拦截",
            not s03_hook._validate_outline(
                {"outline": "# a\n## b\n## c\n## d\n",
                 "stance": {"claim": "c", "audience": "a",
                            "boundary": "听我的就行"}})["ok"])

    t.section("S04 文案与长文")
    article = c.load_json(_ex("article.json"))
    r = s04_copy._validate_article(article)
    t.check("article 干净通过", r["ok"], str(r.get("checks")))
    t.check("article char_count>=800", r["char_count"] >= 800)
    t.check("article 禁词拦截",
            not s04_copy._validate_article(
                {"text": "# x\n\n" + "总而言之" * 200 + "\n\n延伸阅读"})["ok"])
    script = c.load_json(_ex("script.json"))
    r = s04_copy._validate_script(script)
    t.check("script 干净通过", r["ok"], str(r.get("checks")))

    t.section("S05 品牌语调与编辑")
    guide = c.load_json(_ex("guide.json"))
    r = s05_voice._validate_guide(guide)
    t.check("guide 干净通过", r["ok"])
    t.check("guide dimension_count=6", r["dimension_count"] == 6)
    t.check("guide 维度不足拦截",
            not s05_voice._validate_guide(
                {"audience": "a", "tone": "t", "terms": ["x"],
                 "forbidden": ["y"], "grammar": "g",
                 "dimensions": ["称呼"]})["ok"])
    edit = c.load_json(_ex("edit.json"))
    r = s05_voice._validate_edit(edit)
    t.check("edit 干净通过", r["ok"])
    t.check("edit 残留禁词拦截",
            not s05_voice._validate_edit(
                {"text": "这是一个总而言之的句子", "forbidden_hits": [],
                 "term_fixes": []})["ok"])

    t.section("S06 广告、公关与新闻稿")
    ad = c.load_json(_ex("ad.json"))
    r = s06_pr._validate_ad(ad)
    t.check("ad 干净通过", r["ok"])
    t.check("ad 绝对化禁词拦截",
            not s06_pr._validate_ad(
                {"headline": "全网最低", "benefit": "b", "cta": "预约"})["ok"])
    press = c.load_json(_ex("press.json"))
    r = s06_pr._validate_press(press)
    t.check("press 干净通过", r["ok"])
    t.check("press 导语禁词拦截",
            not s06_pr._validate_press(
                {"headline": "h", "dateline": "北京 — 2026-11-04",
                 "lead": "绝对第一", "body": "b", "boilerplate": "bp",
                 "contact": "c"})["ok"])

    t.section("S07 多平台适配")
    adapt = c.load_json(_ex("adapt.json"))
    r = s07_platform._validate_adapt(adapt)
    t.check("adapt 干净通过", r["ok"])
    t.check("adapt 平台非法拦截",
            not s07_platform._validate_adapt(
                {"platform": "论坛", "title": "t", "length_limit": "l",
                 "tone_shift": "ts", "hashtags": []})["ok"])
    publish = c.load_json(_ex("publish.json"))
    r = s07_platform._validate_publish(publish)
    t.check("publish 干净通过", r["ok"])
    t.check("publish item_count=2", r["item_count"] == 2)
    t.check("publish 未授权拦截",
            not s07_platform._validate_publish(
                {"items": [{"platform": "微信公众号", "url": "u", "status": "ready",
                            "authorized": False}]})["ok"])

    t.section("S08 持续本地化")
    term = c.load_json(_ex("term.json"))
    r = s08_localize._validate_term(term)
    t.check("term 干净通过", r["ok"])
    t.check("term glossary_count=3", r["glossary_count"] == 3)
    t.check("term 语言对非法拦截",
            not s08_localize._validate_term(
                {"source": "zh-CN", "target": "xx-XX",
                 "glossary": [{"source": "s", "target": "t"}]})["ok"])
    review_loc = c.load_json(_ex("review_localize.json"))
    r = s08_localize._validate_review(review_loc)
    t.check("review 干净通过", r["ok"])
    t.check("review status 非法拦截",
            not s08_localize._validate_review(
                {"term": "t", "source_lang": "zh-CN", "target_lang": "en",
                 "status": "draft", "reviewer": "r04"})["ok"])
    probe = s08_localize._probe()
    t.check("localize probe 恒 ok=true（如实降级）",
            probe["ok"] and probe["verdict"] == "PASS",
            f"status={probe.get('status')}")
    t.check("localize probe 带 status", "status" in probe)

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 9 技能", len(names) == 9, str(len(names)))
    v = contracts.validate_output("copy", "article", s04_copy._validate_article(article))
    t.check("契约校验 article 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截",
            not contracts.validate_output("copy", "article", {"ok": True})["ok"])
    t.check("契约校验未知动作拦截",
            not contracts.validate_output("copy", "nope", {"ok": True})["ok"])
    t.check("契约校验未知技能拦截",
            not contracts.validate_output("nope", "article", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "copy", "action": "article",
                   "result": s04_copy._validate_article(article)}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "这里内容待定，稍后补充"}})
    t.check("评审拦截空泛/无产物", rev["verdict"] == "FAIL",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "这篇文章可以发布了"}})
    t.check("评审拦截未授权发布", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "publish_unauthorized",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "总而言之，这里有点空"}})
    t.check("评审拦截 AI 味套话", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "ai_fluff",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    t.check("案例列表 >= 2 个", len(cases.list_cases()) >= 2, str(cases.list_cases()))
    t.check("content-strategy 结构通过", cases.validate_case("content-strategy")["ok"])
    t.check("product-copy 结构通过", cases.validate_case("product-copy")["ok"])
    if os.path.exists(os.path.join(HERE, "cases", "headline-test", "case.json")):
        t.check("headline-test 结构通过", cases.validate_case("headline-test")["ok"])

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("topic channels 白名单外置", len(th["topic"]["channels"]) == 10)
    t.check("seo 意图枚举外置", len(th["seo"]["intent_enum"]) == 5)
    t.check("copy 禁词外置", len(th["copy"]["forbidden_zh"]) >= 20)
    t.check("review 阈值外置 review 节", bool(th["review"]["publish_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    t.section("T6 plan 契约门禁")
    pg = harness.validate_plan(_ex("plan_good.json"))
    t.check("plan 干净通过", pg["ok"] and pg.get("grade") == "PASS", str(pg.get("checks")))
    pb = harness.validate_plan(_ex("plan_bad.json"))
    t.check("plan 缺字段拦截", not pb["ok"] and pb.get("grade") == "FAIL")

    t.section("harness 确定性验证器")
    tmp = os.path.join(role_workspace(HERE), "tmp", "harness_test")
    os.makedirs(tmp, exist_ok=True)
    good_article_path = os.path.join(tmp, "article.json")
    c.write_json(good_article_path, article)
    h = harness.run_validator("article", good_article_path)
    t.check("harness article 门禁 PASS", h["ok"] and h["grade"] == "PASS")
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"text": "太短"})
    h = harness.run_validator("article", bad_path)
    t.check("harness article 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_article_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    pr = harness.probe("localize")
    t.check("harness probe localize 恒 PASS", pr["ok"] and pr["grade"] == "PASS")

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4,
            str(demo.get("demo_artifacts", {}).keys()))

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(os.path.join(HERE, "examples", "article.json"), "data", note="")
    task = protocol.Task(title="写一篇内容复利成稿", owner="r11",
                         intent="写一篇关于内容复利的科普文章",
                         inputs=[inp], acceptance=["article 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 1, str(len(done.outputs)))

    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    t.check("闭环 32 行全绿", matrix["ok"], f"passed={matrix['passed']}/{matrix['total']}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")

    t.section("SOP 十维演进双轨集成门禁 (L01~L10)")
    try:
        from engines import (
            CopyRuntimeEngine,
            IntentDAGCompiler,
            CopyReflexiveHealer,
            CopySpecLedger,
            CopySlopGuard,
            ScenarioMatrix,
            ContentAssetBundle,
            ContentDiffPatchEngine,
            ContentSessionMemory,
            ContentTelemetryWatchdog,
        )
        rt = CopyRuntimeEngine()
        probe = rt.probe_health()
        t.check("L01 运行时健康探针", probe["status"] == "healthy")

        comp = IntentDAGCompiler()
        dag_res = comp.decompile_intent("写一篇关于企业AI工具落地的长文，提炼小红书和公众号的核心卖点与金句")
        t.check("L02 意图解构 Kahn DAG", dag_res["ok"] and dag_res["dag"]["is_dag"])

        healer = CopyReflexiveHealer()
        redlines = healer.audit_redlines({"text": "国家级第一品牌，这篇文章可以发布了。TODO待定"})
        t.check("L03 自愈反思拦截红线", len(redlines) >= 3)

        ledger = CopySpecLedger()
        spec = ledger.load_spec()
        t.check("L04 领域账本加载", spec["spec_loaded"] and len(spec["rules"]["release_gates"]) == 8)

        guard = CopySlopGuard()
        slop_res = guard.audit_text("总而言之，毋庸置疑，转化率大幅提升！")
        t.check("L05 质感去劣化 SlopGuard", not slop_res["is_clean"] and slop_res["slop_count"] >= 2)

        sc_mat = ScenarioMatrix()
        sc_res = sc_mat.generate_matrix("内容复利")
        t.check("L06 横向决策看板三维裂变", sc_res["scenario_count"] == 3)

        diff = ContentDiffPatchEngine()
        p_res = diff.create_patch({"a": 1}, {"a": 2})
        t.check("L08 RFC 6902 局部差量", len(p_res) == 1)

        mem = ContentSessionMemory()
        disambig = mem.resolve_pronouns("按刚才第二套风格改写")
        t.check("L09 会话记忆代词消歧", disambig["had_ambiguity"])

        wd = ContentTelemetryWatchdog()
        t.check("L10 工业容灾看门狗", wd.get_state() == "CLOSED")
    except Exception as e:
        t.check("十维演进核心引擎加载与验证", False, str(e))

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R11 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
