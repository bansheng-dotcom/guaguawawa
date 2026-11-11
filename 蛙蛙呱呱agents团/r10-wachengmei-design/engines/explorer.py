# -*- coding: utf-8 -*-
"""Multi-Stylescape 多向方案探索与画廊看板管线 (Multi-Direction Explorer).

对标 huashu-design (28k stars) 设计模式：
1. 接收单一简报，LLM 自动扩展出 3 个不同视角的方向（例如：极致简约、赛博朋克、印象水彩）；
2. 批量生成这 3 个方向的草图；
3. 将最终生成物汇总为一个可视化的多图并列看板（Design Gallery Dashboard）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from PIL import Image

from engines import get_engine_manager, get_design_prompter, ImageGenTask


class StylescapeExplorer:
    """多方案并行探索器。"""
    
    @classmethod
    def generate_three_directions(cls, brief: Dict[str, Any], output_dir: str) -> List[str]:
        """批量生成三种风格的方案，并汇总成画廊。"""
        prompter = get_design_prompter()
        manager = get_engine_manager()
        
        # 预设三个对比鲜明的风格方向
        directions = ["minimalist", "cyberpunk", "watercolor"]
        artifacts = []
        
        for style in directions:
            # 1. 动态生成各方向 Prompt
            spec = prompter.expand(brief.get("concept", "product"), category_or_style=style)
            
            # 2. 调度引擎出图
            task = ImageGenTask(
                prompt=spec.get("prompt_en", ""),
                negative_prompt=spec.get("negative_prompt_en", ""),
                width=512, height=512, # 并行探索使用小尺寸预览
                style=style
            )
            engine = manager.select_best_engine()
            if getattr(engine, "is_mock", False):
                # 没有真实引擎：宁可返回空，也不拿占位图冒充三种风格探索
                return []
            res = engine.generate(task, output_dir=output_dir)
            
            if res.ok and res.image_paths:
                artifacts.append((style, res.image_paths[0]))
        
        return cls._create_gallery_dashboard(artifacts, output_dir)

    @classmethod
    def _create_gallery_dashboard(cls, artifacts: List[Tuple[str, str]], output_dir: str) -> List[str]:
        """将三张图拼合为一个画廊看板。"""
        if not artifacts:
            return []
            
        try:
            images = [Image.open(p) for _, p in artifacts]
            w, h = images[0].size
            # 拼接图 (3x1)
            gallery = Image.new("RGB", (w * len(images), h), (255, 255, 255))
            for i, img in enumerate(images):
                gallery.paste(img, (i * w, 0))
            
            gallery_path = os.path.join(output_dir, "gallery_dashboard.png")
            gallery.save(gallery_path, format="PNG")
            return [gallery_path]
        except Exception as e:
            return [p for _, p in artifacts]
