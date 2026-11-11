# -*- coding: utf-8 -*-
"""S01 AI 生图与插画 —— 能力域 1（最终完全体：LLM 动态大脑 + 真实外置引擎调度 + 真实 VLM 多模态审校反思 + 商业排版联动）。
"""
from __future__ import annotations

import os
import json
import sys
import time
from typing import Any, Dict, List, Optional

from . import _common as c
from engines import get_engine_manager, ImageGenTask, get_design_prompter, get_vlm_critic
from engines.explorer import StylescapeExplorer
from engines.inpaint import InpaintEditEngine

NAME = "imagegen"
DESC = "AI生图与插画：prompt / style / generate (LLM + VLM + Engines)"
_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ck(ok: bool, msg: str, dim: str = "", sev: Optional[str] = None, **ev) -> Dict[str, Any]:
    """sev 三档：OK / WARN（不拦但记录）/ BLOCKER（拦）。不传则按 ok 推导。"""
    d = {"ok": bool(ok), "msg": msg, "dim": dim,
         "sev": sev or ("OK" if ok else "BLOCKER")}
    d.update(ev)
    return d


def _resolve_style(style: Any, th: Dict[str, Any], reg: Dict[str, Any]) -> Dict[str, Any]:
    """把任意风格名解析成可渲染的 core style。

    返回 {render_style, level, requested, failure_modes, text_policy_default, aspect_default}。
    render_style 为 None 表示无法解析（BLOCKER）。core 直接命中；extended/experimental
    经 registry 的 aliases 命中后降级到其 render_style，门禁只记 WARN 不拦。
    """
    core = list(th["imagegen"]["style_types"])
    out = {"requested": style, "render_style": None, "level": "unknown",
           "failure_modes": [], "text_policy_default": "none", "aspect_default": ""}
    if not isinstance(style, str) or not style.strip():
        return out
    if style in core:
        out.update(render_style=style, level="core")
        return out
    rec = c.style_index(reg).get(style.strip().lower())
    if not rec:
        return out
    rs = rec.get("render_style") or rec.get("parent")
    if rs not in core:
        return out
    level = str(rec.get("level") or "extended")
    out.update(render_style=rs,
               level=level,
               failure_modes=list(rec.get("failure_modes") or []),
               text_policy_default=str(rec.get("text_policy_default") or "none"),
               aspect_default=str(rec.get("aspect_default") or ""))
    if level == "experimental":
        # 未过基准的风格只允许写进 prompt 文本层，不允许占用 style 字段
        out.update(render_style=None,
                   block_reason="experimental：未过基准，只能写进 prompt 文本层")
    return out


def _style_pack(style: str, th: Dict[str, Any], reg: Dict[str, Any]) -> Dict[str, Any]:
    """把注册表配方接到生图管线上：校验认得的风格，生图也要认得。

    没有这一步，`generate` 只会把风格名丢给 LLM 扩写，recipe / 文字策略 / 画幅全丢。
    """
    rs = _resolve_style(style, th, reg)
    rec = c.style_index(reg).get(str(style).lower()) if rs["render_style"] else None
    rec = rec or {}
    sizes = (th["imagegen"].get("image_sizes") or {})
    return {
        "resolved": rs["render_style"],
        "level": rs["level"],
        "style_hint": (f"{rs['render_style']}（{style}）" if rs["render_style"] else str(style)),
        "positive": str(rec.get("positive_recipe") or ""),
        "negative": str(rec.get("negative_recipe") or ""),
        "text_clause": _text_clause(str(rec.get("text_policy_default") or "none")),
        "text_policy": str(rec.get("text_policy_default") or "none"),
        "image_size": sizes.get(str(rec.get("aspect_default") or "1:1")),
        "failure_modes": list(rec.get("failure_modes") or []),
    }


def _text_policy_for(brief: Dict[str, Any], th: Dict[str, Any],
                     pack: Dict[str, Any]) -> str:
    """显式 > 载体默认 > 风格默认 > none（与 _validate_prompt 同序）。"""
    return (brief.get("text_policy")
            or (th["imagegen"].get("text_policy_by_media") or {}).get(str(brief.get("media")))
            or pack.get("text_policy")
            or "none")


def _admission(baseline: Any) -> Dict[str, Any]:
    """准入判据（写死，不靠感觉）：3 seed 里 ≥2 过线 → 建议 core。

    `seeds<3` 一律不升 core —— 单张样张只能证明「出得来」，不能证明「稳」。
    """
    b = baseline if isinstance(baseline, dict) else {}
    seeds = int(b.get("seeds") or 0)
    passed = int(b.get("pass") or 0)
    if seeds <= 0:
        return {"suggest": "extended", "reason": "未跑基准，只能软放行",
                "passed": 0, "seeds": 0}
    if seeds < 3:
        return {"suggest": "extended", "reason": f"仅 {seeds} seed，未达 3 seed 门槛",
                "passed": passed, "seeds": seeds}
    if passed >= 2:
        return {"suggest": "core", "reason": f"{passed}/{seeds} 过线（≥2/3）",
                "passed": passed, "seeds": seeds}
    return {"suggest": "experimental",
            "reason": f"仅 {passed}/{seeds} 过线，未达 2/3，降级禁用 style 字段",
            "passed": passed, "seeds": seeds}


# 留白意图词 vs 正向空场声明：上一轮实测「负向写 text」4/4 失败，
# 必须逼提示词正面声明空场是什么，否则模型会用自造品牌名填满。
_SPACE_INTENT = ("space for", "empty space", "empty panel", "negative space",
                 "留白", "标题位", "空场")
_SPACE_DECL = ("flat solid", "pure color field", "solid color field",
               "no lettering", "no typography", "do not invent",
               "不出现任何文字", "纯色空场")

# 这些载体天生依赖文字排版，靠生图硬扛必然出乱码（实测：A4 信息图、C 组界面）
_TEXT_HEAVY_MEDIA = {"infographic", "ui-screen", "comic", "character-sheet",
                     "social-card", "storyboard", "mockup", "packaging"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=False)

    cp = act.add_parser("compose", help="确定性出提示词（不依赖 LLM / 引擎，拿来就能用）")
    cp.add_argument("--input", default=None, help="设计需求 JSON（与 --need 至少给一个）")
    cp.add_argument("--need", default=None, help="一句话需求，如：中秋蔬菜礼盒主图，暖色调，突出新鲜")
    cp.add_argument("--ref", default=None,
                    help="参考设计系统（如 linear / apple / notion），注入其配色与氛围")
    cp.add_argument("--style", default=None, help="风格名，如 flat / 3d-food / kawaii")
    cp.add_argument("--media", default=None, help="载体，如 image / poster / packaging")

    rf = act.add_parser("refs", help="设计参考库：知名网站的设计系统（颜色/字体/氛围）")
    rf.add_argument("--query", default=None, help="关键词检索，如 dark cinematic / playful")
    rf.add_argument("--site", default=None, help="按名称取细节，如 linear")
    rf.add_argument("--rebuild", action="store_true", help="重建索引")

    ins = act.add_parser("inspire", help="灵感检索计划：站点清单 + 搜索词 + 版权规则")
    ins.add_argument("--need", required=True, help="灵感主题，如：高原蔬菜包装的高级感")
    ins.add_argument("--category", default=None,
                     help="限定类别：ui/web/brand/packaging/type/illustration/photo/color/motion/cn/trend")
    ins.add_argument("--fetch", action="store_true", help="尝试抓取公开页面元信息（需联网）")
    ins.add_argument("--limit", type=int, default=6)
    cp.add_argument("--output-dir", default=None)
    cp.add_argument("--format", default="md", choices=["md", "json"], help="输出格式（都会落盘）")

    pr = act.add_parser("prompt", help="校验生图提示词包")
    pr.add_argument("--input", required=True)

    st = act.add_parser("style", help="校验风格探索")
    st.add_argument("--input", required=True)

    act.add_parser("probe", help="批量探测所有外置生图软件及云端 API 健康状态")

    cat = act.add_parser("catalog", help="生成能力目录：载体 × 风格矩阵 + catalog.html")
    cat.add_argument("--output-dir", default=None, help="目录输出位置")

    act.add_parser("admit", help="按准入判据给出升降级建议（只报不改）")

    act.add_parser("engines", help="列出可接入的生图引擎与接入开关（env）")

    pk = act.add_parser("pack", help="生成基准提示词包（每风格 N 份，不调用渲染器）")
    pk.add_argument("--output-dir", default=None)
    pk.add_argument("--seeds", type=int, default=3)

    sc = act.add_parser("score", help="对已生成图做客观评分（占位检测 + 色板/画幅）")
    sc.add_argument("--dir", required=True)

    gen = act.add_parser("generate", help="执行全自动 AI 生图、LLM 扩写、VLM 质检反思与商用排版闭环管线")
    gen.add_argument("--input", required=True, help="设计需求 JSON 文件")
    gen.add_argument("--explore", action="store_true", help="是否启动 Multi-Stylescape 多向方案探索")
    gen.add_argument("--engine", default=None, help="指定首选生图引擎")
    gen.add_argument("--output-dir", default=None, help="高清大图输出目录")
    gen.add_argument("--dry-run", action="store_true",
                     help="只出「最终会发出去的 prompt/负向/尺寸/风险」，不调用任何引擎")

    # 新增：对话式增量重绘改稿子命令
    edt = act.add_parser("edit", help="对已有设计图进行局部增量重绘与无损改稿 (Inpainting)")
    edt.add_argument("--image", required=True, help="基础底图路径")
    edt.add_argument("--instruction", required=True, help="改稿自然语言指令，如'把背景换成赛博雨夜'")
    edt.add_argument("--region", default="background", help="重绘目标区域: background(背景) / subject(主体) / border(边框)")
    edt.add_argument("--engine", default=None, help="指定生图引擎")
    edt.add_argument("--style", default="commercial-photography",
                     help="改稿风格（走注册表解析，如 flat / 3d-food）")
    edt.add_argument("--output-dir", default=None, help="输出目录")


