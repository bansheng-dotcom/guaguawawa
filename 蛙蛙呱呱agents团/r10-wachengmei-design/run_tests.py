#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R10 端到端回归测试：把 SOP 的 T10 验收脚本化。

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
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
for p in (HERE, AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

from skills import (s01_imagegen, s02_logo, s03_uiux, s04_brand,  # noqa: E402
                    s05_motion, s06_imaging, s07_media, s08_transcribe,
                    s09_render)
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
    t.check("10 个技能", len(m.get("skills", [])) == 10, str(len(m.get("skills", []))))
    t.check("角色 r10", m.get("role") == "r10")
    t.check("输入端口 brand_brief/content",
            m.get("inputs") == ["brand_brief", "content"])

    t.section("S01 AI 生图与插画")
    prompt = c.load_json(_ex("prompt.json"))
    r = s01_imagegen._validate_prompt(prompt)
    t.check("prompt 干净通过", r["ok"])
    t.check("prompt lock_count=3", r["lock_count"] == 3)
    t.check("prompt 媒体非法短路拦截",
            not s01_imagegen._validate_prompt(
                {"media": "video", "style": "flat", "prompt": "p",
                 "negative_prompt": "n", "style_locks": ["l"]})["ok"])
    t.check("prompt 风格锁自我推翻拦截",
            not s01_imagegen._validate_prompt(
                {"media": "image", "style": "flat", "prompt": "p",
                 "negative_prompt": "不要 flat", "style_locks": ["flat"]})["ok"])
    style = c.load_json(_ex("style.json"))
    r = s01_imagegen._validate_style(style)
    t.check("style 干净通过", r["ok"])
    t.check("style 非法 hex 拦截",
            not s01_imagegen._validate_style(
                {"style": "flat", "composition": ["c"], "palette": ["red"]})["ok"])

    t.section("S02 Logo 与图标")
    logo = c.load_json(_ex("logo.json"))
    r = s02_logo._validate_logo(logo)
    t.check("logo 干净通过", r["ok"])
    t.check("logo concept_count=3", r["concept_count"] == 3)
    t.check("logo tests_passed=3", r["tests_passed"] == 3)
    bad_logo = dict(logo); bad_logo["tests"] = {"16": True}
    t.check("logo 缺尺寸测试拦截", not s02_logo._validate_logo(bad_logo)["ok"])
    bad_logo2 = dict(logo); bad_logo2["colors"] = {"primary": "blue", "secondary": "yellow"}
    t.check("logo 非法色拦截", not s02_logo._validate_logo(bad_logo2)["ok"])
    favicon = c.load_json(_ex("favicon.json"))
    r = s02_logo._validate_favicon(favicon)
    t.check("favicon 干净通过", r["ok"])
    t.check("favicon variant_count=3", r["variant_count"] == 3)
    t.check("favicon 非 svg 拦截", not s02_logo._validate_favicon(
        {"variants": [{"name": "favicon"}, {"name": "app-icon"}, {"name": "x"}],
         "source": "logo.png"})["ok"])

    t.section("S03 产品 UI/UX")
    screen = c.load_json(_ex("screen.json"))
    r = s03_uiux._validate_screen(screen)
    t.check("screen 干净通过", r["ok"])
    t.check("screen zone_count=4", r["zone_count"] == 4)
    t.check("screen component_count=3", r["component_count"] == 3)
    bad_screen = copy.deepcopy(screen); bad_screen["a11y"]["focus_visible"] = False
    t.check("screen a11y 缺焦点拦截", not s03_uiux._validate_screen(bad_screen)["ok"])
    ux = c.load_json(_ex("ux.json"))
    r = s03_uiux._validate_ux(ux)
    t.check("ux 干净通过", r["ok"])
    t.check("ux cause_count=3", r["cause_count"] == 3)
    t.check("ux 缺验证指标拦截", not s03_uiux._validate_ux(
        {"problem": "p", "causes": ["c"], "improvements": ["i"],
         "validation": {}})["ok"])

    t.section("S04 品牌 VI 与设计令牌")
    vi = c.load_json(_ex("vi.json"))
    r = s04_brand._validate_vi(vi)
    t.check("vi 干净通过", r["ok"])
    t.check("vi direction_count=3", r["direction_count"] == 3)
    bad_vi = copy.deepcopy(vi); bad_vi["directions"][0]["narrative"] = "因为蓝色代表信任"
    t.check("vi 陈词滥调拦截", not s04_brand._validate_vi(bad_vi)["ok"])
    bad_vi2 = copy.deepcopy(vi); bad_vi2["voice"]["forbidden"] = ""
    t.check("vi 缺 voice 维拦截", not s04_brand._validate_vi(bad_vi2)["ok"])
    token = c.load_json(_ex("token.json"))
    r = s04_brand._validate_token(token)
    t.check("token 干净通过", r["ok"])
    t.check("token token_count=3", r["token_count"] == 3)
    t.check("token 主色非法拦截", not s04_brand._validate_token(
        {"tokens": {"color": [{"name": "a", "value": "b"}],
                    "typography": [{"name": "c", "value": "d"}],
                    "spacing": [{"name": "e", "value": "f"}]},
         "primary": "blue"})["ok"])

    t.section("S05 交互原型与动效")
    motion = c.load_json(_ex("motion.json"))
    r = s05_motion._validate_motion(motion)
    t.check("motion 干净通过", r["ok"])
    t.check("motion 人格非法拦截", not s05_motion._validate_motion(
        {"personality": "violent", "duration_ms": 220, "easing": "e",
         "acceleration": {"enter": "decelerate", "exit": "accelerate"},
         "reduced_motion": True,
         "layers": {"primary": "a", "secondary": "b", "ambient": "c"}})["ok"])
    t.check("motion 加减速反向拦截", not s05_motion._validate_motion(
        {"personality": "playful", "duration_ms": 220, "easing": "e",
         "acceleration": {"enter": "accelerate", "exit": "decelerate"},
         "reduced_motion": True,
         "layers": {"primary": "a", "secondary": "b", "ambient": "c"}})["ok"])
    prototype = c.load_json(_ex("prototype.json"))
    r = s05_motion._validate_prototype(prototype)
    t.check("prototype 干净通过", r["ok"])
    t.check("prototype screen_count=3", r["screen_count"] == 3)

    t.section("S06 修图与图像工程")
    edit = c.load_json(_ex("edit.json"))
    r = s06_imaging._validate_edit(edit)
    t.check("edit 干净通过", r["ok"])
    t.check("edit 非法操作拦截", not s06_imaging._validate_edit(
        {"operations": ["explode"], "source": "a.png", "overwrite": "never"})["ok"])
    t.check("edit 危险覆盖拦截", not s06_imaging._validate_edit(
        {"operations": ["resize"], "source": "a.png", "overwrite": "always"})["ok"])
    probe = s06_imaging._probe()
    t.check("imaging probe 恒 ok=true（如实降级）", probe["ok"] and probe["verdict"] == "PASS",
            f"status={probe.get('status')}")
    t.check("imaging probe 带 status", "status" in probe)

    t.section("S07 视频与音频处理")
    media = c.load_json(_ex("media.json"))
    r = s07_media._validate_media(media)
    t.check("media 干净通过", r["ok"])
    t.check("media 奇数缩放拦截", not s07_media._validate_media(
        {"operations": ["scale"], "source": "a.mov",
         "target": {"container": "mp4", "audio": "aac"},
         "scale": {"width": 1921, "height": 1080}, "overwrite": "suffix"})["ok"])
    t.check("media 非法容器拦截", not s07_media._validate_media(
        {"operations": ["transcode"], "source": "a.mov",
         "target": {"container": "avi", "audio": "aac"}, "overwrite": "never"})["ok"])
    probe = s07_media._probe()
    t.check("media probe 恒 ok=true", probe["ok"] and probe["verdict"] == "PASS")

    t.section("S08 转写与字幕")
    transcribe = c.load_json(_ex("transcribe.json"))
    r = s08_transcribe._validate_transcribe(transcribe)
    t.check("transcribe 干净通过", r["ok"])
    t.check("transcribe segment_count=2", r["segment_count"] == 2)
    t.check("transcribe 非法模型拦截", not s08_transcribe._validate_transcribe(
        {"model_size": "huge", "source": "a.mp3", "text": "t",
         "segments": [{"start": 0, "end": 1, "text": "t"}]})["ok"])
    probe = s08_transcribe._probe()
    t.check("transcribe probe 恒 ok=true", probe["ok"] and probe["verdict"] == "PASS")

    t.section("S09 数据视觉与营销物料（生成层）")
    poster = c.load_json(_ex("poster.json"))
    r = s09_render._validate_poster(poster)
    t.check("poster 契约干净通过", r["ok"])
    t.check("poster point_count=3", r["point_count"] == 3)
    t.check("poster 非法主题拦截", not s09_render._validate_poster(
        {"title": "t", "subtitle": "s", "theme": "rainbow", "subject": "mouse",
         "selling_points": [{"title": "a", "desc": "b"},
                            {"title": "c", "desc": "d"},
                            {"title": "e", "desc": "f"}]})["ok"])
    t.check("poster 卖点不足 3 拦截", not s09_render._validate_poster(
        {"title": "t", "subtitle": "s", "theme": "tech-blue", "subject": "mouse",
         "selling_points": [{"title": "a", "desc": "b"}]})["ok"])
    svg = s09_render.render_poster(poster)
    t.check("poster 渲染出 SVG", svg.startswith("<svg") and "selling" in svg.lower()
            or "M 600 940" in svg)
    t.check("poster 主题枚举齐全", set(s09_render._theme()["themes"]) ==
            {"tech-blue", "brand-yellow", "minimal"})

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 10 技能", len(names) == 10, str(len(names)))
    v = contracts.validate_output("logo", "logo", s02_logo._validate_logo(logo))
    t.check("契约校验 logo 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截",
            not contracts.validate_output("logo", "logo", {"ok": True})["ok"])
    t.check("契约校验未知动作拦截",
            not contracts.validate_output("logo", "nope", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "logo", "action": "logo",
                   "result": s02_logo._validate_logo(logo)}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "这里内容待定，稍后补充"}})
    t.check("评审拦截空泛/无产物", rev["verdict"] == "FAIL",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "已做高可用生产级部署"}})
    t.check("评审拦截越界到生产工程", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_creep",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    t.check("案例列表 >= 2 个", len(cases.list_cases()) >= 2, str(cases.list_cases()))
    t.check("logo-rebrand 结构通过", cases.validate_case("logo-rebrand")["ok"])
    t.check("app-launch-visual 结构通过", cases.validate_case("app-launch-visual")["ok"])

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("生图 style 白名单外置", len(th["imagegen"]["style_types"]) == 8)
    t.check("logo mark_types 白名单外置", len(th["logo"]["mark_types"]) == 8)
    t.check("动效人格时长外置", th["motion"]["duration_ms"]["playful"] == [150, 300])
    t.check("评审阈值外置 review 节", bool(th["review"]["vague_words"]))

    t.section("T6 plan 契约门禁")
    pg = harness.validate_plan(_ex("plan_good.json"))
    t.check("plan 干净通过", pg["ok"] and pg.get("grade") == "PASS", str(pg.get("checks")))
    pb = harness.validate_plan(_ex("plan_bad.json"))
    t.check("plan 缺字段拦截", not pb["ok"] and pb.get("grade") == "FAIL")

    t.section("harness 确定性验证器")
    tmp_dir = os.path.join(HERE, "workspace", "tmp")
    if not os.path.isdir(tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="r10_harness_", dir=tmp_dir)
    good_logo_path = os.path.join(tmp, "logo.json")
    c.write_json(good_logo_path, logo)
    h = harness.run_validator("logo", good_logo_path)
    t.check("harness logo 门禁 PASS", h["ok"] and h["grade"] == "PASS")
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"mark_type": "star", "concepts": [], "tests": {},
                            "trademark_check": [],
                            "colors": {"primary": "x", "secondary": "y"}})
    h = harness.run_validator("logo", bad_path)
    t.check("harness logo 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")
    vi_path = os.path.join(tmp, "vi.json")
    c.write_json(vi_path, vi)
    vd = harness.verify(good_logo_path, vi_path)
    t.check("harness verify 组合门禁 PASS", vd["ok"] and vd["verdict"] == "PASS")

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4,
            str(demo.get("demo_artifacts", {}).keys()))

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(os.path.join(HERE, "examples", "logo.json"), "data", note="")
    task = protocol.Task(title="设计一个 logo", owner="r10", intent="设计一个 logo 并生成图标变体",
                         inputs=[inp], acceptance=["logo 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 1, str(len(done.outputs)))

    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    t.check("闭环 28 行全绿", matrix["ok"], f"passed={matrix['passed']}/{matrix['total']}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")

    t.section("十维演进集成测试 (L01~L10 双轨集成门禁)")
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_evolution_l01_l10")
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    t.check("演进集成测试 100% 通过", result.wasSuccessful(), f"failures={len(result.failures)}, errors={len(result.errors)}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R10 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
