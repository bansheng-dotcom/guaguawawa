# -*- coding: utf-8 -*-
"""自定义命令引擎：把任意本地/远程生图脚本接成 R10 的引擎。

为什么需要它：
    R10 内置 8 个引擎，但用户的真实生成器可能是一个 MCP、一个 CLI、
    或者某个带鉴权的 HTTP 脚本。没有这个入口，就只能改代码。
    有了它，只要设一个环境变量就能接上。

契约：
    R10_IMAGE_CMD 指向一个可执行命令。R10 通过 stdin 传入 JSON：
        {"prompt": "...", "negative_prompt": "...", "width": 1024,
         "height": 1024, "seed": -1, "out": "<必须写入的图片路径>"}
    命令必须把图片写到 out 指定路径；也可以把路径打印到 stdout。

示例：
    set R10_IMAGE_CMD=python D:/my_gen.py
    （my_gen.py 读 stdin，调用你的模型/接口，保存到 payload["out"]）

安全：命令由使用者显式配置；未配置时引擎探测为离线，不会被自动选中。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask


class CommandEngine(BaseImageEngine):
    """把外部命令包装成引擎（默认名 Custom-Cmd）。"""

    def __init__(self, name: str = "Custom-Cmd"):
        self.cmd = os.environ.get("R10_IMAGE_CMD", "").strip()
        super().__init__(name=name, endpoint=self.cmd or "unset")

    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        if not self.cmd:
            return EngineProbeResult(
                engine_name=self.name, online=False, endpoint="unset",
                details="未配置 R10_IMAGE_CMD；设为一个可执行命令即可接入自有生成器")
        return EngineProbeResult(
            engine_name=self.name, online=True, endpoint=self.cmd,
            latency_ms=0.5,
            details="已配置自定义命令引擎（stdin 收 JSON，按 out 写图）")

    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        if not self.cmd:
            return EngineGenResult(ok=False, engine_name=self.name,
                                   error="未配置 R10_IMAGE_CMD")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir,
                                f"r10_custom_{int(time.time())}.png")
        payload = {
            "prompt": task.prompt,
            "negative_prompt": task.negative_prompt,
            "width": task.width, "height": task.height,
            "seed": task.seed, "style": task.style,
            "out": out_path,
        }
        t0 = time.time()
        try:
            proc = subprocess.run(self.cmd, shell=True, input=json.dumps(payload),
                                  capture_output=True, text=True, timeout=300,
                                  encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return EngineGenResult(ok=False, engine_name=self.name,
                                   error="自定义命令超时（300s）")
        except Exception as exc:  # noqa: BLE001
            return EngineGenResult(ok=False, engine_name=self.name,
                                   error=f"自定义命令执行失败：{exc}")
        if proc.returncode != 0:
            return EngineGenResult(ok=False, engine_name=self.name,
                                   error=f"命令退出码 {proc.returncode}: "
                                         f"{(proc.stderr or '')[-300:]}")
        if not os.path.isfile(out_path):
            printed = (proc.stdout or "").strip().splitlines()
            cand = printed[-1].strip() if printed else ""
            if cand and os.path.isfile(cand):
                out_path = cand
            else:
                return EngineGenResult(
                    ok=False, engine_name=self.name,
                    error="命令未写出图片：请写到 payload['out'] 或打印路径")
        return EngineGenResult(ok=True, engine_name=self.name,
                               image_paths=[out_path], seed_used=task.seed,
                               elapsed_seconds=time.time() - t0,
                               prompt_used=task.prompt)
