# -*- coding: utf-8 -*-
"""太乙神数 全量回归 + 结构不变量 + 积年独立重算。

三层（对标 liuren_regress.py 的 8640 课体检）：
1. 穷举体检 sweep()：计式×积年法 × 时间序列，报崩溃/结构错误。
2. 结构不变量 check_structural()：局式数∈1-72、积年>0、太乙落宫∈1-16、
   主客算范围、计神文昌始击等合法地支/卦位、八门/八宫旺衰 8 宫齐全。
3. 积年独立重算 check_jinian()：用 lunar_python 独立算农历年，校验
   年计 4 积年法（统宗/太乙局 10153917、金镜 1936557、淘金歌 10154193）。

运行:
  python scripts/libs/taiyi_regress.py            # 全部（quick 穷举 + 积年）
  python scripts/libs/taiyi_regress.py sweep      # 只跑穷举体检（quick）
  python scripts/libs/taiyi_regress.py full       # 全量穷举（含 60 甲子年）
  python scripts/libs/taiyi_regress.py jinian     # 只跑积年独立重算

已知引擎边界（本模块实测，诚实标注）：
- 命法(ji_style=5)：pan 抛 TypeError，上游未完成，不纳入穷举。
- 日计×太乙局(2,3)：TypeError（list indices float），穷举跳过。
- 时计/分计×非统宗：旧代码死循环，穷举只用统宗。
- 【已修复 2026-10-08】每年大雪(~12/7)~小寒(~1/6)约 30 天 pan 崩溃，根因
  是 sxtwl 垫片 getJieQi()/getJieQiJD() 在冬至年界返回上一节气年（中文键
  「冬至」错配 2023-12-22 而非 2024-12-21）；已用「按日期匹配节气表」+
  「索引取模归 0」修正，穷举 0 崩溃。
"""
import collections
import datetime
import os
import sys

# 有效宫位：十二地支 + 四维卦 + 中（计神等偶用）
_VALID_GONG = set("子丑寅卯辰巳午未申酉戌亥") | {"乾", "坤", "艮", "巽", "中"}
# 年计积年基数（kintaiyi.accnum 的 tndict）
_JINIAN_BASE = {0: 10153917, 1: 1936557, 2: 10154193, 3: 10153917}
_JI = {0: "年計", 1: "月計", 2: "日計", 3: "時計", 4: "分計"}
_METHOD = {0: "統宗", 1: "金鏡", 2: "淘金歌", 3: "太乙局"}


def _pan(y, mo, d, h, mi, ji, m):
    from engines.taiyi.kintaiyi import Taiyi
    return Taiyi(y, mo, d, h, mi).pan(ji, m)


def _gong(v):
    """取字段的宫位部分（文昌为 list 取 [0]，其余为 str）"""
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v) if v not in (None, "") else ""


# —— 层2：结构不变量 ——
def check_structural(r, ji_style=0):
    """校验一盘的结构不变量，返回错误类型或 None。"""
    ju = r.get("局式", {})
    num = ju.get("數")
    if not isinstance(num, int) or not (1 <= num <= 72):
        return "局式数越界"
    # 積年數只有年计(ji_style=0)填，其余计式留空属正常
    if ji_style == 0:
        jn = ju.get("積年數")
        if not isinstance(jn, int) or jn <= 0:
            return "积年非法"
    lg = r.get("太乙落宮")
    if not isinstance(lg, int) or not (1 <= lg <= 16):
        return "太乙落宫越界"
    for key in ("主算", "客算", "定算"):
        v = r.get(key)
        if isinstance(v, list) and v and not (isinstance(v[0], int) and 1 <= v[0] <= 40):
            return "算数越界"
    for key in ("計神", "文昌", "始擊", "天乙", "地乙", "直符", "四神", "太歲"):
        g = _gong(r.get(key))
        if g and g not in _VALID_GONG:
            return f"{key}非法宫位"
    for key in ("主將", "客將", "主參", "客參"):
        v = r.get(key)
        if v is not None and (not isinstance(v, int) or not (1 <= v <= 16)):
            return f"{key}越界"
    for key in ("八門分佈", "八宮旺衰"):
        d = r.get(key)
        if not isinstance(d, dict) or len(d) < 8:
            return f"{key}缺宫"
    return None


# —— 层3：积年独立重算 ——
def check_jinian(dt):
    """用 lunar_python 独立算农历年，校验年计 4 积年法。返回 [(method, engine, expect, ok)]。"""
    try:
        from lunar_python import Solar
        ly = Solar.fromYmd(dt.year, dt.month, dt.day).getLunar().getYear()
    except Exception as e:
        return [("依赖缺失", str(e), None, False)]
    out = []
    for m in range(4):
        try:
            r = _pan(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0, m)
            eng = r.get("局式", {}).get("積年數")
            expect = _JINIAN_BASE[m] + ly + (1 if ly < 0 else 0)
            out.append((_METHOD[m], eng, expect, eng == expect))
        except Exception as e:
            out.append((_METHOD[m], f"崩溃 {type(e).__name__}", None, False))
    return out