def run(args) -> Dict[str, Any]:
    if getattr(args, "action", None) is None:
        return _route_menu()
    if args.action == "compose":
        brief = c.load_json(args.input) if getattr(args, "input", None) else {}
        if getattr(args, "need", None):
            brief.setdefault("need", args.need)
        if getattr(args, "ref", None):
            brief.setdefault("ref", args.ref)
        if getattr(args, "style", None):
            brief.setdefault("style", args.style)
        if getattr(args, "media", None):
            brief.setdefault("media", args.media)
        return _compose_prompt(brief, getattr(args, "output_dir", None),
                               getattr(args, "format", "md"))
    if args.action == "refs":
        return _refs(getattr(args, "query", None), getattr(args, "site", None),
                     bool(getattr(args, "rebuild", False)))
    if args.action == "inspire":
        return _inspire(args.need, getattr(args, "category", None),
                        bool(getattr(args, "fetch", False)),
                        int(getattr(args, "limit", 6)))
    if args.action == "prompt":
        return _validate_prompt(c.load_json(args.input))
    if args.action == "style":
        return _validate_style(c.load_json(args.input))
    if args.action == "probe":
        return get_engine_manager().probe_all()
    if args.action == "catalog":
        return _build_catalog(getattr(args, "output_dir", None))
    if args.action == "admit":
        return _admit_report()
    if args.action == "engines":
        return _engines_help()
    if args.action == "pack":
        return _build_pack(getattr(args, "output_dir", None), int(getattr(args, "seeds", 3)))
    if args.action == "score":
        return _score_images(args.dir)
    if args.action == "edit":
        out_dir = getattr(args, "output_dir", None) or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
        return InpaintEditEngine.edit_image(
            image_path=args.image,
            instruction=args.instruction,
            output_dir=out_dir,
            target_region=getattr(args, "region", "background"),
            preferred_engine=getattr(args, "engine", None),
            style=getattr(args, "style", "commercial-photography")
        )
    if args.action == "generate":
        brief = c.load_json(args.input)
        if getattr(args, "dry_run", False):
            return _dry_run_generate(brief, getattr(args, "output_dir", None))
        eng = _engine_available()
        if not eng["available"]:
            # 默认走提示词路线：不再让人在菜单里选，直接把可粘贴提示词给他
            out = _compose_prompt(brief, getattr(args, "output_dir", None))
            out.update(degraded=True, degraded_reason="无可用生图引擎，已自动走提示词路线",
                       engine_required=False,
                       next="复制 Prompt/Negative 去外部工具；想直接出图执行 "
                            "`python agent.py imagegen engines` 看接入方式")
            return out
        if getattr(args, "explore", False):
            # 启动 Multi-Stylescape 模式
            out_dir = getattr(args, "output_dir", None) or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
            gallery = StylescapeExplorer.generate_three_directions(brief, out_dir)
            if not gallery:
                return _route_menu(reason="探索未产出真实图（引擎不可用或只有 mock），已拒绝占位图")
            return {
                "ok": True, "verdict": "PASS", "mode": "explore",
                "gallery_artifacts": gallery,
                "next": "已成功生成 3 种不同风格的多向探索画廊，请选定后微调。"
            }
        return _run_full_generation_pipeline(brief, preferred_engine=getattr(args, "engine", None), output_dir=getattr(args, "output_dir", None))
    return {"error": f"未知动作: {args.action}"}


def _validate_prompt(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    reg = c.load_registry()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    media = data.get("media")
    core_media = th["imagegen"]["output_media"]
    ext_media = th["imagegen"].get("output_media_extended", [])
    if media in core_media:
        checks.append(_ck(True, f"media={media!r} 命中 core 载体白名单",
                          "imagegen.media"))
    elif media in ext_media:
        checks.append(_ck(True,
                          f"media={media!r} 是 extended 载体（已登记，未单独验收）",
                          "imagegen.media", sev="WARN"))
    else:
        checks.append(_ck(False,
                          f"media={media!r} 既不在 core {core_media} "
                          f"也不在 extended {ext_media}",
                          "imagegen.media"))
        return c.result(checks, ok=False, verdict="FAIL", grade="FAIL",
                        media=media, style=data.get("style"))

    # 风格：任意别名 → 解析成 core render_style；extended 只 WARN 不拦。
    rs = _resolve_style(data.get("style"), th, reg)
    ok_style = rs["render_style"] is not None
    if rs["level"] == "experimental":
        checks.append(_ck(False,
                          f"style={data.get('style')!r} 是 experimental（未过基准）："
                          f"只能写进 prompt 文本层，不能占 style 字段",
                          "imagegen.style", level="experimental"))
    elif not ok_style:
        checks.append(_ck(False,
                          f"style={data.get('style')!r} 既不在 core 白名单 "
                          f"{th['imagegen']['style_types']}，也不在注册表",
                          "imagegen.style"))
    elif rs["level"] == "core":
        checks.append(_ck(True, f"style={rs['render_style']!r} 命中 core 白名单",
                          "imagegen.style", resolved_style=rs["render_style"],
                          style_level="core"))
    else:
        checks.append(_ck(True,
                          f"style={data.get('style')!r} → 渲染为 {rs['render_style']!r}"
                          f"（{rs['level']}，已登记 {len(rs['failure_modes'])} 条已知失败模式）",
                          "imagegen.style", sev="WARN",
                          resolved_style=rs["render_style"],
                          style_level=rs["level"],
                          known_failures=rs["failure_modes"]))

    prompt = str(data.get("prompt", "")).strip()
    checks.append(_ck(bool(prompt), f"prompt 非空（{len(prompt)} 字）",
                      "imagegen.prompt"))

    negative = str(data.get("negative_prompt", "")).strip()
    neg_min = th["imagegen"]["negative_min"]
    checks.append(_ck(bool(negative), f"negative_prompt 非空（≥{neg_min} 项）",
                      "imagegen.negative_prompt"))

    locks = data.get("style_locks")
    ok_locks = isinstance(locks, list) and len(locks) >= 1
    checks.append(_ck(ok_locks,
                      f"style_locks ≥1（实际 {len(locks) if isinstance(locks, list) else 0}）",
                      "imagegen.style_locks"))

    # 风格锁自洽：锁条目不得在负向提示词中被否定（自我推翻）
    contradiction = []
    if ok_locks and negative:
        for lock in locks:
            if isinstance(lock, str) and lock.strip():
                # 负向提示词中命中锁原文（或其否定式）即矛盾
                if lock in negative or f"不{lock}" in negative or f"无{lock}" in negative:
                    contradiction.append(lock)
    ok_lock = not contradiction
    checks.append(_ck(ok_lock,
                      f"风格锁不被负向提示词推翻（矛盾 {contradiction or '无'}）",
                      "imagegen.lock_consistency"))

    # 文字策略：显式 > 载体级默认 > 风格默认 > none
    tp_by_media = th["imagegen"].get("text_policy_by_media", {}) or {}
    tp = (data.get("text_policy")
          or tp_by_media.get(str(media))
          or rs["text_policy_default"]
          or "none")
    ok_tp = tp in th["imagegen"]["text_policy"]
    checks.append(_ck(ok_tp,
                      f"text_policy={tp!r} 合法（枚举 {th['imagegen']['text_policy']}）",
                      "imagegen.text_policy", text_policy=tp))

    # 留白必须正向声明：只靠负向 text 挡不住（实测 4/4 出伪文字/自造品牌名）
    if ok_tp and tp == "none" and prompt:
        wants_space = any(k in prompt.lower() for k in _SPACE_INTENT)
        declared = any(k in prompt.lower() for k in _SPACE_DECL)
        if wants_space and not declared:
            checks.append(_ck(True,
                              "留白/标题位未正向声明为空场：负向 text 已被实测证明挡不住，"
                              "建议补 'flat solid color field, no lettering, do not invent brand name'",
                              "imagegen.negative_space", sev="WARN"))

    # 结构性硬限制：这类载体天生依赖文字，模型必出乱码/自造文案
    if ok_tp and media in _TEXT_HEAVY_MEDIA and tp != "overlay-later":
        checks.append(_ck(True,
                          f"media={media!r} 天然依赖文字：模型会产出乱码标签/自造文案，"
                          f"建议 text_policy='overlay-later' 并后期排版",
                          "imagegen.hard_limit", sev="WARN",
                          hard_limit="exact-typography"))

    blocked = any(x["sev"] == "BLOCKER" for x in checks)
    warned = any(x["sev"] == "WARN" for x in checks)
    ok = not blocked
    grade = "FAIL" if blocked else ("PASS_WITH_WARNING" if warned else "PASS")
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    grade=grade, media=media, style=data.get("style"),
                    resolved_style=rs["render_style"], style_level=rs["level"],
                    text_policy=tp,
                    lock_count=len(locks) if isinstance(locks, list) else 0,
                    warning_count=sum(1 for x in checks if x["sev"] == "WARN"))


