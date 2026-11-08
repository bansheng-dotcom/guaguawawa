# -*- coding: utf-8 -*-
"""奇门独立评估者（对抗性第二意见 · 终审）

借鉴 mingli-skills「独立评估者」思路 + 本项目 `bazi_evaluator.py` / `adversarial.py` 的
「独立规则链重推」范式：不是 self-eval，而是用**另一条独立路径**从原始排盘重新推导
检测层（四害 + 五不遇时 + 伏吟反吟 + 内外盘 + 十干克应），再与主判 `rules.qimen_*`
逐维比对。发现矛盾即标「信号冲突，须复核」，缺失的检测（伏吟/反吟/内外盘等 rules 未实现）
单独列出，不冒充已判。

与主路径的差异（刻意为之，保证独立）：
  - 主路径 `judge/rules.py`：`qimen_menpo/jixing/rumu/wubuyushi/geju/...` 各函数，表在 rules 内。
  - 本模块：表**在此独立重写一份**（不 import rules 的表），从《奇门遁甲统宗》《秘笈大全》
    直接核对，杜绝「主判表抄错、自证自对」（对照 zhiwei BRIGHTNESS 曾抄错 148/168 处的教训）。

用法：
  python -m judge.qimen_evaluator 2026 10 7 10        # 单盘终审（太阳历 年 月 日 时）
  import qimen_evaluator as qe
  r = qe.cross_check(datetime(2026, 10, 7, 10))
"""
import sys
import os
import datetime
import re

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from engines.qimen import Qimen  # noqa: E402
from judge import rules  # noqa: E402
from judge import qimen_keying  # noqa: E402

# ============================ 独立真值表（不复用 rules 的表） ============================
# 八门五行 / 九宫五行 —— 出处《奇门遁甲统宗》门宫生克（休水/生土/伤杜木/景火/死土/惊开金）。
_MEN_WX = {"休": "水", "生": "土", "伤": "木", "杜": "木", "景": "火", "死": "土", "惊": "金", "开": "金"}
_GONG_WX = {"坎": "水", "坤": "土", "震": "木", "巽": "木", "中": "土", "乾": "金", "兑": "金", "艮": "土", "离": "火"}
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 六仪击刑落宫：六仪所带地支(甲子戊→子…甲寅癸→寅)与落宫地支相刑。
# 子卯刑→戊落震；戌未刑→己落坤；申寅刑→庚落艮；午午自刑→辛落离；辰辰自刑→壬落巽；寅巳刑→癸落巽。
_JIXING = {"戊": "震", "己": "坤", "庚": "艮", "辛": "离", "壬": "巽", "癸": "巽"}

# 三奇六仪入墓宫：乙木墓未(坤)、丙丁火墓戌(乾)、戊己土墓辰(巽)、庚辛金墓丑(艮)、壬癸水墓辰(巽)。
# ⚠ 壬癸水墓有流派分歧（阴水癸墓未），本表采《秘笈大全》通行口径（壬癸同墓辰/巽），与 rules 对齐。
_MU = {"乙": "坤", "丙": "乾", "丁": "乾", "戊": "巽", "己": "巽",
       "庚": "艮", "辛": "艮", "壬": "巽", "癸": "巽"}

# 五不遇时：时干克日干（阳克阳/阴克阴）。
_WUBUYUSHI = {"甲": "庚", "乙": "辛", "丙": "壬", "丁": "癸", "戊": "甲",
              "己": "乙", "庚": "丙", "辛": "丁", "壬": "戊", "癸": "己"}

# 内外盘：阳遁内盘 [坎1 艮8 震3 巽4]，阴遁内盘 [离9 坤2 兑7 乾6]。
_NEIPAN_YANG = {1, 8, 3, 4}
_NEIPAN_YIN = {9, 2, 7, 6}

_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_GUA_GONG = {"坎": 1, "坤": 2, "震": 3, "巽": 4, "中": 5, "乾": 6, "兌": 7, "艮": 8, "離": 9}
_GONG_GUA = {v: k for k, v in _GUA_GONG.items()}
_DUI = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4, 5: 5}


# ============================ 排盘解析（复用 qimen_regress 同款口径） ============================
def _parse_ju(paiju):
    """'陰遁九局中元' -> (阴阳, 局数) 或 None。"""
    if not paiju or "局" not in paiju:
        return None
    yy = "阴" if paiju[0] in "陰阴" else "阳"
    k = _CN_NUM.get(paiju[2])
    return (yy, k) if k is not None else None


