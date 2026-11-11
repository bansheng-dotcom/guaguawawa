# -*- coding: utf-8 -*-
"""生图引擎统一管理器与调度中心。

功能：
1. 集中管理所有本地引擎 (ComfyUI, SD-WebUI, Fooocus) 与云端接口 (FLUX, Midjourney, DALL-E 3, 通义万相, 智谱 CogView)；
2. 一键批量健康巡检 (probe_all)；
3. 智能路由与自适应降级：优先使用在线的本地专业引擎，次选云端 API，若全离线则执行优雅降级（本地视觉样张保底）。
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask
from .cloud_apis import (CogViewEngine, DalleEngine, DashScopeWanxEngine,
                         FluxCloudEngine, FooocusEngine, MidjourneyEngine)
from .comfyui import ComfyUIEngine
from .sdwebui import SDWebUIEngine
from .command import CommandEngine
from .placeholder_guard import guard_result


class MockFallbackEngine(BaseImageEngine):
    """当所有外部生图软件均未启动时的离线保底引擎。

    使用 PIL 高性能渲染一张专业级构图占位概念稿，并输出完整的设计元数据与接入提示，
    保证系统链路 100% 畅通且不报错。

    注意：它**不是**生图模型。`is_mock=True` 供上层识别——任何把它当成交付物的路径
    都必须拦下，否则用户会拿到一张写着 "Fallback Mock" 的假成品。
    """

    is_mock = True

    def __init__(self, name: str = "Local-Visual-Fallback"):
        super().__init__(name=name, endpoint="local://embedded")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            latency_ms=0.5,
            version="1.0-embedded",
            details="内置确定性高保真视觉渲染保底层 (PIL + 参数化几何构图)",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        os.makedirs(output_dir, exist_ok=True)
        t0 = time.time()
        from PIL import Image, ImageDraw, ImageFont

        w, h = task.width, task.height
        # 打造深邃暗黑设计底色与霓虹渐变感
        img = Image.new("RGB", (w, h), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # 绘制网格辅助线
        grid_step = 80
        for x in range(0, w, grid_step):
            draw.line([(x, 0), (x, h)], fill=(30, 41, 59), width=1)
        for y in range(0, h, grid_step):
            draw.line([(0, y), (w, y)], fill=(30, 41, 59), width=1)

        # 绘制中央视觉焦点光晕与主几何体
        cx, cy = w // 2, h // 2
        r = min(w, h) // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(34, 211, 238), width=4)
        draw.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=(8, 145, 178))

        # 标注设计提示词信息
        try:
            font = ImageFont.truetype("arial.ttf", 28)
            small_font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        draw.text((60, 60), f"R10 PROTOTYPE: {task.style.upper()}", fill=(34, 211, 238), font=font)
        draw.text((60, 110), f"Prompt: {task.prompt[:60]}...", fill=(248, 250, 252), font=small_font)
        draw.text((60, h - 80), f"Size: {w}x{h} | Seed: {task.seed} | Engine: Fallback Mock", fill=(148, 163, 184), font=small_font)

        out_path = os.path.join(output_dir, f"r10_design_{int(time.time())}.png")
        img.save(out_path, format="PNG")

        return EngineGenResult(
            ok=True,
            engine_name=self.name,
            image_paths=[out_path],
            seed_used=task.seed,
            elapsed_seconds=time.time() - t0,
            prompt_used=task.prompt,
            raw_response={
                "notice": "外部生图软件（ComfyUI/SD）未启动，已自动使用内置视觉渲染器生成设计布局概念样稿。"
            },
        )


class EngineManager:
    """引擎管理器。"""

    def __init__(self):
        # 注册所有引擎实例
        self.engines: Dict[str, BaseImageEngine] = {
            "comfyui": ComfyUIEngine(endpoint=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")),
            "sdwebui": SDWebUIEngine(endpoint=os.environ.get("SD_WEBUI_URL", "http://127.0.0.1:7860")),
            "fooocus": FooocusEngine(endpoint=os.environ.get("FOOOCUS_URL", "http://127.0.0.1:8888")),
            "flux": FluxCloudEngine(),
            "dalle": DalleEngine(),
            "midjourney": MidjourneyEngine(),
            "wanx": DashScopeWanxEngine(),
            "cogview": CogViewEngine(),
            # 自定义命令引擎：设 R10_IMAGE_CMD 即可接自有生成器（MCP/CLI/带鉴权脚本）
            "custom": CommandEngine(),
        }
        self.fallback = MockFallbackEngine()

    def get_engine(self, name: str) -> Optional[BaseImageEngine]:
        return self.engines.get(name.lower())

    def probe_all(self, timeout: float = 1.5) -> Dict[str, Any]:
        """批量探测所有生图软件及云端 API 的健康状态。"""
        results = {}
        online_count = 0
        for name, engine in self.engines.items():
            res = engine.probe(timeout=timeout)
            results[name] = res.to_dict()
            if res.online:
                online_count += 1

        return {
            "total_engines": len(self.engines),
            "online_count": online_count,
            "engines": results,
            "recommendation": (
                "检测到可用的生图软件服务，可立即接管真实生图！"
                if online_count > 0
                else "当前所有外置软件服务均未启动或未配置 API Key。推荐：启动本地 ComfyUI (8188) 或 SD-WebUI (7860 --api)，即可实现无缝代理由 Agent 接管出图。"
            ),
        }

    def select_best_engine(self, preferred: Optional[str] = None) -> BaseImageEngine:
        """挑选最适宜的可用引擎。"""
        # 1. 如果用户显式指定了引擎
        if preferred:
            eng = self.get_engine(preferred)
            if eng and eng.probe(timeout=1.0).online:
                return eng

        # 2. 显式配置的自定义命令引擎优先（用户自己接的生成器）
        custom = self.engines.get("custom")
        if custom is not None and custom.probe(timeout=1.0).online:
            return custom

        # 3. 本地高阶引擎优先 (ComfyUI > SD-WebUI > Fooocus)
        for local_name in ["comfyui", "sdwebui", "fooocus"]:
            eng = self.engines[local_name]
            if eng.probe(timeout=1.0).online:
                return eng

        # 3. 商业云端 API 其次 (FLUX > DALL-E > 通义万相 > CogView > Midjourney)
        for cloud_name in ["flux", "dalle", "wanx", "cogview", "midjourney"]:
            eng = self.engines[cloud_name]
            if eng.probe(timeout=1.0).online:
                return eng

        # 4. 离线保底
        return self.fallback

    def generate(
        self,
        task: ImageGenTask,
        output_dir: str,
        preferred_engine: Optional[str] = None,
    ) -> EngineGenResult:
        """统一调度执行生图。"""
        engine = self.select_best_engine(preferred=preferred_engine)
        # 占位图防护：接口回占位（stub）时判失败，绝不把假图当成品
        return guard_result(engine.generate(task, output_dir=output_dir), engine.name)


# 全局单例管理器
_default_manager: Optional[EngineManager] = None


def get_engine_manager() -> EngineManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = EngineManager()
    return _default_manager