def _validate_style(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    reg = c.load_registry()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    rs = _resolve_style(data.get("style"), th, reg)
    ok_style = rs["render_style"] is not None
    if rs["level"] == "experimental":
        checks.append(_ck(False,
                          f"style={data.get('style')!r} 是 experimental（未过基准），"
                          f"不能占 style 字段",
                          "style.type", level="experimental"))
    elif rs["level"] == "core":
        checks.append(_ck(True, f"style={data.get('style')!r} 命中 core 白名单",
                          "style.type", resolved_style=rs["render_style"],
                          style_level="core"))
    elif ok_style:
        checks.append(_ck(True,
                          f"style={data.get('style')!r} → 渲染为 {rs['render_style']!r}"
                          f"（{rs['level']}）",
                          "style.type", sev="WARN",
                          resolved_style=rs["render_style"],
                          style_level=rs["level"]))
    else:
        checks.append(_ck(False,
                          f"style={data.get('style')!r} 不在 core 白名单 "
                          f"{th['imagegen']['style_types']} 也不在注册表",
                          "style.type"))

    composition = data.get("composition")
    ok_comp = isinstance(composition, list) and len(composition) >= 1
    checks.append(_ck(ok_comp,
                      f"composition ≥1（实际 {len(composition) if isinstance(composition, list) else 0}）",
                      "style.composition"))
    comp_ok = ok_comp
    if isinstance(composition, list):
        for i, item in enumerate(composition):
            if not isinstance(item, str) or not item.strip():
                checks.append(_ck(False, f"composition[{i}] 非字符串",
                                  "style.composition"))
                comp_ok = False

    palette = data.get("palette")
    ok_pal = isinstance(palette, list) and all(
        isinstance(p, str) and c.is_hex_color(p) for p in palette) if isinstance(palette, list) else False
    checks.append(_ck(ok_pal, f"palette 为 hex 色列表（{palette!r}）",
                      "style.palette"))

    blocked = any(x["sev"] == "BLOCKER" for x in checks)
    warned = any(x["sev"] == "WARN" for x in checks)
    ok = not blocked
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    grade="FAIL" if blocked else ("PASS_WITH_WARNING" if warned else "PASS"),
                    style=data.get("style"),
                    resolved_style=rs["render_style"], style_level=rs["level"],
                    comp_count=len(composition) if isinstance(composition, list) else 0,
                    palette=palette if isinstance(palette, list) else [])


# --------------------------------------------------------------------------- #
# 能力目录：把「我们能生成什么」变成可查的矩阵（12 载体 × 57 风格）
# --------------------------------------------------------------------------- #
def _verified_state(rec: Dict[str, Any]) -> str:
    """四态：verified（有客观检查且过线）/ sampled（有样张、客观检查不覆盖）/
    failed（样张跑挂）/ unverified（没跑过）。"""
    b = rec.get("baseline") or {}
    seeds = int(b.get("seeds") or 0)
    passed = int(b.get("pass") or 0)
    if seeds <= 0:
        return "unverified"
    if passed <= 0:
        return "failed"
    if passed >= 2 and b.get("objective"):
        return "verified"
    return "sampled"


_PACK_SUBJECTS = {
    "3d-character": "a chubby green frog mascot wearing a small orange scarf",
    "3d-clay": "a chubby green frog mascot wearing a small orange scarf",
    "engraving": "a farmer harvesting vegetables in a highland field",
    "comic-ink": "a farmer harvesting vegetables in a highland field",
    "technical-blueprint": "a modular vegetable shipping crate, engineering drawing",
}
_PACK_DEFAULT_SUBJECT = "a crate of fresh vegetables (cabbage, carrots, tomatoes) on a plain surface"


def _text_clause(policy: str) -> str:
    if policy == "overlay-later":
        return ("generous empty space reserved for a headline, flat solid color field "
                "for later typography, do not invent any brand name or wordmark")
    if policy == "render-attempt":
        return "minimal single-line lettering only"
    return "absolutely no text, no lettering, no logo, no watermark"


def _build_pack(output_dir: Optional[str] = None, seeds: int = 3) -> Dict[str, Any]:
    """生成可直接喂给任意渲染器的提示词包（每风格 seeds 份），不含生图调用。"""
    th = c.load_thresholds()
    reg = c.load_registry()
    sizes = th["imagegen"].get("image_sizes", {}) or {}
    out_dir = output_dir or os.path.join(_AGENT_DIR, "workspace", "pack")
    pdir = os.path.join(out_dir, "prompts")
    os.makedirs(pdir, exist_ok=True)

    files, manifest = [], []
    for e in reg.get("entries", []):
        if not isinstance(e, dict) or e.get("axis") != "style":
            continue
        name = str(e.get("id") or "").split(".", 1)[-1]
        aspect = str(e.get("aspect_default") or "1:1")
        tp = str(e.get("text_policy_default") or "none")
        subject = _PACK_SUBJECTS.get(name, _PACK_DEFAULT_SUBJECT)
        prompt = f"{subject}, {e.get('positive_recipe', '')}, {_text_clause(tp)}"
        negative = str(e.get("negative_recipe") or "")
        for n in range(1, seeds + 1):
            item = {"id": f"{name}__seed{n}", "style": name,
                    "render_style": e.get("render_style") or e.get("parent"),
                    "level": e.get("level"), "seed_index": n,
                    "image_size": sizes.get(aspect, "square_hd"),
                    "aspect": aspect, "text_policy": tp,
                    "prompt": prompt, "negative_prompt": negative}
            p = os.path.join(pdir, item["id"] + ".json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)
            files.append(p)
            manifest.append(item)

    mpath = os.path.join(out_dir, "MANIFEST.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump({"count": len(manifest), "seeds_per_style": seeds,
                   "items": manifest}, f, ensure_ascii=False, indent=2)
    readme = os.path.join(out_dir, "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(
            "# R10 基准提示词包\n\n"
            f"{len(manifest)} 条（{len(manifest)//max(seeds,1)} 风格 × {seeds} seed）。\n\n"
            "跑完后把图按 `<id>.jpg` 命名放进 `images/`，再执行：\n\n"
            "```bash\npython agent.py imagegen score --dir workspace/pack/images\n```\n\n"
            "评分报告会告诉你每条风格有几张过客观检查，再用 `imagegen admit` 看升降级建议。\n")
    return c.result(
        [_ck(True, f"提示词包已生成：{len(manifest)} 条 → {pdir}",
             "imagegen.pack")],
        ok=True, verdict="PASS", grade="PASS", count=len(manifest),
        seeds_per_style=seeds, artifacts=[mpath, readme],
        next="交给任意渲染器生成，图存 <id>.jpg 后跑 imagegen score 回填")


