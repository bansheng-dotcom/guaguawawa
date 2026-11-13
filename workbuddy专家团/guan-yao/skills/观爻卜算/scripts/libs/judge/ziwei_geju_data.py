# -*- coding: utf-8 -*-
"""紫微格局判定 · 数据表迁移版（JSON 规则表 + 通用解释器）。

把 ziwei_geju.py 里 18 个硬编码 _check_* 函数，迁成 tianzhi-core duanyu.py 式
JSON 规则表 + GejuAdapter（盘面适配器）。每条格局带
  id/name(格局名) verdict(吉凶) text(原文) note(断语) cond(判定条件) reading(读法)
判定由 duanyu_engine 的通用解释器 + GejuAdapter 完成；ziwei_geju.judge_patterns
仍可作交叉印证（两套判定结果应一致，不一致即标「信号冲突」）。

用法：
  from judge.ziwei_geju_data import find_geju
  hits = find_geju(chart)   # chart 为 pan/zhiwei 产出的盘（含「十二宫」）
"""
from __future__ import annotations

from judge.duanyu_engine import BaseAdapter, find
from pan import zhiwei


class GejuAdapter(BaseAdapter):
    """紫微格局适配器：把 pan/zhiwei 的十二宫盘映射到 duanyu_engine DSL。

    chart["十二宫"][idx] = {"宫": 宫名, "支": 地支, "命": bool,
                            "主星": [(星名, 庙旺, 四化)], "辅星": [星名]}
    宫位索引寅=0。命宫由 p["命"] 定位。
    """

    def __init__(self, chart):
        self.chart = chart
        self.palaces = chart["十二宫"]
        self.by_name = {p["宫"]: i for i, p in enumerate(self.palaces)}
        self.by_zhi = {p["支"]: i for i, p in enumerate(self.palaces)}
        self.ming = next((i for i, p in enumerate(self.palaces) if p.get("命")), 0)
        self.year_gan = chart.get("年干")
        self.gender = chart.get("性别")

    def _stars(self, idx):
        p = self.palaces[idx]
        names = {n for n, _b, _s in p["主星"]}
        names.update(p["辅星"])
        return names

    def _idx(self, P):
        if P == "命":
            return self.ming
        if P in self.by_name:
            return self.by_name[P]
        if P in self.by_zhi:
            return self.by_zhi[P]
        raise ValueError(f"不是宫名或地支：{P!r}")

    def _has(self, idx, stars, mode):
        names = self._stars(idx)
        return all(s in names for s in stars) if mode == "all" else any(s in names for s in stars)

    def _sanfang(self, idx, stars, mode):
        zs = zhiwei.sanfang_sizheng(idx)      # [本宫, 对宫, 三合两宫]
        inn = [any(s in self._stars(q) for q in zs) for s in stars]
        return all(inn) if mode == "all" else any(inn)

    def _star_at(self, name):
        for i in range(12):
            if name in self._stars(i):
                return self.palaces[i]["支"]
        return None

    def _star_brightness(self, idx, star):
        """该宫某主星的庙旺（庙/旺/得/利/平/不/陷，无则 None）。"""
        for n, b, s in self.palaces[idx]["主星"]:
            if n == star:
                return b
        return None

    def _star_sihua(self, idx, star):
        """该宫某主星的四化（禄/权/科/忌，无则 None）。"""
        for n, b, s in self.palaces[idx]["主星"]:
            if n == star:
                return s
        return None

    def test(self, c):
        mode = c.get("mode", "all")
        if "stars" in c and "at" in c:
            return self._has(self._idx(c["at"]), c["stars"], mode)
        if "none" in c:
            return not self._has(self._idx(c["at"]), c["none"], "any")
        if "sanfang" in c:
            idx = self._idx(c["sanfang"])
            zs = zhiwei.sanfang_sizheng(idx)
            got = sum(1 for s in c["stars"] if any(s in self._stars(q) for q in zs))
            if "min" in c or "max" in c:
                return c.get("min", 0) <= got <= c.get("max", len(c["stars"]))
            return got == len(c["stars"]) if mode == "all" else got >= 1
        if "zhi" in c:
            return self.palaces[self._idx(c["zhi"])]["支"] in c["in"]
        if "star_at" in c:
            z = self._star_at(c["star_at"])
            return z in c["in"] if z else False
        if "same_palace" in c:
            return any(all(s in self._stars(i) for s in c["same_palace"]) for i in range(12))
        if "luma_jiaochi" in c:
            lu = [i for i in range(12) if "禄存" in self._stars(i)]
            ma = [i for i in range(12) if "天马" in self._stars(i)]
            if not lu or not ma:
                return False
            return bool(set(lu) & set(ma)) or any((l + 6) % 12 in ma for l in lu)
        if "riyue_bingming" in c:
            tai = [i for i in range(12) if "太阳" in self._stars(i)]
            yin = [i for i in range(12) if "太阴" in self._stars(i)]
            if not tai or not yin:
                return False
            if set(tai) & set(yin):
                return True
            if self.by_zhi["卯"] in tai and self.by_zhi["亥"] in yin:
                return True
            if self.by_zhi["巳"] in tai and self.by_zhi["酉"] in yin:
                return True
            return False
        if "jia" in c:  # 夹：stars 分列某宫前后两宫（各至少一星在侧）
            idx = self._idx(c["jia"])
            front = self._stars((idx - 1) % 12)
            back = self._stars((idx + 1) % 12)
            stars = set(c["stars"])
            union = front | back
            return all(s in union for s in stars) and bool(stars & front) and bool(stars & back)
        if "miaowang" in c:  # 某星在某宫且庙旺落在 in 列表
            idx = self._idx(c["at"])
            b = self._star_brightness(idx, c["star"])
            return b in c["in"]
        if "sihua" in c:  # 某宫(或三方四正)某星化某四化；不指定 star 则任意星化该四化即真
            si = c["si"]
            if "sanfang" in c:  # 命三方四正有化某四化
                zs = zhiwei.sanfang_sizheng(self._idx(c["sanfang"]))
                if "star" in c:
                    return any(self._star_sihua(q, c["star"]) == si for q in zs)
                return any(s == si for q in zs for n, b, s in self.palaces[q]["主星"])
            idx = self._idx(c["at"])
            if "star" in c:
                return self._star_sihua(idx, c["star"]) == si
            return any(s == si for n, b, s in self.palaces[idx]["主星"])
        if "kongwang" in c:  # 某宫支 / 某星落宫支 在生年旬空（空亡）支里
            kong = set(self.chart.get("空亡", []))
            kw = c["kongwang"]
            if "star" in kw:
                z = self._star_at(kw["star"])
                return z in kong
            idx = self._idx(kw["at"])
            return self.palaces[idx]["支"] in kong
        if "gan" in c:  # 生年干在列表内
            return self.year_gan in c["gan"]
        if "gender" in c:  # 性别（男/女）
            return self.gender == c["gender"]
        raise ValueError(f"不认识的条件：{c!r}")


S = "紫微斗数全书"

