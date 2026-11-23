# -*- coding: utf-8 -*-
"""scripts/scan_business_terms.py —— 扫 core/ 里的业务线硬编码（防复发）。

规则：通用模块不许内置具体业务词（地名/品牌/行业品类）。
本脚本把命中按「代码赋值 vs 注释说明」分开：
  - CODE 命中 → 需要清理（除非在允许清单里）；
  - COMMENT 命中 → 历史说明，保留。

用法：
  python scripts/scan_business_terms.py            # 报告
  python scripts/scan_business_terms.py --check    # 有 CODE 命中则退出码 1
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")

# 业务词表：出现即视为「历史项目内容」
TERMS = [
    # 品牌 / IP / 行业
    "泡泡玛特", "手办", "潮玩", "盲盒", "手串", "女装", "母婴", "宠物",
    "零食", "主粮", "尿裤", "纸尿裤", "奶粉", "辅食", "童装", "牙膏", "洗发水",
    # 地名
    "内蒙古", "呼和浩特", "包头", "鄂尔多斯", "赤峰",
    "朝阳", "海淀", "丰台", "通州", "昌平", "大兴", "顺义", "石景山",
]

# 允许清单：这些文件里的业务词是数据/字典的合法内容，不是历史硬编码
ALLOW_FILES = {
    "domain_pack.py",              # 行业包关键词表（合法）
    "chart_renderers_ext.py",      # 中国地图坐标（地图数据）
    "dataset.py",                  # 图表示例数据（待迁出 core，另案处理）
}


def scan():
    hits = []
    for dirpath, dirnames, filenames in os.walk(CORE):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), CORE).replace("\\", "/")
            if "samples_data" in rel:   # 样例数据的指定隔离区，不在此扫描
                continue
            try:
                lines = open(os.path.join(dirpath, fn), encoding="utf-8",
                             errors="replace").read().splitlines()
            except OSError:
                continue
            for i, ln in enumerate(lines, 1):
                for t in TERMS:
                    if t in ln:
                        kind = "COMMENT" if ln.strip().startswith("#") else "CODE"
                        hits.append((rel, i, kind, t, ln.strip()[:110]))
                        break
    return hits


def _baseline_path():
    return os.path.join(ROOT, "configs", "business_terms_baseline.json")


def _whitelist_path():
    return os.path.join(ROOT, "configs", "core_files.json")


def _core_files():
    """core/ 下全部 .py（相对路径，正斜杠），samples_data 除外。"""
    out = []
    for dp, dns, fns in os.walk(CORE):
        dns[:] = [d for d in dns if d not in ("__pycache__",)]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), CORE).replace("\\", "/")
            if "samples_data" in rel:
                continue
            out.append(rel)
    return sorted(out)


def _scan_new_files():
    """白名单外的新文件——这才是拦「新业务以新模块进 core」的唯一手段。

    业务词黑名单只能认已知词；新业务一定带来新词。所以对 core/ 加文件白名单：
    新增一个模块就要显式改 configs/core_files.json（等于强制人工过目一次）。
    """
    cur = set(_core_files())
    if not os.path.isfile(_whitelist_path()):
        return sorted(cur), set(cur)   # 没有白名单时只报告，不拦
    try:
        import json as _json
        allow = set(_json.loads(open(_whitelist_path(), encoding="utf-8").read()) or [])
    except Exception:  # noqa: BLE001
        return sorted(cur), set(cur)
    return sorted(cur - allow), allow


def _counts(code_hits):
    from collections import Counter
    return dict(Counter(h[0] for h in code_hits))


def main() -> int:
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="有新增 CODE 命中（超过基线）则退出码 1")
    ap.add_argument("--write-baseline", action="store_true",
                    help="把当前命中写成基线（棘轮只拦新增）")
    ap.add_argument("--write-whitelist", action="store_true",
                    help="把 core/ 当前文件列表写进白名单（新增模块须显式加白）")
    args = ap.parse_args()

    hits = scan()
    code_hits = [h for h in hits if h[2] == "CODE"
                 and os.path.basename(h[0]) not in ALLOW_FILES]
    print("命中 %d（CODE %d / COMMENT %d），需清理 %d" % (
        len(hits), sum(1 for h in hits if h[2] == "CODE"),
        sum(1 for h in hits if h[2] == "COMMENT"), len(code_hits)))

    cur = _counts(code_hits)
    if args.write_baseline:
        os.makedirs(os.path.dirname(_baseline_path()), exist_ok=True)
        open(_baseline_path(), "w", encoding="utf-8").write(
            json.dumps(cur, ensure_ascii=False, indent=1, sort_keys=True))
        print("baseline 已写入:", _baseline_path())
        return 0

    base = {}
    if os.path.isfile(_baseline_path()):
        try:
            base = json.loads(open(_baseline_path(), encoding="utf-8").read()) or {}
        except Exception:  # noqa: BLE001
            base = {}
    # 只拦"新增"：某文件命中数超过基线即为新债；低于基线算改善，不拦
    new_debt = {f: (n, base.get(f, 0)) for f, n in cur.items()
                if n > base.get(f, 0)}
    for rel, i, kind, t, txt in code_hits:
        print("  %s:%d [%s] %s" % (rel, i, t, txt))
    if base:
        print("基线对比：新增文件 %d 个（低于基线=改善）" % len(new_debt))
        for f, (n, b) in new_debt.items():
            print("   NEW %s: %d > baseline %d" % (f, n, b))
    elif os.path.isfile(_baseline_path()):
        print("基线为空：当前 0 需清理（任何新增都会被拦）")
    else:
        print("提示：没有基线，先跑 --write-baseline 建立棘轮")

    # core/ 文件白名单：新增模块必须显式加白（防「新业务以新模块进 core」）
    new_files, allow = _scan_new_files()
    if args.write_whitelist:
        os.makedirs(os.path.dirname(_whitelist_path()), exist_ok=True)
        open(_whitelist_path(), "w", encoding="utf-8").write(
            json.dumps(_core_files(), ensure_ascii=False, indent=1))
        print("白名单已写入:", _whitelist_path(), "|", len(_core_files()), "个文件")
        return 0
    if allow and new_files:
        print("core/ 新增未加白文件 %d 个（须改 configs/core_files.json 过目）:" % len(new_files))
        for f in new_files:
            print("   NEW FILE", f)
    else:
        print("core/ 文件白名单：无新增（%d 个文件在册）" % len(allow))

    return 1 if (args.check and (new_debt or (allow and new_files))) else 0


if __name__ == "__main__":
    raise SystemExit(main())
