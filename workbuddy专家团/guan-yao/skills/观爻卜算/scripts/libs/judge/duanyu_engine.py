# -*- coding: utf-8 -*-
"""断语编译引擎：JSON 规则表 + 通用判定解释器。

借鉴 tianzhi-core ziwei/duanyu.py（MIT，https://pypi.org/project/tianzhi-core/）的架构：
把典籍断语逐句写成 JSON 规则表，每条带
  src      出处（书名+篇名）
  text     原文（一字不改）
  note     小注
  verdict  吉凶定性（吉/凶/…）
  topic    主题（事业/感情/财运/…）
  cond     判定条件（在盘上可判）
  reading  读法说明（「哪里是读法」照实说）
  skip     不判缘故（泛论/比喻/需看相貌等读不准的句子，宁缺毋滥）
解释器只认组合子（and/or/not）与一套术法相关的「事实查询」原语；术法差异收敛在
**adapter（盘面适配器）**上——引擎不动，换术法只换 adapter 与规则表。

── 为什么是这一步（层③原文推演下沉）──
层③「原文推演」原本是 LLM 自由发挥（引原文→白话→套盘）。这里把其中「这句断语
是否命中这张盘」的**机械判定**下沉为代码：能判的判、判不了的标 skip+缘故，LLM 只
负责把命中结果说成人话。这是「最大杠杆」——可判定部分从不确定的 LLM 变成可对质的代码。

用法：
  from judge.duanyu_engine import find, ZiweiAdapter
  rules = load_rules("data/ziwei_duanyu.json")
  hits, skipped = find(rules, ZiweiAdapter(chart))
"""
from __future__ import annotations

import json

ZHI: str = "子丑寅卯辰巳午未申酉戌亥"

# 星曜组（紫微）：四杀/六杀/六吉/空亡
GROUPS: dict[str, list[str]] = {
    "四杀": ["擎羊", "陀罗", "火星", "铃星"],
    "六杀": ["擎羊", "陀罗", "火星", "铃星", "地劫", "天空"],
    "六吉": ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"],
    "空亡": ["截路空亡", "旬中空亡"],
}
DAY_HOURS = set("卯辰巳午未申")


def at(zhi: str, offset: int) -> str:
    """地支环偏移（sanfang/jia 用）。"""
    return ZHI[(ZHI.index(zhi) + offset) % 12]


# ======================================================================
# 一、通用引擎：组合子 + find + validate（术法无关）
# ======================================================================

class BaseAdapter:
    """盘面适配器协议：实现 test(cond) -> bool，解释器把叶子条件丢给它。

    组合子 and/or/not 由引擎统一处理，adapter 只需认得自己术法的**叶子原语**。
    """

    def test(self, cond: dict) -> bool:
        raise NotImplementedError


def eval_cond(adapter: BaseAdapter, cond) -> bool:
    """判定一个条件。组合子和/or/not 由引擎处理，叶子交给 adapter.test。"""
    if isinstance(cond, dict):
        if "and" in cond:
            return all(eval_cond(adapter, x) for x in cond["and"])
        if "or" in cond:
            return any(eval_cond(adapter, x) for x in cond["or"])
        if "not" in cond:
            return not eval_cond(adapter, cond["not"])
        return adapter.test(cond)
    if isinstance(cond, bool):
        return cond
    raise ValueError(f"不认识的条件：{cond!r}")


def find(rules, adapter: BaseAdapter):
    """遍历规则表，返回 (命中列表, 跳过列表)。

    命中列表元素 = {id, src, text, note, verdict, topic, reading}；
    跳过列表元素 = {id, src, text, skip}（skip 的不判，写明缘故）。
    """
    hits, skipped = [], []
    for r in rules:
        if r.get("skip") or not r.get("cond"):
            skipped.append({"id": r.get("id"), "src": r.get("src"),
                            "text": r.get("text"), "skip": r.get("skip")})
            continue
        try:
            if eval_cond(adapter, r["cond"]):
                hits.append({k: r[k] for k in ("id", "name", "src", "text", "note", "verdict", "topic", "reading")
                             if r.get(k) is not None})
        except Exception as e:  # 单条规则异常不拖垮整表，记进 skipped
            skipped.append({"id": r.get("id"), "src": r.get("src"),
                            "text": r.get("text"), "skip": f"判定异常：{e}"})
    return hits, skipped


