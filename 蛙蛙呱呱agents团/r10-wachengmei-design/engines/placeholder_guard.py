# -*- coding: utf-8 -*-
"""占位图防护：识别「接口没真出图、只回了占位」的情况。

为什么需要它：
    某些生图接口（含 Trae 的 `text_to_image` 公共端点）在无鉴权/无额度时不会报错，
    而是**恒定返回同一张占位图**（"The image is generating… Please refresh page"）。
    重试、换 prompt、换尺寸都没用——因为返回的是写死的字节。
    如果不拦，agent 会把占位图当成品，继续跑 imgops/验收，最后交付一张假图。

判定两步：
    1. 已知占位图的 MD5（精确命中，最快）；
    2. 兜底：几乎纯色/极低方差（占位图通常是整幅浅灰）。

用法：
    from engines.placeholder_guard import is_placeholder_file, PLACEHOLDER_NOTE
    if is_placeholder_file(path):
        ...  # 不要当成品，直接 blocked
"""
from __future__ import annotations

import hashlib
import os
from typing import Optional

# 实测：Trae text_to_image 无鉴权时恒返回这张（1832×1832，176KB）
KNOWN_PLACEHOLDER_MD5 = {
    "19a0b822edb11957055e4588c2159058",
}

PLACEHOLDER_NOTE = (
    "接口返回的是占位图（stub），不是真实生成结果；"
    "重试/换 prompt 都无效，需换到有鉴权的真实引擎（imagegen engines 可查）"
)


def md5_of(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _low_variance(data: bytes, threshold: float = 6.0) -> bool:
    """兜底：整幅图灰度方差极低（近似纯色）。Pillow 不在则跳过。"""
    try:
        import io as _io
        from PIL import Image
        import numpy as np
    except Exception:  # noqa: BLE001
        return False
    try:
        im = Image.open(_io.BytesIO(data)).convert("RGB")
        arr = np.asarray(im).astype("float32").mean(axis=2)
        return float(arr.std()) < threshold
    except Exception:  # noqa: BLE001
        return False


def is_placeholder_bytes(data: bytes) -> bool:
    if not data:
        return False
    if md5_of(data) in KNOWN_PLACEHOLDER_MD5:
        return True
    return _low_variance(data)


def is_placeholder_file(path: str) -> bool:
    try:
        if not path or not os.path.isfile(path):
            return False
        size = os.path.getsize(path)
        if size <= 0:
            return False
        with open(path, "rb") as f:
            return is_placeholder_bytes(f.read())
    except OSError:
        return False


def guard_result(result, engine_name: str = ""):
    """把引擎结果里的占位图判为失败（保持返回结构不变）。"""
    try:
        paths = getattr(result, "image_paths", None) or []
        if getattr(result, "ok", False) and paths and is_placeholder_file(paths[0]):
            result.ok = False
            result.error = f"{engine_name or 'engine'} 返回占位图：{PLACEHOLDER_NOTE}"
            result.image_paths = []
        return result
    except Exception:  # noqa: BLE001
        return result
