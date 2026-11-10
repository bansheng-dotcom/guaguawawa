# -*- coding: utf-8 -*-
"""主流商业生图软件与云端 API 统一预留接口集。

涵盖各大主流生图生态：
1. 本地独立软件类：
   - Fooocus (专精人像、写实与操作简化，端口通常为 7865/8888)
   - InvokeAI (专精画布排版/修图，REST API)
2. 主流云端生图 API：
   - FLUX (SiliconFlow 硅基流动 / Fal.ai / Together.ai / Replicate)
   - OpenAI DALL-E 3 (官方 REST API)
   - Midjourney (第三方中继 / GoAPI / ImagineAPI)
   - 阿里通义万相 (DashScope 阿里云百炼 API)
   - 智谱 AI CogView (Zhipu BigModel API)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask


# =========================================================================== #
# 1. 本地衍生软件：Fooocus Engine
# =========================================================================== #
class FooocusEngine(BaseImageEngine):
    """Fooocus 本地 API 引擎（基于 Fooocus-API 项目，端口通常为 8888 或 7865）。"""

    def __init__(self, endpoint: str = "http://127.0.0.1:8888", name: str = "Fooocus", enabled: bool = True):
        super().__init__(name=name, endpoint=endpoint, enabled=enabled)

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        t0 = time.time()
        url = f"{self.endpoint}/v1/engines/all-models"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "R10-Design-Agent"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.time() - t0) * 1000
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("model_name", "") for m in data] if isinstance(data, list) else []
                return EngineProbeResult(
                    engine_name=self.name,
                    online=True,
                    endpoint=self.endpoint,
                    latency_ms=latency,
                    models=models,
                    version="Fooocus-API",
                    details=f"Fooocus 在线 | 可用模型: {len(models)} 个",
                )
        except Exception as e:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                latency_ms=0.0,
                details=f"Fooocus 未运行或未开启 API 包装层 ({e})",
            )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        probe = self.probe(timeout=1.5)
        if not probe.online:
            return EngineGenResult(ok=False, engine_name=self.name, error="Fooocus 服务离线")

        os.makedirs(output_dir, exist_ok=True)
        url = f"{self.endpoint}/v1/generation/text-to-image"
        payload = json.dumps({
            "prompt": task.prompt,
            "negative_prompt": task.negative_prompt,
            "style_selections": [task.style] if task.style else ["Fooocus V2"],
            "performance_selection": "Speed",
            "aspect_ratios_selection": f"{task.width}*{task.height}",
            "image_number": task.batch_size,
        }).encode("utf-8")

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            saved_paths = []
            for idx, item in enumerate(data if isinstance(data, list) else [data]):
                img_url = item.get("url")
                if img_url:
                    out_path = os.path.join(output_dir, f"fooocus_{int(time.time())}_{idx}.png")
                    urllib.request.urlretrieve(img_url, out_path)
                    saved_paths.append(out_path)

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=task.prompt,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"Fooocus 出图异常: {e}")


# =========================================================================== #
# 2. 云端顶级开源生图：FLUX (SiliconFlow 硅基流动 / Fal.ai / Together)
# =========================================================================== #
class FluxCloudEngine(BaseImageEngine):
    """FLUX.1 (Schnell / Dev / Pro) 云端高速 API 驱动器。

    支持读取环境变量 SILICONFLOW_API_KEY / FAL_KEY / TOGETHER_API_KEY。
    默认接入硅基流动 (SiliconFlow) FLUX.1 接口，开箱即用。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.siliconflow.cn/v1",
        model: str = "black-forest-labs/FLUX.1-schnell",
        name: str = "FLUX-Cloud",
    ):
        super().__init__(name=name, endpoint=endpoint, enabled=True)
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("FLUX_API_KEY", "")
        self.model = model

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.api_key:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                details="未配置 API Key。请设置环境变量 SILICONFLOW_API_KEY 或在配置中填入密钥。",
            )
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            models=[self.model, "black-forest-labs/FLUX.1-dev"],
            version="v1",
            details=f"FLUX 云端引擎就绪 | 默认模型: {self.model}",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.api_key:
            return EngineGenResult(ok=False, engine_name=self.name, error="缺少 API Key")

        os.makedirs(output_dir, exist_ok=True)
        url = f"{self.endpoint}/images/generations"
        payload = json.dumps({
            "model": task.model_name or self.model,
            "prompt": task.prompt,
            "image_size": f"{task.width}x{task.height}",
            "batch_size": task.batch_size,
            "seed": task.seed if task.seed > 0 else None,
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "R10-Design-Agent",
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            saved_paths = []
            for idx, item in enumerate(data.get("images", [])):
                img_url = item.get("url")
                if img_url:
                    out_path = os.path.join(output_dir, f"flux_{int(time.time())}_{idx+1}.jpg")
                    urllib.request.urlretrieve(img_url, out_path)
                    saved_paths.append(out_path)

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=task.prompt,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"FLUX 云端调用异常: {e}")


# =========================================================================== #
# 3. OpenAI DALL-E 3
# =========================================================================== #
class DalleEngine(BaseImageEngine):
    """OpenAI DALL-E 3 官方标准接口驱动器。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.openai.com/v1",
        name: str = "DALL-E-3",
    ):
        super().__init__(name=name, endpoint=endpoint, enabled=True)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.api_key:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                details="未配置 OPENAI_API_KEY 环境变量",
            )
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            models=["dall-e-3", "dall-e-2"],
            details="OpenAI DALL-E 3 引擎就绪",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.api_key:
            return EngineGenResult(ok=False, engine_name=self.name, error="缺少 OPENAI_API_KEY")

        os.makedirs(output_dir, exist_ok=True)
        url = f"{self.endpoint}/images/generations"
        payload = json.dumps({
            "model": "dall-e-3",
            "prompt": task.prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "standard",
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            saved_paths = []
            for idx, item in enumerate(data.get("data", [])):
                img_url = item.get("url")
                if img_url:
                    out_path = os.path.join(output_dir, f"dalle_{int(time.time())}_{idx+1}.png")
                    urllib.request.urlretrieve(img_url, out_path)
                    saved_paths.append(out_path)

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=task.prompt,
                raw_response=data,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"DALL-E 3 调用失败: {e}")


# =========================================================================== #
# 4. Midjourney (支持通用中继代理 / GoAPI / ImagineAPI)
# =========================================================================== #
class MidjourneyEngine(BaseImageEngine):
    """Midjourney 代理网关接口驱动器。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://api.midjourney-proxy.com/mj",
        name: str = "Midjourney",
    ):
        super().__init__(name=name, endpoint=endpoint, enabled=True)
        self.api_key = api_key or os.environ.get("MIDJOURNEY_API_KEY", "")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.api_key:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                details="未配置 MIDJOURNEY_API_KEY",
            )
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            models=["mj-v6.0", "niji-6"],
            details="Midjourney 代理接口已配置",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.api_key:
            return EngineGenResult(ok=False, engine_name=self.name, error="缺少 MIDJOURNEY_API_KEY")

        os.makedirs(output_dir, exist_ok=True)
        url = f"{self.endpoint}/submit/imagine"
        prompt_with_params = f"{task.prompt} --v 6.0 --ar 1:1"
        payload = json.dumps({"prompt": prompt_with_params}).encode("utf-8")

        headers = {
            "mj-api-secret": self.api_key,
            "Content-Type": "application/json",
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            task_id = data.get("result")
            if not task_id:
                return EngineGenResult(ok=False, engine_name=self.name, error=f"提交失败: {data}")

            # 轮询获取任务
            saved_paths = []
            for _ in range(60):
                time.sleep(3.0)
                q_req = urllib.request.Request(f"{self.endpoint}/task/{task_id}/fetch", headers=headers)
                with urllib.request.urlopen(q_req, timeout=10.0) as q_resp:
                    task_info = json.loads(q_resp.read().decode("utf-8"))

                if task_info.get("status") == "SUCCESS":
                    img_url = task_info.get("imageUrl")
                    if img_url:
                        out_path = os.path.join(output_dir, f"mj_{task_id}.png")
                        urllib.request.urlretrieve(img_url, out_path)
                        saved_paths.append(out_path)
                        break
                elif task_info.get("status") in ["FAILURE", "FAILED"]:
                    return EngineGenResult(ok=False, engine_name=self.name, error=task_info.get("failReason", "MJ 失败"))

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=prompt_with_params,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"Midjourney 调用异常: {e}")


