# -*- coding: utf-8 -*-
"""S15 本地图片处理（自有实现，替代外部图像工具链）。

基于 Pillow 的确定性图片操作，不上传、不联网：
  info       读尺寸/格式/体积
  resize     等比或指定尺寸缩放
  crop       裁剪
  compress   重编码压缩（质量可调）
  pad        按比例补边（电商主图/社媒规格）
  watermark  文字水印

纪律：永不覆盖源文件；输出格式白名单；缺 Pillow 时返回 blocked，不假装处理。
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from . import _common as c

NAME = "imgops"
DESC = "本地图片处理：info/resize/crop/compress/pad/watermark"

FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
MAX_PIXELS = 40_000_000


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def _pil() -> Tuple[Any, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, (ImageDraw, ImageFont)
    except Exception:
        return None, None


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, hlp in (("info", "读取图片信息"), ("resize", "缩放"), ("crop", "裁剪"),
                      ("compress", "压缩"), ("pad", "按比例补边"), ("watermark", "加文字水印")):
        a = act.add_parser(name, help=hlp)
        a.add_argument("--input", required=True)
        if name != "info":
            a.add_argument("--out", required=True)
        if name == "resize":
            a.add_argument("--width", type=int, default=0)
            a.add_argument("--height", type=int, default=0)
        if name == "crop":
            a.add_argument("--left", type=int, required=True)
            a.add_argument("--top", type=int, required=True)
            a.add_argument("--right", type=int, required=True)
            a.add_argument("--bottom", type=int, required=True)
        if name == "compress":
            a.add_argument("--quality", type=int, default=82)
        if name == "pad":
            a.add_argument("--ratio", default="1:1")
            a.add_argument("--fill", default="#FFFFFF")
        if name == "watermark":
            a.add_argument("--text", required=True)
            a.add_argument("--opacity", type=int, default=120)


def run(args) -> Dict[str, Any]:
    if args.action == "info":
        return _info(args.input)
    return _mutate(args)


# --------------------------------------------------------------------------- #
def _info(path: str) -> Dict[str, Any]:
    checks = [_ck(os.path.isfile(path), f"文件存在（{path}）", "img.exists")]
    Image, _ = _pil()
    if Image is None:
        checks.append(_ck(False, "Pillow 未安装（pip install pillow）", "img.deps"))
        return c.result(checks, ok=False, verdict="FAIL", status="blocked")
    if not os.path.isfile(path):
        return c.result(checks, ok=False, verdict="FAIL")
    with Image.open(path) as im:
        w, h = im.size
        fmt = im.format
    size = os.path.getsize(path)
    checks.append(_ck(w * h <= MAX_PIXELS, f"像素数 ≤{MAX_PIXELS}（{w}x{h}）", "img.size"))
    return c.result(checks, ok=True, verdict="PASS",
                    width=w, height=h, format=fmt,
                    size_bytes=size, ratio=round(w / h, 3) if h else 0)


def _mutate(args) -> Dict[str, Any]:
    checks = [_ck(os.path.isfile(args.input), "源文件存在", "img.exists"),
              _ck(os.path.abspath(args.input) != os.path.abspath(args.out),
                  "输出不得覆盖源文件", "img.overwrite"),
              _ck(os.path.splitext(args.out)[1].lower() in FORMATS,
                  f"输出格式 ∈ {sorted(FORMATS)}", "img.format")]
    Image, extra = _pil()
    if Image is None:
        checks.append(_ck(False, "Pillow 未安装（pip install pillow）", "img.deps"))
        return c.result(checks, ok=False, verdict="FAIL", status="blocked")
    if not all(x["ok"] for x in checks):
        return c.result(checks, ok=False, verdict="FAIL", next="按 checks 修正参数")
    ImageDraw, ImageFont = extra
    quality = max(1, min(100, int(getattr(args, "quality", 82))))

    with Image.open(args.input) as im:
        im = im.convert("RGBA") if im.mode == "P" else im
        action = args.action
        if action == "resize":
            if args.width <= 0 and args.height <= 0:
                return c.result(checks + [_ck(False, "宽或高至少给一个", "img.resize")],
                                ok=False, verdict="FAIL")
            w, h = im.size
            if args.width and args.height:
                target = (args.width, args.height)
            elif args.width:
                target = (args.width, max(1, round(h * args.width / w)))
            else:
                target = (max(1, round(w * args.height / h)), args.height)
            out_im = im.resize(target, Image.LANCZOS)
        elif action == "crop":
            if not (0 <= args.left < args.right <= im.width and 0 <= args.top < args.bottom <= im.height):
                return c.result(checks + [_ck(False, "裁剪框越界", "img.crop")],
                                ok=False, verdict="FAIL")
            out_im = im.crop((args.left, args.top, args.right, args.bottom))
        elif action == "compress":
            out_im = im
        elif action == "pad":
            try:
                rw, rh = (float(x) for x in args.ratio.split(":"))
            except ValueError:
                return c.result(checks + [_ck(False, "ratio 需形如 3:4", "img.pad")],
                                ok=False, verdict="FAIL")
            target_ratio = rw / rh
            w, h = im.size
            if w / h > target_ratio:
                new_w, new_h = w, round(w / target_ratio)
            else:
                new_w, new_h = round(h * target_ratio), h
            canvas = Image.new("RGBA", (new_w, new_h), args.fill)
            canvas.paste(im, ((new_w - w) // 2, (new_h - h) // 2), im if im.mode == "RGBA" else None)
            out_im = canvas
        elif action == "watermark":
            base = im.convert("RGBA")
            layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            try:
                font = ImageFont.load_default(size=max(14, base.width // 30))
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), args.text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((base.width - tw - 24, base.height - th - 24), args.text,
                      font=font, fill=(255, 255, 255, max(0, min(255, args.opacity))))
            out_im = Image.alpha_composite(base, layer)
        else:  # pragma: no cover
            return c.result(checks + [_ck(False, f"未知动作 {action}", "img.action")],
                            ok=False, verdict="FAIL")

        fmt = FORMATS[os.path.splitext(args.out)[1].lower()]
        save_kw = {"quality": quality} if fmt == "JPEG" else {}
        if fmt == "JPEG" and out_im.mode == "RGBA":
            out_im = out_im.convert("RGB")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        out_im.save(args.out, fmt, **save_kw)

    checks.append(_ck(os.path.getsize(args.out) > 0, "输出文件已生成", "img.out"))
    return c.result(checks, ok=True, verdict="PASS", out=args.out,
                    size_bytes=os.path.getsize(args.out),
                    width=out_im.width, height=out_im.height,
                    next="可交 R08 做落地页素材或 R14 做主图")