def _parse_shiganzhi(ganzhi):
    """'丙午年丁酉月甲寅日己巳時' -> (日干支, 时干支) 或 None。"""
    m = re.search(r"([%s][%s])日([%s][%s])時$" % (_GAN, _ZHI, _GAN, _ZHI), ganzhi)
    return (m.group(1), m.group(2)) if m else None


def _norm(d):
    """繁体卦键 -> 宫数键。"""
    out = {}
    for k, v in (d or {}).items():
        g = _GUA_GONG.get(k)
        if g is not None:
            out[g] = v
    return out


# ============================ 独立检测层推导 ============================
def derive_detection(pan):
    """从原始排盘 pan（Qimen.pan(2) 结果）独立推导完整检测层。返回 dict。

    返回键：
      门迫 击刑 入墓 五不遇时 伏吟(星/门) 反吟(星/门) 内外盘 十干克应
    每项均标「独立判」的结果 + 是否命中；不依赖 rules.qimen_* 的任何表。
    """
    ju = _parse_ju(pan.get("排局"))
    dgz, hgz = _parse_shiganzhi(pan.get("干支")) or (None, None)
    yy = ju[0] if ju else None

    earth = _norm(pan.get("地盤"))      # {宫: 干}
    sky = _norm(pan.get("天盤"))        # {宫: 干}
    men = _norm(pan.get("門"))          # {宫: 门}
    # 神/星 此处不参与四害，仅作数据完整性校验用

    # —— 门迫：门五行克宫五行 ——
    menpo = {}
    for g, m in men.items():
        mw, gw = _MEN_WX.get(m), _GONG_WX.get(_GONG_GUA[g])
        menpo[g] = bool(mw and gw and _KE.get(mw) == gw)

    # —— 六仪击刑 / 入墓：天盘干落宫（六仪击刑以地盘六仪落宫论，入墓以天盘干落宫论） ——
    # 击刑看地盘六仪（戊己庚辛壬癸）所在宫是否为其击刑宫。
    jixing = {}
    for g, gan in earth.items():
        jixing[g] = (_JIXING.get(gan) == _GONG_GUA[g])
    rumu = {}
    for g, gan in sky.items():
        rumu[g] = (_MU.get(gan) == _GONG_GUA[g])

    # —— 五不遇时：时干克日干 ——
    wubu = bool(dgz and hgz and _WUBUYUSHI.get(dgz[0]) == hgz[0])

    # —— 伏吟 / 反吟：天盘干 vs 地盘干 ——
    xing_fuyin = all(sky.get(g) == earth.get(g) for g in earth if g != 5)
    xing_fanyin = all(sky.get(g) == earth.get(_DUI[g]) for g in earth if g != 5)
    # 门伏吟/反吟：门是否在原宫/对宫（原门表：休坎/生艮/伤震/杜巽/景离/死坤/惊兑/开乾）
    _MEN_ORIG = {1: "休", 8: "生", 3: "伤", 4: "杜", 9: "景", 2: "死", 7: "惊", 6: "开"}
    men_fuyin = all(men.get(g) == _MEN_ORIG.get(g) for g in _MEN_ORIG)
    men_fanyin = all(men.get(g) == _MEN_ORIG.get(_DUI[g]) for g in _MEN_ORIG if _DUI[g] in _MEN_ORIG)

    # —— 内外盘 ——
    neipan = _NEIPAN_YANG if yy == "阳" else _NEIPAN_YIN

    # —— 十干克应（用 qimen_keying 共享数据，但对拍 rules.qimen_geju 的包装） ——
    keying = {}
    for g, s in sky.items():
        d = earth.get(g)
        if d:
            keying[g] = qimen_keying.lookup(s, d).get("格局")

    return {
        "局": ju, "日干支": dgz, "时干支": hgz,
        "门迫": menpo, "击刑": jixing, "入墓": rumu,
        "五不遇时": wubu,
        "星伏吟": xing_fuyin, "星反吟": xing_fanyin,
        "门伏吟": men_fuyin, "门反吟": men_fanyin,
        "内盘": neipan, "十干克应": keying,
    }


def _r_ji(r):
    """rules._r 返回 dict 的『judgment』字段（主判口径）。"""
    if isinstance(r, dict):
        return r.get("judgment")
    return getattr(r, "judgment", None)


