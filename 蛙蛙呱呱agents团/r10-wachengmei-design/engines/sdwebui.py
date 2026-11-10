# -*- coding: utf-8 -*-
"""Stable Diffusion WebUI (A1111 / SD-Forge / Fooocus API) 引擎驱动器。

支持：
1. 自动探测本地 7860 端口（SD-WebUI / WebUI-Forge）及 /sdapi/v1/options 接口；
2. 构造 txt2img 标准请求体；
3. 解码返回的 Base64 图像，自动写入 workspace 目录；
4. 读取当前加载的 SD 模型、VAE 及 VRAM 状态。
"""
from __future__ import annotations

import base64
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask


class SDWebUIEngine(BaseImageEngine):
    """Stable Diffusion WebUI / Forge 本地/远程服务驱动器。"""

    def __init__(self, endpoint: str = "http://127.0.0.1:7860", name: str = "SD-WebUI", enabled: bool = True):
        super().__init__(name=name, endpoint=endpoint, enabled=enabled)

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        """探测 SD-WebUI 7860 端口是否存活。"""
        t0 = time.time()
        url = f"{self.endpoint}/sdapi/v1/sd-models"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "R10-Design-Agent"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.time() - t0) * 1000
                models_data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("model_name") or m.get("title", "") for m in models_data if isinstance(m, dict)]

                return EngineProbeResult(
                    engine_name=self.name,
                    online=True,
                    endpoint=self.endpoint,
                    latency_ms=latency,
                    models=models,
                    version="A1111/Forge",
                    details=f"SD-WebUI 在线 | 已加载模型数: {len(models)} | 首选模型: {models[0] if models else 'None'}",
                )
        except Exception as e:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                latency_ms=0.0,
                details=f"服务未启动或未开启 API 模式 ({e})。请启动 WebUI 并确保带有 --api 参数。",
            )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        """调用 SD-WebUI /sdapi/v1/txt2img 接口出图。"""
        probe = self.probe(timeout=1.5)
        if not probe.online:
            return EngineGenResult(
                ok=False,
                engine_name=self.name,
                error=f"SD-WebUI 离线 ({self.endpoint})。请确保 WebUI 正在运行并附带 --api 参数。",
            )

        os.makedirs(output_dir, exist_ok=True)
        seed = task.seed if task.seed > 0 else random.randint(1, 10**10)

        payload_dict = {
            "prompt": task.prompt,
            "negative_prompt": task.negative_prompt,
            "seed": seed,
            "steps": task.steps,
            "cfg_scale": task.cfg_scale,
            "width": task.width,
            "height": task.height,
            "sampler_name": task.sampler_name if task.sampler_name else "Euler a",
            "batch_size": task.batch_size,
            "restore_faces": False,
            "enable_hr": False,
        }

        # 合并自定义额外参数
        if task.extra_params:
            payload_dict.update(task.extra_params)

        payload = json.dumps(payload_dict).encode("utf-8")
        url = f"{self.endpoint}/sdapi/v1/txt2img"
        t0 = time.time()

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "R10-Design-Agent"},
            )
            with urllib.request.urlopen(req, timeout=180.0) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))

            images_b64 = result_json.get("images", [])
            saved_paths: List[str] = []

            for idx, b64_str in enumerate(images_b64):
                # 剥离可能存在的头部前缀
                if "," in b64_str:
                    b64_str = b64_str.split(",", 1)[1]
                img_data = base64.b64decode(b64_str)
                timestamp = int(time.time())
                out_path = os.path.join(output_dir, f"sd_{timestamp}_{idx+1}.png")
                with open(out_path, "wb") as f:
                    f.write(img_data)
                saved_paths.append(out_path)

            elapsed = time.time() - t0
            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                seed_used=seed,
                elapsed_seconds=elapsed,
                prompt_used=task.prompt,
                raw_response={"info": result_json.get("info", "")},
            )

        except Exception as e:
            return EngineGenResult(
                ok=False,
                engine_name=self.name,
                error=f"SD-WebUI 生图请求异常: {e}",
            )
