# -*- coding: utf-8 -*-
"""六爻 13 类用神断语编译：LiuyaoAdapter（盘面适配器）+ 断语规则表。

借鉴 tianzhi-core ziwei/duanyu.py 的架构：把《增删卜易》《火珠林》《卜筮正宗》里
「用神旺衰/原神忌神/持世/旬空月破/入墓」的断语写成 JSON 式规则表，每条带
  src      出处（书名:行号，可 classical_search.py --passage-id 复核）
  text     原文（一字不改）
  note     小注
  verdict  吉凶定性（吉/凶/中）
  topic    事类（求财/求官/婚姻/…）
  cond     判定条件（在盘上可判）
  reading  读法说明
判定由 duanyu_engine 的通用解释器 + 本适配器（六爻盘面原语）完成：能判的判、
判不了的 skip+缘故，LLM 只负责把命中结果说成人话（层③原文推演下沉）。

── 盘面来源 ──
r = najia.zhuang(...) 的装卦结果：{宫, 宫五行, 世爻, 应爻, 日辰, 月建, 旬空, 伏神, 六爻:[...]}
用神定位走 najia.yongshen_for(question)（13 类问事 → 用神六亲，已有代码）。
原神/忌神走 najia._YUANSHEN / najia._JISHEN。

用法：
  from judge.liuyao_duanyu import find_liuyao
  hits, skipped = find_liuyao(r, "求财")
"""
from __future__ import annotations

from judge.duanyu_engine import BaseAdapter, find
from pan import najia

# 五行 → 墓支（水土同墓辰；木墓未、火墓戌、金墓丑）
_MU = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}

S = "增删卜易"


class LiuyaoAdapter(BaseAdapter):
    """六爻盘面适配器：把六爻装卦结果 r 与问事 question 变成可判定的原语。

    leaf 条件词汇（test 认得）：
      ys_is       用神六亲 ∈ [..]
      ys_wang     用神旺衰 ∈ ["旺","相"]（旺相）/ ["衰","死"]（休囚）
      ys_kong     用神旬空
      ys_po       用神月破
      ys_rumu     用神入墓（日辰或月建为用神之墓）
      ys_chi_shi  用神持世
      yuanshen_dong / yuanshen_wang   原神发动 / 原神旺相
      jishen_dong  / jishen_wang      忌神发动 / 忌神旺相
      jishen_chi_shi                  忌神持世
      shi_wang / shi_kong / shi_po    世爻旺相 / 旬空 / 月破
    """

    def __init__(self, r, question=""):
        self.r = r
        self.question = question or ""
        self.ys = najia.yongshen_for(self.question)        # 用神六亲（或 "世"）
        self.yuanshen = najia._YUANSHEN.get(self.ys)       # 原神
        self.jishen = najia._JISHEN.get(self.ys)           # 忌神
        self.lines = r["六爻"]
        self.target = self._find_target()                  # 用神爻（或伏神）

    def _find_target(self):
        if self.ys == "世":
            return next(x for x in self.lines if x["世应"] == "世")
        for x in self.lines:
            if x["本卦"].split()[0] == self.ys:
                return x
        for f in self.r.get("伏神", []):
            if f.get("六亲") == self.ys:
                return {"伏": True, "干支": f["干支"], "伏爻": f["伏爻"]}
        return None

    def _zhi(self):
        if self.target is None:
            return None
        if self.target.get("伏"):
            return self.target["干支"][-1]
        return self.target["本卦"].split()[1][-1]

    def _lv(self):
        zhi = self._zhi()
        if not zhi:
            return "不现"
        return najia._wx_level(zhi, self.r["月建"], self.r["日辰"])["等级"]

    def _rumu(self):
        zhi = self._zhi()
        if not zhi:
            return False
        mu = _MU[najia.ZHI_WX[zhi]]
        return self.r["日辰"] == mu or self.r["月建"] == mu

    def _qin(self, qin):
        """某六亲的爻列表。"""
        return [x for x in self.lines if x["本卦"].split()[0] == qin]

    def _qin_wang(self, qin):
        return any(
            najia._wx_level(x["本卦"].split()[1][-1], self.r["月建"], self.r["日辰"])["等级"] in ("旺", "相")
            for x in self._qin(qin)
        )

    def _shi(self):
        return next(x for x in self.lines if x["世应"] == "世")

    def _shi_lv(self):
        zhi = self._shi()["本卦"].split()[1][-1]
        return najia._wx_level(zhi, self.r["月建"], self.r["日辰"])["等级"]

    def test(self, c):
        if "ys_is" in c:
            return self.ys in c["ys_is"]
        if "ys_wang" in c:
            return self._lv() in c["ys_wang"]
        if "ys_kong" in c:
            zhi = self._zhi()
            return bool(zhi and zhi in self.r["旬空"])
        if "ys_po" in c:
            zhi = self._zhi()
            return bool(self.r["月建"] and zhi and zhi == najia.CHONG.get(self.r["月建"]))
        if "ys_rumu" in c:
            return self._rumu()
        if "ys_chi_shi" in c:
            return bool(self.target and not self.target.get("伏") and self.target.get("世应") == "世")
        if "yuanshen_dong" in c:
            return bool(self.yuanshen) and any(x["动"] for x in self._qin(self.yuanshen))
        if "yuanshen_wang" in c:
            return bool(self.yuanshen) and self._qin_wang(self.yuanshen)
        if "jishen_dong" in c:
            return bool(self.jishen) and any(x["动"] for x in self._qin(self.jishen))
        if "jishen_wang" in c:
            return bool(self.jishen) and self._qin_wang(self.jishen)
        if "jishen_chi_shi" in c:
            return bool(self.jishen) and any(x["世应"] == "世" for x in self._qin(self.jishen))
        if "shi_wang" in c:
            return self._shi_lv() in ("旺", "相")
        if "shi_kong" in c:
            return self._shi()["本卦"].split()[1][-1] in self.r["旬空"]
        if "shi_po" in c:
            zhi = self._shi()["本卦"].split()[1][-1]
            return bool(self.r["月建"] and zhi == najia.CHONG.get(self.r["月建"]))
        raise ValueError(f"不认识的条件：{c!r}")


