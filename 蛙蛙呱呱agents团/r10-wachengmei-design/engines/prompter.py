# -*- coding: utf-8 -*-
"""视觉设计总监级 LLM 创意扩写大脑 (Visual Design Prompter)。

对标 GitHub 标杆项目（ComfyUI-Copilot / comfyui_LLM_party / prompt-generator）：
将口语化、模糊的需求描述（如“国风夏日新品青柠茶海报”）动态解构为：
1. 视觉主体 (Core Subject)
2. 艺术风格与流派 (Style & Genre)
3. 构图与镜头语言 (Composition & Camera Lens)
4. 光影与色彩氛围 (Lighting & Color Palette)
5. 渲染引擎与质感参数 (Octane Render / Unreal Engine 5 / Photorealistic)
6. 负向避坑词 (Negative Prompt)
7. 适宜宽高比与版面预留规划 (Layout & Safe Margin)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from .ledger import get_design_ledger

# 专业级视觉设计总监系统提示词 (Design System Meta-Prompt)
_DESIGN_PROMPTER_SYSTEM = """你是一名国际顶级视觉艺术总监，既懂商业摄影也懂插画与平面设计。
你的任务是将用户的简报 (Brief) 扩写为结构化的专业设计生图参数。

铁律：
1) 风格必须与指定风格一致：指定 flat/line-art/pixel 等插画风格时，不要写摄影镜头、胶片、棚拍等话术；
   指定摄影风格时，不要写扁平色块、矢量描边。
2) 文字策略由调用方给出：
   - none / overlay-later → 负向里必须包含 text, lettering, logo, watermark；
   - render-attempt → 负向里禁止出现 text/logo（否则和自己打架），改为画面预留文字区。
