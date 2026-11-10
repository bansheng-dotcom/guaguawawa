# -*- coding: utf-8 -*-
"""ComfyUI 外置生图引擎驱动器。

支持：
1. 自动探测本地 ComfyUI 服务 (默认端口 8188) 是否存活、显卡显存状态及已有模型列表；
2. 构造标准 API 工作流 JSON 提交到 ComfyUI `/prompt` 接口；
3. 轮询 `/history/{prompt_id}` 获取执行状态；
4. 自动下载生成的高清图并存入目标目录。
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask


class ComfyUIEngine(BaseImageEngine):
    """ComfyUI 本地/远程服务驱动器。"""

    def __init__(self, endpoint: str = "http://127.0.0.1:8188", name: str = "ComfyUI", enabled: bool = True):
        super().__init__(name=name, endpoint=endpoint, enabled=enabled)

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        """探测 ComfyUI 8188 端口是否存活。"""
        t0 = time.time()
        url = f"{self.endpoint}/system_stats"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "R10-Design-Agent"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.time() - t0) * 1000
                data = json.loads(resp.read().decode("utf-8"))
                
                # 获取系统与 GPU 信息
                devices = data.get("devices", [])
                dev_info = devices[0].get("name", "GPU") if devices else "CPU"
                vram_free = ""
                if devices and "vram_free" in devices[0]:
                    vram_free = f" (Free VRAM: {devices[0]['vram_free'] // (1024*1024)}MB)"

                # 尝试获取模型列表
                models = self._fetch_models(timeout=timeout)
                return EngineProbeResult(
                    engine_name=self.name,
                    online=True,
                    endpoint=self.endpoint,
                    latency_ms=latency,
                    models=models,
                    version=data.get("system", {}).get("comfyui_version", "Active"),
                    details=f"ComfyUI 在线 | 设备: {dev_info}{vram_free} | 已加载模型数: {len(models)}",
                )
        except Exception as e:
            return EngineProbeResult(
                engine_name=self.name,
                online=False,
                endpoint=self.endpoint,
                latency_ms=0.0,
                details=f"服务未启动或端口不通 ({e})。请在本地启动 ComfyUI: python main.py --listen",
            )

    def _fetch_models(self, timeout: float = 2.0) -> List[str]:
        """获取 ComfyUI 已安装的 Checkpoint 模型列表。"""
        url = f"{self.endpoint}/object_info/CheckpointLoaderSimple"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "R10-Design-Agent"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                inputs = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
                ckpt_list = inputs.get("ckpt_name", [[]])[0]
                return list(ckpt_list) if isinstance(ckpt_list, list) else []
        except Exception:
            return []

    def build_default_workflow(self, task: ImageGenTask, ckpt_name: Optional[str] = None) -> Dict[str, Any]:
        """按任务意图动态组装 ComfyUI API 工作流节点图。

        动态能力（对标 ComfyUI-Copilot / comfyui-mcp 的 Graph 编排）：
        - 基础链路：Checkpoint → CLIP 正/负向 → EmptyLatent → KSampler → VAEDecode → SaveImage
        - upscale=true：自动串联「Latent 放大 → 二次采样(refine)」的高清放大支路
        - controlnet_image：自动挂载 ControlNet 施加结构与姿态约束
        - loras：[{name, strength}] 自动串联 LoRA 加载节点并替换模型来源
        """
        seed = task.seed if task.seed > 0 else random.randint(1, 10**14)
        target_ckpt = ckpt_name or task.model_name or "v1-5-pruned-emaonly.safetensors"
        extra = task.extra_params or {}
        use_upscale = bool(extra.get("upscale") or extra.get("hires_fix"))
        controlnet_image = extra.get("controlnet_image")
        loras = task.loras or []

        workflow: Dict[str, Any] = {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": task.steps,
                    "cfg": task.cfg_scale,
                    "sampler_name": task.sampler_name if task.sampler_name in [
                        "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_sde"
                    ] else "euler_ancestral",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "4": {
                "inputs": {"ckpt_name": target_ckpt},
                "class_type": "CheckpointLoaderSimple",
            },
            "5": {
                "inputs": {
                    "width": task.width,
                    "height": task.height,
                    "batch_size": task.batch_size,
                },
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"text": task.prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "7": {
                "inputs": {"text": task.negative_prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
        }

        # --- 动态注入 1：LoRA 链式加载 ---
        model_ref: List[Any] = ["4", 0]
        clip_ref: List[Any] = ["4", 1]
        for idx, lora in enumerate(loras):
            node_id = str(50 + idx)
            workflow[node_id] = {
                "inputs": {
                    "lora_name": lora.get("name", ""),
                    "strength_model": float(lora.get("strength", 0.8)),
                    "strength_clip": float(lora.get("strength", 0.8)),
                    "model": model_ref,
                    "clip": clip_ref,
                },
                "class_type": "LoraLoader",
            }
            model_ref = [node_id, 0]
            clip_ref = [node_id, 1]
        workflow["3"]["inputs"]["model"] = model_ref
        workflow["6"]["inputs"]["clip"] = clip_ref
        workflow["7"]["inputs"]["clip"] = clip_ref

        # --- 动态注入 2：ControlNet 结构约束 ---
        if controlnet_image:
            workflow["30"] = {
                "inputs": {"image": controlnet_image, "upload": "image"},
                "class_type": "LoadImage",
            }
            workflow["31"] = {
                "inputs": {"control_net_name": extra.get("controlnet_name", "control_v11p_sd15_openpose.pth")},
                "class_type": "ControlNetLoader",
            }
            workflow["32"] = {
                "inputs": {
                    "strength": float(extra.get("controlnet_strength", 0.8)),
                    "conditioning": ["6", 0],
                    "control_net": ["31", 0],
                    "image": ["30", 0],
                },
                "class_type": "ControlNetApply",
            }
            workflow["3"]["inputs"]["positive"] = ["32", 0]

        # --- 动态注入 4：Inpaint 局部重绘支路（锁定未修改区域，增量修改遮罩区域）---
        mask_image = extra.get("mask_image")
        input_image = extra.get("input_image")
        if input_image and mask_image:
            workflow["40"] = {
                "inputs": {"image": input_image, "upload": "image"},
                "class_type": "LoadImage",
            }
            workflow["41"] = {
                "inputs": {"image": mask_image, "upload": "image"},
                "class_type": "LoadImage",
            }
            workflow["42"] = {
                "inputs": {
                    "pixels": ["40", 0],
                    "vae": ["4", 2],
                    "mask": ["41", 0],
                    "grow_mask_by": int(extra.get("grow_mask", 6)),
                },
                "class_type": "VAEEncodeForInpaint",
            }
            workflow["3"]["inputs"]["latent_image"] = ["42", 0]
            workflow["3"]["inputs"]["denoise"] = float(extra.get("denoise", 0.75))

        # --- 动态注入 3：高清放大支路（Latent Upscale → 二次采样 → 解码）---
        if use_upscale:
            target_w = int(extra.get("upscale_width", task.width * 2))
            target_h = int(extra.get("upscale_height", task.height * 2))
            workflow["20"] = {
                "inputs": {"upscale_method": "nearest-exact", "width": target_w,
                           "height": target_h, "crop": "disabled", "samples": ["3", 0]},
                "class_type": "LatentUpscale",
            }
            workflow["21"] = {
                "inputs": {
                    "seed": seed + 1,
                    "steps": max(10, task.steps // 2),
                    "cfg": task.cfg_scale,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": float(extra.get("refine_denoise", 0.45)),
                    "model": model_ref,
                    "positive": workflow["3"]["inputs"]["positive"],
                    "negative": ["7", 0],
                    "latent_image": ["20", 0],
                },
                "class_type": "KSampler",
            }
            workflow["8"] = {"inputs": {"samples": ["21", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"}
        else:
            workflow["8"] = {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"}

        workflow["9"] = {
            "inputs": {"filename_prefix": "R10_Wachengmei", "images": ["8", 0]},
            "class_type": "SaveImage",
        }
        return workflow

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        """调用 ComfyUI 生成图片并自动下载落盘。"""
        probe = self.probe(timeout=1.5)
        if not probe.online:
            return EngineGenResult(
                ok=False,
                engine_name=self.name,
                error=f"ComfyUI 服务离线 ({self.endpoint})。请先启动 ComfyUI 后重试。",
            )

        # 确定可用模型
        ckpt_name = None
        if probe.models:
            ckpt_name = probe.models[0]
            if task.model_name and task.model_name in probe.models:
                ckpt_name = task.model_name

        workflow = self.build_default_workflow(task, ckpt_name=ckpt_name)
        client_id = f"r10_agent_{int(time.time())}"
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")

        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"{self.endpoint}/prompt",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "R10-Design-Agent"},
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                prompt_id = res_data.get("prompt_id")

            if not prompt_id:
                return EngineGenResult(
                    ok=False,
                    engine_name=self.name,
                    error=f"ComfyUI 未返回 prompt_id: {res_data}",
                )

            # 轮询获取生图结果（最长等待 180 秒）
            saved_images = self._wait_and_download(prompt_id, output_dir, max_wait=180.0)
            elapsed = time.time() - t0

            return EngineGenResult(
                ok=bool(saved_images),
                engine_name=self.name,
                image_paths=saved_images,
                seed_used=workflow["3"]["inputs"]["seed"],
                elapsed_seconds=elapsed,
                prompt_used=task.prompt,
                raw_response={"prompt_id": prompt_id, "model_used": ckpt_name},
            )

        except Exception as e:
            return EngineGenResult(
                ok=False,
                engine_name=self.name,
                error=f"ComfyUI 生图失败: {e}",
            )

    def _wait_and_download(self, prompt_id: str, output_dir: str, max_wait: float = 180.0) -> List[str]:
        """轮询 /history/{prompt_id} 并下载产物图。"""
        os.makedirs(output_dir, exist_ok=True)
        start_time = time.time()
        downloaded: List[str] = []

        while time.time() - start_time < max_wait:
            time.sleep(1.0)
            try:
                hist_url = f"{self.endpoint}/history/{prompt_id}"
                req = urllib.request.Request(hist_url, headers={"User-Agent": "R10-Design-Agent"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    history = json.loads(resp.read().decode("utf-8"))

                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_out in outputs.items():
                        images = node_out.get("images", [])
                        for img_meta in images:
                            fname = img_meta.get("filename")
                            subfolder = img_meta.get("subfolder", "")
                            img_type = img_meta.get("type", "output")
                            if fname:
                                view_url = f"{self.endpoint}/view?filename={urllib.parse.quote(fname)}&subfolder={urllib.parse.quote(subfolder)}&type={urllib.parse.quote(img_type)}"
                                save_path = os.path.join(output_dir, f"comfyui_{fname}")
                                urllib.request.urlretrieve(view_url, save_path)
                                downloaded.append(save_path)
                    if downloaded:
                        break
            except Exception:
                continue

        return downloaded