# ======================================================================
# 13 类用神断语规则表（src 书名:行号 → 典籍 txt 可复核）
# ======================================================================

RULES = [
    # ── 用神旺衰（增删卜易·四处生克章 445）──
    {"id": "ly-ys-0", "src": f"{S}:445", "topic": "通",
     "text": "生用神之神旺相者则以吉断",
     "note": "生用神之神即原神",
     "verdict": "吉",
     "cond": {"yuanshen_wang": True},
     "reading": "原神（生用神之神）旺相，用神得生，以吉断"},

    {"id": "ly-ys-1", "src": f"{S}:445", "topic": "通",
     "text": "若值休囚者有生之名无生之实，与四处俱来克者同断，诸占大凶",
     "note": "生用神之神休囚则无生之实",
     "verdict": "凶",
     "cond": {"and": [{"ys_wang": ["衰", "死"]}, {"not": {"yuanshen_wang": True}}]},
     "reading": "用神休囚、原神又无力生之，有生之名无生之实，凶"},

    # ── 原神/忌神（元神忌神章 531 + 445）──
    {"id": "ly-ys-2", "src": f"{S}:531", "topic": "通",
     "text": "元神，生用神之神即为元神。忌神，克用神之爻也",
     "note": "原神动而有用则生用神",
     "verdict": "吉",
     "cond": {"yuanshen_dong": True},
     "reading": "原神发动，生用神有力，吉"},

    {"id": "ly-ys-3", "src": f"{S}:445", "topic": "通",
     "text": "克用神之神旺相者可以凶推",
     "note": "克用神之神即忌神",
     "verdict": "凶",
     "cond": {"jishen_wang": True},
     "reading": "忌神旺相，能克用神，凶"},

    {"id": "ly-ys-4", "src": f"{S}:531", "topic": "通",
     "text": "忌神，克用神之爻也",
     "note": "忌神发动则克用神",
     "verdict": "凶",
     "cond": {"jishen_dong": True},
     "reading": "忌神发动，克用神，凶"},

    # ── 用神持世（增删卜易 423）──
    {"id": "ly-ys-5", "src": f"{S}:423", "topic": "通",
     "text": "求官者若得官鬼持世，求名必成；求财者得妻财持世，求财必得",
     "note": "用神持世，所求在我",
     "verdict": "吉",
     "cond": {"ys_chi_shi": True},
     "reading": "用神持世，所求之事在我手中，主成"},

    {"id": "ly-ys-6", "src": f"{S}:31", "topic": "求官",
     "text": "占功名得旺官持世以成名，子孙持世而失望",
     "note": "子孙为官之忌神；忌神持世则失望",
     "verdict": "凶",
     "cond": {"and": [{"ys_is": ["官鬼"]}, {"jishen_chi_shi": True}]},
     "reading": "求官忌神（子孙）持世，剥官之神坐世，失望"},

    # ── 世爻旺衰（增删卜易 436）──
    {"id": "ly-ys-7", "src": f"{S}:436", "topic": "通",
     "text": "自占吉凶者以世爻为用神……宜于旺相，最怕休囚",
     "note": "世爻旺相则诸事可为",
     "verdict": "吉",
     "cond": {"shi_wang": True},
     "reading": "世爻旺相，自身有力，诸事可为"},

    {"id": "ly-ys-8", "src": f"{S}:436", "topic": "通",
     "text": "不宜世爻落空，更不宜世爻临月破",
     "note": "世爻空破则自身无力",
     "verdict": "凶",
     "cond": {"or": [{"shi_kong": True}, {"shi_po": True}]},
     "reading": "世爻旬空或月破，自身无力，百无所为"},

    # ── 用神旬空/月破 ──
    {"id": "ly-ys-9", "src": f"{S}:423", "topic": "通",
     "text": "官鬼爻与妻财爻或值旬空月破……有何益也",
     "note": "用神空破则虽持世亦虚",
     "verdict": "凶",
     "cond": {"or": [{"ys_kong": True}, {"ys_po": True}]},
     "reading": "用神旬空或月破，事虚待出空、当月缓"},

    # ── 用神入墓（墓库章：休囚入墓为埋葬）──
    {"id": "ly-ys-10", "src": f"{S}:60", "topic": "通",
     "text": "旺相入库为财库，休囚入墓为埋葬。用神休囚又入墓，如人被埋，诸事难成",
     "note": "休囚入墓，非库乃墓",
     "verdict": "凶",
     "cond": {"and": [{"ys_wang": ["衰", "死"]}, {"ys_rumu": True}]},
     "reading": "用神休囚又入墓，如人被埋，诸事难成"},

    # ── 兄弟劫财（增删卜易 453，求财/占妻妾财物专条）──
    {"id": "ly-ys-11", "src": f"{S}:453", "topic": "求财",
     "text": "兄弟爻乃劫财之神……如占妻、妾、婢、仆及财物者宜克多生少。更喜逢空逢破，使其不能劫我之财",
     "note": "占财物忌兄弟（劫财）旺相得势",
     "verdict": "凶",
     "cond": {"and": [{"ys_is": ["妻财"]}, {"jishen_wang": True}]},
     "reading": "求财忌神（兄弟劫财）旺相得势，能劫我财，凶"},

    # ── 用神定位（火珠林，供断卦第一层「取何爻为用」佐证）──
    {"id": "ly-ys-12", "src": "火珠林:46", "topic": "求财",
     "text": "占买卖财，占家事，占婚婢事，占求财事，占婚姻事，以上皆看财爻",
     "note": "求财/婚姻看妻财",
     "verdict": "中",
     "cond": {"ys_is": ["妻财"]},
     "reading": "此占取妻财为用神"},

    {"id": "ly-ys-13", "src": "火珠林:46", "topic": "求官",
     "text": "占病鬼祟，占失看贼，占求官事，占官词讼，占婚问夫，以上皆看官爻",
     "note": "求官/官司/疾病看官鬼",
     "verdict": "中",
     "cond": {"ys_is": ["官鬼"]},
     "reading": "此占取官鬼为用神"},

    {"id": "ly-ys-14", "src": "火珠林:251", "topic": "子女",
     "text": "占六畜、小儿，看子孙",
     "note": "子女/六畜看子孙",
     "verdict": "中",
     "cond": {"ys_is": ["子孙"]},
     "reading": "此占取子孙为用神"},

    {"id": "ly-ys-15", "src": "火珠林:252", "topic": "文书",
     "text": "若失文书牌号，当以父母爻取",
     "note": "文书/牌号看父母",
     "verdict": "中",
     "cond": {"ys_is": ["父母"]},
     "reading": "此占取父母为用神"},
]


def find_liuyao(r, question=""):
    """装卦结果 r + 问事 → (命中断语列表, 跳过列表)。"""
    return find(RULES, LiuyaoAdapter(r, question))


if __name__ == "__main__":
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    q = sys.argv[1] if len(sys.argv) > 1 else "求财"
    # 自测：用 najia 装一卦
    from pan import najia
    r = najia.zhuang("天风姤", "天山遁", [3, 5], "壬子", "丁酉")
    a = najia.yongshen_analysis(r, q)
    print(f"[六爻断语编译自测] 问事={q} 用神={a['用神']} 落={a['落爻']} 旺衰={a['旺衰']['等级']}")
    hits, skipped = find_liuyao(r, q)
    print("  命中断语：")
    for h in hits:
        print(f"    [{h['verdict']}] {h['text'][:30]}…（{h['src']}）")
    print("  跳过：", [(s['id'], s['skip']) for s in skipped])