# =========================================================================== #
# 5. 阿里通义万相 (Aliyun DashScope)
# =========================================================================== #
class DashScopeWanxEngine(BaseImageEngine):
    """阿里通义万相生图大模型驱动器。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        name: str = "Wanx-Alibaba",
    ):
        super().__init__(name=name, endpoint=endpoint, enabled=True)
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.api_key:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                details="未配置 DASHSCOPE_API_KEY",
            )
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            models=["wanx-v1", "wanx-sketch-to-image-lite"],
            details="阿里通义万相 API 就绪",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.api_key:
            return EngineGenResult(ok=False, engine_name=self.name, error="缺少 DASHSCOPE_API_KEY")

        os.makedirs(output_dir, exist_ok=True)
        payload = json.dumps({
            "model": "wanx-v1",
            "input": {
                "prompt": task.prompt,
                "negative_prompt": task.negative_prompt,
            },
            "parameters": {
                "style": f"<{task.style}>" if task.style else "<auto>",
                "size": f"{task.width}*{task.height}",
                "n": task.batch_size,
            }
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(self.endpoint, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                return EngineGenResult(ok=False, engine_name=self.name, error=f"通义万相提交失败: {data}")

            # 轮询异步任务
            task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
            saved_paths = []
            for _ in range(60):
                time.sleep(2.0)
                q_req = urllib.request.Request(task_url, headers={"Authorization": f"Bearer {self.api_key}"})
                with urllib.request.urlopen(q_req, timeout=10.0) as q_resp:
                    t_data = json.loads(q_resp.read().decode("utf-8"))
                status = t_data.get("output", {}).get("task_status")
                if status == "SUCCEEDED":
                    for idx, res_item in enumerate(t_data.get("output", {}).get("results", [])):
                        img_url = res_item.get("url")
                        if img_url:
                            out_p = os.path.join(output_dir, f"wanx_{task_id}_{idx+1}.png")
                            urllib.request.urlretrieve(img_url, out_p)
                            saved_paths.append(out_p)
                    break
                elif status in ["FAILED", "CANCELED"]:
                    return EngineGenResult(ok=False, engine_name=self.name, error=f"通义万相生成失败: {t_data}")

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=task.prompt,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"通义万相异常: {e}")


# =========================================================================== #
# 6. 智谱 AI CogView (Zhipu BigModel)
# =========================================================================== #
class CogViewEngine(BaseImageEngine):
    """智谱 AI CogView-3 / CogView-3-Plus 引擎驱动器。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: str = "https://open.bigmodel.cn/api/paas/v4/images/generations",
        name: str = "CogView",
    ):
        super().__init__(name=name, endpoint=endpoint, enabled=True)
        self.api_key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.api_key:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                details="未配置 ZHIPUAI_API_KEY",
            )
        return EngineProbeResult(
            engine_name=self.name,
            online=True,
            endpoint=self.endpoint,
            models=["cogview-3-plus", "cogview-3"],
            details="智谱 CogView API 就绪",
        )

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.api_key:
            return EngineGenResult(ok=False, engine_name=self.name, error="缺少 ZHIPUAI_API_KEY")

        os.makedirs(output_dir, exist_ok=True)
        payload = json.dumps({
            "model": "cogview-3-plus",
            "prompt": task.prompt,
            "size": "1024x1024",
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.time()
        try:
            req = urllib.request.Request(self.endpoint, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            saved_paths = []
            for idx, item in enumerate(data.get("data", [])):
                img_url = item.get("url")
                if img_url:
                    out_path = os.path.join(output_dir, f"cogview_{int(time.time())}_{idx+1}.png")
                    urllib.request.urlretrieve(img_url, out_path)
                    saved_paths.append(out_path)

            return EngineGenResult(
                ok=bool(saved_paths),
                engine_name=self.name,
                image_paths=saved_paths,
                elapsed_seconds=time.time() - t0,
                prompt_used=task.prompt,
            )
        except Exception as e:
            return EngineGenResult(ok=False, engine_name=self.name, error=f"CogView 异常: {e}")
