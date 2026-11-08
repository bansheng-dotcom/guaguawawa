# -*- coding: utf-8 -*-
"""测字规则引擎（《测字秘牒》程省 + 《梅花易数》卷四五相字术）——拆字十法 / 心易六法 / 六神 / 五行体。

收口「测字 —— C 类（纯文本，部分可规则化）」的「①测字十法拆形规则」：把 `references/相字术速查.md`
的测字十法 / 心易六法 / 六神主事 / 六神笔法 / 起六神卦诀 / 五行体格式 结构化进代码，供测字断卦
「查表 + 规则判定」——测字靠触机，「神而明之存乎其人」，本引擎只做确定性数据层 + 规则层，
拆字成何字、取何义仍是断卦时据所问之事触机而断（不承诺必然，断语 Grep 典籍原文佐证）。

原则与 shefu_portrait/miaogong_shefu 一致：返回 result（内容）非吉凶，降分辨率、不硬断。

用法：
  from judge.cezi import cezi_shifa, cezi_qigua, cezi_zhushi, cezi_bifa, cezi_wuxing_ti, portrait_cezi
"""
import sys
import os

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

SOURCE_SHI = "《测字秘牒》卷一·测字十法"
SOURCE_XINYI = "《测字秘牒》卷二·心易六法"
SOURCE_QG = "《梅花易数》卷四·笔法筌蹄"
SOURCE_WX = "《梅花易数》卷四·五行体格式"

# —— 测字十法：法名 -> (操作, 例) ——
SHIFA = {
    "装头": ("添笔于字首，如神龙见首", "戊→茂、日→春、早→章"),
    "接脚": ("添笔于字脚，如人举足", "采→悉释番、立→产童、千→秀壬"),
    "穿心": ("字画端正而从中穿入数笔", "文→吏、月→舟用冉、昌→量"),
    "包笼": ("字全体不动，以笔周围包裹", "玉→宝、贝→遗测、矢→族"),
    "破解": ("劈破、解拆字之体段", "行→术衙衍、辛→章、共→莫黄"),
    "添笔": ("添以补不足", "唯→难、王→玉全旺、才→财"),
    "减笔": ("减以损有余（非事当理正不可用）", "混入摘字法则非"),
    "对关": ("专取头足首尾，关开门闭", "头尾阖之如门闭、分开如门开（字中第一要义）"),
    "摘字": ("摘字中一二笔画以断", "借旁人言语、万物影响"),
    "观梅": ("不依程式，心镜光明、随物洞照", "邵子心诀，至精之诀"),
}

# —— 心易六法（六书取义）：法名 -> (操作, 例) ——
XINYI = {
    "象形": ("以字象物、以物象字、以字象字、以意象字", "乙似鱼钩、弓似蛇；烟（因风吹火）"),
    "会意": ("合字形之意成象", "淋=楚汉争锋主口角；霏=长虹截雨主阻隔"),
    "假借": ("借四时/人事/事物为用", "旦借春、千借夏、甲借秋、夕借冬"),
    "谐声": ("借同音字取义", "倒到、秤称、桃逃、梨离、莺（阴）主天阴"),
    "指事": ("因事即断，审情性、察动静、明踪迹", "观人/察色/辨言/辨事/察墨/辨纸/观时/相机等十法"),
    "转注": ("一字多义多音，随机应变", "为（平/去）、行（蘅/杭/沆/慎）、王（平/旺）"),
}

# —— 六神主事（测字取象）：六神 -> 主事 ——
LIUYAO_ZHUSHI = {
    "青龙": "喜庆、贵人、得水、升迁、生机",
    "朱雀": "口舌、文书、音信、是非",
    "勾陈": "牵连、田土、五鬼、发动",
    "螣蛇": "虚惊、缠绕、怪异、梦魇",
    "白虎": "凶伤、血光、孝服、争斗",
    "玄武": "盗骗、暗昧、小人刁唆、私情",
}

# —— 六神笔法（字形辨识）：六神 -> 笔法 ——
LIUYAO_BIFA = {
    "青龙": "撇长回锋、钩弯向上、字势上扬，蚕头燕额",
    "朱雀": "点画尖利、撇捺如鸟喙、口字密集，尖短交加",
    "勾陈": "方框平直、折笔方正、横平竖直，弯弓斜月",
    "螣蛇": "笔画盘曲、回环缠绕、走向不定，长曲势如行",
    "白虎": "撇捺如刀、锋芒外露、钩折带刃，尾尖口阔",
    "玄武": "三点水斜、笔画柔曲圆转、含混，体态方尖",
}

# —— 起六神卦诀：日干 -> 六神（甲乙起青龙…壬癸起玄武） ——
_QIGUA = {"甲": "青龙", "乙": "青龙", "丙": "朱雀", "丁": "朱雀",
          "戊": "勾陈", "己": "螣蛇", "庚": "白虎", "辛": "白虎",
          "壬": "玄武", "癸": "玄武"}