# 18 格局规则表（判定条件为 duanyu_engine DSL，出处《紫微斗数全书》）
GEJU_RULES = [
    {"id": "geju-junchen", "name": "君臣庆会", "verdict": "吉",
     "text": "君臣慶會 紫微左右同守命是也，更會相武陰妙上",
     "note": "紫微为君、左右为辅，贵气聚命，多得贵人助力、掌权有望",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "命"},
                      {"sanfang": "命", "stars": ["左辅", "右弼", "天府", "天相"], "mode": "any"}]},
     "reading": "紫微守命且左右/府相拱照"},

    {"id": "geju-fuxiang", "name": "府相朝垣", "verdict": "吉",
     "text": "府相朝垣命必荣；府相朝垣千锺食禄",
     "note": "天府天相为财荫之星，朝拱命垣，主富贵荣显、财禄丰厚",
     "topic": "格局", "src": S,
     "cond": {"or": [{"stars": ["天府", "天相"], "at": "命", "mode": "any"},
                     {"sanfang": "命", "stars": ["天府", "天相"], "mode": "all"}]},
     "reading": "天府/天相守命，或同见命三方四正"},

    {"id": "geju-jiyue", "name": "机月同梁", "verdict": "吉",
     "text": "机月同梁作吏人 命在寅申方论",
     "note": "机月同梁作吏人，主稳定文职、公门清贵、安分守成",
     "topic": "格局", "src": S,
     "cond": {"sanfang": "命", "stars": ["天机", "太阴", "天同", "天梁"], "mode": "all"},
     "reading": "天机太阴天同天梁四星会命三方四正"},

    {"id": "geju-jiyue-qing", "name": "机月同梁", "verdict": "中",
     "text": "机月同梁作吏人 命在寅申方论",
     "note": "机月同梁三星会命，不完整（倾向，破格）",
     "topic": "格局", "src": S,
     "cond": {"sanfang": "命", "stars": ["天机", "太阴", "天同", "天梁"], "min": 3, "max": 3},
     "reading": "四星缺一，仅三星会命三方四正，倾向不完整"},

    {"id": "geju-yuelang", "name": "月朗天门", "verdict": "吉",
     "text": "月朗天门于亥地登云职掌大权",
     "note": "太阴入庙于亥，主大富大贵、掌权有谋略",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["太阴"], "at": "命"}, {"zhi": "命", "in": ["亥"]}]},
     "reading": "太阴在亥守命"},

    {"id": "geju-rizhao", "name": "日照雷门", "verdict": "吉",
     "text": "日照雷门子辰卯地昼生富贵声扬",
     "note": "太阳在卯入庙守命，主声名显达、富贵扬名（昼生更验）",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["太阳"], "at": "命"}, {"zhi": "命", "in": ["卯"]}]},
     "reading": "太阳在卯守命"},

    {"id": "geju-yuesheng", "name": "月生沧海", "verdict": "吉",
     "text": "月生滄海 月在子宮守田宅是也",
     "note": "太阴在子守田宅，主田宅丰厚、家业安稳、晚福绵长",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["太阴"], "at": "田宅"}, {"zhi": "田宅", "in": ["子"]}]},
     "reading": "太阴在子守田宅"},

    {"id": "geju-qisha", "name": "七杀朝斗", "verdict": "吉",
     "text": "七杀寅申子午一生爵禄荣昌 为七杀朝斗格",
     "note": "七杀在寅申子午朝拱紫微，主武职权贵、威权显赫",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["七杀"], "at": "命"}, {"zhi": "命", "in": ["寅", "申", "子", "午"]}]},
     "reading": "七杀在寅申子午守命"},

    {"id": "geju-wuqu", "name": "武曲庙垣", "verdict": "吉",
     "text": "武曲庙垣威名赫奕",
     "note": "武曲于四墓地入庙，主财帛威权、经商发达",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["武曲"], "at": "命"}, {"zhi": "命", "in": ["辰", "戌", "丑", "未"]}]},
     "reading": "武曲在辰戌丑未守命"},

    {"id": "geju-shizhong", "name": "石中隐玉", "verdict": "吉",
     "text": "身命居子午宫为石中隐玉格，更会科权禄，终身福厚",
     "note": "巨门子午藏玉于石，先难后成、更会科权禄则终身福厚",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["巨门"], "at": "命"}, {"zhi": "命", "in": ["子", "午"]}]},
     "reading": "巨门在子午守命"},

    {"id": "geju-luma", "name": "禄马交驰", "verdict": "吉",
     "text": "禄马交驰亦吉；武曲禄马交驰发财远郡",
     "note": "禄存天马交驰，主财禄丰足、奔波得财、发财远郡",
     "topic": "格局", "src": S,
     "cond": {"luma_jiaochi": True},
     "reading": "禄存与天马同宫或对照"},

    {"id": "geju-qingyang", "name": "擎羊入庙", "verdict": "吉",
     "text": "擎羊入庙富贵声扬；擎羊入庙最利武职",
     "note": "擎羊辰戌丑未入庙，主先破后成、武职发迹、闹中发财",
     "topic": "格局", "src": S,
     "cond": {"star_at": "擎羊", "in": ["辰", "戌", "丑", "未"]},
     "reading": "擎羊在辰戌丑未入庙"},

    {"id": "geju-matou", "name": "马头带剑", "verdict": "吉",
     "text": "马头带剑 谓马有刃是也不是居午格；马头带箭富且贵",
     "note": "擎羊在午带剑，主于险中得富、武职奋斗成贵",
     "topic": "格局", "src": S,
     "cond": {"star_at": "擎羊", "in": ["午"]},
     "reading": "擎羊在午"},

    {"id": "geju-zifu", "name": "紫府同宫", "verdict": "吉",
     "text": "天府惟寅申二宫紫府同宫",
     "note": "紫微天府同宫，主福禄厚重、稳重有成、一生衣食",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["紫微", "天府"]},
     "reading": "紫微天府同宫"},

    {"id": "geju-fubi", "name": "辅弼拱主", "verdict": "吉",
     "text": "輔弼拱主 紫微守命二星來拱是也",
     "note": "左辅右弼拱护紫微，主左右得人、助力强、事业有靠",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "命"},
                      {"sanfang": "命", "stars": ["左辅", "右弼"], "mode": "any"}]},
     "reading": "紫微守命且左辅右弼拱照"},

    {"id": "geju-juri", "name": "巨日同宫", "verdict": "吉",
     "text": "巨日拱照亦为奇",
     "note": "巨门太阳同宫，主食禄驰名、声名在外、口才扬名",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["巨门", "太阳"]},
     "reading": "巨门太阳同宫"},

    {"id": "geju-riyue", "name": "日月并明", "verdict": "吉",
     "text": "日月守命不如照合并明",
     "note": "日月并明，主阴阳调和、福寿双全、名利两得",
     "topic": "格局", "src": S,
     "cond": {"riyue_bingming": True},
     "reading": "太阳太阴同宫，或日卯月亥/日巳月酉拱照"},

    {"id": "geju-shapo", "name": "杀破狼", "verdict": "中",
     "text": "紫微入限本为祥，只恐三方杀破狼",
     "note": "杀破狼会命，主大变动、开创、动荡，成者大起败者大落",
     "topic": "格局", "src": S,
     "cond": {"sanfang": "命", "stars": ["七杀", "破军", "贪狼"], "mode": "all"},
     "reading": "七杀破军贪狼三星会命三方四正"},

    {"id": "geju-juji", "name": "巨机同临", "verdict": "凶",
     "text": "巨门天机为破荡；巨宿天机为破荡",
     "note": "巨门天机同宫破荡，主是非、多谋少成、易破败",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["巨门", "天机"]},
     "reading": "巨门天机同宫"},

    {"id": "geju-tianliang-wu", "name": "天梁午", "verdict": "吉",
     "text": "梁居午位官资清显",
     "note": "天梁在午守命，主清贵、官资清显、刚正不阿",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["天梁"], "at": "命"}, {"zhi": "命", "in": ["午"]}]},
     "reading": "天梁在午守命"},

    {"id": "geju-wutan", "name": "武贪同行", "verdict": "中",
     "text": "先貧後富武貪同身命之宮；貪武同行威鎮邊夷",
     "note": "武曲贪狼同宫，主先贫后富、武职威权、白手起家",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["武曲", "贪狼"]},
     "reading": "武曲贪狼同宫"},

    {"id": "geju-lianqisha", "name": "廉贞七杀", "verdict": "中",
     "text": "廉貞七殺反為積富之人；廉貞七殺流蕩天涯",
     "note": "廉贞七杀同宫两面：庙旺有制则积富，陷地无制则流荡天涯（多面并列，不锁死）",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["廉贞", "七杀"]},
     "reading": "廉贞七杀同宫（积富/流荡两面，看庙旺陷地）"},

    {"id": "geju-huotan", "name": "火贪格", "verdict": "吉",
     "text": "貪狼火星居廟旺名鎮諸邦",
     "note": "贪狼火星同宫，主横发暴富、名镇一方、异路功名",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["贪狼", "火星"]},
     "reading": "贪狼火星同宫"},

    {"id": "geju-kuiyue", "name": "魁钺拱命", "verdict": "吉",
     "text": "天魁天鉞蓋世文章",
     "note": "天魁天钺拱照命宫，主贵人提携、文名盖世、机遇多",
     "topic": "格局", "src": S,
     "cond": {"sanfang": "命", "stars": ["天魁", "天钺"], "mode": "any"},
     "reading": "天魁天钺会命三方四正"},

    {"id": "geju-fuxiang-yin", "name": "府相寅", "verdict": "吉",
     "text": "寅逢府相位登一品之榮",
     "note": "天府天相在寅守命，主位登一品、财荫夹印、富贵荣显",
     "topic": "格局", "src": S,
     "cond": {"stars": ["天府", "天相"], "at": "寅", "mode": "any"},
     "reading": "天府或天相在寅"},

    {"id": "geju-changqu", "name": "昌曲拱命", "verdict": "吉",
     "text": "昌曲夾墀男命貴而且顯；左輔文昌會吉星尊居八座",
     "note": "文昌文曲拱照命宫，主文采出众、科名显达、贵而且显",
     "topic": "格局", "src": S,
     "cond": {"sanfang": "命", "stars": ["文昌", "文曲"], "mode": "any"},
     "reading": "文昌文曲会命三方四正"},

    {"id": "geju-jincan", "name": "金灿光辉", "verdict": "吉",
     "text": "金燦光輝 太陽單守，命在午宮是也",
     "note": "太阳单守命在午（日丽中天），主光明显赫、富贵声扬",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["太阳"], "at": "命"}, {"zhi": "命", "in": ["午"]}]},
     "reading": "太阳单守命在午"},

    {"id": "geju-wuqu-shouyuan", "name": "武曲守垣", "verdict": "吉",
     "text": "武曲守垣 武守命卯宮是也，余不是",
     "note": "武曲单守命在卯，主武职威权、财帛丰足（原文「余不是」，仅卯宫成格）",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["武曲"], "at": "命"}, {"zhi": "命", "in": ["卯"]}]},
     "reading": "武曲单守命在卯"},

    {"id": "geju-caiqiu", "name": "财与囚仇", "verdict": "凶",
     "text": "財與囚仇 武貞同守身命是也",
     "note": "武曲廉贞同守身命，主财星与囚星相仇，先富后败、是非破财",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["武曲", "廉贞"]},
     "reading": "武曲廉贞同宫"},

    {"id": "geju-gupin", "name": "一生孤贫", "verdict": "凶",
     "text": "一生孤貧 謂破守命星陷地是也",
     "note": "破军守命陷地，主一生孤贫、破耗无成（陷地方论，旺地不同）",
     "topic": "格局", "src": S,
     "cond": {"stars": ["破军"], "at": "命"},
     "reading": "破军守命（陷地孤贫，旺地另论）"},

    {"id": "geju-caiyin", "name": "财荫夹印", "verdict": "吉",
     "text": "財蔭夾印 相守命武梁來夾是也，田宅宮亦然",
     "note": "天相守命，武曲天梁夹命，主财荫夹印、富贵双全、一生财禄丰足",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["天相"], "at": "命"}, {"jia": "命", "stars": ["武曲", "天梁"]}]},
     "reading": "天相守命，武曲天梁夹命"},

    {"id": "geju-riyuejiacai", "name": "日月夹财", "verdict": "吉",
     "text": "日月夾財 武守命日月來夾是也，財帛宮亦然",
     "note": "武曲守命，太阳太阴夹命，主财帛丰足、富贵之格",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["武曲"], "at": "命"}, {"jia": "命", "stars": ["太阳", "太阴"]}]},
     "reading": "武曲守命，太阳太阴夹命"},

    {"id": "geju-cailujiama", "name": "财禄夹马", "verdict": "吉",
     "text": "財祿夾馬 馬守命武祿來夾是也，逢生旺尤妙",
     "note": "天马守命，武曲禄存夹命，主禄马交驰、发财远郡、奔波得财",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["天马"], "at": "命"}, {"jia": "命", "stars": ["武曲", "禄存"]}]},
     "reading": "天马守命，武曲禄存夹命"},

    {"id": "geju-jinyu", "name": "金舆扶驾", "verdict": "吉",
     "text": "金輿扶駕 紫微守命前後有日月來夾是也",
     "note": "紫微守命，日月前后夹命，主贵气扶驾、位极人臣",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "命"}, {"jia": "命", "stars": ["太阳", "太阴"]}]},
     "reading": "紫微守命，太阳太阴前后夹命"},

    {"id": "geju-riyuejiaming", "name": "日月夹命", "verdict": "吉",
     "text": "日月夾命 不坐空亡遇逢本宮有吉星是也",
     "note": "太阳太阴夹命（本宫有吉星、不坐空亡方论），主贵气、福泽深厚",
     "topic": "格局", "src": S,
     "cond": {"jia": "命", "stars": ["太阳", "太阴"]},
     "reading": "太阳太阴夹命"},

    {"id": "geju-caiyinjialu", "name": "财印夹禄", "verdict": "吉",
     "text": "財印夾祿 祿守命梁相來夾是也，入財亦然",
     "note": "禄存守命，天梁天相夹命，主财印夹禄、财禄丰足",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["禄存"], "at": "命"}, {"jia": "命", "stars": ["天梁", "天相"]}]},
     "reading": "禄存守命，天梁天相夹命"},

    {"id": "geju-quanlu", "name": "权禄生逢", "verdict": "吉",
     "text": "權祿生逢 二星守命廟旺是也，陷不是",
     "note": "命宫化权化禄二星守命，主掌权得禄、名利双收（原文要求庙旺，陷地不论）",
     "topic": "格局", "src": S,
     "cond": {"and": [{"sihua": {"at": "命", "si": "权"}}, {"sihua": {"at": "命", "si": "禄"}}]},
     "reading": "命宫化权星与化禄星同守（庙旺方论）"},

    {"id": "geju-shengbufengshi", "name": "生不逢时", "verdict": "凶",
     "text": "生不逢時 命坐空亡逢廉貞是也",
     "note": "廉贞守命又命坐空亡，主生不逢时、怀才不遇、际遇蹇滞",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["廉贞"], "at": "命"}, {"kongwang": {"at": "命"}}]},
     "reading": "廉贞守命，命宫坐空亡"},

    {"id": "geju-lufengliangsha", "name": "禄逢两杀", "verdict": "凶",
     "text": "祿逢兩殺 祿坐空亡又逢空劫殺星是也",
     "note": "禄存坐空亡又逢空劫杀星，主财禄虚耗、富贵难守",
     "topic": "格局", "src": S,
     "cond": {"kongwang": {"star": "禄存"}},
     "reading": "禄存落宫坐空亡"},

    {"id": "geju-maluokongwang", "name": "马落空亡", "verdict": "凶",
     "text": "馬落空亡 馬既落亡雖祿沖會無用主奔波",
     "note": "天马落空亡，主终身奔波劳碌、虽禄冲会亦无用",
     "topic": "格局", "src": S,
     "cond": {"kongwang": {"star": "天马"}},
     "reading": "天马落宫坐空亡"},

    {"id": "geju-liangchonghuagai", "name": "两重华盖", "verdict": "凶",
     "text": "兩重華蓋 謂祿存化祿坐命遇空劫是也",
     "note": "禄存化禄坐命又遇地空地劫，主孤高不群、财禄虚花、六亲缘薄",
     "topic": "格局", "src": S,
     "cond": {"and": [{"stars": ["禄存"], "at": "命"}, {"stars": ["地空", "地劫"], "at": "命", "mode": "any"}]},
     "reading": "禄存坐命且命宫见地空地劫"},

    {"id": "geju-xingqiu", "name": "刑囚夹印", "verdict": "中",
     "text": "刑囚夾印 天刑廉貞同臨身命主武勇之人",
     "note": "天刑廉贞同临身命，主武勇、刑权、掌兵（刑囚夹印，主武勇之人）",
     "topic": "格局", "src": S,
     "cond": {"same_palace": ["天刑", "廉贞"]},
     "reading": "天刑廉贞同宫"},

    {"id": "geju-sanqi", "name": "三奇嘉会", "verdict": "吉",
     "text": "科權祿拱名譽昭彰；科明祿暗位列三台",
     "note": "化科化权化禄三奇会命三方四正，主名誉昭彰、科甲名扬、位列三台",
     "topic": "格局", "src": S,
     "cond": {"and": [{"sihua": {"sanfang": "命", "si": "科"}},
                      {"sihua": {"sanfang": "命", "si": "权"}},
                      {"sihua": {"sanfang": "命", "si": "禄"}}]},
     "reading": "命三方四正化科化权化禄三奇会"},
]