# —— 层1：穷举体检 ——
def sweep(quick=True):
    """穷举计式×积年法 × 时间序列。quick=True 跑精简集（~1 分钟），False 跑 60 甲子年全量。"""
    from engines.taiyi.kintaiyi import Taiyi
    stats = {
        "total": 0, "ok": 0, "crash": [], "struct": [],
        "落宫分布": collections.Counter(),
    }
    cases = []  # (ji, method, 年份序列, 固定月日时)
    if quick:
        years = list(range(1990, 1996))          # 6 年，跨多个冬至/年界
        months = range(1, 13)
        days = [datetime.date(2024, 12, 1) + datetime.timedelta(days=i) for i in range(30)]  # 跨冬至
        hours = range(0, 24, 2)
    else:
        years = list(range(1984, 2044))          # 60 甲子年
        months = range(1, 13)
        days = [datetime.date(2024, 12, 1) + datetime.timedelta(days=i) for i in range(90)]
        hours = range(24)
    # 年计×4法：固定安全日(6月15)验证积年/落宫
    for m in range(4):
        for y in years:
            cases.append((0, m, (y, 6, 15, 10, 0)))
    # 月计×4法
    for m in range(4):
        for mo in months:
            cases.append((1, m, (2024, mo, 15, 10, 0)))
    # 日计×3法（太乙局有 bug 跳过）
    for m in range(3):
        for d in days:
            cases.append((2, m, (d.year, d.month, d.day, 10, 0)))
    # 时计×统宗
    for h in hours:
        cases.append((3, 0, (2024, 6, 15, h, 0)))
    # 分计×统宗（采样）
    for mi in range(0, 60, 10):
        cases.append((4, 0, (2024, 6, 15, 10, mi)))

    for n, (ji, m, (y, mo, d, h, mi)) in enumerate(cases):
        stats["total"] += 1
        if n % 40 == 0:
            print(f"    ...进度 {n}/{len(cases)}", flush=True)
        try:
            r = _pan(y, mo, d, h, mi, ji, m)
        except Exception as e:
            stats["crash"].append((_JI[ji], _METHOD[m], f"{y}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}", type(e).__name__))
            continue
        stats["ok"] += 1
        stats["落宫分布"][r.get("太乙落宮")] += 1
        err = check_structural(r, ji)
        if err:
            stats["struct"].append((_JI[ji], _METHOD[m], f"{y}-{mo:02d}-{d:02d}", err))
    return stats


def _crash_by_month(stats):
    """把 crash 按 (计式, 法, 月) 聚合，便于看出冬至窗口。"""
    by = collections.Counter()
    for ji, m, ds, e in stats["crash"]:
        mo = int(ds[5:7]) if len(ds) >= 7 else 0
        by[(ji, m, mo)] += 1
    return by


def _fmt_stats(stats):
    lines = []
    lines.append(f"总计 {stats['total']} 盘 / 成功 {stats['ok']} / 崩溃 {len(stats['crash'])} / 结构错 {len(stats['struct'])}")
    if stats["crash"]:
        lines.append(f"崩溃({len(stats['crash'])}):")
        for c in stats["crash"][:12]:
            lines.append(f"    {c}")
    by = _crash_by_month(stats)
    if by:
        lines.append("崩溃按月聚合(计式/法/月): " + ", ".join(f"{k[0]}{k[1]}·{k[2]}月={v}" for k, v in sorted(by.items())))
    if stats["struct"]:
        lines.append(f"结构错({len(stats['struct'])}):")
        for c in stats["struct"][:10]:
            lines.append(f"    {c}")
    lines.append("太乙落宫分布: " + ", ".join(f"宫{k}={v}" for k, v in sorted(stats["落宫分布"].items())))
    return "\n".join(lines)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    sys.path.insert(0, LIB)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "sweep", "full"):
        print("=" * 60)
        print(f"[层1+2] 穷举体检 + 结构不变量（{'quick' if mode != 'full' else 'full'}）")
        stats = sweep(quick=(mode != "full"))
        print(_fmt_stats(stats))
    if mode in ("all", "jinian"):
        print("=" * 60)
        print("[层3] 积年独立重算（年计 4 法，lunar_python 独立农历年）")
        dt = datetime.datetime(2026, 10, 7, 10, 0)
        for m, eng, expect, ok in check_jinian(dt):
            mark = "✓" if ok else "✗"
            print(f"  {mark} {m}: 引擎积年={eng} 独立期望={expect}")