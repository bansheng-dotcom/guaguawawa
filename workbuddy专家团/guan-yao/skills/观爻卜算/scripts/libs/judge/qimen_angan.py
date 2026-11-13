# -*- coding: utf-8 -*-
"""奇门遁甲暗干（飞干）排盘。

暗干 = 值使门所暗藏之干，古法「值使加时干、阳顺阴逆飞九宫」（《御定奇门宝鉴》古法，
《奇门遁甲秘笈大全》·奇门占事称「飞干」）：
  1. 以值使门落宫为起点，把「时干」（甲遁戊）写在该宫；
  2. 余干按六仪三奇环序「戊己庚辛壬癸丁丙乙」阳遁顺飞、阴遁逆飞洛书九宫（含中5）。
特例：值使门落宫地盘干 == 时干时，时干入中5宫再飞布（低置信度，流派有差异）。

实例（阴遁二局，值使落离九，时干己）：阴遁逆排 →
  离九己 艮八庚 兑七辛 乾六壬 中五癸 巽四丁 震三丙 坤二乙 坎一戊。

用法：
  from judge.qimen_angan import angan_pan
  pan = angan_pan("己", 9, "阴")          # {宫数: 暗干} 九宫
  pan = angan_pan("己", 9, "阴", dipan)   # 带地盘，启用特例判定
"""
_ANGAN_SEQ = "戊己庚辛壬癸丁丙乙"   # 六仪三奇环序
_GAN_YI = {"甲": "戊"}              # 甲遁戊
_GUA_GONG = {"坎": 1, "坤": 2, "震": 3, "巽": 4, "中": 5, "乾": 6, "兌": 7, "艮": 8, "離": 9}


def angan_from_sj(sj):
    """从引擎时家盘 dict 解析并计算暗干盘。返回 (pan {宫数:干}, 时干) 或 None。
    sj 需含 干支/排局/值符值使/地盤 字段。"""
    import re
    gz = sj.get("干支", "")
    m = re.search(r"([甲乙丙丁戊己庚辛壬癸])[子丑寅卯辰巳午未申酉戌亥]時$", gz)
    shi_gan = m.group(1) if m else None
    paiju = sj.get("排局", "")
    yinyang = "阴" if paiju[:1] in "陰阴" else "阳"
    zfzs = sj.get("值符值使") or {}
    zhishi_gua = (zfzs.get("值使門宮") or ["", ""])[1]
    zhishi_gong = _GUA_GONG.get(zhishi_gua)
    dipan = sj.get("地盤") or {}
    dipan_num = {_GUA_GONG[k]: v for k, v in dipan.items() if k in _GUA_GONG}
    if not shi_gan or zhishi_gong is None:
        return None
    return angan_pan(shi_gan, zhishi_gong, yinyang, dipan_num), shi_gan


def _seq_from(shi_gan):
    """从时干起，按六仪三奇环序取 9 干。时干甲遁戊。"""
    yi = _GAN_YI.get(shi_gan, shi_gan)
    idx = _ANGAN_SEQ.index(yi)
    return [_ANGAN_SEQ[(idx + i) % 9] for i in range(9)]


def _loushu_order(yinyang):
    """洛书宫数序（含中5）：阳遁顺飞 1..9，阴遁逆飞 9..1。"""
    return list(range(1, 10)) if yinyang == "阳" else list(range(9, 0, -1))


def angan_pan(shi_gan, zhishi_gong, yinyang, dipan=None):
    """暗干飞布。返回 {宫数: 暗干} 九宫（1坎 2坤 3震 4巽 5中 6乾 7兑 8艮 9离）。

    zhishi_gong: 值使门落宫（宫数 1-9）。
    dipan: {宫数: 地盘干}，用于特例（值使门落宫地盘干==时干 → 时干入中5）。
    """
    yi = _GAN_YI.get(shi_gan, shi_gan)
    seq = _seq_from(yi)               # 9 干，seq[0]=时干
    order = _loushu_order(yinyang)    # 9 宫序
    i = order.index(zhishi_gong)
    gongs = order[i:] + order[:i]     # 从值使宫起的宫序

    # 特例：值使门落宫地盘干 == 时干 → 时干入中5，余干从值使宫起飞布（跳过中5）
    if dipan and dipan.get(zhishi_gong) == yi:
        pan = {5: seq[0]}
        rest = [g for g in gongs if g != 5]
        for j, gan in enumerate(seq[1:]):
            pan[rest[j]] = gan
        return pan

    # 正常：时干加值使门落宫，余干飞布
    return dict(zip(gongs, seq))


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # 自检：阴遁二局 值使落离9 时干己 → 离9己 艮8庚 兑7辛 乾6壬 中5癸 巽4丁 震3丙 坤2乙 坎1戊
    _GUA = {1: "坎", 2: "坤", 3: "震", 4: "巽", 5: "中", 6: "乾", 7: "兑", 8: "艮", 9: "离"}
    pan = angan_pan("己", 9, "阴")
    print("阴遁二局 值使落离9 时干己 暗干：")
    for g in (9, 8, 7, 6, 5, 4, 3, 2, 1):
        print(f"  {_GUA[g]}{g}宫={pan[g]}", end="")
    print()
    assert pan == {9: "己", 8: "庚", 7: "辛", 6: "壬", 5: "癸", 4: "丁", 3: "丙", 2: "乙", 1: "戊"}, pan
    print("自检通过 ✓")