# —— 六神主事吉凶（原文「青龙主喜事…玄武主盗贼」） ——
_LIUYAO_JX = {"青龙": "吉", "白虎": "凶", "朱雀": "凶", "勾陈": "凶", "螣蛇": "凶", "玄武": "凶"}

# —— 五行体格式（字形笔法五行属性）：五行 -> 描述 ——
WUXING_TI = {
    "木": "木长性聪明，木短定功名。木多才学敏，木斜废支撑。",
    "火": "火重性不常，火燥见灾殃。火多攻心腹，火轻足衣粮。",
    "土": "土重根基好，土轻离祖居。土滞破田宅，土定无虚图。",
    "金": "金方利身主，金重性多剐。金走为神动，慷慨及门墙。",
    "水": "水圆多性巧，浊者定昏迷。水泛为不定，水走必东西。",
}


def _r(result, conf, basis):
    return {"result": result, "confidence": conf, "basis": basis}


def cezi_shifa(fa_name):
    """测字十法：法名 -> (操作, 例)。R-CZ-01"""
    if fa_name not in SHIFA:
        return _r(None, "低", f"「{fa_name}」非测字十法（装头/接脚/穿心/包笼/破解/添笔/减笔/对关/摘字/观梅）")
    op, ex = SHIFA[fa_name]
    return _r(f"{fa_name}：{op}（例：{ex}）", "高", f"{SOURCE_SHI}·{fa_name}")


def cezi_xinyi(fa_name):
    """心易六法：法名 -> (操作, 例)。R-CZ-02"""
    if fa_name not in XINYI:
        return _r(None, "低", f"「{fa_name}」非心易六法（象形/会意/假借/谐声/指事/转注）")
    op, ex = XINYI[fa_name]
    return _r(f"{fa_name}：{op}（例：{ex}）", "高", f"{SOURCE_XINYI}·{fa_name}")


def cezi_qigua(day_gan):
    """起六神卦诀：日干 -> 六神。R-CZ-03（甲乙起青龙…壬癸起玄武）"""
    shen = _QIGUA.get(day_gan)
    if not shen:
        return _r(None, "低", f"日干「{day_gan}」非十干")
    return _r(f"{day_gan}日起{shen}", "高", f"{SOURCE_QG}·六神起卦诀")


def cezi_zhushi(shen):
    """六神主事：六神 -> 主事（测字取象）。R-CZ-04"""
    if shen not in LIUYAO_ZHUSHI:
        return _r(None, "低", f"「{shen}」非六神（青龙/朱雀/勾陈/螣蛇/白虎/玄武）")
    jx = _LIUYAO_JX.get(shen, "中")
    return _r(f"{shen}主{LIUYAO_ZHUSHI[shen]}（{jx}）", "高", f"{SOURCE_QG}·六神主事")


def cezi_bifa(shen):
    """六神笔法：六神 -> 笔法（字形辨识）。R-CZ-05"""
    if shen not in LIUYAO_BIFA:
        return _r(None, "低", f"「{shen}」非六神")
    return _r(f"{shen}：{LIUYAO_BIFA[shen]}", "高", f"{SOURCE_QG}·笔法筌蹄")


def cezi_wuxing_ti(wx):
    """五行体格式：五行 -> 字形笔法属性。R-CZ-06"""
    if wx not in WUXING_TI:
        return _r(None, "低", f"「{wx}」非五行（木火土金水）")
    return _r(f"{wx}体：{WUXING_TI[wx]}", "高", f"{SOURCE_WX}")


def portrait_cezi(zi, day_gan, fa_name=""):
    """测字画像聚合：字 + 日干 + 拆法 -> {拆法, 六神, 主事, 笔法, 五行体}。

    供测字断卦「查表 + 规则判定」：拆法给字形操作、六神给主事吉凶向、五行体给字形属性。
    拆字成何字、取何义仍是触机而断（心易六法据所问之事取义），本函数只给结构化判定层。"""
    out = {}
    if fa_name:
        out["拆法"] = cezi_shifa(fa_name)
    qg = cezi_qigua(day_gan)
    out["起六神"] = qg
    shen = qg["result"].split("起")[-1] if qg["result"] else None
    if shen:
        out["六神主事"] = cezi_zhushi(shen)
        out["六神笔法"] = cezi_bifa(shen)
    return {"字": zi, "画像": out}


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    zi, day_gan = a[0], (a[1] if len(a) > 1 else "甲")
    fa = a[2] if len(a) > 2 else ""
    p = portrait_cezi(zi, day_gan, fa)
    print(f"🔬 测字画像（{zi}，{day_gan}日）")
    for k, v in p["画像"].items():
        if v and v.get("result"):
            print(f"  {k}  [{v['confidence']}] {v['result']}")


if __name__ == "__main__":
    main()