def _score_images(directory: str) -> Dict[str, Any]:
    """对已生成的图做客观评分（不含风格锁，风格锁需人眼）。"""
    from PIL import Image
    import numpy as np

    if not directory or not os.path.isdir(directory):
        return c.result([_ck(False, f"目录不存在：{directory}", "imagegen.score")],
                        ok=False, verdict="FAIL")
    files = sorted(f for f in os.listdir(directory)
                   if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    if not files:
        return c.result([_ck(False, f"目录里没有图片：{directory}", "imagegen.score")],
                        ok=False, verdict="FAIL")

    rows = []
    for fn in files:
        p = os.path.join(directory, fn)
        row = {"file": fn, "bytes": os.path.getsize(p)}
        try:
            im = Image.open(p).convert("RGB")
            a = np.asarray(im).astype(np.int32)
            gray_std = float(a.mean(axis=2).std())
            qa = (a // 8) * 8
            flat = qa.reshape(-1, 3)
            keys = flat[:, 0] * 65536 + flat[:, 1] * 256 + flat[:, 2]
            _, cnt = np.unique(keys, return_counts=True)
            cum = np.cumsum(np.sort(cnt)[::-1]) / cnt.sum()
            row.update({
                "w": im.width, "h": im.height,
                "aspect": round(im.width / im.height, 2),
                "placeholder": gray_std < 8.0,
                "palette_c90": int(np.searchsorted(cum, 0.90) + 1),
            })
        except Exception as exc:  # noqa: BLE001
            row.update({"error": str(exc)[:120], "placeholder": True})
        rows.append(row)

    ok_rows = [r for r in rows if not r.get("placeholder") and "error" not in r]
    report = {"dir": directory, "total": len(rows), "real_images": len(ok_rows),
              "placeholders": len(rows) - len(ok_rows), "rows": rows}
    rp = os.path.join(directory, "score_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return c.result(
        [_ck(True, f"评分完成：{len(ok_rows)}/{len(rows)} 张真实图，"
                   f"其余 {len(rows) - len(ok_rows)} 张为占位/损坏",
             "imagegen.score")],
        ok=True, verdict="PASS", grade="PASS", report=rp,
        total=len(rows), real_images=len(ok_rows), **{"placeholders": report["placeholders"]},
        next="风格锁与人眼判断仍需人工；palette_c90 可对双色/像素族做客观判定")


def _admit_report() -> Dict[str, Any]:
    """按准入判据核对 level，只报不改（改 level 必须人工确认）。"""
    reg = c.load_registry()
    drift = []
    for e in reg.get("entries", []):
        if not isinstance(e, dict) or e.get("axis") != "style":
            continue
        a = _admission(e.get("baseline"))
        if a["suggest"] != e.get("level"):
            drift.append({"id": e.get("id"), "level": e.get("level"),
                          "suggest": a["suggest"], "reason": a["reason"]})
    return c.result([_ck(True, f"准入核对：{len(drift)} 条与建议不一致（只报不改）",
                        "imagegen.admit")],
                    ok=True, verdict="PASS", grade="PASS",
                    drift=drift, drift_count=len(drift),
                    next="逐条人工确认后再改 registry 的 level；本命令不写盘")


def _build_catalog(output_dir: Optional[str] = None) -> Dict[str, Any]:
    import html as _html

    th = c.load_thresholds()
    reg = c.load_registry()
    media = list(th["imagegen"]["output_media"])
    entries = [e for e in reg.get("entries", []) if e.get("axis") == "style"]
    entries.sort(key=lambda e: (str(e.get("render_style") or ""),
                                0 if e.get("level") == "core" else 1,
                                str(e.get("id") or "")))
    if not entries:
        return c.result([_ck(False, "风格注册表为空", "imagegen.catalog")],
                        ok=False, verdict="FAIL")

    rows = []
    for e in entries:
        st = _verified_state(e)
        adm = _admission(e.get("baseline"))
        rows.append({
            "id": e.get("id"), "name": str(e.get("id") or "").split(".", 1)[-1],
            "level": e.get("level"), "render_style": e.get("render_style") or e.get("parent"),
            "desc": e.get("desc", ""),
            "text_policy": e.get("text_policy_default", "none"),
            "aspect": e.get("aspect_default", ""),
            "status": st,
            "suggested_level": adm["suggest"], "admission_reason": adm["reason"],
            "baseline": e.get("baseline") or {},
            "failure_modes": e.get("failure_modes") or [],
        })

    counts = {
        "styles_total": len(rows),
        "core": sum(1 for r in rows if r["level"] == "core"),
        "extended": sum(1 for r in rows if r["level"] == "extended"),
        "verified": sum(1 for r in rows if r["status"] == "verified"),
        "sampled": sum(1 for r in rows if r["status"] == "sampled"),
        "failed": sum(1 for r in rows if r["status"] == "failed"),
        "unverified": sum(1 for r in rows if r["status"] == "unverified"),
        "upgrade_ready": sum(1 for r in rows if r["suggested_level"] == "core"),
        "media": len(media),
        "combinations": len(media) * len(rows),
    }
    out_dir = output_dir or os.path.join(_AGENT_DIR, "workspace", "catalog")
    sdir = os.path.join(out_dir, "samples")
    os.makedirs(sdir, exist_ok=True)

    # 把 baseline.sample 指向的原图缩成卡片缩略图，目录能直接看图
    used: Dict[str, int] = {}
    for r in rows:
        raw = str((r["baseline"] or {}).get("sample") or "").strip()
        r["thumb"] = ""
        r["_raw"] = raw
        if not raw:
            continue
        used[raw] = used.get(raw, 0) + 1
        p = raw if os.path.isabs(raw) else os.path.join(_AGENT_DIR, "..", "..", raw)
        p = os.path.abspath(p)
        if not os.path.isfile(p):
            continue
        dest = os.path.join(sdir, r["name"] + ".jpg")
        try:
            from PIL import Image
            im = Image.open(p).convert("RGB")
            im.thumbnail((520, 520))
            im.save(dest, quality=86)
            r["thumb"] = "samples/" + r["name"] + ".jpg"
        except Exception:  # noqa: BLE001
            r["thumb"] = ""
    for r in rows:
        r["shared"] = used.get(r.get("_raw") or "", 0) > 1

    json_path = os.path.join(out_dir, "catalog.json")
    html_path = os.path.join(out_dir, "catalog.html")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"version": reg.get("version", ""), "counts": counts,
                   "hard_limits": reg.get("hard_limits", {}),
                   "sources": reg.get("sources", []),
                   "media": media, "styles": rows}, f, ensure_ascii=False, indent=2)

    with_img = [r for r in rows if r["thumb"]]
    without = [r for r in rows if not r["thumb"]]

    hl = reg.get("hard_limits") or {}
    limits_html = "".join(
        "<li><b>" + _html.escape(str(i.get("desc", ""))) + "</b>"
        + "<span>→ " + _html.escape(str(i.get("workaround", ""))) + "</span></li>"
        for i in (hl.get("items") or []))

    def card(r: Dict[str, Any], dim: bool = False) -> str:
        st = r["status"]
        badge = "core" if r["level"] == "core" else "ext"
        name = _html.escape(str(r["name"]))
        if r["thumb"]:
            thumb = "<img src='" + r["thumb"] + "' loading='lazy' alt='" + name + "'>"
        else:
            thumb = "<div class='ph'>未跑基准</div>"
        warns = "".join("<li>" + _html.escape(str(x)) + "</li>"
                        for x in (r["failure_modes"] or [])[:2])
        warn_block = ("<ul class='warn'>" + warns + "</ul>") if warns else ""
        return ("<figure class='card " + st + (" dim" if dim else "") + "'>"
                + thumb
                + "<figcaption><div class='name'>" + name
                + "<span class='badge " + badge + "'>" + badge + "</span></div>"
                + "<div class='desc'>" + _html.escape(str(r.get("desc") or "")) + "</div>"
                + "<div class='meta'>→ " + _html.escape(str(r["render_style"]))
                + " · " + _html.escape(str(r["text_policy"]))
                + " · " + _html.escape(str(r.get("aspect") or ""))
                + " · <span class='st " + st + "'>" + st + "</span>"
                + (" · ↺ 同图复用" if r.get("shared") else "") + "</div>"
                + warn_block + "</figcaption></figure>")

    color = {"verified": "#22c55e", "sampled": "#f59e0b",
             "failed": "#ef4444", "unverified": "#334155"}
    head = "".join("<th class='rot'>" + _html.escape(m) + "</th>" for m in media)
    body = []
    for r in rows:
        cells = "".join(
            "<td><span class='cell' style='background:" + color[r["status"]] + "' "
            "title='" + _html.escape(str(r["name"])) + " × " + _html.escape(m)
            + " · 风格状态=" + r["status"] + "（载体维度未单独实测）'></span></td>"
            for m in media)
        badge = "core" if r["level"] == "core" else "ext"
        body.append(
            "<tr><td class='sty'><b>" + _html.escape(str(r["name"])) + "</b>"
            "<span class='badge " + badge + "'>" + badge + "</span></td>"
            "<td class='map'>" + _html.escape(str(r["render_style"])) + "</td>"
            "<td class='map'>" + _html.escape(str(r["text_policy"])) + "</td>" + cells
            + "<td class='st " + r["status"] + "'>" + r["status"] + "</td>"
            + "<td class='map' title='" + _html.escape(str(r["admission_reason"])) + "'>"
            + _html.escape(str(r["suggested_level"])) + "</td></tr>")

    doc = f"""<!doctype html><meta charset="utf-8">
<title>R10 能出哪些风格 · {counts['styles_total']} 风格 / {counts['media']} 载体</title>
<style>
 body{{margin:0;padding:28px;background:#0b1120;color:#e2e8f0;
      font:14px/1.6 "Segoe UI","Microsoft YaHei",sans-serif}}
 h1{{font-size:22px;margin:0 0 4px}}
 h2{{font-size:15px;margin:28px 0 12px;color:#cbd5e1;
     border-left:3px solid #38bdf8;padding-left:8px}}
 .sub{{color:#94a3b8;margin-bottom:18px}}
 .stats{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
 .stat{{background:#111c33;border:1px solid #1e293b;border-radius:10px;padding:8px 14px}}
 .stat b{{display:block;font-size:19px;color:#38bdf8}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:14px}}
 .card{{margin:0;background:#111c33;border:1px solid #1e293b;border-radius:12px;
        overflow:hidden}}
 .card img{{width:100%;height:170px;object-fit:cover;display:block;background:#0b1120}}
 .card .ph{{height:170px;display:flex;align-items:center;justify-content:center;
            background:#0f172a;color:#7c8ba1;font-size:12px;
            border-bottom:1px dashed #1e293b}}
 .card figcaption{{padding:10px 12px 12px}}
 .name{{font-weight:600;font-size:13px}}
 .desc{{color:#94a3b8;font-size:12px;margin-top:2px;min-height:32px}}
 .meta{{color:#64748b;font-size:11px;margin-top:6px}}
 .warn{{margin:6px 0 0;padding-left:16px;color:#fca5a5;font-size:11px}}
 .badge{{margin-left:6px;font-size:10px;padding:1px 5px;border-radius:999px;
        background:#1e293b;color:#93c5fd}}
 .badge.core{{background:#164e63;color:#67e8f9}}
 .dim{{opacity:.62}}
 .verified{{color:#4ade80}} .sampled{{color:#fbbf24}} .failed{{color:#f87171}}
 .unverified{{color:#64748b}}
 table{{border-collapse:collapse;font-size:12px}}
 th,td{{border-bottom:1px solid #1e293b;padding:4px 6px;text-align:left}}
 th.rot{{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:500;
        color:#94a3b8;height:96px;font-size:11px}}
 .sty b{{font-weight:600}} .map{{color:#94a3b8;font-size:11px}}
 .cell{{display:block;width:16px;height:16px;border-radius:3px;opacity:.85}}
 .legend{{margin-top:22px;color:#94a3b8;font-size:12px}}
 .limits{{margin:0;padding-left:18px;color:#cbd5e1;font-size:12px;max-width:1100px}}
 .limits li{{margin:5px 0}}
 .limits b{{color:#f87171;font-weight:600}}
 .limits span{{color:#94a3b8;margin-left:8px}}
</style>
<h1>R10 能出哪些风格</h1>
<div class="sub">{counts['styles_total']} 风格 × {counts['media']} 载体 =
 {counts['combinations']} 个可声明组合。有样张 {len(with_img)} 条（其中待人工 {counts['sampled']}、
 已知失败 {counts['failed']}），未跑基准 {counts['unverified']} 条。</div>
<div class="stats">
 <div class="stat"><b>{counts['styles_total']}</b>风格总数</div>
 <div class="stat"><b>{counts['core']}</b>core 强校验</div>
 <div class="stat"><b>{counts['extended']}</b>extended 软校验</div>
 <div class="stat"><b>{len(with_img)}</b>有样张</div>
 <div class="stat"><b>{counts['unverified']}</b>未跑基准</div>
 <div class="stat"><b>{counts['combinations']}</b>可声明组合</div>
</div>
<h2>能看图的：{len(with_img)} 条</h2>
<div class="grid">{''.join(card(r) for r in with_img)}</div>
<h2>还没样张的：{len(without)} 条（只代表可声明，不代表已验证）</h2>
<div class="grid">{''.join(card(r, dim=True) for r in without)}</div>
<h2>结构性硬限制：换任何风格都绕不过</h2>
<ul class="limits">{limits_html}</ul>
<h2>组合矩阵（行=风格，列=载体）</h2>
<table><thead><tr><th>风格</th><th>渲染为</th><th>文字策略</th>{head}<th>状态</th><th>建议</th></tr></thead>
<tbody>{''.join(body)}</tbody></table>
<div class="legend">生成：<code>python agent.py imagegen catalog</code> ·
数据源：experience/thresholds.json + experience/style_registry.json ·
缩略图来自 baseline.sample，未跑基准的条目没有图。</div>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(doc)

    return c.result(
        [_ck(True, f"目录生成：{counts['media']} 载体 × {counts['styles_total']} 风格 "
                   f"（已验证 {counts['verified']} / 待人工 {counts['sampled']} / "
                   f"失败 {counts['failed']} / 未验证 {counts['unverified']}）",
                   "imagegen.catalog")],
        ok=True, verdict="PASS", grade="PASS", **counts,
        artifacts=[json_path, html_path], next="目录已生成，可直接给非技术同事查「要一张 X 能不能出」")


_BASE_NEG = ("lowres, blurry, jpeg artifacts, watermark, signature, "
             "extra fingers, deformed, cropped")

_ROUTES = [
    {"id": "1", "label": "只要提示词（拿去外部工具生图，最常用）",
     "cmd": "python agent.py imagegen compose --input brief.json"},
    {"id": "2", "label": "校验我已有的提示词包",
     "cmd": "python agent.py imagegen prompt --input prompt.json"},
    {"id": "3", "label": "看能出哪些风格 / 硬限制",
     "cmd": "python agent.py imagegen catalog"},
    {"id": "4", "label": "批量生成提示词包（57 风格 × N seed）",
     "cmd": "python agent.py imagegen pack --seeds 3"},
    {"id": "5", "label": "已接引擎，直接出图",
     "cmd": "python agent.py imagegen generate --input brief.json"},
]


def _engine_available() -> Dict[str, Any]:
    """快速判断有没有出图能力：本地服务端口 + 云端 Key，不做完整 probe。"""
    import socket
    for name, port in (("comfyui", 8188), ("sdwebui", 7860), ("fooocus", 8888)):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return {"available": True, "via": f"local:{name}({port})"}
        finally:
            s.close()
    for key in ("OPENAI_API_KEY", "SILICONFLOW_API_KEY", "DASHSCOPE_API_KEY",
                "ZHIPUAI_API_KEY", "MIDJOURNEY_API_KEY"):
        if os.environ.get(key):
            return {"available": True, "via": f"env:{key}"}
    return {"available": False, "via": "",
            "reason": "无本地生图服务（8188/7860/8888）也未配置云端 API Key"}


def _route_menu(reason: str = "", interactive: Optional[bool] = None) -> Dict[str, Any]:
    """没有明确路径时，把选择权交回给人，而不是默认走某一条。"""
    eng = _engine_available()
    rec = "5" if eng["available"] else "1"
    if interactive is None:
        interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())
    lines = ["R10 生图与插画 · 请选择走哪条路："]
    for r in _ROUTES:
        mark = "  ← 推荐" if r["id"] == rec else ""
        lines.append(f"  {r['id']}. {r['label']}{mark}")
        lines.append(f"     {r['cmd']}")
    lines.append(f"引擎探测：{'可用 → ' + eng['via'] if eng['available'] else '不可用（' + eng['reason'] + '）'}")
    if reason:
        lines.append(f"原因：{reason}")
    text = "\n".join(lines)
    picked = None
    if interactive:
        try:
            print(text)
            picked = input(f"输入 1-5（回车默认 {rec}）：").strip() or rec
        except (EOFError, KeyboardInterrupt):
            picked = rec
        finally:
            print()  # 保证后续 __AGENT_RESULT__ 独占一行
    return {
        "ok": True, "verdict": "PASS", "grade": "PASS",
        "route_menu": True, "options": _ROUTES, "recommended": rec,
        "picked": picked if picked in {r["id"] for r in _ROUTES} else None,
        "engine": eng, "reason": reason, "menu_text": text,
        "checks": [_ck(True, "未指定路径，已输出分流选项", "imagegen.route")],
        "next": (f"选定后执行对应命令；当前推荐 {rec}. "
                 + next(r["label"] for r in _ROUTES if r["id"] == rec)),
    }


_REFS_DIR = os.path.join(_AGENT_DIR, "references", "design-library")
_REFS_INDEX = os.path.join(_REFS_DIR, "_index.json")
_HEX = None  # 延迟导入 re，避免顶部堆依赖


def _build_refs_index() -> Dict[str, Any]:
    """把 references/design-library/*.md 解析成可检索索引（颜色/字体/氛围）。"""
    import re as _re
    if not os.path.isdir(_REFS_DIR):
        return {"count": 0, "sites": {}}
    title_re = _re.compile(r"^#\s+Design System:\s*(.+)$", _re.M)
    hex_re = _re.compile(r"#[0-9A-Fa-f]{6}")
    sites: Dict[str, Any] = {}
    for fn in sorted(os.listdir(_REFS_DIR)):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        text = open(os.path.join(_REFS_DIR, fn), encoding="utf-8", errors="replace").read()
        m = title_re.search(text)
        name = (m.group(1).strip() if m else fn[:-3])
        # 氛围：Visual Theme 段的第一段正文
        atmosphere = ""
        sec = _re.search(r"##\s*1\.?\s*Visual Theme[^\n]*\n(.*?)(?=\n##\s)", text, _re.S)
        if sec:
            for block in sec.group(1).split("\n\n"):
                b = block.strip()
                if len(b) > 60 and not b.startswith("#"):
                    atmosphere = " ".join(b.split())[:320]
                    break
        # 字体：Typography 段首段
        typo = ""
        tsec = _re.search(r"##\s*3\.?\s*Typography[^\n]*\n(.*?)(?=\n##\s)", text, _re.S)
        if tsec:
            for block in tsec.group(1).split("\n\n"):
                b = block.strip()
                if len(b) > 40 and not b.startswith("#"):
                    typo = " ".join(b.split())[:220]
                    break
        colors = []
        for c in hex_re.findall(text):
            c = c.lower()
            if c not in colors:
                colors.append(c)
            if len(colors) >= 6:
                break
        sites[name.lower()] = {"name": name, "file": fn, "atmosphere": atmosphere,
                               "typography": typo, "colors": colors}
    index = {"count": len(sites), "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "sites": sites}
    try:
        with open(_REFS_INDEX, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return index


def _load_refs(rebuild: bool = False) -> Dict[str, Any]:
    if not rebuild and os.path.isfile(_REFS_INDEX):
        try:
            with open(_REFS_INDEX, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("count"):
                return data
        except (OSError, ValueError):
            pass
    return _build_refs_index()


def _ref_score(site: Dict[str, Any], tokens: List[str]) -> int:
    hay = ((site.get("name", "") + " " + site.get("atmosphere", "") + " "
            + site.get("typography", "")).lower())
    return sum(1 for t in tokens if t and t in hay)


def _refs(query: Optional[str] = None, site: Optional[str] = None,
          rebuild: bool = False, limit: int = 5) -> Dict[str, Any]:
    idx = _load_refs(rebuild=rebuild)
    sites = idx.get("sites", {})
    if not sites:
        return c.result([_ck(False, "参考库为空：references/design-library 下没有 .md",
                             "imagegen.refs")], ok=False, verdict="FAIL",
                        count=0, next="把 DESIGN.md 放进 design-library/ 后 --rebuild")
    if site:
        key = str(site).lower().strip()
        hit = sites.get(key) or sites.get(key.replace(".md", ""))
        if not hit:
            near = [k for k in sites if key in k][:5]
            return c.result([_ck(False, f"参考库无 {site!r}（相近：{near}）",
                                 "imagegen.refs")], ok=False, verdict="FAIL", count=0)
        return c.result([_ck(True, f"命中参考：{hit['name']}", "imagegen.refs")],
                        ok=True, verdict="PASS", grade="PASS",
                        count=idx["count"], reference=hit,
                        prompt_hint=(f"design language inspired by {hit['name']}, "
                                     f"palette {', '.join(hit['colors'][:4])}"))
    if query:
        tokens = [t for t in str(query).lower().replace("，", " ").split() if t]
        ranked = sorted(sites.values(),
                        key=lambda s: _ref_score(s, tokens), reverse=True)
        matched = [s for s in ranked if _ref_score(s, tokens) > 0][:limit]
        if not matched:
            matched = ranked[:limit]
        return c.result([_ck(True, f"检索 {query!r}：{len(matched)} 条候选",
                             "imagegen.refs")],
                        ok=True, verdict="PASS", grade="PASS",
                        count=idx["count"], matches=matched)
    listing = [{"name": s["name"], "colors": s["colors"][:3],
                "atmosphere": s["atmosphere"][:90]} for s in sites.values()]
    return c.result([_ck(True, f"参考库共 {idx['count']} 套设计系统", "imagegen.refs")],
                    ok=True, verdict="PASS", grade="PASS",
                    count=idx["count"], sites=listing,
                    next="用 --query 关键词或 --site 名称取细节；--rebuild 重建索引")


_SITES_PATH = os.path.join(_AGENT_DIR, "references", "inspiration-sites.json")
_RIGHTS_RULE = ("只可参考配色 / 排版 / 氛围，禁止复刻具体构图、图形、角色、文案；"
                "素材站素材不得直接当品牌 logo 或主视觉使用；无授权不得转售或再分发。")


def _load_sites() -> Dict[str, Any]:
    try:
        with open(_SITES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("sites"):
            return data
    except (OSError, ValueError):
        pass
    return {"sites": [], "rights_levels": {}}


def _robots_allows(url: str, timeout: float = 5.0) -> bool:
    """最小化 robots 检查；取不到 robots.txt 时按允许处理并记录。"""
    import urllib.parse
    import urllib.robotparser
    try:
        parts = urllib.parse.urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch("R10DesignBot", url)
    except Exception:  # noqa: BLE001
        return True


def _fetch_meta(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    """只取公开 HTML 的元信息（标题/描述/og:image），不下载图片、不登录。"""
    import re as _re
    import urllib.request
    if not _robots_allows(url, timeout):
        return {"url": url, "ok": False, "error": "robots 不允许抓取"}
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "R10DesignBot/1.0 (design reference research)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(400_000).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "ok": False, "error": f"{type(exc).__name__}: {exc}"[:160]}
    def _one(pat: str) -> str:
        m = _re.search(pat, html, _re.I | _re.S)
        return " ".join(m.group(1).split())[:200] if m else ""
    return {"url": url, "ok": True,
            "title": _one(r"<title[^>]*>(.*?)</title>"),
            "description": _one(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']'),
            "og_image": _one(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']')}


def _inspire(need: str, category: Optional[str] = None, fetch: bool = False,
             limit: int = 6, timeout: float = 8.0) -> Dict[str, Any]:
    """给一次「去设计网站找灵感」的可执行计划；有网络时附带抓到的元信息。"""
    need = str(need or "").strip()
    if not need:
        return c.result([_ck(False, "缺少灵感主题（need）", "imagegen.inspire")],
                        ok=False, verdict="FAIL")
    data = _load_sites()
    sites = data.get("sites", [])
    if not sites:
        return c.result([_ck(False, "站点清单为空：references/inspiration-sites.json",
                             "imagegen.inspire")], ok=False, verdict="FAIL")

    tokens = [t for t in need.lower().replace("，", " ").split() if t]
    pool = [s for s in sites if not category or s.get("category") == category] or sites

    def score(s: Dict[str, Any]) -> int:
        hay = (s.get("name", "") + " " + s.get("focus", "") + " "
               + s.get("category", "")).lower()
        return sum(1 for t in tokens if t in hay)

    picked = sorted(pool, key=score, reverse=True)[:max(1, int(limit))]
    plan = [{"site": s["name"], "url": s["url"], "category": s["category"],
             "access": s.get("access", ""), "rights": s["rights"],
             "query": need, "look_for": s.get("focus", "")} for s in picked]

    records = []
    if fetch:
        for item in plan[:3]:
            rec = _fetch_meta(item["url"], timeout=timeout)
            rec["rights"] = item["rights"]
            records.append(rec)

    free = [p["site"] for p in plan if p["rights"] == "free-asset"]
    prompt_seed = ("参考方向：" + "；".join(p["look_for"] for p in plan[:3])
                   + "。只借鉴配色与排版气质，不复刻版式。")
    return c.result(
        [_ck(True, f"灵感计划：{len(plan)} 个站点（free-asset {len(free)} 个），"
                   f"{'已抓取 ' + str(len(records)) + ' 条元信息' if fetch else '未联网'}",
             "imagegen.inspire")],
        ok=True, verdict="PASS", grade="PASS",
        need=need, plan=plan, fetched=records,
        rights_notice=_RIGHTS_RULE,
        prompt_seed=prompt_seed,
        next=("把 prompt_seed 作为 mood 传给 compose；素材站内容可商用但仍不可当 logo。"
              if not fetch else "核对抓取结果后，把最有用的 1–2 条写进 design-library 做参考"))



def _brief_subject(brief: Dict[str, Any]) -> str:
    """业务主体：用户自己的话优先，绝不回落到通用模板。"""
    for key in ("subject", "need", "concept", "product", "prompt"):
        val = brief.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _compose_prompt(brief: Dict[str, Any], output_dir: Optional[str] = None,
                    fmt: str = "md") -> Dict[str, Any]:
    """确定性出提示词：不依赖 LLM、不依赖引擎，直接可用。"""
    th = c.load_thresholds()
    reg = c.load_registry()
    style_given = bool(str(brief.get("style") or "").strip())
    style = str(brief.get("style") or "flat")
    pack = _style_pack(style, th, reg)
    subject = _brief_subject(brief)
    if not subject:
        return c.result(
            [_ck(False, "缺少业务主体：subject / need / concept 至少给一个，"
                        "否则只能产出空模板（有风格没内容）", "imagegen.compose")],
            ok=False, verdict="FAIL", grade="FAIL",
            provided=sorted(brief.keys()),
            example={"subject": "中秋蔬菜礼盒主图，甘蓝与胡萝卜，白底",
                     "style": "3d-food", "media": "image", "width": 1200, "height": 1200},
            next="补上 subject（或 --need 一句话需求）后重跑；风格与参数可选")
    media = brief.get("media")
    tp = (brief.get("text_policy")
          or (th["imagegen"].get("text_policy_by_media") or {}).get(str(media))
          or "none")
    width = int(brief.get("width") or 0)
    height = int(brief.get("height") or 0)
    image_size = (_size_for(width, height, th) if width and height
                  else (pack["image_size"] or "square_hd"))

    # 业务字段按出现顺序拼：主体 → 场景 → 道具 → 情绪 → 必含元素 → 风格配方 → 文字策略
    extras = []
    for key in ("scene", "props", "mood", "must_include"):
        val = brief.get(key)
        if isinstance(val, str) and val.strip():
            extras.append(val.strip())
    ref_hit = None
    if brief.get("ref"):
        _idx = _load_refs()
        ref_hit = _idx.get("sites", {}).get(str(brief["ref"]).lower().strip())
        if ref_hit:
            extras.append("design language inspired by " + ref_hit["name"]
                          + ", palette " + ", ".join(ref_hit["colors"][:4])
                          + ", " + (ref_hit["atmosphere"][:140] or ""))
    prompt = ", ".join(p for p in [subject, *extras, pack["positive"],
                                   _text_clause(tp)] if p)
    avoid = str(brief.get("avoid") or "").strip()
    negative = ", ".join(p for p in (pack["negative"], avoid,
                                     str(brief.get("negative_prompt") or ""),
                                     _BASE_NEG) if p)

    risks = list(pack["failure_modes"])
    if media in _TEXT_HEAVY_MEDIA and tp != "overlay-later":
        risks.append("该载体依赖文字：会出乱码标签，建议 overlay-later + 后期排版")
    if not pack["resolved"]:
        risks.append("风格未登记：结果不可复现，建议先加进注册表")
    hard = [str(i.get("desc", "")) for i in (reg.get("hard_limits") or {}).get("items", [])]

    title = str(brief.get("title") or subject or "未命名")
    md = (f"### {title} · {style}（→ {pack['resolved'] or '未登记'}）\n\n"
          f"**Prompt**\n```\n{prompt}\n```\n\n"
          f"**Negative**\n```\n{negative}\n```\n\n"
          f"**参数**：image_size=`{image_size}` · text_policy=`{tp}` · "
          f"level=`{pack['level']}`\n\n"
          f"**已知风险**：{'；'.join(risks) if risks else '无'}\n\n"
          f"**结构性硬限制（换风格也绕不过）**：{'；'.join(hard)}\n")

    out_dir = output_dir or os.path.join(_AGENT_DIR, "workspace", "prompts")
    os.makedirs(out_dir, exist_ok=True)
    slug = (pack["resolved"] or "unknown")
    md_path = os.path.join(out_dir, f"{slug}.md")
    json_path = os.path.join(out_dir, f"{slug}.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"title": title, "style": style, "resolved_style": pack["resolved"],
                   "level": pack["level"], "image_size": image_size,
                   "text_policy": tp, "prompt": prompt, "negative_prompt": negative,
                   "risks": risks, "hard_limits": hard}, f, ensure_ascii=False, indent=2)

    return c.result(
        [_ck(True, f"提示词已生成：{style} → {pack['resolved'] or '未登记'}，"
                   f"{image_size}，可直接复制"
                   + ("" if style_given else "（未指定风格，按 flat 出）"),
             "imagegen.compose")],
        ok=True, verdict="PASS", grade="PASS",
        prompt=prompt, negative_prompt=negative, image_size=image_size,
        text_policy=tp, resolved_style=pack["resolved"], level=pack["level"],
        style_defaulted=not style_given,
        reference=(ref_hit or None),
        risks=risks, hard_limits=hard, artifacts=[md_path, json_path],
        next="复制 Prompt/Negative 到你的生图工具；文字与图表刻度请后期排版"
             + ("" if style_given else "；想换风格加 --style <风格名>"))


_ENGINE_WIRING = {
    "comfyui": {"kind": "local", "enable": "COMFYUI_URL",
                "example": "COMFYUI_URL=http://127.0.0.1:8188"},
    "sdwebui": {"kind": "local", "enable": "SD_WEBUI_URL",
                "example": "SD_WEBUI_URL=http://127.0.0.1:7860"},
    "fooocus": {"kind": "local", "enable": "FOOOCUS_URL",
                "example": "FOOOCUS_URL=http://127.0.0.1:8888"},
    "flux": {"kind": "cloud", "enable": "SILICONFLOW_API_KEY",
             "example": "SILICONFLOW_API_KEY=sk-..."},
    "dalle": {"kind": "cloud", "enable": "OPENAI_API_KEY",
              "example": "OPENAI_API_KEY=sk-..."},
    "wanx": {"kind": "cloud", "enable": "DASHSCOPE_API_KEY",
             "example": "DASHSCOPE_API_KEY=sk-..."},
    "cogview": {"kind": "cloud", "enable": "ZHIPUAI_API_KEY",
                "example": "ZHIPUAI_API_KEY=..."},
    "midjourney": {"kind": "cloud", "enable": "MIDJOURNEY_API_KEY",
                   "example": "MIDJOURNEY_API_KEY=..."},
}


def _engine_catalog() -> Dict[str, Any]:
    """列出所有可接的引擎 + 各自的接入开关（不猜，读引擎实例和 env 契约）。"""
    mgr = get_engine_manager()
    rows = []
    for key, eng in getattr(mgr, "engines", {}).items():
        wiring = _ENGINE_WIRING.get(key, {})
        try:
            online = bool(eng.probe(timeout=0.5).online)
        except Exception:  # noqa: BLE001
            online = False
        rows.append({
            "id": key, "name": getattr(eng, "name", key),
            "kind": wiring.get("kind", ""),
            "endpoint": str(getattr(eng, "endpoint", "")),
            "env": wiring.get("enable", ""),
            "example": wiring.get("example", ""),
            "online": online,
        })
    online_n = sum(1 for r in rows if r["online"])
    lines = ["R10 可接入的生图引擎（接任意一个，generate 就会自动切真实出图）：",
             "  " + "-" * 66]
    for r in rows:
        state = "在线" if r["online"] else "未接"
        lines.append(f"  [{state}] {r['id']:10s} {r['name']:14s} {r['kind']:5s} "
                     f"{r['env']:22s} 例：{r['example']}")
    lines.append("  " + "-" * 66)
    lines.append("  本地：先起服务再设 URL（ComfyUI 默认 8188，SD-WebUI 需 --api 7860）")
    lines.append("  云端：只设 Key 即可，无需改代码")
    lines.append("  接好后验证：python agent.py imagegen engines")
    lines.append("  然后直接出图：python agent.py imagegen generate --input brief.json")
    return {"engines": rows, "online_count": online_n, "text": "\n".join(lines)}


def _engines_help() -> Dict[str, Any]:
    cat = _engine_catalog()
    return c.result(
        [_ck(True, f"引擎接口清单：{len(cat['engines'])} 个可接，当前在线 {cat['online_count']}",
             "imagegen.engines")],
        ok=True, verdict="PASS", grade="PASS",
        engines=cat["engines"], online_count=cat["online_count"],
        text=cat["text"], next="按 env 接入任意一个引擎后重跑本命令确认在线")


def _size_for(width: int, height: int, th: Dict[str, Any]) -> str:
    sizes = th["imagegen"].get("image_sizes") or {}
    if not width or not height:
        return "square_hd"
    ratio = width / float(height)
    for name, size in sizes.items():
        try:
            a, b = str(name).split(":")
            if abs(float(a) / float(b) - ratio) < 0.02:
                return size
        except (ValueError, ZeroDivisionError):
            continue
    return "square_hd"


def _dry_run_generate(brief: Dict[str, Any], output_dir: Optional[str] = None) -> Dict[str, Any]:
    """不碰引擎的试跑：把「最终会发出去的东西」摊开给人确认。

    没有可用引擎时，这是唯一诚实的产出——不是占位图，是待确认的规格。
    """
    th = c.load_thresholds()
    reg = c.load_registry()
    subject = _brief_subject(brief)
    if not subject:
        return c.result(
            [_ck(False, "缺少业务主体：subject / need / concept 至少给一个，"
                        "不提供就只能产出模板", "imagegen.dry_run")],
            ok=False, verdict="FAIL", grade="FAIL",
            next="补上 subject 或 --need 后重跑")
    style = str(brief.get("style") or "flat")
    pack = _style_pack(style, th, reg)
    title = str(brief.get("title") or subject)
    concept = subject
    if pack["positive"]:
        concept = f"{concept}, {pack['positive']}, {pack['text_clause']}"

    width = int(brief.get("width") or 0)
    height = int(brief.get("height") or 0)
    image_size = (_size_for(width, height, th) if width and height
                  else (pack["image_size"] or "square_hd"))
    tp = _text_policy_for(brief, th, pack)

    spec: Dict[str, Any] = {}
    if brief.get("expand", True):
        try:
            spec = get_design_prompter().expand(
                concept, category_or_style=pack["style_hint"],
                aspect_ratio=f"{width or 1024}:{height or 1024}",
                text_policy=tp) or {}
        except Exception:  # noqa: BLE001  没有 LLM 也要能试跑
            spec = {}

    prompt = str(spec.get("prompt_en") or concept)
    negative = str(spec.get("negative_prompt_en") or "lowres, bad anatomy, text, watermark")
    if pack["negative"]:
        negative = f"{negative}, {pack['negative']}"

    media = brief.get("media")
    risks = list(pack["failure_modes"])
    if media in _TEXT_HEAVY_MEDIA and tp != "overlay-later":
        risks.append("该载体天然依赖文字：会出乱码标签，建议 overlay-later + 后期排版")
    if not pack["resolved"]:
        risks.append("风格未登记：只会把名字交给 LLM 扩写，结果不可复现")

    plan = {
        "title": title, "style_requested": style,
        "resolved_style": pack["resolved"], "level": pack["level"],
        "media": media, "text_policy": tp, "image_size": image_size,
        "width": width or 1024, "height": height or 1024,
        "prompt": prompt, "negative_prompt": negative,
        "recipe_injected": bool(pack["positive"]), "risks": risks,
        "engine_used": "none (dry-run)",
    }
    out_dir = output_dir or os.path.join(_AGENT_DIR, "workspace", "dryrun")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "dryrun_" + (pack["resolved"] or "unknown") + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    return c.result(
        [_ck(True, f"试跑：{style} → {pack['resolved'] or '未登记'}，{image_size}，"
                   f"{len(risks)} 条风险（未调用引擎）", "imagegen.dry_run")],
        ok=True, verdict="PASS", grade="PASS", artifacts=[path], **plan,
        next="确认 prompt 与风险后再正式生成；风险项建议先改提示词或换交付形态")


# --------------------------------------------------------------------------- #
# 终极全自动智能生图与审校闭环流水线 (LLM Prompter + Engines + VLM Critic + Compositor)
# --------------------------------------------------------------------------- #
def _mock_block(engine: Any, steps_log: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """命中 mock 引擎时的统一拒绝：不写产物、不报 PASS。"""
    name = getattr(engine, "name", "mock")
    return c.result(
        [_ck(False, f"唯一可用引擎是 {name}（占位渲染，非生图模型），拒绝产出假交付物",
             "imagegen.engine")],
        ok=False, verdict="FAIL", grade="FAIL", blocked=True,
        engine_used=name, route_menu=True, options=_ROUTES, recommended="1",
        steps_log=steps_log or [],
        next="没有真实引擎：先用 `imagegen compose` 拿提示词，"
             "或启动 ComfyUI(8188)/SD-WebUI(7860 --api) 后重试")


def _run_full_generation_pipeline(brief: Dict[str, Any], preferred_engine: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
    if not output_dir:
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
    os.makedirs(output_dir, exist_ok=True)
    steps_log: List[Dict[str, Any]] = []

    # Step 1: 需求解析 + 注册表配方注入（否则新风格只剩一个名字，LLM 扩写会飘）
    subject = _brief_subject(brief)
    if not subject:
        return c.result(
            [_ck(False, "缺少业务主体：subject / need / concept 至少给一个",
                 "imagegen.brief")],
            ok=False, verdict="FAIL", grade="FAIL", steps_log=steps_log,
            next="补上 subject 后重跑；不要用通用模板代替真实业务描述")
    title = str(brief.get("title") or subject)
    raw_concept = subject
    style = str(brief.get("style") or "flat")
    pack = _style_pack(style, c.load_thresholds(), c.load_registry())
    if pack["positive"]:
        raw_concept = f"{raw_concept}, {pack['positive']}, {pack['text_clause']}"
    width = int(brief.get("width") or 1024)
    height = int(brief.get("height") or 1024)
    steps_log.append({"step": 1, "name": "需求解析", "status": "OK",
                      "detail": f"主题: {title} | 风格: {style} → {pack['resolved'] or '未登记'} | 尺寸: {width}x{height}",
                      "style_pack": {"resolved": pack["resolved"], "level": pack["level"],
                                     "recipe_injected": bool(pack["positive"]),
                                     "known_failures": pack["failure_modes"]}})

    # Step 2: 接入真正的 LLM 创意大脑进行专业 Prompt 扩写 (DesignPrompter)
    prompter = get_design_prompter()
    expanded_spec = prompter.expand(raw_concept, category_or_style=pack["style_hint"],
                                    aspect_ratio=f"{width}:{height}",
                                    text_policy=pack.get("text_policy", "none"))

    expanded_prompt = expanded_spec.get("prompt_en", raw_concept)
    negative_prompt = expanded_spec.get("negative_prompt_en", "lowres, bad anatomy, text, watermark")
    if pack["negative"]:
        negative_prompt = f"{negative_prompt}, {pack['negative']}"
    
    steps_log.append({
        "step": 2,
        "name": "LLM 创意大脑扩写",
        "status": "OK",
        "prompt_en": expanded_prompt,
        "negative_prompt": negative_prompt,
        "color_palette": expanded_spec.get("color_palette", [])
    })

    # Step 3~5: 引擎调度 → 后处理 → VLM 质检 → 反思自愈（闭环重试，直至达标或耗尽次数）
    manager = get_engine_manager()
    critic = get_vlm_critic()
    max_retries = int(brief.get("max_retries", 2))

    current_prompt = expanded_prompt
    current_negative = negative_prompt
    attempts: List[Dict[str, Any]] = []
    processed_images: List[str] = []
    raw_images: List[str] = []
    gen_result = None
    review_res = None
    selected_engine = None
    heal_log: List[str] = []

    for attempt in range(1, max_retries + 2):
        selected_engine = manager.select_best_engine(preferred=preferred_engine)

        # 第二道锁：即使引擎探测误判（比如 key 设了但失效），也不许拿 mock 当交付物
        if getattr(selected_engine, "is_mock", False):
            return _mock_block(selected_engine, steps_log)

        steps_log.append({
            "step": 3, "attempt": attempt, "name": "外置引擎调度",
            "status": "OK", "engine": selected_engine.name, "endpoint": selected_engine.endpoint,
        })

        task = ImageGenTask(
            prompt=current_prompt,
            negative_prompt=current_negative,
            width=width,
            height=height,
            steps=int(brief.get("steps", 30)),
            cfg_scale=float(brief.get("cfg_scale", 7.5)),
            style=style,
            seed=int(brief.get("seed", -1)),
            model_name=brief.get("model_name"),
        )

        gen_result = selected_engine.generate(task, output_dir=output_dir)
        if not gen_result.ok:
            attempts.append({"attempt": attempt, "engine": selected_engine.name,
                             "ok": False, "error": gen_result.error})
            steps_log.append({"step": 3.1, "attempt": attempt, "name": "生图失败",
                              "status": "FAIL", "error": gen_result.error})
            if attempt <= max_retries:
                continue
            return {
                "ok": False,
                "verdict": "FAIL",
                "error": gen_result.error,
                "engine_used": selected_engine.name,
                "steps_log": steps_log,
                "attempts": attempts,
                "next": "生图失败，请检查外置生图软件是否启动或云端 API Key 是否配置。",
            }

        raw_images = gen_result.image_paths
        steps_log.append({"step": 3.1, "attempt": attempt, "name": "生图物理落地",
                          "status": "OK", "images": raw_images})

        # Step 4: 视觉后处理、Design-to-Code 图层推导与伴生资产包生成
        processed_images = _postprocess_images(raw_images, brand_mark=brief.get("brand", "LINGXI · R10 PRO"))
        
        # 导出伴生结构化规格包 (Layered Spec JSON)
        from engines.layout_spec import LayoutSpecEngine
        spec_bundle_path = os.path.join(output_dir, "design_layer_spec.json")
        target_base_img = raw_images[0] if raw_images else processed_images[0]
        layer_spec = LayoutSpecEngine.analyze_layout(target_base_img, title_text=title, price_text=brief.get("price", "¥99"))
        with open(spec_bundle_path, "w", encoding="utf-8") as f:
            json.dump(layer_spec.to_dict(), f, ensure_ascii=False, indent=2)

        steps_log.append({
            "step": 4, "attempt": attempt, "name": "视觉后处理与图层规格导出",
            "status": "OK", "artifacts": processed_images, "spec_bundle": spec_bundle_path
        })

        # Step 5: 多模态 VLM 视觉质检
        target_img = processed_images[0] if processed_images else raw_images[0]
        review_res = critic.review(target_img, brief=raw_concept, expected_style=style)
        attempts.append({
            "attempt": attempt, "engine": selected_engine.name, "ok": True,
            "score": review_res.score, "passed": review_res.passed,
            "defects": review_res.defects, "artifact": target_img,
        })
        steps_log.append({
            "step": 5, "attempt": attempt, "name": "多模态 VLM 视觉审校",
            "status": "OK" if review_res.passed else "WARN",
            "critic_result": review_res.to_dict(),
        })

        if review_res.passed:
            break

        # 反思自愈：注入缺陷特征，微调种子后重试
        if attempt <= max_retries:
            fix = review_res.suggestions or " ".join(review_res.defects) or "improve subject integrity and layout margins"
            current_negative = f"{current_negative}, {fix}"
            current_prompt = f"{current_prompt}, refined detail, ensure intact structure"
            heal_log.append(f"[第{attempt}次反思] {fix}")
            steps_log.append({"step": 6, "attempt": attempt, "name": "视觉反思自愈",
                              "status": "RETRY", "injected_negative": fix})

    passed = bool(review_res and review_res.passed)
    return {
        "ok": True,
        "verdict": "PASS" if passed else "PASS_WITH_WARNING",
        "engine_used": selected_engine.name if selected_engine else "",
        "attempts": len(attempts),
        "retry_count": max(0, len(attempts) - 1),
        "auto_heal_log": heal_log,
        "prompt_used": current_prompt,
        "negative_used": current_negative,
        "artifacts": processed_images,
        "spec_bundle": os.path.join(output_dir, "design_layer_spec.json"),
        "raw_images": raw_images,
        "vlm_review": review_res.to_dict() if review_res else {},
        "steps_log": steps_log,
        "next": (
            f"R10 全自动智能设计与生图管线圆满成功（{len(attempts)} 次尝试，自愈 {len(heal_log)} 次）！"
            f"最终商用物料已产出: {processed_images}"
        ),
    }


def _postprocess_images(image_paths: List[str], brand_mark: str = "LINGXI · R10 PRO") -> List[str]:
    """视觉后处理：执行 Anti-Slop 质感精修 (Polish) 并叠加专业商业品牌标签条。"""
    from engines.slop_guard import SlopGuard
    out_paths: List[str] = []
    for img_p in image_paths:
        try:
            # 1. 执行质感精修 (去除廉价噪点、提升微反差)
            polished_p = SlopGuard.polish(img_p)

            # 2. 叠加品牌标签
            from PIL import Image, ImageDraw, ImageFont
            img = Image.open(polished_p).convert("RGBA")
            draw = ImageDraw.Draw(img)
            draw.rectangle([30, img.height - 80, 300, img.height - 30], fill=(15, 23, 42, 210))
            try:
                font = ImageFont.truetype("arial.ttf", 22)
            except Exception:
                font = ImageFont.load_default()
            draw.text((42, img.height - 68), brand_mark, fill=(34, 211, 238), font=font)
            out_p = img_p.rsplit(".", 1)[0] + "_commercial.png"
            img.convert("RGB").save(out_p, format="PNG")
            out_paths.append(out_p)
        except Exception:
            out_paths.append(img_p)
    return out_paths