def validate(rules, adapter: BaseAdapter):
    """规则表自检：逐条跑 cond，认得则通过，抛异常则报哪条不合法。"""
    bad = []
    for r in rules:
        if r.get("skip") or not r.get("cond"):
            continue
        try:
            eval_cond(adapter, r["cond"])
        except Exception as e:
            bad.append((r.get("id"), str(e)))
    return bad


def load_rules(path) -> list[dict]:
    """从 JSON 文件读规则表。支持 {"rules": [...]} 或裸列表。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("rules", [])
    return data


# ======================================================================
# 二、紫微适配器（忠实移植 tianzhi-core ziwei/duanyu.py 的 _Pan + _ev）
# ======================================================================

class ZiweiAdapter(BaseAdapter):
    """紫微盘面适配器。chart 结构同 tianzhi-core：

    chart = {
      "ming": 地支, "shen": 地支,
      "palaces": [{"name": 宫名, "zhi": 地支, "stars": [{"name": 星, "hua"?: 四化, "miao"?: 庙旺}]}],
      "input": {"gender": 0|1, "lunar": {"year": (天干,地支), "hour": 地支}},
    }
    """

    def __init__(self, chart):
        self.c = chart
        self.by = {p["zhi"]: p for p in chart["palaces"]}
        self.name = {p["name"]: p["zhi"] for p in chart["palaces"]}
        self.pos, self.hua, self.miao = {}, {}, {}
        for p in chart["palaces"]:
            for s in p["stars"]:
                self.pos[s["name"]] = p["zhi"]
                if s.get("hua"):
                    self.hua[s["name"]] = s["hua"]
                if s.get("miao"):
                    self.miao[s["name"]] = s["miao"]
        lunar = chart["input"]["lunar"]
        self.gan, self.yzhi, self.hour = lunar["year"][0], lunar["year"][1], lunar["hour"]

    # —— 原语 ——
    def zhis(self, P):
        """宫名 → 地支列表（「命身」给两个）。"""
        if P == "命":
            return [self.c["ming"]]
        if P == "身":
            return [self.c["shen"]]
        if P == "命身":
            return list(dict.fromkeys([self.c["ming"], self.c["shen"]]))
        if P in self.name:
            return [self.name[P]]
        if P in ZHI:
            return [P]
        raise ValueError(f"不是宫名或地支：{P!r}")

    def expand(self, stars):
        out = []
        for s in stars:
            out.extend(GROUPS.get(s, [s]))
        return out

    def has(self, z, stars, mode="all"):
        """这些星是否在 z 宫。mode=all 都要在，any 任一在。"""
        names = set(p["name"] for p in self.by[z]["stars"])
        ss = self.expand(stars)
        return all(s in names for s in ss) if mode == "all" else any(s in names for s in ss)

    # —— 叶子条件 ——
    def test(self, c):
        mode = c.get("mode", "all")
        if "stars" in c and "at" in c:
            return any(self.has(z, c["stars"], mode) for z in self.zhis(c["at"]))
        if "none" in c:
            return all(not self.has(z, c["none"], "any") for z in self.zhis(c["at"]))
        if "sanfang" in c:
            def sf(z):
                zs = [z, at(z, 6), at(z, 4), at(z, -4)]
                ss = self.expand(c["stars"])
                inn = [any(self.has(q, [s], "all") for q in zs) for s in ss]
                return all(inn) if mode == "all" else any(inn)
            return any(sf(z) for z in self.zhis(c["sanfang"]))
        if "jia" in c:
            a, b = (c["stars"] * 2)[:2]
            def jia(z):
                l, r = at(z, -1), at(z, 1)
                return (self.has(l, [a], "any") and self.has(r, [b], "any")) or \
                       (self.has(r, [a], "any") and self.has(l, [b], "any"))
            return any(jia(z) for z in self.zhis(c["jia"]))
        if "zhi" in c:
            return any(z in c["in"] for z in self.zhis(c["zhi"]))
        if "star_at" in c:
            return self.pos.get(c["star_at"]) in c["in"]
        if "miao" in c:
            return self.miao.get(c["miao"]) in c["in"]
        if "hua" in c:
            return self.hua.get(c["hua"]) in c["in"]
        if "hua_at" in c:
            hs = [self.hua[s] for s in self.hua if self.pos.get(s) in self.zhis(c["hua_at"])]
            ok = [h in hs for h in c["in"]]
            return all(ok) if mode == "all" else any(ok)
        if "hua_sanfang" in c:
            def hsf(z):
                zs = {z, at(z, 6), at(z, 4), at(z, -4)}
                hs = [self.hua[s] for s in self.hua if self.pos.get(s) in zs]
                ok = [h in hs for h in c["in"]]
                return all(ok) if mode == "all" else any(ok)
            return any(hsf(z) for z in self.zhis(c["hua_sanfang"]))
        if "gan" in c:
            return self.gan in c["gan"]
        if "yzhi" in c:
            return self.yzhi in c["yzhi"]
        if "gender" in c:
            return self.c["input"]["gender"] == c["gender"]
        if "day" in c:
            return (self.hour in DAY_HOURS) == c["day"]
        raise ValueError(f"不认识的条件：{c!r}")


# ======================================================================
# 三、自检 demo（跑通引擎的最小示例）
# ======================================================================

class DemoAdapter(BaseAdapter):
    """最小适配器，演示引擎与规则表如何接：只认 at/entities 两个原语。"""

    def __init__(self, board):
        self.board = board  # {"place": ["entity", ...]}

    def test(self, c):
        entities = self.board.get(c["at"], [])
        want = c["entities"]
        mode = c.get("mode", "all")
        return all(e in entities for e in want) if mode == "all" else any(e in entities for e in want)


if __name__ == "__main__":
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    rules = [
        {"id": "demo-0", "src": "示例经·某篇", "text": "A与B同宫则吉", "note": "同宫也",
         "verdict": "吉", "topic": "事业",
         "cond": {"and": [
             {"at": "命", "entities": ["A", "B"], "mode": "all"},
             {"not": {"at": "命", "entities": ["凶星"], "mode": "any"}},
         ]},
         "reading": "A、B 同守命宫且无凶星则吉"},
        {"id": "demo-1", "src": "示例经·某篇", "text": "某泛论之句", "verdict": "吉", "topic": "性格",
         "skip": "泛论无星位，不判"},
    ]
    board = {"命": ["A", "B"], "财帛": ["C"]}
    hits, skipped = find(rules, DemoAdapter(board))
    print("[duanyu_engine demo] 命中：", [(h["id"], h["verdict"]) for h in hits])
    print("  跳过：", [(s["id"], s["skip"]) for s in skipped])
    # 紫微适配器自检：跑 tianzhi-core 例盘（一张含紫微/天府的小盘）
    chart = {
        "ming": "寅", "shen": "寅",
        "palaces": [{"name": "命宫", "zhi": "寅",
                     "stars": [{"name": "紫微", "miao": "庙"}, {"name": "天府", "miao": "庙"}]}],
        "input": {"gender": 0, "lunar": {"year": ("甲", "子"), "hour": "午"}},
    }
    r2 = [{"id": "zw-demo", "src": "紫微斗数全书·某", "text": "紫微天府同宫主贵",
           "verdict": "吉", "topic": "格局", "reading": "紫府同守命宫",
           "cond": {"stars": ["紫微", "天府"], "at": "命", "mode": "all"}}]
    h2, _ = find(r2, ZiweiAdapter(chart))
    print("[紫微适配器自检] 命中：", [(h["id"], h["verdict"]) for h in h2])
