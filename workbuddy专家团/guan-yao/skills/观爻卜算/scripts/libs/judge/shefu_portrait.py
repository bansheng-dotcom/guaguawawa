# -*- coding: utf-8 -*-
"""射覆·特征画像引擎（借鉴 henrryjoke/shefu）——从卦象/课式信号生成「特征画像」。

原则：「AI 是画师不是鉴定师——刻画特征，命名权交给玩家。」

用法:
  python libs/shefu_portrait.py liuren 青龙 朱雀 天后     # 大六壬：传天将名
  python libs/shefu_portrait.py meihua 离 兑             # 梅花：传八卦名
  python libs/shefu_portrait.py update '{"命中":[...],"错误":[...]}'  # 后验回填

核心函数:
  portrait(signals)      -> 特征画像（6维度 × 置信度🟢🟡🔴）
  portrait_liuren(list)  -> 大六壬信号 -> 画像
  portrait_meihua(list)  -> 梅花信号 -> 画像
  update_kb(round_json)  -> 回填 类象库.json 的 confidence + validations
"""
import os
import json
import sys

from gua import GUA64, GUA

HERE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(HERE, "..", "..", "..", "data", "类象库.json")

_DIMS = ["颜色", "材质", "形态", "功能", "结构", "性质"]

# 五行盲区：盘面缺某五行 → 对该五行所主物件「分辨力低」（缺≠非，见射覆特征画像.md §6.4）
_WX_ALL = ["金", "木", "水", "火", "土"]
_WX_BLIND = {
    "金": "金属/刀剪/利器",
    "木": "木竹/织物/绳线",
    "水": "液体/暗昧/污秽",
    "火": "发光发热/红赤/点火",
    "土": "陶瓦/容器/玉石/泥土",
}
# 卦盲区（梅花）：六观缺某卦 → 缺该卦主类象
_GUA_ALL = ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]
_GUA_BLIND = {
    "乾": "金属圆/玉/贵重",
    "坤": "布帛/五谷/瓦器/方柔",
    "震": "震动/发声/草木/车辆",
    "巽": "木竹/风/绳直",
    "坎": "水/液体/陷",
    "离": "火/光明/中空/电",
    "艮": "山/止/果蓏/手",
    "兑": "金刃/缺器/刀剪/带口工具",
}


def _load():
    with open(KB_PATH, encoding="utf-8") as f:
        return json.load(f)


def _conf_level(c):
    if c >= 0.7:
        return "高"
    if c >= 0.4:
        return "中"
    return "低"


_CONTEXT_DIMS = {
    "物性": ["颜色", "材质", "形态", "结构", "形状", "物类", "数目"],
    "功能": ["功能", "性质", "人物", "动物"],
    "方位": ["方位"],
}


def portrait(signals, context=None):
    """signals: [(名称, 权重), ...]（天将名/八卦名/地支名）。返回特征画像 dict。

    维度动态聚合：天将/八卦用 6 物性维度，地支用 五行/方位/物类/数目/颜色，
    混传时按实际命中的维度并集输出。context 可选：物性/功能/方位，按语境筛维度。"""
    kb = _load()
    tables = (kb.get("天将", {}), kb.get("八卦", {}), kb.get("地支", {}), kb.get("天干", {}))
    agg = {}  # dim -> {value: score}
    used = 0
    for name, w in signals:
        node = None
        for t in tables:
            if name in t:
                node = t[name]
                break
        if not node:
            continue
        used += 1
        for dim, vals in node.get("dimensions", {}).items():
            for v in vals:
                score = v["confidence"] * w
                d = agg.setdefault(dim, {})
                d[v["value"]] = max(d.get(v["value"], 0.0), score)
    out = {}
    for dim in sorted(agg):
        items = sorted(agg[dim].items(), key=lambda x: -x[1])
        out[dim] = [(val, _conf_level(sc), round(sc, 2)) for val, sc in items[:2]]
    if context in _CONTEXT_DIMS:
        out = {k: v for k, v in out.items() if k in _CONTEXT_DIMS[context]}
    return {"signals": [s[0] for s in signals], "used": used, "dimensions": out,
            "blind": blind_spots(signals)}


def portrait_liuren(tianjiang_list):
    """大六壬：天将名列表（初传在前、权重高）。"""
    w = {tianjiang_list[0]: 1.0} if tianjiang_list else {}
    sig = []
    for i, t in enumerate(tianjiang_list):
        weight = 1.0 if i == 0 else 0.6
        sig.append((t, weight))
    return portrait(sig)


def portrait_meihua(gua_list):
    """梅花：八卦名列表（用卦在前、权重高）。"""
    sig = [(g, 1.0 if i == 0 else 0.7) for i, g in enumerate(gua_list)]
    return portrait(sig)


_ZHI = "子丑寅卯辰巳午未申酉戌亥"


def _zhi_from_name(name):
    """从「天罡（辰）」提取地支「辰」；纯地支原样返回；无则 None。"""
    if not name:
        return None
    for ch in name:
        if ch in _ZHI:
            return ch
    return None


