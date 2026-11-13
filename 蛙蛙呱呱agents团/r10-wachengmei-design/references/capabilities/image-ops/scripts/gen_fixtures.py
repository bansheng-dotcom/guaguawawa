#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新生成本包的图片夹具（可重复）。

为什么要有它：
    图片夹具是二进制文件，放进仓库后难以审查"它到底是什么"。
    用脚本生成，任何人 `python scripts/gen_fixtures.py` 就能重建，
    也能一眼看出夹具的规格（64×64 / RGB / 纯色）。

用法：
    python scripts/gen_fixtures.py            # 生成（覆盖）
    python scripts/gen_fixtures.py --check    # 只校验夹具存在且规格正确

依赖：Pillow（缺失时如实报错，不伪造）
退出码：0 成功 / 1 校验失败 / 2 环境问题
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
TESTS = os.path.join(PACK, "tests")

SAMPLE = os.path.join(TESTS, "sample.png")
FAKE = os.path.join(TESTS, "not-a-png.png")
COLOR = (30, 58, 95)   # #1E3A5F，与品牌主色同族，便于肉眼核对
SIZE = (64, 64)


def gen() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("[fixtures] 缺少 Pillow，无法生成图片夹具。", file=sys.stderr)
        print("           安装：pip install Pillow", file=sys.stderr)
        return 2
    os.makedirs(TESTS, exist_ok=True)
    Image.new("RGB", SIZE, COLOR).save(SAMPLE)
    print(f"[fixtures] wrote {os.path.relpath(SAMPLE, PACK)}  {SIZE[0]}x{SIZE[1]} RGB {COLOR}")
    # 伪 PNG：故意写成文本，用于验证"格式伪装"能被拦
    with open(FAKE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("this is not a png, used to verify format detection\n")
    print(f"[fixtures] wrote {os.path.relpath(FAKE, PACK)}  (text, 用于反例)")
    return 0


def check() -> int:
    problems = []
    if not os.path.isfile(SAMPLE):
        problems.append(f"缺少 {os.path.relpath(SAMPLE, PACK)}")
    else:
        try:
            from PIL import Image
            with Image.open(SAMPLE) as im:
                if im.size != SIZE:
                    problems.append(f"sample.png 尺寸 {im.size} != {SIZE}")
                if im.mode != "RGB":
                    problems.append(f"sample.png 模式 {im.mode} != RGB")
        except ImportError:
            problems.append("缺少 Pillow，无法校验 sample.png")
        except Exception as exc:
            problems.append(f"sample.png 打不开：{exc}")
    if not os.path.isfile(FAKE):
        problems.append(f"缺少 {os.path.relpath(FAKE, PACK)}")

    if problems:
        print("[fixtures] CHECK FAIL")
        for p in problems:
            print("  -", p)
        return 1
    print(f"[fixtures] CHECK OK  sample={SIZE[0]}x{SIZE[1]} RGB  fake=text")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="图片夹具生成/校验")
    ap.add_argument("--check", action="store_true", help="只校验，不写盘")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    return check() if args.check else gen()


if __name__ == "__main__":
    raise SystemExit(main())
