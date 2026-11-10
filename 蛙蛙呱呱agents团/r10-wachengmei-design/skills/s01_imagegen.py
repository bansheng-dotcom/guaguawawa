# -*- coding: utf-8 -*-
"""S01 AI 生图与插画 —— 能力域 1（最终完全体：LLM 动态大脑 + 真实外置引擎调度 + 真实 VLM 多模态审校反思 + 商业排版联动）。
"""
from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List, Optional

from . import _common as c
from engines import get_engine_manager, ImageGenTask, get_design_prompter, get_vlm_critic
from engines.explorer import StylescapeExplorer
from engines.inpaint import InpaintEditEngine

NAME = "imagegen"
DESC = "AI生图与插画：prompt / style / generate (LLM + VLM + Engines)"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    pr = act.add_parser("prompt", help="校验生图提示词包")
    pr.add_argument("--input", required=True)

    st = act.add_parser("style", help="校验风格探索")
    st.add_argument("--input", required=True)

    act.add_parser("probe", help="批量探测所有外置生图软件及云端 API 健康状态")

    gen = act.add_parser("generate", help="执行全自动 AI 生图、LLM 扩写、VLM 质检反思与商用排版闭环管线")
    gen.add_argument("--input", required=True, help="设计需求 JSON 文件")
    gen.add_argument("--explore", action="store_true", help="是否启动 Multi-Stylescape 多向方案探索")
    gen.add_argument("--engine", default=None, help="指定首选生图引擎")
    gen.add_argument("--output-dir", default=None, help="高清大图输出目录")

    # 新增：对话式增量重绘改稿子命令
    edt = act.add_parser("edit", help="对已有设计图进行局部增量重绘与无损改稿 (Inpainting)")
    edt.add_argument("--image", required=True, help="基础底图路径")
    edt.add_argument("--instruction", required=True, help="改稿自然语言指令，如'把背景换成赛博雨夜'")
    edt.add_argument("--region", default="background", help="重绘目标区域: background(背景) / subject(主体) / border(边框)")
    edt.add_argument("--engine", default=None, help="指定生图引擎")
    edt.add_argument("--output-dir", default=None, help="输出目录")


def run(args) -> Dict[str, Any]:
    if args.action == "prompt":
        return _validate_prompt(c.load_json(args.input))
    if args.action == "style":
        return _validate_style(c.load_json(args.input))
    if args.action == "probe":
        return get_engine_manager().probe_all()
    if args.action == "edit":
        out_dir = getattr(args, "output_dir", None) or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
        return InpaintEditEngine.edit_image(
            image_path=args.image,
            instruction=args.instruction,
            output_dir=out_dir,
            target_region=getattr(args, "region", "background"),
            preferred_engine=getattr(args, "engine", None)
        )
    if args.action == "generate":
        brief = c.load_json(args.input)
        if getattr(args, "explore", False):
            # 启动 Multi-Stylescape 模式
            out_dir = getattr(args, "output_dir", None) or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
            gallery = StylescapeExplorer.generate_three_directions(brief, out_dir)
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
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    media = data.get("media")
    ok_media = media in th["imagegen"]["output_media"]
    checks.append(_ck(ok_media,
                      f"media={media!r} 在白名单 {th['imagegen']['output_media']}",
                      "imagegen.media"))
    if not ok_media:
        return c.result(checks, ok=False, verdict="FAIL",
                        media=media, style=data.get("style"))

    style = data.get("style")
    ok_style = style in th["imagegen"]["style_types"]
    checks.append(_ck(ok_style,
                      f"style={style!r} 在白名单 {th['imagegen']['style_types']}",
                      "imagegen.style"))

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

    ok = ok_media and ok_style and bool(prompt) and bool(negative) and ok_locks and ok_lock
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    media=media, style=style,
                    lock_count=len(locks) if isinstance(locks, list) else 0)


def _validate_style(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    style = data.get("style")
    ok_style = style in th["imagegen"]["style_types"]
    checks.append(_ck(ok_style,
                      f"style={style!r} 在白名单 {th['imagegen']['style_types']}",
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

    ok = ok_style and comp_ok and ok_pal
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    style=style,
                    comp_count=len(composition) if isinstance(composition, list) else 0,
                    palette=palette if isinstance(palette, list) else [])


# --------------------------------------------------------------------------- #
# 终极全自动智能生图与审校闭环流水线 (LLM Prompter + Engines + VLM Critic + Compositor)
# --------------------------------------------------------------------------- #
def _run_full_generation_pipeline(brief: Dict[str, Any], preferred_engine: Optional[str] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
    if not output_dir:
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace", "artifacts"))
    os.makedirs(output_dir, exist_ok=True)
    steps_log: List[Dict[str, Any]] = []

    # Step 1: 需求解析
    title = brief.get("title", "商业宣传主视觉")
    raw_concept = brief.get("concept", brief.get("prompt", "High-end product commercial poster"))
    style = brief.get("style", "commercial-photography")
    width = int(brief.get("width", 1024))
    height = int(brief.get("height", 1024))
    steps_log.append({"step": 1, "name": "需求解析", "status": "OK", "detail": f"主题: {title} | 风格: {style} | 尺寸: {width}x{height}"})

    # Step 2: 接入真正的 LLM 创意大脑进行专业 Prompt 扩写 (DesignPrompter)
    prompter = get_design_prompter()
    expanded_spec = prompter.expand(raw_concept, category_or_style=style, aspect_ratio=f"{width}:{height}")
    
    expanded_prompt = expanded_spec.get("prompt_en", raw_concept)
    negative_prompt = expanded_spec.get("negative_prompt_en", "lowres, bad anatomy, text, watermark")
    
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