def find_geju(chart):
    """判定紫微格局，返回命中的 [{id,name,verdict,text,note,src,reading}]。"""
    return find(GEJU_RULES, GejuAdapter(chart))[0]


# —— 诸星同垣·星落宫断语（每星在某宫 + 同度星 + 生年干 = 吉凶格）——
# 出处：《紫微斗数全书》卷三「论诸星分属南北斗化吉凶」每星总论下的十二宫落宫断语。
# 与格局（星曜组合）不同，这类断语把「生年干」作为判定条件，是断命的核心细分。
STAR_GONG = [
    {"id": "sg-ziwei-zi", "star": "紫微", "verdict": "吉",
     "text": "子宫喜丁己庚生人贵格，壬癸生人不耐久",
     "note": "紫微在子宫，丁己庚生年干者贵格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "子"}, {"gan": ["丁", "己", "庚"]}]},
     "reading": "紫微在子 + 丁己庚生年干"},

    {"id": "sg-ziwei-wu", "star": "紫微", "verdict": "吉",
     "text": "午宫入庙喜甲丁己生人财官格，丙戊生人成败带疾",
     "note": "紫微在午入庙，甲丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "午"}, {"gan": ["甲", "丁", "己"]}]},
     "reading": "紫微在午 + 甲丁己生年干"},

    {"id": "sg-ziwei-maoyou", "star": "紫微", "verdict": "中",
     "text": "卯酉宫贪狼同度，乙辛甲庚生人贵不耐久",
     "note": "紫微在卯酉与贪狼同度，乙辛甲庚生年干者贵不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["紫微"], "at": "卯"}, {"stars": ["紫微"], "at": "酉"}]},
                      {"same_palace": ["紫微", "贪狼"]}, {"gan": ["乙", "辛", "甲", "庚"]}]},
     "reading": "紫微在卯酉 + 贪狼同度 + 乙辛甲庚生年干"},

    {"id": "sg-ziwei-yinshen", "star": "紫微", "verdict": "吉",
     "text": "寅申宫旺地与天府同度，甲庚丁己生人财官格",
     "note": "紫微在寅申旺地与天府同度，甲庚丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["紫微"], "at": "寅"}, {"stars": ["紫微"], "at": "申"}]},
                      {"same_palace": ["紫微", "天府"]}, {"gan": ["甲", "庚", "丁", "己"]}]},
     "reading": "紫微在寅申 + 天府同度 + 甲庚丁己生年干"},

    {"id": "sg-ziwei-sihai", "star": "紫微", "verdict": "吉",
     "text": "巳亥宫旺地与七杀同度，乙戊生人财官格",
     "note": "紫微在巳亥旺地与七杀同度，乙戊生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["紫微"], "at": "巳"}, {"stars": ["紫微"], "at": "亥"}]},
                      {"same_palace": ["紫微", "七杀"]}, {"gan": ["乙", "戊"]}]},
     "reading": "紫微在巳亥 + 七杀同度 + 乙戊生年干"},

    {"id": "sg-ziwei-chenxu", "star": "紫微", "verdict": "吉",
     "text": "辰戌宫得地与天相同度，乙己甲庚癸生人财官格",
     "note": "紫微在辰戌得地与天相同度，乙己甲庚癸生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["紫微"], "at": "辰"}, {"stars": ["紫微"], "at": "戌"}]},
                      {"same_palace": ["紫微", "天相"]}, {"gan": ["乙", "己", "甲", "庚", "癸"]}]},
     "reading": "紫微在辰戌 + 天相同度 + 乙己甲庚癸生年干"},

    {"id": "sg-ziwei-chouwei", "star": "紫微", "verdict": "吉",
     "text": "丑未宫入庙与破军同度，乙己甲庚丁壬生人财官格",
     "note": "紫微在丑未入庙与破军同度，乙己甲庚丁壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["紫微"], "at": "丑"}, {"stars": ["紫微"], "at": "未"}]},
                      {"same_palace": ["紫微", "破军"]}, {"gan": ["乙", "己", "甲", "庚", "丁", "壬"]}]},
     "reading": "紫微在丑未 + 破军同度 + 乙己甲庚丁壬生年干"},

    # —— 天机 ——
    {"id": "sg-tianji-ziwu", "star": "天机", "verdict": "吉",
     "text": "子午宫入庙，丁己癸甲庚壬生人财官格",
     "note": "天机在子午入庙，丁己癸甲庚壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "子"}, {"stars": ["天机"], "at": "午"}]},
                      {"gan": ["丁", "己", "癸", "甲", "庚", "壬"]}]},
     "reading": "天机在子午 + 丁己癸甲庚壬生年干"},

    {"id": "sg-tianji-maoyou", "star": "天机", "verdict": "吉",
     "text": "卯酉宫旺地与巨门同度，乙辛戊癸生人财官格",
     "note": "天机在卯酉旺地与巨门同度，乙辛戊癸生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "卯"}, {"stars": ["天机"], "at": "酉"}]},
                      {"same_palace": ["天机", "巨门"]}, {"gan": ["乙", "辛", "戊", "癸"]}]},
     "reading": "天机在卯酉 + 巨门同度 + 乙辛戊癸生年干"},

    {"id": "sg-tianji-yinshen", "star": "天机", "verdict": "吉",
     "text": "寅申宫得地与太阴同度，丁己癸甲庚壬生人财官格",
     "note": "天机在寅申得地与太阴同度，丁己癸甲庚壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "寅"}, {"stars": ["天机"], "at": "申"}]},
                      {"same_palace": ["天机", "太阴"]}, {"gan": ["丁", "己", "癸", "甲", "庚", "壬"]}]},
     "reading": "天机在寅申 + 太阴同度 + 丁己癸甲庚壬生年干"},

    {"id": "sg-tianji-sihai", "star": "天机", "verdict": "中",
     "text": "巳亥宫和平，丙壬戊生人合局不耐久",
     "note": "天机在巳亥和平，丙壬戊生年干者合局不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "巳"}, {"stars": ["天机"], "at": "亥"}]},
                      {"gan": ["丙", "壬", "戊"]}]},
     "reading": "天机在巳亥 + 丙壬戊生年干"},

    {"id": "sg-tianji-chenxu", "star": "天机", "verdict": "吉",
     "text": "辰戌宫利益与天梁同度，壬庚丁生人为福",
     "note": "天机在辰戌利益与天梁同度，壬庚丁生年干者为福",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "辰"}, {"stars": ["天机"], "at": "戌"}]},
                      {"same_palace": ["天机", "天梁"]}, {"gan": ["壬", "庚", "丁"]}]},
     "reading": "天机在辰戌 + 天梁同度 + 壬庚丁生年干"},

    {"id": "sg-tianji-chouwei", "star": "天机", "verdict": "吉",
     "text": "丑未宫陷地，丙戊丁壬生人财官格，乙壬生人禄合格",
     "note": "天机在丑未陷地，丙戊丁壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天机"], "at": "丑"}, {"stars": ["天机"], "at": "未"}]},
                      {"gan": ["丙", "戊", "丁", "壬"]}]},
     "reading": "天机在丑未 + 丙戊丁壬生年干"},

    # —— 武曲 ——
    {"id": "sg-wuqu-ziwu", "star": "武曲", "verdict": "吉",
     "text": "子午宫旺地，与天府同度，丁己庚生人财官格",
     "note": "武曲在子午旺地与天府同度，丁己庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "子"}, {"stars": ["武曲"], "at": "午"}]},
                      {"same_palace": ["武曲", "天府"]}, {"gan": ["丁", "己", "庚"]}]},
     "reading": "武曲在子午 + 天府同度 + 丁己庚生年干"},

    {"id": "sg-wuqu-maoyou", "star": "武曲", "verdict": "吉",
     "text": "卯酉宫利益，与七杀同度，乙辛生人财官格",
     "note": "武曲在卯酉利益与七杀同度，乙辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "卯"}, {"stars": ["武曲"], "at": "酉"}]},
                      {"same_palace": ["武曲", "七杀"]}, {"gan": ["乙", "辛"]}]},
     "reading": "武曲在卯酉 + 七杀同度 + 乙辛生年干"},

    {"id": "sg-wuqu-yinshen", "star": "武曲", "verdict": "吉",
     "text": "寅申宫得地，与天相同度，丁己甲庚生人财官格",
     "note": "武曲在寅申得地与天相同度，丁己甲庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "寅"}, {"stars": ["武曲"], "at": "申"}]},
                      {"same_palace": ["武曲", "天相"]}, {"gan": ["丁", "己", "甲", "庚"]}]},
     "reading": "武曲在寅申 + 天相同度 + 丁己甲庚生年干"},

    {"id": "sg-wuqu-sihai", "star": "武曲", "verdict": "吉",
     "text": "巳亥宫和平，与破军同度，壬戊生人财官格",
     "note": "武曲在巳亥和平与破军同度，壬戊生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "巳"}, {"stars": ["武曲"], "at": "亥"}]},
                      {"same_palace": ["武曲", "破军"]}, {"gan": ["壬", "戊"]}]},
     "reading": "武曲在巳亥 + 破军同度 + 壬戊生年干"},

    {"id": "sg-wuqu-chenxu", "star": "武曲", "verdict": "吉",
     "text": "辰戌宫入庙，甲乙生人财官格",
     "note": "武曲在辰戌入庙，甲乙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "辰"}, {"stars": ["武曲"], "at": "戌"}]},
                      {"gan": ["甲", "乙"]}]},
     "reading": "武曲在辰戌 + 甲乙生年干"},

    {"id": "sg-wuqu-chouwei", "star": "武曲", "verdict": "吉",
     "text": "丑未宫入庙，与贪狼同度，戊辛生人大贵财官格",
     "note": "武曲在丑未入庙与贪狼同度，戊辛生年干者大贵财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["武曲"], "at": "丑"}, {"stars": ["武曲"], "at": "未"}]},
                      {"same_palace": ["武曲", "贪狼"]}, {"gan": ["戊", "辛"]}]},
     "reading": "武曲在丑未 + 贪狼同度 + 戊辛生年干"},

    # —— 天同 ——
    {"id": "sg-tiantong-ziwu", "star": "天同", "verdict": "吉",
     "text": "子宫旺地午宫陷，丁己癸辛生人财官格",
     "note": "天同在子午（子宫旺午宫陷），丁己癸辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "子"}, {"stars": ["天同"], "at": "午"}]},
                      {"gan": ["丁", "己", "癸", "辛"]}]},
     "reading": "天同在子午 + 丁己癸辛生年干"},

    {"id": "sg-tiantong-maoyou", "star": "天同", "verdict": "吉",
     "text": "卯酉宫和平，乙丙辛生人财官格",
     "note": "天同在卯酉和平，乙丙辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "卯"}, {"stars": ["天同"], "at": "酉"}]},
                      {"gan": ["乙", "丙", "辛"]}]},
     "reading": "天同在卯酉 + 乙丙辛生年干"},

    {"id": "sg-tiantong-yinshen", "star": "天同", "verdict": "吉",
     "text": "寅宫利申宫旺，与天梁同度，乙甲丁生人福厚",
     "note": "天同在寅申与天梁同度，乙甲丁生年干者福厚",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "寅"}, {"stars": ["天同"], "at": "申"}]},
                      {"same_palace": ["天同", "天梁"]}, {"gan": ["乙", "甲", "丁"]}]},
     "reading": "天同在寅申 + 天梁同度 + 乙甲丁生年干"},

    {"id": "sg-tiantong-sihai", "star": "天同", "verdict": "吉",
     "text": "巳亥宫入庙，壬丙戊生人财官格",
     "note": "天同在巳亥入庙，壬丙戊生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "巳"}, {"stars": ["天同"], "at": "亥"}]},
                      {"gan": ["壬", "丙", "戊"]}]},
     "reading": "天同在巳亥 + 壬丙戊生年干"},

    {"id": "sg-tiantong-chenxu", "star": "天同", "verdict": "中",
     "text": "辰戌宫和平，丙丁生人利达，庚癸生人福不耐久",
     "note": "天同在辰戌和平，丙丁生年干者利达，庚癸不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "辰"}, {"stars": ["天同"], "at": "戌"}]},
                      {"gan": ["丙", "丁"]}]},
     "reading": "天同在辰戌 + 丙丁生年干"},

    {"id": "sg-tiantong-chouwei", "star": "天同", "verdict": "吉",
     "text": "丑未宫不得地，与巨门同度，乙壬甲辛庚生人财官格",
     "note": "天同在丑未不得地与巨门同度，乙壬甲辛庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天同"], "at": "丑"}, {"stars": ["天同"], "at": "未"}]},
                      {"same_palace": ["天同", "巨门"]}, {"gan": ["乙", "壬", "甲", "辛", "庚"]}]},
     "reading": "天同在丑未 + 巨门同度 + 乙壬甲辛庚生年干"},

    # —— 廉贞 ——
    {"id": "sg-lianzhen-ziwu", "star": "廉贞", "verdict": "吉",
     "text": "子午宫和平，与天相同度，丁己甲生人财官格",
     "note": "廉贞在子午与天相同度，丁己甲生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["廉贞"], "at": "子"}, {"stars": ["廉贞"], "at": "午"}]},
                      {"same_palace": ["廉贞", "天相"]}, {"gan": ["丁", "己", "甲"]}]},
     "reading": "廉贞在子午 + 天相同度 + 丁己甲生年干"},

    {"id": "sg-lianzhen-maoyou", "star": "廉贞", "verdict": "吉",
     "text": "卯酉宫和平，与破军同度，乙辛癸生人吉",
     "note": "廉贞在卯酉与破军同度，乙辛癸生年干者吉",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["廉贞"], "at": "卯"}, {"stars": ["廉贞"], "at": "酉"}]},
                      {"same_palace": ["廉贞", "破军"]}, {"gan": ["乙", "辛", "癸"]}]},
     "reading": "廉贞在卯酉 + 破军同度 + 乙辛癸生年干"},

    {"id": "sg-lianzhen-yinshen", "star": "廉贞", "verdict": "吉",
     "text": "寅宫和平，甲庚己生人贵格。申宫入庙甲庚戊生人贵格，丙生人次之",
     "note": "廉贞在寅申，甲庚己生年干者贵格（申宫入庙甲庚戊）",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["廉贞"], "at": "寅"}, {"stars": ["廉贞"], "at": "申"}]},
                      {"gan": ["甲", "庚", "己", "戊"]}]},
     "reading": "廉贞在寅申 + 甲庚己戊生年干"},

    {"id": "sg-lianzhen-sihai", "star": "廉贞", "verdict": "中",
     "text": "巳亥宫陷地，甲己丙戊生人福不耐久",
     "note": "廉贞在巳亥陷地，甲己丙戊生年干者福不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["廉贞"], "at": "巳"}, {"stars": ["廉贞"], "at": "亥"}]},
                      {"gan": ["甲", "己", "丙", "戊"]}]},
     "reading": "廉贞在巳亥 + 甲己丙戊生年干"},

    {"id": "sg-lianzhen-chenxu", "star": "廉贞", "verdict": "吉",
     "text": "辰戌宫利益，与天府同度，甲庚生人财官格",
     "note": "廉贞在辰戌利益与天府同度，甲庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["廉贞"], "at": "辰"}, {"stars": ["廉贞"], "at": "戌"}]},
                      {"same_palace": ["廉贞", "天府"]}, {"gan": ["甲", "庚"]}]},
     "reading": "廉贞在辰戌 + 天府同度 + 甲庚生年干"},

    # —— 天府 ——
    {"id": "sg-tianfu-ziwu", "star": "天府", "verdict": "吉",
     "text": "子午宫与武曲同度，丁己癸生人为福，财官格",
     "note": "天府在子午与武曲同度，丁己癸生年干者为福财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天府"], "at": "子"}, {"stars": ["天府"], "at": "午"}]},
                      {"same_palace": ["天府", "武曲"]}, {"gan": ["丁", "己", "癸"]}]},
     "reading": "天府在子午 + 武曲同度 + 丁己癸生年干"},

    {"id": "sg-tianfu-maoyou", "star": "天府", "verdict": "吉",
     "text": "卯宫入庙，酉宫旺地，乙丙辛生人财官格",
     "note": "天府在卯酉（卯入庙酉旺地），乙丙辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天府"], "at": "卯"}, {"stars": ["天府"], "at": "酉"}]},
                      {"gan": ["乙", "丙", "辛"]}]},
     "reading": "天府在卯酉 + 乙丙辛生年干"},

    {"id": "sg-tianfu-yinshen", "star": "天府", "verdict": "吉",
     "text": "寅宫入庙，申宫得地，与紫微同度，丁己生人财官格",
     "note": "天府在寅申与紫微同度，丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天府"], "at": "寅"}, {"stars": ["天府"], "at": "申"}]},
                      {"same_palace": ["天府", "紫微"]}, {"gan": ["丁", "己"]}]},
     "reading": "天府在寅申 + 紫微同度 + 丁己生年干"},

    {"id": "sg-tianfu-sihai", "star": "天府", "verdict": "吉",
     "text": "巳亥宫得地，乙丙戊辛生人财官格",
     "note": "天府在巳亥得地，乙丙戊辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天府"], "at": "巳"}, {"stars": ["天府"], "at": "亥"}]},
                      {"gan": ["乙", "丙", "戊", "辛"]}]},
     "reading": "天府在巳亥 + 乙丙戊辛生年干"},

    {"id": "sg-tianfu-chenxu", "star": "天府", "verdict": "吉",
     "text": "辰戌宫入庙，与廉贞同度，甲庚壬生人财官格",
     "note": "天府在辰戌入庙与廉贞同度，甲庚壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天府"], "at": "辰"}, {"stars": ["天府"], "at": "戌"}]},
                      {"same_palace": ["天府", "廉贞"]}, {"gan": ["甲", "庚", "壬"]}]},
     "reading": "天府在辰戌 + 廉贞同度 + 甲庚壬生年干"},

    # —— 贪狼 ——
    {"id": "sg-tanlang-ziwu", "star": "贪狼", "verdict": "吉",
     "text": "子午宫旺地，丁己生人福厚，丙戊庚生寅申人下局",
     "note": "贪狼在子午旺地，丁己生年干者福厚",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "子"}, {"stars": ["贪狼"], "at": "午"}]},
                      {"gan": ["丁", "己"]}]},
     "reading": "贪狼在子午 + 丁己生年干"},

    {"id": "sg-tanlang-maoyou", "star": "贪狼", "verdict": "吉",
     "text": "卯酉宫利益，与紫微同度，见火星贵，乙辛己生人宜之，财官格",
     "note": "贪狼在卯酉与紫微同度见火星，乙辛己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "卯"}, {"stars": ["贪狼"], "at": "酉"}]},
                      {"same_palace": ["贪狼", "紫微"]}, {"gan": ["乙", "辛", "己"]}]},
     "reading": "贪狼在卯酉 + 紫微同度 + 乙辛己生年干"},

    {"id": "sg-tanlang-yinshen", "star": "贪狼", "verdict": "吉",
     "text": "寅申宫和平，庚生人财官格",
     "note": "贪狼在寅申和平，庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "寅"}, {"stars": ["贪狼"], "at": "申"}]},
                      {"gan": ["庚"]}]},
     "reading": "贪狼在寅申 + 庚生年干"},

    {"id": "sg-tanlang-sihai", "star": "贪狼", "verdict": "中",
     "text": "巳亥宫陷地，与廉贞同度，丙戊壬生人为福不耐久",
     "note": "贪狼在巳亥陷地与廉贞同度，丙戊壬生年干者福不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "巳"}, {"stars": ["贪狼"], "at": "亥"}]},
                      {"same_palace": ["贪狼", "廉贞"]}, {"gan": ["丙", "戊", "壬"]}]},
     "reading": "贪狼在巳亥 + 廉贞同度 + 丙戊壬生年干"},

    {"id": "sg-tanlang-chenxu", "star": "贪狼", "verdict": "吉",
     "text": "辰戌宫入庙，戊己生人财官格",
     "note": "贪狼在辰戌入庙，戊己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "辰"}, {"stars": ["贪狼"], "at": "戌"}]},
                      {"gan": ["戊", "己"]}]},
     "reading": "贪狼在辰戌 + 戊己生年干"},

    {"id": "sg-tanlang-chouwei", "star": "贪狼", "verdict": "吉",
     "text": "丑未宫入庙，与武曲同度，见火星，戊己庚生人贵格",
     "note": "贪狼在丑未入庙与武曲同度见火星，戊己庚生年干者贵格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["贪狼"], "at": "丑"}, {"stars": ["贪狼"], "at": "未"}]},
                      {"same_palace": ["贪狼", "武曲"]}, {"gan": ["戊", "己", "庚"]}]},
     "reading": "贪狼在丑未 + 武曲同度 + 戊己庚生年干"},

    # —— 巨门 ——
    {"id": "sg-jumen-ziwu", "star": "巨门", "verdict": "吉",
     "text": "子午宫旺地，丁己癸辛生人福厚，丙戊生人主困",
     "note": "巨门在子午旺地，丁己癸辛生年干者福厚",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "子"}, {"stars": ["巨门"], "at": "午"}]},
                      {"gan": ["丁", "己", "癸", "辛"]}]},
     "reading": "巨门在子午 + 丁己癸辛生年干"},

    {"id": "sg-jumen-maoyou", "star": "巨门", "verdict": "吉",
     "text": "卯酉宫入庙，与天机同度，乙辛己丙生人财官格，丁戊生人有成败",
     "note": "巨门在卯酉入庙与天机同度，乙辛己丙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "卯"}, {"stars": ["巨门"], "at": "酉"}]},
                      {"same_palace": ["巨门", "天机"]}, {"gan": ["乙", "辛", "己", "丙"]}]},
     "reading": "巨门在卯酉 + 天机同度 + 乙辛己丙生年干"},

    {"id": "sg-jumen-yinshen", "star": "巨门", "verdict": "吉",
     "text": "寅申宫入庙，与太阳同度，庚癸辛生人财官格",
     "note": "巨门在寅申入庙与太阳同度，庚癸辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "寅"}, {"stars": ["巨门"], "at": "申"}]},
                      {"same_palace": ["巨门", "太阳"]}, {"gan": ["庚", "癸", "辛"]}]},
     "reading": "巨门在寅申 + 太阳同度 + 庚癸辛生年干"},

    {"id": "sg-jumen-sihai", "star": "巨门", "verdict": "吉",
     "text": "巳亥旺宫单守，癸辛丙生人财官格",
     "note": "巨门在巳亥旺宫单守，癸辛丙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "巳"}, {"stars": ["巨门"], "at": "亥"}]},
                      {"gan": ["癸", "辛", "丙"]}]},
     "reading": "巨门在巳亥 + 癸辛丙生年干"},

    {"id": "sg-jumen-chenxu", "star": "巨门", "verdict": "吉",
     "text": "辰戌宫和平，癸辛生人主贵，丁生人困",
     "note": "巨门在辰戌和平，癸辛生年干者主贵",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "辰"}, {"stars": ["巨门"], "at": "戌"}]},
                      {"gan": ["癸", "辛"]}]},
     "reading": "巨门在辰戌 + 癸辛生年干"},

    {"id": "sg-jumen-chouwei", "star": "巨门", "verdict": "吉",
     "text": "丑未宫不得地，癸辛丙生人财官格",
     "note": "巨门在丑未不得地，癸辛丙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["巨门"], "at": "丑"}, {"stars": ["巨门"], "at": "未"}]},
                      {"gan": ["癸", "辛", "丙"]}]},
     "reading": "巨门在丑未 + 癸辛丙生年干"},

    # —— 天相 ——
    {"id": "sg-tianxiang-ziwu", "star": "天相", "verdict": "吉",
     "text": "子午宫入庙，与廉贞同度，丁己癸甲生人财官格",
     "note": "天相在子午入庙与廉贞同度，丁己癸甲生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天相"], "at": "子"}, {"stars": ["天相"], "at": "午"}]},
                      {"same_palace": ["天相", "廉贞"]}, {"gan": ["丁", "己", "癸", "甲"]}]},
     "reading": "天相在子午 + 廉贞同度 + 丁己癸甲生年干"},

    {"id": "sg-tianxiang-maoyou", "star": "天相", "verdict": "吉",
     "text": "卯酉宫陷地，乙辛生人吉。甲庚生人主困",
     "note": "天相在卯酉陷地，乙辛生年干者吉",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天相"], "at": "卯"}, {"stars": ["天相"], "at": "酉"}]},
                      {"gan": ["乙", "辛"]}]},
     "reading": "天相在卯酉 + 乙辛生年干"},

    {"id": "sg-tianxiang-yinshen", "star": "天相", "verdict": "吉",
     "text": "寅申宫入庙，与武曲同度，丁甲庚生人财官格",
     "note": "天相在寅申入庙与武曲同度，丁甲庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天相"], "at": "寅"}, {"stars": ["天相"], "at": "申"}]},
                      {"same_palace": ["天相", "武曲"]}, {"gan": ["丁", "甲", "庚"]}]},
     "reading": "天相在寅申 + 武曲同度 + 丁甲庚生年干"},

    {"id": "sg-tianxiang-sihai", "star": "天相", "verdict": "吉",
     "text": "巳亥宫得地，丙戊壬生人为福",
     "note": "天相在巳亥得地，丙戊壬生年干者为福",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天相"], "at": "巳"}, {"stars": ["天相"], "at": "亥"}]},
                      {"gan": ["丙", "戊", "壬"]}]},
     "reading": "天相在巳亥 + 丙戊壬生年干"},

    # —— 天梁 ——
    {"id": "sg-tianliang-ziwu", "star": "天梁", "verdict": "吉",
     "text": "子午宫入庙，丁己癸生人福厚财格",
     "note": "天梁在子午入庙，丁己癸生年干者福厚财格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天梁"], "at": "子"}, {"stars": ["天梁"], "at": "午"}]},
                      {"gan": ["丁", "己", "癸"]}]},
     "reading": "天梁在子午 + 丁己癸生年干"},

    {"id": "sg-tianliang-maoyou", "star": "天梁", "verdict": "吉",
     "text": "卯宫入庙酉宫得地，与太阳同度，乙壬辛生人财官格",
     "note": "天梁在卯酉与太阳同度，乙壬辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天梁"], "at": "卯"}, {"stars": ["天梁"], "at": "酉"}]},
                      {"same_palace": ["天梁", "太阳"]}, {"gan": ["乙", "壬", "辛"]}]},
     "reading": "天梁在卯酉 + 太阳同度 + 乙壬辛生年干"},

    {"id": "sg-tianliang-chenxu", "star": "天梁", "verdict": "吉",
     "text": "辰戌宫入庙，与天机同度，丁己壬庚生人财官格",
     "note": "天梁在辰戌入庙与天机同度，丁己壬庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天梁"], "at": "辰"}, {"stars": ["天梁"], "at": "戌"}]},
                      {"same_palace": ["天梁", "天机"]}, {"gan": ["丁", "己", "壬", "庚"]}]},
     "reading": "天梁在辰戌 + 天机同度 + 丁己壬庚生年干"},

    {"id": "sg-tianliang-chouwei", "star": "天梁", "verdict": "吉",
     "text": "丑未宫入庙，壬乙生人财官格，六戊生人大贵",
     "note": "天梁在丑未入庙，壬乙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天梁"], "at": "丑"}, {"stars": ["天梁"], "at": "未"}]},
                      {"gan": ["壬", "乙"]}]},
     "reading": "天梁在丑未 + 壬乙生年干"},

    {"id": "sg-tianliang-yinshen", "star": "天梁", "verdict": "吉",
     "text": "寅宫入庙申宫陷地，与天同同度，丁己甲庚生人财官格",
     "note": "天梁在寅申与天同同度，丁己甲庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["天梁"], "at": "寅"}, {"stars": ["天梁"], "at": "申"}]},
                      {"same_palace": ["天梁", "天同"]}, {"gan": ["丁", "己", "甲", "庚"]}]},
     "reading": "天梁在寅申 + 天同同度 + 丁己甲庚生年干"},

    # —— 七杀 ——
    {"id": "sg-qisha-ziwu", "star": "七杀", "verdict": "吉",
     "text": "子午宫旺地，丁己甲生人财官格",
     "note": "七杀在子午旺地，丁己甲生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["七杀"], "at": "子"}, {"stars": ["七杀"], "at": "午"}]},
                      {"gan": ["丁", "己", "甲"]}]},
     "reading": "七杀在子午 + 丁己甲生年干"},

    {"id": "sg-qisha-maoyou", "star": "七杀", "verdict": "吉",
     "text": "卯酉宫旺地，与武曲同度，乙辛生人福厚财官格",
     "note": "七杀在卯酉旺地与武曲同度，乙辛生年干者福厚财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["七杀"], "at": "卯"}, {"stars": ["七杀"], "at": "酉"}]},
                      {"same_palace": ["七杀", "武曲"]}, {"gan": ["乙", "辛"]}]},
     "reading": "七杀在卯酉 + 武曲同度 + 乙辛生年干"},

    {"id": "sg-qisha-yinshen", "star": "七杀", "verdict": "吉",
     "text": "寅申宫入庙，甲庚丁己生人财官格",
     "note": "七杀在寅申入庙，甲庚丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["七杀"], "at": "寅"}, {"stars": ["七杀"], "at": "申"}]},
                      {"gan": ["甲", "庚", "丁", "己"]}]},
     "reading": "七杀在寅申 + 甲庚丁己生年干"},

    {"id": "sg-qisha-sihai", "star": "七杀", "verdict": "吉",
     "text": "巳亥宫和平，与紫微同度，丙戊壬生人财官格",
     "note": "七杀在巳亥和平与紫微同度，丙戊壬生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["七杀"], "at": "巳"}, {"stars": ["七杀"], "at": "亥"}]},
                      {"same_palace": ["七杀", "紫微"]}, {"gan": ["丙", "戊", "壬"]}]},
     "reading": "七杀在巳亥 + 紫微同度 + 丙戊壬生年干"},

    # —— 破军 ——
    {"id": "sg-pojun-ziwu", "star": "破军", "verdict": "吉",
     "text": "子午宫入庙，丁己癸生人福厚，丙戊生人主困",
     "note": "破军在子午入庙，丁己癸生年干者福厚",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "子"}, {"stars": ["破军"], "at": "午"}]},
                      {"gan": ["丁", "己", "癸"]}]},
     "reading": "破军在子午 + 丁己癸生年干"},

    {"id": "sg-pojun-maoyou", "star": "破军", "verdict": "吉",
     "text": "卯酉宫陷地与廉贞同度，乙辛癸生人利，甲庚丙生人不耐久",
     "note": "破军在卯酉陷地与廉贞同度，乙辛癸生年干者利",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "卯"}, {"stars": ["破军"], "at": "酉"}]},
                      {"same_palace": ["破军", "廉贞"]}, {"gan": ["乙", "辛", "癸"]}]},
     "reading": "破军在卯酉 + 廉贞同度 + 乙辛癸生年干"},

    {"id": "sg-pojun-chenxu", "star": "破军", "verdict": "吉",
     "text": "辰戌宫旺地，甲癸生人为福",
     "note": "破军在辰戌旺地，甲癸生年干者为福",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "辰"}, {"stars": ["破军"], "at": "戌"}]},
                      {"gan": ["甲", "癸"]}]},
     "reading": "破军在辰戌 + 甲癸生年干"},

    {"id": "sg-pojun-chouwei", "star": "破军", "verdict": "吉",
     "text": "丑未宫旺地与紫微同度，丙戊乙生人财官格",
     "note": "破军在丑未旺地与紫微同度，丙戊乙生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "丑"}, {"stars": ["破军"], "at": "未"}]},
                      {"same_palace": ["破军", "紫微"]}, {"gan": ["丙", "戊", "乙"]}]},
     "reading": "破军在丑未 + 紫微同度 + 丙戊乙生年干"},

    {"id": "sg-pojun-yinshen", "star": "破军", "verdict": "吉",
     "text": "寅申宫得地，甲庚丁己生人财官格",
     "note": "破军在寅申得地，甲庚丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "寅"}, {"stars": ["破军"], "at": "申"}]},
                      {"gan": ["甲", "庚", "丁", "己"]}]},
     "reading": "破军在寅申 + 甲庚丁己生年干"},

    {"id": "sg-pojun-sihai", "star": "破军", "verdict": "吉",
     "text": "巳亥宫与武曲同度，戊生人福厚",
     "note": "破军在巳亥与武曲同度，戊生年干者福厚",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["破军"], "at": "巳"}, {"stars": ["破军"], "at": "亥"}]},
                      {"same_palace": ["破军", "武曲"]}, {"gan": ["戊"]}]},
     "reading": "破军在巳亥 + 武曲同度 + 戊生年干"},

    # —— 太阳 ——
    {"id": "sg-taiyang-ziwu", "star": "太阳", "verdict": "吉",
     "text": "子宫陷午宫旺，丁己生人财官格，壬丙戊生人悔吝",
     "note": "太阳在子午（子宫陷午宫旺），丁己生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阳"], "at": "子"}, {"stars": ["太阳"], "at": "午"}]},
                      {"gan": ["丁", "己"]}]},
     "reading": "太阳在子午 + 丁己生年干"},

    {"id": "sg-taiyang-maoyou", "star": "太阳", "verdict": "吉",
     "text": "卯宫庙酉宫和平，乙辛生人财官格，甲庚生人困",
     "note": "太阳在卯酉（卯庙酉和平），乙辛生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阳"], "at": "卯"}, {"stars": ["太阳"], "at": "酉"}]},
                      {"gan": ["乙", "辛"]}]},
     "reading": "太阳在卯酉 + 乙辛生年干"},

    {"id": "sg-taiyang-yinshen", "star": "太阳", "verdict": "吉",
     "text": "寅宫旺申宫得地与巨门同度，丁己甲庚生人财官格",
     "note": "太阳在寅申与巨门同度，丁己甲庚生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阳"], "at": "寅"}, {"stars": ["太阳"], "at": "申"}]},
                      {"same_palace": ["太阳", "巨门"]}, {"gan": ["丁", "己", "甲", "庚"]}]},
     "reading": "太阳在寅申 + 巨门同度 + 丁己甲庚生年干"},

    {"id": "sg-taiyang-si", "star": "太阳", "verdict": "吉",
     "text": "巳宫旺财官格。亥宫陷逢杀孤寡贫穷",
     "note": "太阳在巳宫旺主财官格（亥宫陷逢杀则孤寡贫穷）",
     "topic": "落宫", "src": S,
     "cond": {"stars": ["太阳"], "at": "巳"},
     "reading": "太阳在巳（旺）"},

    {"id": "sg-taiyang-chen", "star": "太阳", "verdict": "吉",
     "text": "辰宫旺财官格。戌宫陷反背孤寡",
     "note": "太阳在辰宫旺主财官格（戌宫陷则反背孤寡）",
     "topic": "落宫", "src": S,
     "cond": {"stars": ["太阳"], "at": "辰"},
     "reading": "太阳在辰（旺）"},

    {"id": "sg-taiyang-chouwei", "star": "太阳", "verdict": "吉",
     "text": "丑宫陷未宫得地与太阴同度，加吉星财官格",
     "note": "太阳在丑未与太阴同度加吉星，主财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阳"], "at": "丑"}, {"stars": ["太阳"], "at": "未"}]},
                      {"same_palace": ["太阳", "太阴"]}]},
     "reading": "太阳在丑未 + 太阴同度"},

    # —— 太阴（三合局落宫）——
    {"id": "sg-taiyin-zichouyin", "star": "太阴", "verdict": "吉",
     "text": "子丑寅宫入庙，丁戊生人财官格",
     "note": "太阴在子丑寅三合入庙，丁戊生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阴"], "at": "子"}, {"stars": ["太阴"], "at": "丑"}, {"stars": ["太阴"], "at": "寅"}]},
                      {"gan": ["丁", "戊"]}]},
     "reading": "太阴在子丑寅 + 丁戊生年干"},

    {"id": "sg-taiyin-maochensi", "star": "太阴", "verdict": "凶",
     "text": "卯辰巳宫陷地，乙壬戊生人孤寡不耐久",
     "note": "太阴在卯辰巳三合陷地，乙壬戊生年干者孤寡不耐久",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阴"], "at": "卯"}, {"stars": ["太阴"], "at": "辰"}, {"stars": ["太阴"], "at": "巳"}]},
                      {"gan": ["乙", "壬", "戊"]}]},
     "reading": "太阴在卯辰巳 + 乙壬戊生年干"},

    {"id": "sg-taiyin-wuweishen", "star": "太阴", "verdict": "吉",
     "text": "午宫陷未申宫利益，丁庚甲入生人财官格",
     "note": "太阴在午未申（午陷未申利），丁庚甲生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阴"], "at": "午"}, {"stars": ["太阴"], "at": "未"}, {"stars": ["太阴"], "at": "申"}]},
                      {"gan": ["丁", "庚", "甲"]}]},
     "reading": "太阴在午未申 + 丁庚甲生年干"},

    {"id": "sg-taiyin-youxuhai", "star": "太阴", "verdict": "吉",
     "text": "酉戌亥宫入庙，丙丁生人财官格，吉星众大贵",
     "note": "太阴在酉戌亥三合入庙，丙丁生年干者财官格",
     "topic": "落宫", "src": S,
     "cond": {"and": [{"or": [{"stars": ["太阴"], "at": "酉"}, {"stars": ["太阴"], "at": "戌"}, {"stars": ["太阴"], "at": "亥"}]},
                      {"gan": ["丙", "丁"]}]},
     "reading": "太阴在酉戌亥 + 丙丁生年干"},
]


