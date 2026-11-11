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
    t.check("14 个技能", len(m.get("skills", [])) == 14, str(len(m.get("skills", []))))
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

    # 风格注册表：extended 降级放行、未登记拦截、新载体放行、文字策略校验
    ext = dict(prompt); ext["style"] = "risograph"
    r = s01_imagegen._validate_prompt(ext)
    t.check("extended 风格解析到 core 并 WARN 放行",
            r["ok"] and r["grade"] == "PASS_WITH_WARNING" and r["resolved_style"] == "duotone",
            f"{r.get('grade')} / {r.get('resolved_style')}")
    t.check("extended 带出已知失败模式", bool(r["checks"][1].get("known_failures")))
    unknown = dict(prompt); unknown["style"] = "vaporwave"
    t.check("未登记风格拦截", not s01_imagegen._validate_prompt(unknown)["ok"])
    alias = dict(prompt); alias["style"] = "赛博朋克"
    t.check("中文别名解析", s01_imagegen._validate_prompt(alias)["resolved_style"] == "gradient")
    bad_tp = dict(prompt); bad_tp["text_policy"] = "auto"
    t.check("text_policy 非法拦截", not s01_imagegen._validate_prompt(bad_tp)["ok"])
    new_media = dict(prompt); new_media["media"] = "infographic"
    t.check("新载体 infographic 放行", s01_imagegen._validate_prompt(new_media)["ok"])
    cat_dir = tempfile.mkdtemp(prefix="r10_catalog_")
    cat = s01_imagegen._build_catalog(cat_dir)
    t.check("catalog 生成", cat["ok"] and cat["styles_total"] == len(c.load_registry()["entries"]),
            str(cat.get("styles_total")))
    t.check("catalog 产出四态 + 建议列",
            {"verified", "sampled", "failed", "unverified"} <= set(cat),
            str(sorted(k for k in cat if k in ("verified", "sampled", "failed", "unverified"))))

    # 准入判据（写死）：3 seed ≥2 过 → core；不足 3 seed 不升
    t.check("准入 3seed/2过 → core",
            s01_imagegen._admission({"seeds": 3, "pass": 2})["suggest"] == "core")
    t.check("准入单 seed 不升 core",
            s01_imagegen._admission({"seeds": 1, "pass": 1})["suggest"] == "extended")
    t.check("准入无基准 → extended（软放行）",
            s01_imagegen._admission({})["suggest"] == "extended")
    t.check("准入 0/3 → experimental（降级禁用）",
            s01_imagegen._admission({"seeds": 3, "pass": 0})["suggest"] == "experimental")

    # experimental 只能进 prompt 文本层，不能占 style 字段
    fake_reg = {"entries": [{"id": "style.vaporwave", "axis": "style",
                             "level": "experimental", "render_style": "gradient",
                             "aliases": []}]}
    r = s01_imagegen._resolve_style("vaporwave", c.load_thresholds(), fake_reg)
    t.check("experimental 解析出但不给 render_style",
            r["render_style"] is None and r["level"] == "experimental")
    t.check("未登记风格占 style 字段被拦",
            s01_imagegen._validate_prompt(
                {"media": "image", "style": "vaporwave", "prompt": "p",
                 "negative_prompt": "n", "style_locks": ["l"]})["ok"] is False)
    adm = s01_imagegen._admit_report()
    t.check("admit 只报不改", adm["ok"] and "drift" in adm, str(adm.get("drift_count")))

    # 提示词包：每风格 N 份，不调用渲染器
    pk_dir = tempfile.mkdtemp(prefix="r10_pack_")
    pk = s01_imagegen._build_pack(pk_dir, seeds=2)
    t.check("pack 生成 风格数×N",
            pk["count"] == len(c.load_registry()["entries"]) * 2, str(pk["count"]))
    t.check("pack 产物可读",
            os.path.isfile(os.path.join(pk_dir, "MANIFEST.json")))

    # 客观评分：占位图与真实图必须分开
    from PIL import Image, ImageDraw  # noqa: E402
    sc_dir = tempfile.mkdtemp(prefix="r10_score_")
    Image.new("RGB", (64, 64), (242, 242, 242)).save(
        os.path.join(sc_dir, "a_placeholder.png"))
    real = Image.new("RGB", (64, 64), (20, 120, 60))
    ImageDraw.Draw(real).rectangle([8, 8, 56, 56], fill=(240, 200, 60))
    real.save(os.path.join(sc_dir, "b_real.png"))
    sc = s01_imagegen._score_images(sc_dir)
    t.check("score 识别占位图", sc["ok"] and sc["placeholders"] == 1, str(sc.get("placeholders")))
    t.check("score 识别真实图", sc["real_images"] == 1, str(sc.get("real_images")))
    t.check("score 空目录拦截",
            not s01_imagegen._score_images(os.path.join(sc_dir, "nope"))["ok"])

    # 载体分级：extended 载体 WARN 放行，非法载体拦截
    ext_media = dict(prompt); ext_media["media"] = "social-card"
    r = s01_imagegen._validate_prompt(ext_media)
    t.check("extended 载体 WARN 放行", r["ok"] and r["grade"] == "PASS_WITH_WARNING")
    bad_media = dict(prompt); bad_media["media"] = "video"
    t.check("非法载体拦截", not s01_imagegen._validate_prompt(bad_media)["ok"])
    # 载体级文字策略默认值生效（poster → overlay-later）
    r = s01_imagegen._validate_prompt({**prompt, "media": "poster"})
    t.check("载体级 text_policy 默认 overlay-later",
            r["text_policy"] == "overlay-later", str(r.get("text_policy")))

    # 结构性硬限制：注册表要带，且文字型载体在 text_policy=none 时给 WARN
    reg_now = c.load_registry()
    t.check("注册表带 hard_limits（≥6 条）",
            len(reg_now.get("hard_limits", {}).get("items", [])) >= 6,
            str(len(reg_now.get("hard_limits", {}).get("items", []))))
    t.check("注册表带来源引用", bool(reg_now.get("sources")))
    r = s01_imagegen._validate_prompt({**prompt, "media": "infographic",
                                       "text_policy": "none"})
    t.check("文字型载体给硬限制 WARN",
            any(x.get("hard_limit") == "exact-typography" for x in r["checks"]),
            str([x.get("dim") for x in r["checks"]]))

    # 生图管线也要拿到配方：新风格不能只是「名字被放行」
    pack = s01_imagegen._style_pack("brutalist", c.load_thresholds(), c.load_registry())
    t.check("generate 管线注入新风格配方",
            pack["resolved"] == "flat" and "massive black type" in pack["positive"],
            pack["positive"][:40])
    t.check("配方带文字策略与画幅",
            pack["text_clause"] and pack["image_size"], str(pack["image_size"]))
    t.check("未登记风格不注入配方",
            s01_imagegen._style_pack("vaporwave", c.load_thresholds(),
                                     c.load_registry())["positive"] == "")

    # dry-run：不碰引擎，产出可确认的规格 + 风险
    dry_dir = tempfile.mkdtemp(prefix="r10_dry_")
    dr = s01_imagegen._dry_run_generate(
        {"title": "试跑", "concept": "蔬菜礼盒", "style": "brutalist",
         "media": "banner", "expand": False}, dry_dir)
    t.check("dry-run 不使用引擎", str(dr["engine_used"]).startswith("none"),
            str(dr["engine_used"]))
    t.check("dry-run 带出配方", "massive black type" in dr["prompt"])
    t.check("dry-run 出风险清单", len(dr["risks"]) >= 2, str(dr["risks"]))
    t.check("dry-run 落盘", os.path.isfile(dr["artifacts"][0]))
    dr2 = s01_imagegen._dry_run_generate(
        {"concept": "x", "style": "vaporwave", "expand": False}, dry_dir)
    t.check("dry-run 未登记风格提示不可复现",
            any("未登记" in r for r in dr2["risks"]), str(dr2["risks"]))
    t.check("dry-run 尺寸按 16:9 换算",
            s01_imagegen._size_for(1920, 1080, c.load_thresholds()) == "landscape_16_9")

    # 离线兜底必须跟着 core 风格走，不能一律套摄影话术
    from engines.prompter import DesignPrompter  # noqa: E402
    fb = DesignPrompter()._expert_fallback("蔬菜礼盒", "flat（brutalist）", "16:9")
    t.check("离线兜底不串味到摄影",
            "Hasselblad" not in fb["prompt_en"] and "flat vector" in fb["prompt_en"],
            fb["prompt_en"][:60])
    fb2 = DesignPrompter()._expert_fallback("蔬菜礼盒", "3d（3d-food）", "1:1")
    t.check("离线兜底按风格选模板", "claymation" in fb2["prompt_en"], fb2["prompt_en"][:50])

    # 气质词分档：摄影腔不得漏进插画/平面/3D 风格
    photo_tokens = ("Hasselblad", "product photography", "award-winning",
                    "cheap oversaturated slop", "plastic texture")
    p = DesignPrompter()
    leaked = []
    for st in c.load_thresholds()["imagegen"]["style_types"]:
        if st == "photo":
            continue
        fb = p._expert_fallback("蔬菜礼盒", st, "1:1")
        hit = [t2 for t2 in photo_tokens
               if t2 in fb["prompt_en"] or t2 in fb["negative_prompt_en"]]
        if hit:
            leaked.append((st, hit))
    t.check("非摄影风格不漏摄影评价词", not leaked, str(leaked))
    t.check("摄影风格仍保留摄影话术",
            "product photography" in p._expert_fallback("x", "photo", "1:1")["prompt_en"])
    t.check("3D 走 render 语气而非摄影",
            "3d render composition" in p._expert_fallback("x", "3d", "1:1")["prompt_en"])

    # 负向与文字策略不能自相矛盾
    fb_none = p._expert_fallback("x", "flat", "1:1", text_policy="none")
    fb_att = p._expert_fallback("x", "flat", "1:1", text_policy="render-attempt")
    fb_ol = p._expert_fallback("x", "flat", "1:1", text_policy="overlay-later")
    neg_none = {w.strip().lower() for w in fb_none["negative_prompt_en"].split(",")}
    neg_att = {w.strip().lower() for w in fb_att["negative_prompt_en"].split(",")}
    t.check("text_policy=none 负向含 text", "text" in neg_none)
    t.check("render-attempt 负向不再写 text/logo",
            not (neg_att & {"text", "lettering", "logo", "logos"}),
            fb_att["negative_prompt_en"])

    # 文档与注册表一致性：文档不许写死过期数字，命令表不许漏入口
    import re as _re
    _n = len(c.load_registry()["entries"])
    _ref = open(os.path.join(HERE, "references", "01-imagegen.md"), encoding="utf-8").read()
    _nums = _re.findall(r"×\s*(\d+)\s*风格", _ref) + _re.findall(r"(\d+)\s*风格 ×", _ref)
    t.check("references 风格数与注册表一致", str(_n) in _nums, f"doc={_nums} reg={_n}")
    _skill = open(os.path.join(HERE, "SKILL.md"), encoding="utf-8").read()
    t.check("SKILL.md 命令表含 compose", "imagegen compose" in _skill)
    t.check("SKILL.md 命令表含 engines", "imagegen engines" in _skill)

    # 跨智能体契约：从别的角色目录调用，必须拿到同样的 JSON 契约
    _p = subprocess.run(
        [sys.executable, os.path.join(HERE, "agent.py"),
         "imagegen", "compose", "--need", "跨角色测试：冷凉蔬菜礼盒主图"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=os.path.join(AGENTS, "r14-wajiaoyi-commerce"))
    _line = next((ln for ln in _p.stdout.splitlines()
                  if ln.startswith("__AGENT_RESULT__ ")), "")
    _payload = json.loads(_line[len("__AGENT_RESULT__ "):]) if _line else {}
    t.check("跨角色目录调用 compose 可用",
            _payload.get("ok") is True and "礼盒" in str(_payload.get("prompt", "")),
            str(_payload.get("ok")))
    t.check("overlay-later 正向加留白句",
            "reserved for later typography" in fb_ol["prompt_en"])

    # 提示词通道：确定性 compose（不依赖 LLM / 引擎）
    cp_dir = tempfile.mkdtemp(prefix="r10_cp_")
    co = s01_imagegen._compose_prompt(
        {"title": "蔬菜礼盒", "subject": "内蒙古冷凉蔬菜礼盒", "style": "brutalist",
         "media": "banner", "width": 1920, "height": 1080}, cp_dir)
    t.check("compose 提示词含配方", "massive black type" in co["prompt"])
    t.check("compose 负向已合并", "watermark" in co["negative_prompt"])
    t.check("compose 尺寸按画幅", co["image_size"] == "landscape_16_9",
            co["image_size"])
    t.check("compose 落盘 md+json",
            len(co["artifacts"]) == 2 and all(os.path.isfile(a) for a in co["artifacts"]))

    # 没有业务主体时必须报错，不许回落到通用模板
    empty = s01_imagegen._compose_prompt({}, cp_dir)
    t.check("compose 缺主体报错", empty["ok"] is False and "主体" in empty["checks"][0]["msg"])
    t.check("compose 缺主体给出示例", bool(empty.get("example")))
    by_need = s01_imagegen._compose_prompt(
        {"need": "中秋蔬菜礼盒主图，暖色调，突出新鲜度", "style": "3d-food"}, cp_dir)
    t.check("compose 支持一句话需求",
            by_need["ok"] and "中秋蔬菜礼盒主图" in by_need["prompt"],
            by_need["prompt"][:40])
    rich = s01_imagegen._compose_prompt(
        {"subject": "甘蓝礼盒", "style": "flat", "scene": "高原菜田清晨",
         "props": "木箱与麻绳", "mood": "清新温暖", "avoid": "塑料感"}, cp_dir)
    t.check("compose 业务字段按序拼接",
            all(k in rich["prompt"] for k in ("甘蓝礼盒", "高原菜田清晨", "木箱与麻绳", "清新温暖")),
            rich["prompt"][:60])
    t.check("compose avoid 进负向", "塑料感" in rich["negative_prompt"])

    # 设计参考库（离线版「参观设计网站」）
    rf = s01_imagegen._refs()
    t.check("参考库载入 ≥25 套", rf["ok"] and rf["count"] >= 25, str(rf.get("count")))
    rq = s01_imagegen._refs(query="dark cinematic")
    t.check("参考库关键词检索有结果", rq["ok"] and len(rq.get("matches", [])) > 0,
            str(len(rq.get("matches", []))))
    rs = s01_imagegen._refs(site="linear")
    t.check("按站点取细节含色板", rs["ok"] and len(rs["reference"]["colors"]) >= 3,
            str(rs.get("reference", {}).get("colors")))
    cr = s01_imagegen._compose_prompt(
        {"need": "品牌主视觉", "style": "gradient", "ref": "linear"}, cp_dir)
    t.check("compose --ref 注入参考设计语言",
            "design language inspired by Linear" in cr["prompt"]
            and bool(cr.get("reference")))

    # 灵感检索：站点清单 + 计划 + 版权规则
    _sites = s01_imagegen._load_sites()
    t.check("灵感站点 ≥35", len(_sites.get("sites", [])) >= 35,
            str(len(_sites.get("sites", []))))
    insp = s01_imagegen._inspire("高原蔬菜包装的高级感", category="packaging")
    t.check("inspire 出计划", insp["ok"] and len(insp["plan"]) >= 2, str(len(insp.get("plan", []))))
    t.check("每条计划带版权档位",
            all(p.get("rights") in ("free-asset", "inspiration-only", "licensed-only")
                for p in insp["plan"]))
    t.check("版权规则含禁止复刻", "禁止复刻" in insp["rights_notice"])
    t.check("inspire 缺主题拦截", not s01_imagegen._inspire("")["ok"])
    t.check("抓取失败不抛异常",
            s01_imagegen._fetch_meta("http://127.0.0.1:9/", timeout=1).get("ok") is False)

    # 分流菜单：无引擎时必须把人引到「只要提示词」
    menu = s01_imagegen._route_menu(interactive=False)
    t.check("分流菜单有 5 条", len(menu["options"]) == 5)
    eng_now = s01_imagegen._engine_available()
    if not eng_now["available"]:
        t.check("无引擎时推荐 1（只要提示词）", menu["recommended"] == "1")
        class _A:
            pass
        a = _A()
        a.action = "generate"; a.input = _ex("prompt.json"); a.explore = False
        a.engine = None; a.dry_run = False
        a.output_dir = tempfile.mkdtemp(prefix="r10_gen_")
        r = s01_imagegen.run(a)
        t.check("无引擎 generate 自动降级为提示词（不再给菜单）",
                r.get("degraded") is True and bool(r.get("prompt")),
                str(r.get("degraded")))
        t.check("降级产物带 next 指路引擎", "engines" in str(r.get("next")))
    else:
        t.check("引擎可用，跳过无引擎分流断言", True)

    # 第二道锁：mock 引擎永不当交付物
    from engines.manager import MockFallbackEngine  # noqa: E402
    mk = MockFallbackEngine()
    t.check("mock 引擎带 is_mock 标记", getattr(mk, "is_mock", False) is True)
    blk = s01_imagegen._mock_block(mk)
    t.check("命中 mock 一律 blocked 且不报 PASS",
            blk["ok"] is False and blk.get("blocked") is True
            and blk["verdict"] == "FAIL")
    t.check("mock 拒绝时仍给分流菜单",
            blk.get("route_menu") is True and blk.get("recommended") == "1")

    # 引擎接口清单：必须给得出 env 开关，方便用户自己接
    eg = s01_imagegen._engines_help()
    t.check("引擎清单覆盖 8 个", eg["ok"] and len(eg["engines"]) == 8,
            str(len(eg.get("engines", []))))
    t.check("引擎清单带 env 接入开关",
            all(e["env"] for e in eg["engines"]))
    t.check("引擎清单区分本地/云端",
            {e["kind"] for e in eg["engines"]} == {"local", "cloud"})

    # edit / explore 也不许拿 mock 当交付物
    if not eng_now["available"]:
        from engines.inpaint import InpaintEditEngine  # noqa: E402
        from engines.explorer import StylescapeExplorer  # noqa: E402
        g_dir = tempfile.mkdtemp(prefix="r10_guard_")
        src_img = os.path.join(g_dir, "src.png")
        Image.new("RGB", (64, 64), (120, 160, 90)).save(src_img)
        out_dir = os.path.join(g_dir, "out")
        os.makedirs(out_dir, exist_ok=True)
        ed = InpaintEditEngine.edit_image(image_path=src_img, instruction="换成雨天",
                                         output_dir=out_dir, target_region="background")
        t.check("edit 无引擎时 blocked 且不留中间产物",
                ed.get("blocked") is True and not os.listdir(out_dir),
                str(os.listdir(out_dir)))
        t.check("explore 无引擎返回空而非占位图",
                StylescapeExplorer.generate_three_directions({"concept": "x"}, g_dir) == [])

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
    t.check("契约覆盖 14 技能", len(names) == 14, str(len(names)))
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
    reg = c.load_registry()
    core_proj = sorted(str(e.get("id", "")).split(".", 1)[-1]
                       for e in reg["entries"] if e.get("level") == "core")
    t.check("生图 core 白名单 = 注册表投影",
            sorted(th["imagegen"]["style_types"]) == core_proj,
            f"{th['imagegen']['style_types']} vs {core_proj}")
    t.check("风格注册表 ≥ 40 条", len(reg["entries"]) >= 40, str(len(reg["entries"])))
    t.check("extended 全部映射到 core",
            all((e.get("render_style") or e.get("parent")) in th["imagegen"]["style_types"]
                for e in reg["entries"] if e.get("level") == "extended"))
    t.check("载体白名单 12 项", len(th["imagegen"]["output_media"]) == 12,
            str(len(th["imagegen"]["output_media"])))
    t.check("logo mark_types 白名单外置", len(th["logo"]["mark_types"]) == 8)
    t.check("动效人格时长外置", th["motion"]["duration_ms"]["playful"] == [150, 300])
    t.check("评审阈值外置 review 节", bool(th["review"]["vague_words"]))

    t.section("T6 plan 契约门禁")
    pg = harness.validate_plan(_ex("plan_good.json"))
    t.check("plan 干净通过", pg["ok"] and pg.get("grade") == "PASS", str(pg.get("checks")))
    pb = harness.validate_plan(_ex("plan_bad.json"))
    t.check("plan 缺字段拦截", not pb["ok"] and pb.get("grade") == "FAIL")

    t.section("harness 确定性验证器")
    tmp_dir = os.path.join(role_workspace(HERE), "tmp")
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