def portrait_jinkoujue(four):
    """金口诀射覆：四位多象合成（贵神天将 + 将神地支 + 地分地支）。
    four: jinkoujue.cast() 的 r['四位'] dict（人元/贵神/将神/地分）。
    权重：贵神 1.0 > 地分 0.9 > 将神 0.7（用爻细化加权留待后续）。"""
    sig = []
    gs = (four or {}).get("贵神", {}).get("名")
    if gs:
        sig.append((gs, 1.0))
    jz = _zhi_from_name((four or {}).get("将神", {}).get("名", ""))
    if jz:
        sig.append((jz, 0.7))
    df = (four or {}).get("地分", {}).get("符号")
    if df:
        sig.append((df, 0.9))
    ry = (four or {}).get("人元", {}).get("符号")
    if ry:
        sig.append((ry, 0.6))
    return portrait(sig)


_TIANJIANG_ABBR = {
    "贵": "贵人", "蛇": "螣蛇", "朱": "朱雀", "合": "六合",
    "勾": "勾陈", "龙": "青龙", "空": "天空", "虎": "白虎",
    "常": "太常", "玄": "玄武", "阴": "太阴", "后": "天后",
}

_NAME_TO_GUA = {name: (shang, xia) for (shang, xia), name in GUA64.items()}


def portrait_liuren_sanchuan(sanchuan):
    """大六壬射覆：三传地支 + 天将多象合成（天将缩写→全名）。
    sanchuan: liuren.cast() 的 r['三傳'] dict，每传 [地支, 天将缩写, 六亲, ...]。"""
    sig = []
    for i, key in enumerate(("初傳", "中傳", "末傳")):
        chuan = sanchuan.get(key) if sanchuan else None
        if not chuan:
            continue
        w = 1.0 if i == 0 else (0.7 if i == 1 else 0.5)
        if chuan[0]:
            sig.append((chuan[0], w))
        if len(chuan) > 1 and chuan[1]:
            sig.append((_TIANJIANG_ABBR.get(chuan[1], chuan[1]), w))
    return portrait(sig)


def portrait_meihua_pan(r):
    """梅花射覆：本/互/变 + 错/综/复 六观多象合成。
    r: meihua.cast() 的返回 dict（含 体卦/用卦/上卦/下卦/互卦/变卦/错卦/综卦/复卦上/复卦下）。"""
    sig = []
    seen = set()

    def add(g, w):
        if g and g not in seen:
            seen.add(g)
            sig.append((g, w))

    add(r.get("体卦"), 1.0)
    add(r.get("用卦"), 0.8)
    add(r.get("上卦"), 0.6)
    add(r.get("下卦"), 0.6)
    # 六观会合：互/变/错/综/复 各取上下卦纳入（权重：体用 > 变 > 互/错/综 > 复）
    for name, w in (("互卦", 0.5), ("变卦", 0.7), ("错卦", 0.5), ("综卦", 0.5),
                    ("复卦上", 0.4), ("复卦下", 0.4)):
        pair = _NAME_TO_GUA.get(r.get(name))
        if pair:
            add(GUA[pair[0]], w)
            add(GUA[pair[1]], w)
    return portrait(sig)


_LAIYI = {
    ("木", "土"): "口舌兼狱讼", ("土", "木"): "口舌兼狱讼",
    ("火", "金"): "祸事", ("金", "火"): "祸事",
    ("水", "土"): "田宅、人有死", ("土", "水"): "田宅、人有死",
    ("水", "火"): "妇女残", ("火", "水"): "妇女残",
}


def jinkoujue_laiyi(renyuan_wx, jiang_wx):
    """金口诀占来意：人元干与将神五行组合断来意（《六壬神课金口诀古本》·占来意歌）。
    返回 {来意, 出处}。"""
    key = (renyuan_wx, jiang_wx)
    if key in _LAIYI:
        return {"来意": _LAIYI[key], "出处": "《六壬神课金口诀古本》·占来意歌"}
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    if sheng.get(renyuan_wx) == jiang_wx:
        return {"来意": "人元生将，主喜事求谋", "出处": "《六壬神课金口诀古本》·占来意歌·四位相生诸事喜"}
    if sheng.get(jiang_wx) == renyuan_wx:
        return {"来意": "将生人元，主贵人助力、诸事喜", "出处": "《六壬神课金口诀古本》·占来意歌·四位相生诸事喜"}
    if renyuan_wx == jiang_wx:
        return {"来意": "干将比和，谋事平和", "出处": "《六壬神课金口诀古本》·占来意歌"}
    return {"来意": "生克未入歌诀，参四位总断", "出处": "《六壬神课金口诀古本》·占来意歌"}


def _wuxing_of(name):
    """跨节点查五行：天将/八卦取顶层「五行」，地支/天干取 dimensions 五行。"""
    kb = _load()
    for kind in ("天将", "八卦", "地支", "天干"):
        node = kb.get(kind, {}).get(name)
        if not node:
            continue
        wx = node.get("五行")
        if wx:
            return wx
        vals = node.get("dimensions", {}).get("五行", [])
        if vals:
            return vals[0]["value"]
    return None