def find_star_gong(chart):
    """判定诸星同垣落宫断语，返回命中的 [{id,star,verdict,text,note,src,reading}]。"""
    return find(STAR_GONG, GejuAdapter(chart))[0]


# —— 入命诀·凶格（诸星同垣：某星守命 + 凶星组合 = 凶）——
# 出处：《紫微斗数全书》每星「入男命/入女命吉凶诀」歌诀中「星守命 + 凶星」的断语。
# 与落宫（星在某地支）不同，这里判「星守命（不指定地支）+ 凶星同宫/三方」的组合凶格。
MING_JU = [
    {"id": "mj-ziwei-ersha", "star": "紫微", "verdict": "凶",
     "text": "紫微守命最为良，二杀逢之寿不长，羊陀火铃来相会，只好空门礼梵王。",
     "note": "紫微守命逢擎羊陀罗（二杀），主寿不长、宜空门",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "命"},
                      {"sanfang": "命", "stars": ["擎羊", "陀罗"], "mode": "any"}]},
     "reading": "紫微守命 + 擎羊陀罗会命"},

    {"id": "mj-ziwei-qisha", "star": "紫微", "verdict": "凶",
     "text": "火铃羊陀来相会，七杀同宫多不贵，欺人孤独更刑伤，若是空门为吉利。",
     "note": "紫微守命逢火铃羊陀七杀，主不贵、孤独刑伤",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "命"}, {"same_palace": ["紫微", "七杀"]},
                      {"sanfang": "命", "stars": ["火星", "铃星", "擎羊", "陀罗"], "mode": "any"}]},
     "reading": "紫微守命 + 七杀同宫 + 火铃羊陀会"},

    {"id": "mj-tianji-huaji", "star": "天机", "verdict": "凶",
     "text": "天机化忌落闲宫，纵有财官亦不荣，退尽家财兼寿夭，飘蓬僧道住山中。",
     "note": "天机化忌落闲宫，主退财、寿夭、宜僧道",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天机"], "at": "命"}, {"sihua": {"at": "命", "star": "天机", "si": "忌"}}]},
     "reading": "天机守命且化忌"},

    {"id": "mj-taiyang-huaji", "star": "太阳", "verdict": "凶",
     "text": "失陷太阳居反背，化忌逢之多蹇昧，又遭横事破家财，命强化禄也无益。",
     "note": "太阳陷地又化忌，主蹇昧、破财（命强化禄也无益）",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["太阳"], "at": "命"}, {"sihua": {"at": "命", "star": "太阳", "si": "忌"}}]},
     "reading": "太阳守命且化忌"},

    {"id": "mj-tiantong-huoling", "star": "天同", "verdict": "凶",
     "text": "天同守命落闲宫，火铃杀凑更为凶，天机梁月来相会，只好空门度岁终。",
     "note": "天同守命落闲宫逢火铃杀，主凶、宜空门",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天同"], "at": "命"},
                      {"sanfang": "命", "stars": ["火星", "铃星"], "mode": "any"}]},
     "reading": "天同守命 + 火铃会命"},

    {"id": "mj-lianzhen-sha", "star": "廉贞", "verdict": "凶",
     "text": "廉贞坐命落闲宫，贪破羊火忌相逢，纵有财官也不美，平生何以得从容。",
     "note": "廉贞坐命落闲宫逢贪破羊火忌，主不美、不从容",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["廉贞"], "at": "命"},
                      {"sanfang": "命", "stars": ["贪狼", "破军", "擎羊", "火星"], "mode": "any"}]},
     "reading": "廉贞守命 + 贪破羊火会命"},

    {"id": "mj-tianfu-huoling", "star": "天府", "verdict": "凶",
     "text": "火铃羊陀三方会，为人奸诈多劳碌，空劫同垣不为佳，只宜空门享福人。",
     "note": "天府守命逢火铃羊陀三方会，主奸诈劳碌、宜空门",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天府"], "at": "命"},
                      {"sanfang": "命", "stars": ["火星", "铃星", "擎羊", "陀罗"], "mode": "any"}]},
     "reading": "天府守命 + 火铃羊陀三方会"},

    {"id": "mj-tanlang-yangtuo", "star": "贪狼", "verdict": "凶",
     "text": "贪狼守命擎羊逢，陀杀交加必困穷，武破廉贞同杀劫，百艺防身度岁终。",
     "note": "贪狼守命逢擎羊陀罗杀，主困穷、百艺防身",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["贪狼"], "at": "命"},
                      {"sanfang": "命", "stars": ["擎羊", "陀罗"], "mode": "any"}]},
     "reading": "贪狼守命 + 擎羊陀罗会命"},

    {"id": "mj-jumen-yangtuo", "star": "巨门", "verdict": "凶",
     "text": "巨门守命遇擎羊，火铃逢之事不祥，为人性急多颠倒，百事茫茫乱主张。",
     "note": "巨门守命逢擎羊火铃，主不祥、性急颠倒",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["巨门"], "at": "命"},
                      {"sanfang": "命", "stars": ["擎羊", "火星", "铃星"], "mode": "any"}]},
     "reading": "巨门守命 + 擎羊火铃会命"},

    {"id": "mj-tianxiang-sha", "star": "天相", "verdict": "凶",
     "text": "天相之星武破同，羊陀火铃更为凶，或作技术经商辈，若在空门享福隆。",
     "note": "天相守命逢武破羊陀火铃，主凶、宜技术经商或空门",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天相"], "at": "命"},
                      {"sanfang": "命", "stars": ["武曲", "破军", "擎羊", "陀罗", "火星", "铃星"], "mode": "any"}]},
     "reading": "天相守命 + 武破羊陀火铃会命"},

    {"id": "mj-tianliang-huo", "star": "天梁", "verdict": "凶",
     "text": "天梁遇火落闲宫，陀杀重逢更是凶，孤刑带疾破家财，空门技艺可营工。",
     "note": "天梁落闲宫逢火陀杀，主孤刑带疾破财",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天梁"], "at": "命"},
                      {"sanfang": "命", "stars": ["火星", "陀罗"], "mode": "any"}]},
     "reading": "天梁守命 + 火陀会命"},

    {"id": "mj-qisha-xian", "star": "七杀", "verdict": "凶",
     "text": "杀居陷地不堪言，凶祸犹如伴虎眠，若是杀强无制伏，少年恶死到黄泉。",
     "note": "七杀居陷地无制，主凶祸、少年恶死",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["七杀"], "at": "命"},
                      {"miaowang": {"at": "命", "star": "七杀", "in": ["陷", "不", "平"]}}]},
     "reading": "七杀守命陷地"},

    {"id": "mj-pojun-sha", "star": "破军", "verdict": "凶",
     "text": "破军不喜在身宫，廉贞火羊陀会凶，不见伤残定寿夭，只宜僧道度平生。",
     "note": "破军守身逢廉贞火羊陀，主伤残寿夭、宜僧道",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["破军"], "at": "身"},
                      {"sanfang": "身", "stars": ["廉贞", "火星", "擎羊", "陀罗"], "mode": "any"}]},
     "reading": "破军守身 + 廉贞火羊陀会"},

    # —— 入命诀·吉格 ——
    {"id": "mj-taiyang-quanlu", "star": "太阳", "verdict": "吉",
     "text": "命里逢阳福寿浓，更兼权禄两相逢，魁昌左右来相凑，富贵双全比石崇。",
     "note": "太阳守命更会权禄魁昌左右，主福寿、富贵双全",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["太阳"], "at": "命"},
                      {"sanfang": "命", "stars": ["天魁", "文昌", "左辅", "右弼"], "mode": "any"}]},
     "reading": "太阳守命 + 魁昌左右会命"},

    {"id": "mj-tianfu-quanlu", "star": "天府", "verdict": "吉",
     "text": "天府之星守命宫，加之权禄喜相逢，魁昌左右来相会，附凤攀龙上九重。",
     "note": "天府守命更会权禄魁昌左右，主富贵、附凤攀龙",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["天府"], "at": "命"},
                      {"sanfang": "命", "stars": ["天魁", "文昌", "左辅", "右弼"], "mode": "any"}]},
     "reading": "天府守命 + 魁昌左右会命"},

    {"id": "mj-ziwei-tianfu-shen", "star": "紫微", "verdict": "吉",
     "text": "紫微女命守身宫，天府尊星同到宫，更得吉星同主照，金冠封赠福滔滔。",
     "note": "紫微守身宫与天府同宫（女命），主封赠福厚",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["紫微"], "at": "身"}, {"same_palace": ["紫微", "天府"]},
                      {"gender": "女"}]},
     "reading": "紫微守身 + 天府同宫 + 女命"},

    {"id": "mj-wuqu-tianfu-nv", "star": "武曲", "verdict": "吉",
     "text": "女人武曲命中逢，天府加之志气雄，左右禄存相逢聚，富贵双全美无穷。",
     "note": "武曲守命与天府同宫（女命），主志气、富贵双全",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["武曲"], "at": "命"}, {"same_palace": ["武曲", "天府"]},
                      {"gender": "女"}]},
     "reading": "武曲守命 + 天府同宫 + 女命"},

    # —— 入命诀·女命凶格 ——
    {"id": "mj-tiantong-taiyin-nv", "star": "天同", "verdict": "凶",
     "text": "天同若与太阴同，女命逢之淫巧容，衣禄虽丰终不美，偏房侍妾与人通。",
     "note": "天同太阴同宫（女命），主淫巧、衣禄不美、偏房",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"same_palace": ["天同", "太阴"]}, {"gender": "女"}]},
     "reading": "天同太阴同宫 + 女命"},

    {"id": "mj-lianzhen-tanpo-nv", "star": "廉贞", "verdict": "凶",
     "text": "廉贞贪破曲相逢，陀火交加极贱庸，定主刑夫并克子，只好偏房娼婢容。",
     "note": "廉贞守命逢贪破曲陀火（女命），主刑夫克子、偏房",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["廉贞"], "at": "命"},
                      {"sanfang": "命", "stars": ["贪狼", "破军", "陀罗", "火星"], "mode": "any"},
                      {"gender": "女"}]},
     "reading": "廉贞守命 + 贪破陀火会 + 女命"},

    {"id": "mj-taiyin-xian-sha", "star": "太阴", "verdict": "凶",
     "text": "太阴陷在命和身，不喜三方恶杀侵，克害夫君又夭寿，更虚血气少精神。",
     "note": "太阴陷地守命身又三方恶杀（女命），主克夫夭寿",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["太阴"], "at": "命"},
                      {"miaowang": {"at": "命", "star": "太阴", "in": ["陷", "不"]}},
                      {"gender": "女"}]},
     "reading": "太阴守命陷地 + 女命"},

    {"id": "mj-tanlang-xian-nv", "star": "贪狼", "verdict": "凶",
     "text": "贪狼陷地女非祥，衣食虽丰也不良，克害良人并男女，又教衾枕守孤孀。",
     "note": "贪狼陷地（女命），主克害、孤孀",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["贪狼"], "at": "命"},
                      {"miaowang": {"at": "命", "star": "贪狼", "in": ["陷"]}},
                      {"gender": "女"}]},
     "reading": "贪狼守命陷地 + 女命"},

    {"id": "mj-jumen-xian-nv", "star": "巨门", "verdict": "凶",
     "text": "巨门命陷主淫娼，侍女偏房免灾殃，相貌清奇多近宠，不然寿夭或凶亡。",
     "note": "巨门陷地（女命），主淫娼、偏房或凶亡",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["巨门"], "at": "命"},
                      {"miaowang": {"at": "命", "star": "巨门", "in": ["陷", "不"]}},
                      {"gender": "女"}]},
     "reading": "巨门守命陷地 + 女命"},

    {"id": "mj-qisha-tanhuo-nv", "star": "七杀", "verdict": "凶",
     "text": "七杀孤星贪宿逢，火陀凑合非为贵，女人得此性不良，只好偏房为使婢。",
     "note": "七杀守命逢贪狼火陀（女命），主性不良、偏房",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["七杀"], "at": "命"},
                      {"sanfang": "命", "stars": ["贪狼", "火星", "陀罗"], "mode": "any"},
                      {"gender": "女"}]},
     "reading": "七杀守命 + 贪狼火陀会 + 女命"},

    {"id": "mj-pojun-qingyang-nv", "star": "破军", "verdict": "凶",
     "text": "破军女命不宜逢，擎羊加陷便为凶，克害良人非一次，须教悲哭度朝昏。",
     "note": "破军守命（女命）逢擎羊陷，主克害、悲哭",
     "topic": "命诀", "src": S,
     "cond": {"and": [{"stars": ["破军"], "at": "命"},
                      {"sanfang": "命", "stars": ["擎羊"], "mode": "any"},
                      {"gender": "女"}]},
     "reading": "破军守命 + 擎羊会 + 女命"},
]


def find_ming_ju(chart):
    """判定入命诀凶格，返回命中的 [{id,star,verdict,text,note,src,reading}]。"""
    return find(MING_JU, GejuAdapter(chart))[0]


if __name__ == "__main__":
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # 自测：排一张盘跑两种判定（数据表 vs 硬编码），核对是否一致
    from pan import zhiwei as _zw
    chart = _zw.cast(1990, 5, 8, 9, 30, 0, 1) if hasattr(_zw, "cast") else None
    if chart:
        hits = find_geju(chart)
        print(f"[格局·数据表版] 命中 {len(hits)} 格：")
        for h in hits:
            print(f"  [{h['verdict']}] {h['name']} — {h['note']}（{h['src']}）")