# ============================ 交叉终审 ============================
def cross_check(pan):
    """独立检测层 vs rules.qimen_* 逐维比对。返回 {维度比对[], 缺失检测[], verdict}。"""
    det = derive_detection(pan)
    cmp = []

    # 门迫：逐宫比对
    for g, indep_hit in det["门迫"].items():
        gong = _GONG_GUA[g]
        men = _norm(pan.get("門")).get(g)
        if not men:
            continue
        main_ji = _r_ji(rules.qimen_menpo(men, gong))
        main_hit = main_ji == "凶"
        if indep_hit != main_hit:
            cmp.append(("门迫", g, f"{men}门落{gong}宫", indep_hit, main_hit))

    # 击刑：地盘六仪逐宫
    for g, indep_hit in det["击刑"].items():
        gan = _norm(pan.get("地盤")).get(g)
        gong = _GONG_GUA[g]
        if not gan or gan not in "戊己庚辛壬癸":
            continue
        main_ji = _r_ji(rules.qimen_jixing(gan, gong))
        main_hit = main_ji == "凶"
        if indep_hit != main_hit:
            cmp.append(("击刑", g, f"{gan}落{gong}宫", indep_hit, main_hit))

    # 入墓：天盘干逐宫
    for g, indep_hit in det["入墓"].items():
        gan = _norm(pan.get("天盤")).get(g)
        gong = _GONG_GUA[g]
        if not gan:
            continue
        main_ji = _r_ji(rules.qimen_rumu(gan, gong))
        main_hit = main_ji == "凶"
        if indep_hit != main_hit:
            cmp.append(("入墓", g, f"{gan}落{gong}宫", indep_hit, main_hit))

    # 五不遇时
    if det["日干支"] and det["时干支"]:
        main_ji = _r_ji(rules.qimen_wubuyushi(det["日干支"][0], det["时干支"][0]))
        main_hit = main_ji == "凶"
        if det["五不遇时"] != main_hit:
            cmp.append(("五不遇时", None, f"{det['日干支']}日{det['时干支']}时", det["五不遇时"], main_hit))

    # 十干克应：逐宫比对「是否命中具名格局」（独立 lookup 格局名非 None == 主判非「非具名」）
    for g, name in det["十干克应"].items():
        sky_g = _norm(pan.get("天盤")).get(g)
        earth_g = _norm(pan.get("地盤")).get(g)
        if not sky_g or not earth_g:
            continue
        main_r = rules.qimen_geju(sky_g, earth_g)
        main_is_named = False
        if isinstance(main_r, dict):
            main_is_named = "非具名" not in str(main_r.get("basis", ""))
        if (name is not None) != main_is_named:
            cmp.append(("十干克应", g, f"天{sky_g}地{earth_g}", name, main_is_named))

    # 缺失检测（rules 未实现的维度，独立判已提供）
    missing = ["星伏吟", "星反吟", "门伏吟", "门反吟", "内外盘"]

    verdict = "信号冲突，须复核" if cmp else "一致（独立检测层与 rules 主判无矛盾）"
    return {
        "检测层": det, "比对": cmp, "缺失检测": missing,
        "verdict": verdict,
        "冲突数": len(cmp),
    }


# ============================ main ============================
def main():
    a = [int(x) for x in sys.argv[1:5]]
    if len(a) < 4:
        print(__doc__)
        return
    y, mo, d, h = a
    pan = Qimen(y, mo, d, h, 0).pan(2)
    r = cross_check(pan)
    det = r["检测层"]
    ju = det["局"]
    print(f"[奇门独立评估者·终审] {y}-{mo:02d}-{d:02d} {h:02d}:00  {ju[0] if ju else '?'}遁{ju[1] if ju else '?'}局")
    print(f"  日{det['日干支']} 时{det['时干支']}")
    print(f"  独立检测层：五不遇时={det['五不遇时']} 星伏吟={det['星伏吟']} 星反吟={det['星反吟']} "
          f"门伏吟={det['门伏吟']} 门反吟={det['门反吟']} 内盘={sorted(det['内盘'])}")
    print(f"  门迫宫={[g for g, v in det['门迫'].items() if v]} 击刑宫={[g for g, v in det['击刑'].items() if v]} "
          f"入墓宫={[g for g, v in det['入墓'].items() if v]}")
    if r["比对"]:
        for k, g, ctx, ind, main in r["比对"]:
            print(f"  ⚠ {k}宫{g}（{ctx}）：独立判{ind} ≠ 主判{main}")
    print(f"  缺失检测（rules 未实现，独立判已补）：{'、'.join(r['缺失检测'])}")
    print(f"  verdict: {r['verdict']}")


if __name__ == "__main__":
    main()