def blind_spots(signals):
    """盲区标注：盘面信号「缺什么」→ 对哪类物件分辨力低。

    两类盲区：
    - 五行盲区：signals 五行并集 vs 金木水火土全集，缺者标「对{所主物类}分辨力低」。
    - 卦盲区：仅当 signals 含八卦名时，六观卦并集 vs 八卦全集，缺者标「缺该卦主类象」。

    铁律（缺X≠非X）：盲区只表「本盘对该类分辨力低（无该类信号可依）」，绝不推出
    「物件非该类」——起盘采样有限，缺＝没起出，不是不存在（2026-10-18 指甲刀教训：
    金口诀四位无金、梅花六观无兑，实物却是铁指甲刀）。"""
    present_wx = set()
    present_gua = set()
    for name, _w in signals:
        wx = _wuxing_of(name)
        if wx:
            present_wx.add(wx)
        if name in _GUA_ALL:
            present_gua.add(name)
    out = {}
    miss_wx = [wx for wx in _WX_ALL if wx not in present_wx]
    if miss_wx:
        out["五行"] = [f"缺{wx}→对{_WX_BLIND[wx]}分辨力低" for wx in miss_wx]
    miss_gua = [g for g in _GUA_ALL if g not in present_gua]
    if present_gua and miss_gua:
        out["卦"] = [f"缺{g}→缺「{_GUA_BLIND[g]}」类象" for g in miss_gua]
    return out


def related_wuxing(names):
    """五行同气联象（网络化）：返回 {五行: [库内同气节点名...]}。
    跨 天将/八卦/地支/天干 四类节点，按五行关联同气象——射覆取象不全时，
    可用同气节点补全漏掉的象源。"""
    kb = _load()
    wx_map = {}
    for kind in ("天将", "八卦", "地支", "天干"):
        for nm, node in kb.get(kind, {}).items():
            wx = node.get("五行")
            if not wx:
                vals = node.get("dimensions", {}).get("五行", [])
                wx = vals[0]["value"] if vals else None
            if wx:
                wx_map[nm] = wx
    out = {}
    for name in names:
        w = wx_map.get(name)
        if not w:
            continue
        same = sorted(nm for nm, ow in wx_map.items() if ow == w)
        out.setdefault(w, same)
    return out


def update_kb(round_json):
    """后验回填（递进调整，禁止单例大改）：round_json = {"命中":[...], "遗漏":[...], "错误":[...]}。
    每条 {"类":"天将/八卦/地支/天干","名":"朱雀","维度":"颜色","值":"红"}。
    命中 confidence+0.05、遗漏 +0.02、错误 −0.10（上下限 0.95/0.10），validations+1。
    借鉴 shefu v0.3.0：小步递进、区分三类，避免「对一个答案把某信号拉满」的过拟合。"""
    kb = _load()
    for tag, delta in (("命中", 0.05), ("遗漏", 0.02), ("错误", -0.10)):
        for item in round_json.get(tag, []):
            kind = item.get("类", "天将")
            name = item.get("名")
            dim = item.get("维度")
            val = item.get("值")
            if name not in kb.get(kind, {}):
                continue
            for v in kb[kind][name].get("dimensions", {}).get(dim, []):
                if v["value"] == val:
                    v["confidence"] = round(max(0.10, min(0.95, v["confidence"] + delta)), 2)
                    v["validations"] = v.get("validations", 0) + 1
    kb["_meta"]["total_validations"] = kb["_meta"].get("total_validations", 0) + 1
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    return {"updated": True, "total_validations": kb["_meta"]["total_validations"]}


def _fmt(p):
    lines = [f"🔬 特征画像（命中信号 {p['used']}/{len(p['signals'])}）"]
    for dim, vals in p["dimensions"].items():
        s = " / ".join(f"[{v[1]}] {v[0]}" for v in vals)
        lines.append(f"  {dim}  {s}")
    blind = p.get("blind") or {}
    if blind:
        lines.append("⚠️ 盲区（本盘分辨力低的维度，缺≠非，建议交互补）")
        for kind, items in blind.items():
            lines.append(f"  {kind}: {'、'.join(items)}")
    # 候选参考：取材质+形态+功能+物类 top 值拼成候选类别（降分辨率给候选，不点名）
    cand = []
    for dim in ("材质", "形态", "功能", "物类"):
        vals = p["dimensions"].get(dim, [])
        if vals and vals[0][0] != "—":
            cand.append(vals[0][0])
    if cand:
        lines.append(f"💡 候选参考：{' + '.join(cand)}（候选类别，非点名）")
    lines.append("结束语：以上是根据卦象展开的特征画像，并非确定性结论。")
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "liuren":
        print(_fmt(portrait_liuren(a[1:])))
    elif cmd == "meihua":
        print(_fmt(portrait_meihua(a[1:])))
    elif cmd == "update":
        data = json.loads(a[1] if len(a) > 1 else "{}")
        print(update_kb(data))
    else:
        print(_fmt(portrait([(x, 1.0) for x in a])))


if __name__ == "__main__":
    main()