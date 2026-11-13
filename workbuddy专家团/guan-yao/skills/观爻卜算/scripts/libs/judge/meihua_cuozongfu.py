# -*- coding: utf-8 -*-
"""梅花「错综复三观」+ 会合参证 —— 补齐射覆/测物的「错/综/复」三观。

背景：梅花射覆现有「本卦 + 互卦 + 变卦」多象合成（shefu_portrait.portrait_meihua_pan），
但缺易学「错/综/复」三观——同一卦从三个变换视角看，会合互相参证，能补出「取象不全」
漏掉的物象线索（对标 henrryjoke/shefu 的「反对体用 + 变复求义」方法论，术语归一到梅花）。

三观定义（操作纯函数见 `gua.py`）：
  - 错卦（对体）：六爻阴阳全变 —— 同一气的呼吸两端（阴阳对待）。
  - 综卦（反体）：卦画上下颠倒 —— 同一事的主客两面（视角翻转）。
  - 复卦（伏）：  上体/下体各自翻为对体（偏变）—— 外部/内部翻转后的偏向。
再加已存在的 互卦（二三四/三四五）与 变卦（动爻翻转），合成「六观会合」。

反对形态（玄明《反对篇》三类，deterministic 可回归）：
  - 自反对体（综=自身，8 卦）：乾坤坎离颐大过中孚小过 —— 无主客、自身即全体。
  - 反=对（综=错，8 卦）：泰否随蛊渐归妹既济未济 —— 时位合一、翻转即全变。
  - 标准四卦组（其余 48 卦）：反对交织。

用法：
  python -m judge.meihua_cuozongfu 3 8 2   # 上下卦数 + 动爻（上卦3下卦8，动2爻）
  import meihua_cuozongfu as mcz
  r = mcz.hecan(3, 8, 2)
"""
import sys
import os

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from gua import GUA, WX, cuo, zong, fu, liu_of, name_of, tri_to_num, hexagram_name  # noqa: E402


def _parts(liu):
    """六爻列表 -> (上卦数, 下卦数)。"""
    xia = tri_to_num(tuple(liu[:3]))
    shang = tri_to_num(tuple(liu[3:]))
    return shang, xia


def _view(liu):
    """六爻列表 -> {卦名, 上卦, 下卦, 上卦五行, 下卦五行}。"""
    shang, xia = _parts(liu)
    return {
        "卦名": name_of(liu),
        "上卦": GUA[shang], "下卦": GUA[xia],
        "上五行": WX[shang], "下五行": WX[xia],
    }


def six_views(shang, xia, dong):
    """六观展开：本/错/综/复上/复下/互/变。返回 {观名: view dict}（观名顺序=会合顺序）。"""
    liu = liu_of(shang, xia)
    hu_xia = tri_to_num(tuple(liu[1:4]))     # 下互=二三四
    hu_shang = tri_to_num(tuple(liu[2:5]))   # 上互=三四五
    liu2 = list(liu)
    liu2[dong - 1] ^= 1                       # 变卦=动爻翻转

    return {
        "本卦": _view(liu),
        "错卦": _view(cuo(liu)),
        "综卦": _view(zong(liu)),
        "复卦上(上伏)": _view(fu(liu, "上")),
        "复卦下(下伏)": _view(fu(liu, "下")),
        "互卦": {"卦名": hexagram_name(hu_shang, hu_xia), "上卦": GUA[hu_shang], "下卦": GUA[hu_xia],
                 "上五行": WX[hu_shang], "下五行": WX[hu_xia]},
        "变卦": _view(liu2),
    }


def fan_dui_type(liu):
    """反对形态分类：自反对体 / 反=对 / 标准四卦组。返回 (分类, 说明)。"""
    ben = name_of(liu)
    cuo_n = name_of(cuo(liu))
    zong_n = name_of(zong(liu))
    if zong_n == ben:
        return "自反对体", "综卦即自身，无主客之分，自身即是全体"
    if zong_n == cuo_n:
        return "反=对", "综卦=错卦，时位合一，主客翻转即阴阳全反"
    return "标准四卦组", "反对交织：本卦↔综卦(主客·时)、本卦↔错卦(对待·位)"


def hecan(shang, xia, dong):
    """会合参证：六观 + 反对形态 + 体气同气统计。返回 dict（可回归）。"""
    liu = liu_of(shang, xia)
    yong, ti = (xia, shang) if dong <= 3 else (shang, xia)
    ti_wx = WX[ti]

    views = six_views(shang, xia, dong)
    fd_kind, fd_note = fan_dui_type(liu)

    # 体气同气统计：六观（除本卦）中，上卦或下卦五行 == 体卦五行的观。
    tong_qi = []
    for name, v in views.items():
        if name == "本卦":
            continue
        if ti_wx in (v["上五行"], v["下五行"]):
            tong_qi.append(name)

    # 参证结论（deterministic，与 tianzhi-core「断语→判定条件」同思路：能判的判）
    if len(tong_qi) >= 3:
        canzheng = "体气多面印证（错/综/复/互/变中多观与体卦同气，画像较稳）"
    elif len(tong_qi) == 0:
        canzheng = "体气无旁证（诸观皆异气，宜参变卦落处、不以单观定物）"
    else:
        canzheng = f"体气部分印证（{len(tong_qi)} 观同气，画像有据但勿过度收敛）"

    return {
        "本卦": views["本卦"]["卦名"],
        "体卦": GUA[ti], "体五行": ti_wx,
        "用卦": GUA[yong], "用五行": WX[yong],
        "六观": views,
        "反对形态": fd_kind,
        "反对说明": fd_note,
        "体气同气观": tong_qi,
        "参证结论": canzheng,
    }


def _fmt(r):
    lines = [f"【错综复三观 · 会合参证】本卦 {r['本卦']}  体{r['体卦']}({r['体五行']}) 用{r['用卦']}({r['用五行']})"]
    lines.append(f"  反对形态：{r['反对形态']} —— {r['反对说明']}")
    for name, v in r["六观"].items():
        mark = " ◆体气同气" if (name != "本卦" and r["体五行"] in (v["上五行"], v["下五行"])) else ""
        lines.append(f"  {name:12s} {v['卦名']:6s}（{v['上卦']}上{v['上五行']} / {v['下卦']}下{v['下五行']}）{mark}")
    lines.append(f"  参证结论：{r['参证结论']}")
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__)
        return
    shang, xia, dong = int(a[0]), int(a[1]), int(a[2])
    print(_fmt(hecan(shang, xia, dong)))


if __name__ == "__main__":
    main()