请严格返回符合以下 JSON Schema 的纯 JSON 对象，不要包含 Markdown 标记或多余解释：
{
  "subject_zh": "主体中文精准描述",
  "prompt_en": "英文正向生图提示词，用逗号分隔，包含主体、细节、光影、渲染器、画质标签",
  "negative_prompt_en": "针对该风格的英文负向规避词",
  "style_type": "风格类型，如：cyberpunk, 3d, minimalist, watercolor, commercial-photography, flat",
  "composition": "构图法则，如：golden-ratio, rule-of-thirds, clean-centered, bold-poster-grid",
  "lighting": "光影规范，如：studio-soft-box, dramatic-rim-light, flat-even-illustration-light",
  "color_palette": ["#HEX1", "#HEX2", "#HEX3"],
  "recommended_ratio": "1:1 或 16:9 或 9:16 或 3:4",
  "layout_safe_margin": "如：top-30-percent-empty-for-title (留白区域指示，便于后续文字排版)"
}
"""


class DesignPrompter:
    """视觉创意扩写大脑。优先读取兼容 OpenAI / DeepSeek 的 API，无 Key 时启动专家规则知识库。"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
        self.model = model or os.environ.get("DESIGN_LLM_MODEL") or "deepseek-chat"

    def expand(self, brief: str, category_or_style: str = "auto", aspect_ratio: str = "1:1",
               text_policy: str = "none") -> Dict[str, Any]:
        """将自然语言简报扩写为结构化专业设计工程参数。"""
        if self.api_key:
            try:
                res = self._call_llm(brief, category_or_style, aspect_ratio, text_policy)
                if res and isinstance(res, dict) and "prompt_en" in res:
                    return res
            except Exception as e:
                # LLM 调用失败时优雅降级至专家知识库
                pass

        return self._expert_fallback(brief, category_or_style, aspect_ratio, text_policy)

    def _call_llm(self, brief: str, category_or_style: str, aspect_ratio: str,
                  text_policy: str = "none") -> Dict[str, Any]:
        """调用兼容 OpenAI 的 LLM 接口。"""
        url = f"{self.base_url}/chat/completions"
        user_content = (f"设计简报: {brief}\n指定风格倾向: {category_or_style}\n"
                        f"建议比例: {aspect_ratio}\n文字策略: {text_policy}")
        
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": _DESIGN_PROMPTER_SYSTEM},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "R10-Design-Director-LLM",
        }

        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _expert_fallback(self, brief: str, category_or_style: str, aspect_ratio: str,
                         text_policy: str = "none") -> Dict[str, Any]:
        """离线专家知识库兜底（覆盖商业设计各主流流派与构图留白，并对齐 DESIGN.md 账本规范）。"""
        ledger = get_design_ledger()
        style = category_or_style.lower() if category_or_style != "auto" else "commercial-photography"
        
        # 风格特征知识库
        style_traits = {
            "cyberpunk": {
                "keywords": "cyberpunk aesthetic, vibrant neon cyan and magenta rim light, dark moody reflective background, high-tech metallic textures, octane render, ray tracing, 8k",
                "neg": "blurry, low quality, oversaturated noise, deformed parts, ugly background",
                "colors": ["#0F172A", "#22D3EE", "#F43F5E"],
            },
            "3d": {
                "keywords": "3D cute claymation style, soft ambient occlusion, studio softbox lighting, clean pastel gradients, high detailed 3D render, blender 3d, unreal engine 5",
                "neg": "rough edges, photorealistic human, noisy texture, dark shadows",
                "colors": ["#F8FAFC", "#38BDF8", "#F59E0B"],
            },
            "watercolor": {
                "keywords": "hand-painted traditional watercolor, wet-on-wet technique, soft color bleed, artistic fine-art paper texture, delicate brush strokes, tranquil atmosphere",
                "neg": "digital vector, 3d render, sharp geometric lines, harsh contrast",
                "colors": ["#FAFAF9", "#0284C7", "#10B981"],
            },
            "minimalist": {
                "keywords": "minimalist scandinavian design, vast negative space, bold geometric composition, elegant natural soft daylight, premium magazine editorial aesthetic",
                "neg": "cluttered, chaotic elements, neon, complex background, text",
                "colors": ["#FFFFFF", "#1E293B", "#94A3B8"],
            },
            "flat": {
                "keywords": "flat vector illustration, bold flat color blocks, clean geometric shapes, minimal shading, crisp edges, editorial illustration",
                "neg": "photo, 3d render, gradient mesh, heavy texture, realistic skin",
                "colors": ["#0F766E", "#F59E0B", "#0EA5E9"],
            },
            "line-art": {
                "keywords": "minimal line art, thin consistent black strokes, pure white background, single accent color, technical precision, generous white space",
                "neg": "photo, gradient, heavy shadow, texture, color fill",
                "colors": ["#111827", "#F59E0B", "#FFFFFF"],
            },
            "gradient": {
                "keywords": "smooth gradient mesh, translucent layered shapes, luminous soft edges, modern abstract poster, fine grain",
                "neg": "photo, harsh edges, muddy colors, text",
                "colors": ["#4C1D95", "#F43F5E", "#FBBF24"],
            },
            "duotone": {
                "keywords": "duotone two-color print, halftone dots, high contrast silhouette, screen print texture, flat spot inks",
                "neg": "full color, photo, smooth gradient, third color",
                "colors": ["#14532D", "#F5E6C8", "#14532D"],
            },
            "isometric": {
                "keywords": "isometric 3D scene, 30 degree top-down angle, miniature diorama, soft ambient shadow, pure white background, clean vector-like render",
                "neg": "perspective distortion, photo, dark background, clutter",
                "colors": ["#FFFFFF", "#86EFAC", "#FB923C"],
            },
            "pixel": {
                "keywords": "true 16-bit pixel art, hard pixel edges with no anti-aliasing, limited 32-color palette, nearest-neighbor upscale, retro game aesthetic",
                "neg": "anti-aliasing, smooth gradient, painterly shading, photographic detail",
                "colors": ["#1E1B4B", "#F59E0B", "#22D3EE"],
            },
            "collage": {
                "keywords": "mixed-media collage, torn paper edges, layered print fragments, visible cut lines, editorial zine energy",
                "neg": "seamless render, 3d, clean vector, smooth gradient",
                "colors": ["#FAF5EB", "#B91C1C", "#1F2937"],
            },
            "commercial-photography": {
                "keywords": "commercial advertising hero shot, 8k high-end product photography, Hasselblad 100mm lens, f/4 aperture, dramatic studio rim light, ultra sharp focus, pristine surfaces",
                "neg": "grainy, amateur photo, bad hands, distortion, watermark, oversaturated",
                "colors": ["#111827", "#3B82F6", "#F3F4F6"],
            }
        }

        # 只按「解析后的 core 风格」匹配，否则 "flat（brutalist）" 会掉进摄影兜底
        base = category_or_style.split("（")[0].split("(")[0].strip().lower()
        matched_style = None
        for k in style_traits:
            if k == base:
                matched_style = k
                break
        if matched_style is None:
            for k in style_traits:
                if k in base or k in brief.lower():
                    matched_style = k
                    break
        matched_style = matched_style or "commercial-photography"

        trait = style_traits[matched_style]

        # 收尾语气按族分档：摄影 / 平面海报 / 插画。原实现把摄影腔（award-winning、
        # cheap oversaturated slop）套到所有风格上，是这次要清掉的残留。
        photo_family = {"commercial-photography", "cyberpunk"}
        render_family = {"3d"}
        poster_family = {"duotone", "gradient", "minimalist"}
        if matched_style in photo_family:
            tail = "professional commercial photography composition, controlled studio lighting"
            lighting = "commercial-studio-lighting"
            composition = "clean-centered-with-safe-margins"
        elif matched_style in render_family:
            tail = "clean 3d render composition, soft studio lighting, crisp material definition"
            lighting = "soft-studio-render-light"
            composition = "centered-product-composition"
        elif matched_style in poster_family:
            tail = "strong poster composition, clear visual hierarchy, deliberate negative space"
            lighting = "flat-graphic-lighting"
            composition = "bold-poster-grid"
        else:
            tail = "clean editorial illustration composition, balanced negative space"
            lighting = "flat-even-illustration-light"
            composition = "editorial-balanced-composition"

        # 品牌色用中性表述：不描述明暗气质，避免与浅色插画冲突
        brand_colors_hint = (f"brand accent color {ledger.accent_color}, "
                             f"brand primary color {ledger.primary_color}")

        parts = [f"Design visual of ({brief})", trait["keywords"], brand_colors_hint, tail]
        if text_policy == "overlay-later":
            parts.append("clean empty area reserved for later typography")
        prompt_en = ", ".join(p for p in parts if p)

        # 负向分三层：风格专属 + 通用质量 + 文字。
        # 文字层只在非 render-attempt 时加，否则会和「允许渲染文字」自相矛盾。
        universal_neg = "low quality, jpeg artifacts, blurry, deformed, cropped subject"
        text_neg = "text, lettering, logo, watermark, signature"
        neg_parts = [trait["neg"], universal_neg]
        if text_policy != "render-attempt":
            neg_parts.append(text_neg)
        negative_prompt = ", ".join(p for p in neg_parts if p)

        return {
            "subject_zh": brief,
            "prompt_en": prompt_en,
            "negative_prompt_en": negative_prompt,
            "style_type": matched_style,
            "composition": composition,
            "lighting": lighting,
            "color_palette": [ledger.primary_color, ledger.accent_color, ledger.secondary_color],
            "recommended_ratio": aspect_ratio or "1:1",
            "layout_safe_margin": ledger.safe_margin_rules,
            "source": "expert-design-engine-with-design-md",
        }


_prompter_instance: Optional[DesignPrompter] = None


def get_design_prompter() -> DesignPrompter:
    global _prompter_instance
    if _prompter_instance is None:
        _prompter_instance = DesignPrompter()
    return _prompter_instance
