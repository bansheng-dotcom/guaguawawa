# -*- coding: utf-8 -*-
"""断卦规则引擎：把「断：体用生克」这类开放提示落成可判定、可回归测试的 if-then 规则函数。

每条规则返回结构化判定 dict：
  {judgment: 吉/凶/中, confidence: 高/中/低, evidence: 规则ID, basis: 依据说明}
断卦时优先调用这些规则；规则覆盖不到的再标 [规则推演]，不得凭空 [主观推断]。

规则 ID 即「证据编号」：每条断语可回溯到 R-XX-NN 规则号。
"""
from judge import qimen_keying
from judge.qimen_angan import angan_pan as _angan_pan
from judge import liuren_shensha
from judge import liuren_bifa
from pan import jinkoujue
import xingchong

_GAN = "甲乙丙丁戊己庚辛壬癸"
_ZHI = "子丑寅卯辰巳午未申酉戌亥"
_WX = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
_ZHI_WX = {"寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金",
           "亥": "水", "子": "水", "辰": "土", "戌": "土", "丑": "土", "未": "土"}

# 典籍出处指针（断卦时仍须按此 Grep 原文佐证，双重保证）
_SRC_XJBFS = "《钦定协纪辨方书》"
_SRC_XLK = "《御定星历考原》"


# —— 返回契约（三种形状，各司其职） ——
# 1. 吉凶规则函数（走 _r）：{"judgment": 吉/凶/中, "confidence", "evidence", "basis"}
# 2. 射覆/物类函数（jinkoujue_shefu_* / miaogong_shefu）：{"result": 物类内容, ...} —— result 是「内容」非「吉凶」
# 3. 交叉验证（cross_validate / fusion_mark）：{"verdict": 一致/冲突/互补, ...} —— verdict 是「一致性结论」
# 流派分歧（UND）一律返回 None + 标「流派分歧」，不臆造。
def _r(j, conf, ev, basis):
    return {"judgment": j, "confidence": conf, "evidence": ev, "basis": basis}


# —— 小六壬 ——
_LIU_GONG_JI_XIONG = {"大安": ("吉", "安稳顺遂"), "留连": ("中", "拖延纠缠"),
                      "速喜": ("吉", "快速喜庆"), "赤口": ("凶", "口舌官非"),
                      "小吉": ("吉", "和合小吉"), "空亡": ("凶", "落空无果")}


def xiaoliuren(gong):
    """小六壬六宫吉凶。R-XLR-01"""
    j, m = _LIU_GONG_JI_XIONG.get(gong, ("中", "未明"))
    return _r(j, "高", "R-XLR-01", f"落宫「{gong}」主{m}")


# —— 梅花易数 ——
def meihua(wx_body, wx_yong):
    """梅花体用生克。R-MH-01"""
    if wx_yong == wx_body:
        return _r("吉", "高", "R-MH-01", f"体用比和（{wx_body}）同心可成")
    if _KE.get(wx_yong) == wx_body:
        return _r("凶", "高", "R-MH-01", f"用克体（{wx_yong}克{wx_body}）对方压制，宜避缓")
    if _SHENG.get(wx_yong) == wx_body:
        return _r("吉", "高", "R-MH-01", f"用生体（{wx_yong}生{wx_body}）有助力")
    if _KE.get(wx_body) == wx_yong:
        return _r("中", "中", "R-MH-01", f"体克用（{wx_body}克{wx_yong}）费力可成")
    if _SHENG.get(wx_body) == wx_yong:
        return _r("中", "中", "R-MH-01", f"体生用（{wx_body}生{wx_yong}）泄气，付出多回报少")
    return _r("中", "低", "R-MH-01", "生克关系未明")


def meihua_probability(wx_body, wx_yong):
    """梅花体用生克 → 成事/得物概率档（借鉴 yijing-find-lost-item 风险等级表）。R-MH-02
    用于测物/寻物/求成事的「概率」量化，档位：极高/较高/中等/较低/很低。"""
    if _SHENG.get(wx_yong) == wx_body:
        return _r("极高", "高", "R-MH-02", f"用生体（{wx_yong}生{wx_body}）主动来助/易得")
    if wx_yong == wx_body:
        return _r("较高", "高", "R-MH-02", f"体用比和（{wx_body}）同心/在常处")
    if _KE.get(wx_body) == wx_yong:
        return _r("中等", "中", "R-MH-02", f"体克用（{wx_body}克{wx_yong}）费力可得")
    if _KE.get(wx_yong) == wx_body:
        return _r("较低", "高", "R-MH-02", f"用克体（{wx_yong}克{wx_body}）受制较难")
    if _SHENG.get(wx_body) == wx_yong:
        return _r("很低", "中", "R-MH-02", f"体生用（{wx_body}生{wx_yong}）泄气，可能已损/难成")
    return _r("中等", "低", "R-MH-02", "生克关系未明")


# 梅花十八类占：每类「以体为主、用为××」取用规则 + 五种生克快断（据《梅花易数》卷二「十八类占」）
_MEIHUA_18LEI = {
    "天时": {"special": "不分体用，全观诸卦详推五行——离多主晴、坎多主雨、坤主阴晦、乾主晴明、震多春夏雷、巽多四时风、艮多久雨必晴、兑多不雨亦阴"},
    "人事": {"ti": "本人", "yong": "所谋之事/对方", "体克用": ("吉", "谋为可成"), "用克体": ("凶", "事克我不宜"), "体生用": ("中", "有耗失之患"), "用生体": ("吉", "有进益之喜"), "比和": ("吉", "谋为吉利")},
    "家宅": {"ti": "本人", "yong": "家宅", "体克用": ("吉", "家宅多吉"), "用克体": ("凶", "家宅多凶"), "体生用": ("中", "多耗散防失盗"), "用生体": ("吉", "多进益有馈送"), "比和": ("吉", "家宅安稳")},
    "屋舍": {"ti": "本人", "yong": "屋舍", "体克用": ("吉", "居之吉"), "用克体": ("凶", "居之凶"), "体生用": ("中", "资财衰退"), "用生体": ("吉", "门户兴隆"), "比和": ("吉", "自然安稳")},
    "婚姻": {"ti": "所占之家", "yong": "所婚之家", "体克用": ("中", "可成但迟"), "用克体": ("凶", "不可成，成亦有害"), "体生用": ("中", "婚难成或有失"), "用生体": ("吉", "婚易成或有得"), "比和": ("吉", "婚姻吉利")},
    "生产": {"ti": "母", "yong": "子/生产", "体克用": ("中", "不利于子"), "用克体": ("凶", "不利于母"), "体生用": ("中", "利于子"), "用生体": ("吉", "利于母"), "比和": ("吉", "生育顺快")},
    "饮食": {"ti": "本人", "yong": "饮食", "体克用": ("中", "饮食有阻"), "用克体": ("凶", "饮食必无"), "体生用": ("中", "饮食难就"), "用生体": ("吉", "饮食必丰"), "比和": ("吉", "饮食丰足")},
    "求谋": {"ti": "本人", "yong": "所谋之事", "体克用": ("中", "谋可成但迟"), "用克体": ("凶", "求谋不成且有害"), "体生用": ("中", "多谋少遂"), "用生体": ("吉", "不谋而成"), "比和": ("吉", "求谋称意")},
    "求名": {"ti": "本人", "yong": "名声/功名", "体克用": ("中", "名可成但迟"), "用克体": ("凶", "名不可成"), "体生用": ("凶", "名不可就，或因名有丧"), "用生体": ("吉", "名易成，或因名有得"), "比和": ("吉", "功名称意")},
    "求财": {"ti": "本人", "yong": "财", "体克用": ("吉", "有财"), "用克体": ("凶", "无财"), "体生用": ("中", "财有损耗之忧"), "用生体": ("吉", "财有进益之喜"), "比和": ("吉", "财利快意")},
    "交易": {"ti": "本人", "yong": "交易/财", "体克用": ("吉", "有财"), "用克体": ("凶", "不成"), "体生用": ("中", "难成或有失"), "用生体": ("吉", "即成且有财"), "比和": ("吉", "易成")},
    "出行": {"ti": "本人", "yong": "所行之应", "体克用": ("吉", "可行，所至得意"), "用克体": ("凶", "出则有祸"), "体生用": ("中", "有破耗之失"), "用生体": ("吉", "有意外之财"), "比和": ("吉", "出行顺快")},
    "行人": {"ti": "在家者", "yong": "行人", "体克用": ("中", "行人归迟"), "用克体": ("凶", "行人不归"), "体生用": ("中", "行人未归"), "用生体": ("吉", "行人即归"), "比和": ("吉", "归期不日")},
    "谒见": {"ti": "本人", "yong": "所见之人", "体克用": ("吉", "可见"), "用克体": ("凶", "不见"), "体生用": ("中", "难见，见亦无益"), "用生体": ("吉", "可见且有得"), "比和": ("吉", "欢然相见")},
    "失物": {"ti": "本人", "yong": "失物", "体克用": ("中", "可寻，迟得"), "用克体": ("凶", "不可寻"), "体生用": ("中", "物难见"), "用生体": ("吉", "物易寻"), "比和": ("吉", "物不失")},
    "疾病": {"ti": "病人", "yong": "病症", "体克用": ("吉", "病易安，勿药有喜"), "用克体": ("凶", "病难愈，虽药无功"), "体生用": ("中", "迁延难好"), "用生体": ("吉", "即愈"), "比和": ("吉", "疾病易安")},
    "官讼": {"ti": "本人", "yong": "对辞之人/官讼", "体克用": ("吉", "己胜人"), "用克体": ("凶", "人胜己"), "体生用": ("中", "非失理，或因官有丧"), "用生体": ("吉", "得理，或因讼有得"), "比和": ("吉", "官讼最吉，主和")},
    "坟墓": {"ti": "本人", "yong": "坟墓", "体克用": ("吉", "葬之吉"), "用克体": ("凶", "葬之凶"), "体生用": ("中", "葬主运退"), "用生体": ("吉", "葬主兴隆，荫益后嗣"), "比和": ("吉", "吉地，葬之吉昌")},
}


def meihua_18lei(lei, wx_body, wx_yong):
    """梅花十八类占：按类取「体/用」角色 + 生克快断。R-MH-03
    lei=类名（人事/家宅/婚姻/求财/失物/疾病/官讼…），wx_body=体卦五行，wx_yong=用卦五行。
    出处《梅花易数》卷二十八类占，断卦按类名 Grep 原文佐证。"""
    info = _MEIHUA_18LEI.get(lei)
    if not info:
        return _r("中", "低", "R-MH-03", f"「{lei}」非十八类占之一")
    if "special" in info:
        return _r("中", "高", "R-MH-03", f"天时占：{info['special']}（出处《梅花易数·天时占第一》，断卦 Grep「天时占」原文）")
    if _KE.get(wx_yong) == wx_body:
        rel = "用克体"
    elif _KE.get(wx_body) == wx_yong:
        rel = "体克用"
    elif _SHENG.get(wx_yong) == wx_body:
        rel = "用生体"
    elif _SHENG.get(wx_body) == wx_yong:
        rel = "体生用"
    else:
        rel = "比和"
    j, m = info[rel]
    return _r(j, "高", "R-MH-03",
              f"{lei}占（体={info['ti']}，用={info['yong']}）：{rel}（{wx_yong}vs{wx_body}）→ {m}（出处《梅花易数·{lei}占》，断卦 Grep「{lei}占」原文）")


def meihua_wangshuai(wx, month_zhi=""):
    """梅花卦气旺衰（衰旺论）。R-MH-04
    wx=体卦五行，month_zhi=月支（寅卯木旺、巳午火旺、申酉金旺、亥子水旺、辰戌丑未土旺）。
    旺=当令；相=得月令生；衰=受月令克；休=泄气/克它。出处《梅花易数·卦气旺/卦气衰/衰旺论》。"""
    if not month_zhi:
        return _r("中", "低", "R-MH-04", "未给月令，卦气旺衰需月支判断")
    mwx = _ZHI_WX.get(month_zhi, "")
    if not mwx:
        return _r("中", "低", "R-MH-04", f"月支「{month_zhi}」无法判五行")
    if wx == mwx:
        return _r("旺", "高", "R-MH-04", f"体卦{wx}当令（月支{month_zhi}属{mwx}）乘旺，虽受克亦无大害")
    if _SHENG.get(mwx) == wx:
        return _r("相", "高", "R-MH-04", f"体卦{wx}得月令生扶（{month_zhi}属{mwx}生{wx}），旺而有生则吉")
    if _KE.get(mwx) == wx:
        return _r("衰", "高", "R-MH-04", f"体卦{wx}受月令克（{month_zhi}属{mwx}克{wx}），衰而逢克则凶甚")
    return _r("休", "中", "R-MH-04", f"体卦{wx}于月令{month_zhi}（{mwx}）休囚，宜守")


# 梅花「以变卦断物」（变卦式八则）——五行→物类
_BIANYAO_WULEI = {
    "金": "铁器、金属、铜钱、破磁盘瓦石（刚硬；天泽履断铁器、泽天夬断破磁盘、雷泽归妹断铁）",
    "木": "软物、文章之体、竹草木（地雷复「木是用爻断软物文章之体」）",
    "土": "土物、瓦石（泽火革「用金体火夏火旺出土必土物」）",
    "火": "火类、光明、文书、彩绘（离，近日远取雉）",
    "水": "水类、柔软、流动（坎）",
}


def meihua_bianyao_shefu(bian_yao_wx):
    """梅花「以变卦断物」（变卦式八则）。R-MH-05
    测物/断物除体用外，取「变出何卦、变爻属何五行，即以该五行断物类」——变爻五行 → 物类候选。
    出处《梅花易数》·变卦式八则，断卦 Grep 卦名原文佐证。"""
    val = _BIANYAO_WULEI.get(bian_yao_wx)
    if not val:
        return _r("中", "低", "R-MH-05", f"变爻五行「{bian_yao_wx}」无物类映射")
    return _r(val, "高", "R-MH-05", f"变爻{bian_yao_wx} → {val}（《梅花易数》·变卦式八则）")


# —— 八字旺衰（第一维：得令） ——
def bazi_deling(day_gan, month_zhi):
    """八字旺衰·得令。R-BZ-01"""
    day_wx = _WX.get(day_gan, "")
    ling = _ZHI_WX.get(month_zhi, "")
    if day_wx == ling:
        return _r("旺", "高", "R-BZ-01", f"日主{day_wx}得月令{ling}（比劫）")
    if _SHENG.get(ling) == day_wx:
        return _r("旺", "高", "R-BZ-01", f"月令{ling}生日主{day_wx}（印）")
    if _KE.get(ling) == day_wx:
        return _r("弱", "高", "R-BZ-01", f"月令{ling}克日主{day_wx}（官杀）")
    return _r("弱", "中", "R-BZ-01", f"日主{day_wx}失令于月令{ling}（食伤/财）")


# —— 八字流年/合婚（干支关系、岁运、喜忌） ——
def bazi_zhi_relation(z1, z2):
    """八字·两两地支关系。R-BZ-02"""
    r = xingchong.zhi_relation(z1, z2)
    if r["主关系"] == "平":
        return _r("中", "高", "R-BZ-02", f"{z1}{z2}无合冲刑害")
    desc = "；".join(f"{x['关系']}" for x in r["关系列表"])
    j = "凶" if r["吉凶"] in ("凶", "半凶") else ("吉" if r["吉凶"] in ("吉", "半吉") else "中")
    return _r(j, "高", "R-BZ-02", f"{z1}{z2}：{desc}")


def bazi_gan_he(g1, g2):
    """八字·两天干五合/相克。R-BZ-03"""
    r = xingchong.gan_relation(g1, g2)
    j = "吉" if r["吉凶"] == "吉" else ("凶" if r["吉凶"] == "凶" else "中")
    return _r(j, "高", "R-BZ-03", f"{g1}{g2}：{r['含义']}")


def bazi_suiyun_binglin(liunian_gz, dayun_gz):
    """八字·岁运并临（流年干支==大运干支）。R-BZ-04"""
    if dayun_gz and liunian_gz == dayun_gz:
        return _r("凶", "高", "R-BZ-04",
                  f"岁运并临（流年{liunian_gz}与大运{dayun_gz}干支相同），伏吟，吉凶加倍——逢喜则喜、逢忌则忌")
    return _r("中", "低", "R-BZ-04", "非岁运并临")


def bazi_tianke_dichong(liunian_gz, rizhu_gz):
    """八字·天克地冲（流年干克日干且流年支冲日支）。R-BZ-05"""
    lg, lz = liunian_gz[0], liunian_gz[1]
    rg, rz = rizhu_gz[0], rizhu_gz[1]
    ke = xingchong.gan_relation(lg, rg)["关系"] == "相克"
    chong = any(x["关系"] == "六冲" for x in xingchong.zhi_relation(lz, rz)["关系列表"])
    if ke and chong:
        return _r("凶", "高", "R-BZ-05",
                  f"流年{liunian_gz}天克地冲日柱{rizhu_gz}（{lg}克{rg}且{lz}冲{rz}），变动大，防婚恋/健康/事业波动")
    return _r("中", "低", "R-BZ-05", "非天克地冲日柱")


def bazi_liunian_xiji(liunian_gan, xi, ji):
    """八字·流年天干五行喜忌。R-BZ-06。xi/ji 为五行集合（扶抑喜忌）。"""
    wx = _WX.get(liunian_gan, "")
    if wx in xi:
        return _r("吉", "中", "R-BZ-06", f"流年天干{liunian_gan}({wx})为喜神（喜{''.join(sorted(xi))}），主助力")
    if wx in ji:
        return _r("凶", "中", "R-BZ-06", f"流年天干{liunian_gan}({wx})为忌神（忌{''.join(sorted(ji))}），主压力")
    return _r("中", "低", "R-BZ-06", f"流年天干{liunian_gan}({wx})喜忌未明")


def bazi_fantaisui(liunian_zhi, nian_zhi):
    """八字·犯太岁（值/冲/刑/害/破年支）。R-BZ-07"""
    if liunian_zhi == nian_zhi:
        return _r("中", "高", "R-BZ-07", f"流年支{liunian_zhi}值太岁（本命年），宜稳不宜冲")
    r = xingchong.zhi_relation(liunian_zhi, nian_zhi)
    bad = [x["关系"] for x in r["关系列表"] if x["吉凶"] in ("凶", "半凶")]
    if bad:
        return _r("凶", "高", "R-BZ-07", f"流年支{liunian_zhi}对年支{nian_zhi}犯{'、'.join(bad)}，犯太岁，宜谨守")
    return _r("中", "低", "R-BZ-07", f"流年支{liunian_zhi}不犯年支{nian_zhi}")


def bazi_wangshuai_level(score):
    """八字·旺衰量化档次。R-BZ-08。score 为 0-100 旺衰得分（权重法）。"""
    if score > 55:
        return _r("强", "中", "R-BZ-08", f"旺衰得分 {score} → 身强（>55），喜克泄耗")
    if score >= 45:
        return _r("中", "中", "R-BZ-08", f"旺衰得分 {score} → 中和（45-55），喜忌需结合调候格局")
    return _r("弱", "中", "R-BZ-08", f"旺衰得分 {score} → 身弱（<45），喜生扶")


def bazi_geju_chengjiu(judge):
    """八字·格局成破救应。R-BZ-09。judge 为 成格/破格/破格有救。"""
    if judge == "成格":
        return _r("吉", "中", "R-BZ-09", "格局成格，无破格十神，主顺遂")
    if judge == "破格有救":
        return _r("中", "中", "R-BZ-09", "格局破格但有救应，有波折可化解")
    if judge == "破格":
        return _r("凶", "中", "R-BZ-09", "格局破格且无救应，防对应事项之失")
    return _r("中", "低", "R-BZ-09", "格局成破未明")


# —— 择日 ——
_JIANCHU = {"建": "小吉", "除": "吉", "满": "吉", "平": "平", "定": "吉", "执": "吉",
            "破": "大凶", "危": "小凶", "成": "大吉", "收": "吉", "开": "大吉", "闭": "凶"}
_HUANGDAO = {"明堂": "吉", "玉堂": "吉", "青龙": "吉", "金匮": "吉", "天德": "吉", "司命": "吉",
             "天刑": "凶", "朱雀": "凶", "白虎": "凶", "天牢": "凶", "玄武": "凶", "勾陈": "凶"}


def zeri_jianchu(jianchu):
    """择日·建除十二神。R-ZR-01"""
    g = _JIANCHU.get(jianchu, "平")
    j = "吉" if "吉" in g and "凶" not in g else ("凶" if "凶" in g else "中")
    return _r(j, "高", "R-ZR-01", f"建除「{jianchu}」为{g}")


def zeri_huangdao(huangdao):
    """择日·黄道黑道。R-ZR-02"""
    g = _HUANGDAO.get(huangdao)
    if g == "吉":
        return _r("吉", "高", "R-ZR-02", f"黄道「{huangdao}」吉")
    if g == "凶":
        return _r("凶", "高", "R-ZR-02", f"黑道「{huangdao}」凶")
    return _r("中", "低", "R-ZR-02", f"「{huangdao}」未明")


# —— 老黄历补全（结构化判定层：给出方向 + 出处指针，原文仍由 Grep 检索佐证） ——
def zeri_zhishen(zhi_shen):
    """老黄历·十二值神吉凶（协纪辨方书精确起法）。R-ZR-03"""
    g = _HUANGDAO.get(zhi_shen)
    if g == "吉":
        return _r("吉", "高", "R-ZR-03",
                  f"值神「{zhi_shen}」黄道吉神（出处：{_SRC_XJBFS}·十二值神，断卦按值神名 Grep 原文佐证）")
    if g == "凶":
        return _r("凶", "高", "R-ZR-03",
                  f"值神「{zhi_shen}」黑道凶神（出处：{_SRC_XJBFS}·十二值神，断卦按值神名 Grep 原文佐证）")
    return _r("中", "低", "R-ZR-03", f"值神「{zhi_shen}」未明")


def zeri_pengzu(gan_ji, zhi_ji):
    """老黄历·彭祖百忌（当日禁忌，非吉凶定档，标「避」）。R-ZR-04"""
    return _r("中", "高", "R-ZR-04",
              f"彭祖百忌：{gan_ji}；{zhi_ji}——当日所忌之事宜避（出处：{_SRC_XJBFS}·彭祖百忌，断卦 Grep「彭祖百忌」原文佐证）")


def zeri_fangwei(fw):
    """老黄历·吉神方位（喜神/财神/福神/阳贵/阴贵，供趋吉择向）。R-ZR-05"""
    parts = " ".join(f"{k}{fw.get(k, '')}" for k in ("喜神", "财神", "福神", "阳贵", "阴贵") if fw.get(k))
    return _r("吉", "高", "R-ZR-05",
              f"吉神方位：{parts}——求财谒贵宜向财神/贵人方（出处：{_SRC_XJBFS}·吉神方位，断卦按「喜神/财神/福神/贵人」Grep 原文佐证）")


# —— 奇门遁甲（结构化规则：判定 + 典籍出处指针，原文仍由 Grep 检索佐证） ——
_QIMEN_MEN = {"开": ("吉", "宜开创、出行、远行"), "休": ("吉", "宜休养、求财、交易"),
              "生": ("吉", "宜求财、经营、种植"), "伤": ("凶", "宜捕猎、讨债，余事忌"),
              "杜": ("中", "宜藏形、躲避，主阻隔"), "景": ("中", "宜上书、考试、广告"),
              "死": ("凶", "宜吊丧、行刑，余事大凶"), "惊": ("凶", "主惊恐、口舌、官司")}
_QIMEN_STAR = {"天心": ("吉", "宜疗病、求谋"), "天任": ("吉", "宜求财、婚嫁"),
               "天辅": ("吉", "宜求学、文书"), "天禽": ("吉", "宜祭祀、祈福"),
               "天冲": ("中", "宜出师、报仇"), "天蓬": ("凶", "宜守不宜动"),
               "天芮": ("凶", "宜求医（主疾病）"), "天柱": ("凶", "宜守、忌争讼"),
               "天英": ("凶", "宜文书、忌远行")}
_QIMEN_SHEN = {"值符": ("吉", "百恶消散"), "太阴": ("吉", "宜密谋、藏避"),
               "六合": ("吉", "宜婚嫁、交易"), "九地": ("吉", "宜屯守、埋藏"),
               "九天": ("吉", "宜扬兵、出行"), "腾蛇": ("凶", "主虚惊、怪异"),
               "白虎": ("凶", "主血光、杀伤"), "玄武": ("凶", "主盗骗、暗昧")}
_QIMEN_MEN_WX = {"开": "金", "休": "水", "生": "土", "伤": "木", "杜": "木", "景": "火", "死": "土", "惊": "金"}
_QIMEN_GONG_WX = {"坎": "水", "坤": "土", "震": "木", "巽": "木", "中": "土", "乾": "金", "兑": "金", "艮": "土", "离": "火"}
_WUBUYUSHI = {"甲": "庚", "乙": "辛", "丙": "壬", "丁": "癸", "戊": "甲",
              "己": "乙", "庚": "丙", "辛": "丁", "壬": "戊", "癸": "己"}


def qimen_men(men):
    """奇门八门吉凶。R-QM-01"""
    j, m = _QIMEN_MEN.get(men, ("中", "未明"))
    return _r(j, "高", "R-QM-01", f"八门「{men}」{m}（出处：《奇门遁甲统宗》《奇门遁甲秘笈大全》）")


def qimen_star(star):
    """奇门九星吉凶。R-QM-02"""
    j, m = _QIMEN_STAR.get(star, ("中", "未明"))
    return _r(j, "高", "R-QM-02", f"九星「{star}」{m}（出处：《奇门遁甲统宗》）")


def qimen_shen(shen):
    """奇门八神吉凶。R-QM-03"""
    j, m = _QIMEN_SHEN.get(shen, ("中", "未明"))
    return _r(j, "高", "R-QM-03", f"八神「{shen}」{m}（出处：《奇门遁甲统宗》《烟波钓叟歌》）")


def qimen_menpo(men, gong):
    """奇门门迫：门克宫。R-QM-04"""
    mw, gw = _QIMEN_MEN_WX.get(men), _QIMEN_GONG_WX.get(gong)
    if mw and gw and _KE.get(mw) == gw:
        return _r("凶", "高", "R-QM-04",
                  f"门迫（{men}门{mw}克{gong}宫{gw}），百事不利宜改期换方（出处：《奇门遁甲统宗》）")
    return _r("中", "中", "R-QM-04", "无门迫")


def qimen_geju(tianpan, dipan):
    """奇门十干克应（81 格局，天盘干+地盘干）。R-QM-05"""
    r = qimen_keying.lookup(tianpan, dipan)
    if r["格局"]:
        j = qimen_keying.jx_to_judgment(r["吉凶"])
        return _r(j, "高", "R-QM-05",
                  f"「{r['格局']}」（天盘{tianpan}加地盘{dipan}）：{r['含义']}（出处：{r['出处']}）")
    return _r("中", "低", "R-QM-05", f"天盘{tianpan}加地盘{dipan}非具名格局，依门星神宫生克参断")


def qimen_wubuyushi(day_gan, hour_gan):
    """奇门五不遇时：时干克日干。R-QM-06"""
    if _WUBUYUSHI.get(day_gan) == hour_gan:
        return _r("凶", "高", "R-QM-06",
                  f"五不遇时（{day_gan}日{hour_gan}时，时干克日干），百事不利宜改期（出处：《奇门遁甲统宗》）")
    return _r("中", "中", "R-QM-06", "非五不遇时")


# 六仪击刑：六仪所带地支(甲子戊→子…甲寅癸→寅)与落宫地支相刑的宫位
_QIMEN_JIXING = {"戊": "震", "己": "坤", "庚": "艮", "辛": "离", "壬": "巽", "癸": "巽"}
# 三奇六仪入墓：乙木墓未(坤)、丙丁火墓戌(乾)、戊己土墓辰(巽)、庚辛金墓丑(艮)、壬癸水墓辰(巽)
_QIMEN_MU = {"乙": "坤", "丙": "乾", "丁": "乾", "戊": "巽", "己": "巽",
             "庚": "艮", "辛": "艮", "壬": "巽", "癸": "巽"}
# 三奇得使（值使落宫）：乙逢犬马(乾/离)、丙鼠猴(坎/坤)、丁骑龙虎(巽/艮)
_QIMEN_DESHI = {"乙": ("乾", "离"), "丙": ("坎", "坤"), "丁": ("巽", "艮")}


def qimen_jixing(yi, gong):
    """奇门六仪击刑：六仪所带地支与落宫地支相刑。R-QM-07"""
    jx = _QIMEN_JIXING.get(yi)
    if jx and gong == jx:
        return _r("凶", "高", "R-QM-07",
                  f"六仪「{yi}」落{gong}宫，仪支与宫支相刑为「六仪击刑」，凶灾各别、百事不宜（出处：《奇门遁甲秘笈大全》「六仪击刑何太凶」）")
    return _r("中", "中", "R-QM-07", f"六仪「{yi}」落{gong}宫，无击刑")


def qimen_rumu(gan, gong):
    """奇门三奇六仪入墓：干落其墓库之宫。R-QM-08"""
    mu = _QIMEN_MU.get(gan)
    if mu and gong == mu:
        return _r("凶", "高", "R-QM-08",
                  f"「{gan}」落{gong}宫为「入墓」，图谋不扬、纵见利难得手（出处：《奇门遁甲秘笈大全》「三奇入墓宜细推」）")
    return _r("中", "中", "R-QM-08", f"「{gan}」落{gong}宫，未入墓")


def qimen_deshi(qi, gong):
    """奇门三奇得使：三奇临值使门且值使落其得使宫。R-QM-09"""
    ds = _QIMEN_DESHI.get(qi)
    if ds and gong in ds:
        return _r("吉", "高", "R-QM-09",
                  f"{qi}奇得使（值使落{gong}宫），偏裨效力、急外有助（出处：《烟波钓叟歌》「乙逢犬马丙鼠猴，六丁玉女骑龙虎」）")
    return _r("中", "中", "R-QM-09", f"{qi}奇未得使")


def qimen_yunv(zhishi_gong, ding_gong):
    """奇门玉女守门：值使门与丁奇（玉女）同宫。R-QM-10"""
    if zhishi_gong and ding_gong and zhishi_gong == ding_gong:
        return _r("吉", "高", "R-QM-10",
                  f"值使门与丁奇（玉女）同宫为「玉女守门」，利阴私和合、出入亨通（出处：《烟波钓叟歌》「又有三奇游六仪，号为玉女守门扉」）")
    return _r("中", "中", "R-QM-10", "无玉女守门")


def qimen_angan(shi_gan, zhishi_gong, yinyang, dipan=None):
    """奇门暗干（飞干）：值使门加时干，阳顺阴逆飞九宫，值使门宫内暗干即「飞干」。R-QM-11

    完整算法见 `qimen_angan.angan_pan`：时干(甲遁戊)加值使门落宫，余干按六仪三奇环序
    「戊己庚辛壬癸丁丙乙」阳顺阴逆飞洛书九宫(含中5)。值使门宫内暗干=时干；
    特例(值使门落宫地盘干==时干)时干入中5。三奇(乙丙丁)则暗获、庚辛则暗藏凶。
    """
    ang = _angan_pan(shi_gan, zhishi_gong, yinyang, dipan).get(zhishi_gong)
    j = "吉" if ang in ("乙", "丙", "丁") else ("凶" if ang in ("庚", "辛") else "中")
    note = "，三奇暗获" if ang in "乙丙丁" else ("，庚辛暗藏凶" if ang in "庚辛" else "")
    return _r(j, "高", "R-QM-11",
              f"值使门落{zhishi_gong}宫，门内暗干（飞干）为「{ang}」{note}"
              f"（值使加时干阳顺阴逆飞九宫，出处：《奇门遁甲秘笈大全》「飞干」、《御定奇门宝鉴》）")


# —— 大六壬（结构化判定：十二天将/神煞/毕法赋，原文仍由 Grep 佐证） ——
def liuren_tianjiang(name):
    """大六壬十二天将吉凶。R-LR-01"""
    r = liuren_shensha.tianjiang(name)
    j = "吉" if r["吉凶"] == "吉" else ("凶" if r["吉凶"] == "凶" else "中")
    return _r(j, "高", "R-LR-01",
              f"天将「{name}」{r['主事']}（出处：{r['出处']}，断卦 Grep 天将名原文佐证）")


def liuren_shensha_rule(name, zhi=""):
    """大六壬神煞吉凶。R-LR-02"""
    jx = {"驿马": "中", "桃花": "中", "华盖": "中", "劫煞": "凶", "灾煞": "凶", "岁煞": "凶",
          "日德": "吉", "日禄": "吉", "羊刃": "凶", "天乙贵人": "吉", "月德": "吉",
          "天喜": "吉", "红鸾": "吉", "旬空": "凶",
          "天德": "吉", "天马": "中", "生气": "吉", "死气": "凶", "天医": "吉",
          "月厌": "凶", "皇恩": "吉", "游都": "凶", "鲁都": "凶", "五墓": "凶",
          "岁破": "凶", "月破": "凶", "天罗": "凶", "地网": "凶", "天赦": "吉", "四废": "凶"}.get(name, "中")
    where = f"临{zhi}" if zhi else ""
    return _r(jx, "高", "R-LR-02",
              f"神煞「{name}」{where}（{jx}，出处《六壬大全》《六壬指南》，断卦 Grep 神煞名原文佐证）")


def liuren_bifa_rule(ju):
    """大六壬毕法赋句吉凶。R-LR-03"""
    hits = liuren_bifa.lookup(ju)
    if not hits:
        return _r("中", "低", "R-LR-03",
                  f"毕法赋无「{ju}」直接条目，按课体推演并标 [规则推演]")
    h = hits[0]
    return _r(h["吉凶"], "高", "R-LR-03",
              f"毕法赋「{h['句']}」主{h['主断']}（出处：{h['出处']}，断卦 Grep 条名原文佐证）")


def liuren_bifa_resolve(hits):
    """毕法赋多句同时命中时的取舍/冲突裁决（借鉴 liuren-skill 赋文冲突取舍）。R-LR-04
    hits: [{吉凶, 句, 主断}, ...]。多句同向→取首句为主、余为辅；吉凶矛盾→标「信号冲突」降级。"""
    if not hits:
        return _r("中", "低", "R-LR-04", "毕法赋无命中")
    if len(hits) == 1:
        h = hits[0]
        return _r(h["吉凶"], "高", "R-LR-04", f"毕法赋「{h['句']}」主{h['主断']}")
    jx = {h["吉凶"] for h in hits}
    names = "、".join(h["句"] for h in hits)
    if len(jx) == 1:
        return _r(hits[0]["吉凶"], "高", "R-LR-04",
                  f"毕法赋多句同向（{names}），主取「{hits[0]['句']}」{hits[0]['主断']}，余为辅")
    if "吉" in jx and "凶" in jx:
        return _r("信号冲突", "中", "R-LR-04",
                  f"毕法赋吉凶矛盾（{names}），仅供参考并降级")
    return _r("中", "中", "R-LR-04", f"毕法赋多句偏中（{names}）")


# —— 大六壬金口诀（五动爻吉凶倾向 + 四位总断）——
_JK_WUDONG_JX = {
    "妻动": ("中", "干克方，占主妻妾、官财防损折、外来索取"),
    "官动": ("吉", "神克干，利求官、逢驿马迁官，常人主公府事"),
    "贼动": ("凶", "神克将，内贼生、损财卑幼病、谋望无成"),
    "财动": ("吉", "将克神，利求财、营求有喜，占官不谐"),
    "鬼动": ("凶", "方克干，忧灾怪、口舌喧争、家宅未安泰"),
}


def jinkoujue_wudong(renyuan_wx, guishen_wx, jiang_wx, difen_wx):
    """金口诀五动爻判定。R-JK-01
    输入四位五行（人元/贵神/将神/地分），返回命中的动爻与综合倾向。
    出处《六壬神课金口诀古本》·五动爻诵，断卦按动爻名 Grep 原文佐证。"""
    hits = []
    if _KE.get(renyuan_wx) == difen_wx:
        hits.append("妻动")
    if _KE.get(guishen_wx) == renyuan_wx:
        hits.append("官动")
    if _KE.get(guishen_wx) == jiang_wx:
        hits.append("贼动")
    if _KE.get(jiang_wx) == guishen_wx:
        hits.append("财动")
    if _KE.get(difen_wx) == renyuan_wx:
        hits.append("鬼动")
    if not hits:
        return _r("中", "中", "R-JK-01",
                  "四位无克，不入五动，从旺断（取旺神为用）")
    detail = "、".join(f"{n}（{_JK_WUDONG_JX[n][1]}）" for n in hits)
    jxs = {_JK_WUDONG_JX[n][0] for n in hits}
    if "凶" in jxs and "吉" in jxs:
        j = "信号冲突"
    elif "凶" in jxs:
        j = "凶"
    elif "吉" in jxs:
        j = "吉"
    else:
        j = "中"
    return _r(j, "高", "R-JK-01",
              f"五动爻：{detail}（出处《六壬神课金口诀古本》·五动爻诵，断卦 Grep 动爻名原文佐证）")


# —— 大六壬金口诀·射覆门（射覆歌 + 十干颜色 + 数目 + 射物所在）——
# 射覆是「测物/来意」，返回值是物类候选不是吉凶，故用 result 键（与 miaogong_shefu 一致），
# 供断卦降分辨率出「特征画像」，不押物名。
_JK_SHEFU_ZHILEI = {
    "寅": "衣服（木）", "卯": "草木（东园）", "辰": "药类", "巳": "文章（火雀）",
    "午": "红果文信", "未": "食、衣、黄", "申": "钱纸（金）", "酉": "珍宝光（金）",
    "戌": "谷瓦类（土）", "亥": "绳带细长", "子": "黑文毛墨（水）", "丑": "铁五谷刚（土）",
}

_JK_SHEFU_GUISHEN = {
    "青龙": "钱财、铁、木", "螣蛇": "灰、花、砖瓦", "腾蛇": "灰、花、砖瓦",
    "朱雀": "文书、毛羽兽类、红花锦绣衣", "六合": "器物、草、竹木盘盒",
    "勾陈": "土、泥土砖瓦、破碎伤", "天空": "壶瓶瓦罐（空）",
    "贵人": "牛角、镜、石钱、光明圆滑金", "贵神": "牛角、镜、石钱、光明圆滑金", "天乙": "牛角、镜、石钱、光明圆滑金",
    "天后": "疋缎丝绵、衣帛采绳（见水）", "太阴": "手帕、纸、钱、妇人刀尺耳珠环",
    "玄武": "笔墨、墨斗、石灰木灰木匙", "太常": "饮食、妇人衣、甘美黄白",
    "白虎": "纸布、铜、鼠、骨瓶磁瓶",
}

_JK_SHIGAN_YANSE = {"甲": "青", "乙": "碧", "丙": "赤", "丁": "紫", "戊": "黄",
                    "己": "绛红", "庚": "白", "辛": "灰", "壬": "黑", "癸": "绿"}

_JK_GANZHI_SHU = {"甲": 9, "己": 9, "乙": 8, "庚": 8, "丙": 7, "辛": 7,
                  "丁": 6, "壬": 6, "戊": 5, "癸": 5}
_JK_ZHI_SHU = {"子": 9, "午": 9, "丑": 8, "未": 8, "寅": 7, "申": 7,
               "卯": 6, "酉": 6, "辰": 5, "戌": 5, "巳": 4, "亥": 4}
_JK_WX_SHU = {"水": 1, "火": 2, "木": 3, "金": 4, "土": 5}
_JK_GAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛", "辛": "丙",
              "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}


def _jk_res(result, conf, ev, basis):
    return {"result": result, "confidence": conf, "evidence": ev, "basis": basis}


def jinkoujue_shefu_zhilei(difen_zhi):
    """金口诀射覆门·射覆歌其一：十二地支 → 物类。R-JK-02
    出处《六壬神课金口诀古本》·射覆门·射覆歌，断卦 Grep 支名原文佐证。"""
    val = _JK_SHEFU_ZHILEI.get(difen_zhi)
    if not val:
        return _jk_res(None, "低", "R-JK-02", f"地支「{difen_zhi}」无射覆歌映射")
    return _jk_res(val, "高", "R-JK-02",
                   f"射覆歌：{difen_zhi}为{val}（《六壬神课金口诀古本》·射覆门）")


def jinkoujue_shefu_guishen(guishen_name):
    """金口诀射覆门·射覆歌其二：十二贵神 → 物类。R-JK-03
    出处《六壬神课金口诀古本》·射覆门·射覆歌，断卦 Grep 神名原文佐证。"""
    val = _JK_SHEFU_GUISHEN.get(guishen_name)
    if not val:
        return _jk_res(None, "低", "R-JK-03", f"贵神「{guishen_name}」无射覆歌映射")
    return _jk_res(val, "高", "R-JK-03",
                   f"射覆歌：{guishen_name}为{val}（《六壬神课金口诀古本》·射覆门）")


def jinkoujue_shefu_yanse_shumu(renyuan_gan, yong_zhi="", yong_wx=""):
    """金口诀射覆门：十干颜色 + 支干数目 + 五行数目 + 射物所在。R-JK-04
    renyuan_gan 人元干；yong_zhi 用爻地支（支干数目）；yong_wx 用爻五行（五行数目）。
    出处《六壬神课金口诀古本》·射覆门·十干颜色/支干数目/五行数目/射物所在。"""
    parts = []
    yan = _JK_SHIGAN_YANSE.get(renyuan_gan)
    if yan:
        parts.append(f"十干颜色：{renyuan_gan}主{yan}")
    if renyuan_gan in _JK_GANZHI_SHU:
        parts.append(f"干数目：{renyuan_gan}数{_JK_GANZHI_SHU[renyuan_gan]}")
    if yong_zhi in _JK_ZHI_SHU:
        parts.append(f"支数目：{yong_zhi}数{_JK_ZHI_SHU[yong_zhi]}")
    if yong_wx in _JK_WX_SHU:
        parts.append(f"五行数目：{yong_wx}数{_JK_WX_SHU[yong_wx]}")
    he = _JK_GAN_HE.get(renyuan_gan)
    if he:
        parts.append(f"射物所在：见{renyuan_gan}物在{he}之下（天干合处）")
    if not parts:
        return _jk_res(None, "低", "R-JK-04", "缺人元干/用爻，颜色数目所在难定")
    return _jk_res("；".join(parts), "高", "R-JK-04",
                   f"{'；'.join(parts)}（《六壬神课金口诀古本》·射覆门）")


# —— 太乙神数 ——
_TAIYI_SUAN_JI = ("三才足數", "上和", "下和", "長和", "太和", "中和")
_TAIYI_SUAN_XIONG = ("無天", "無地", "無人", "純陽", "純陰", "雜陽", "雜陰", "重陽", "重陰")


def taiyi_suan(suan):
    """太乙主算/客算/定算的算数吉凶。R-TY-01
    suan 为引擎返回的 list：[算数, [断语...]]，如 [16, ["三才足數", "下和"]]。
    出处《太乙金镜式经》主客算论，断卦按断语 Grep 原文佐证。"""
    tags = []
    if isinstance(suan, list) and len(suan) > 1 and isinstance(suan[1], list):
        tags = [str(t) for t in suan[1]]
    if not tags:
        return _r("中", "低", "R-TY-01", "算数断语缺失，主客算吉凶难判")
    ji = [t for t in tags if t.startswith(_TAIYI_SUAN_JI)]
    xiong = [t for t in tags if t.startswith(_TAIYI_SUAN_XIONG)]
    if xiong and not ji:
        return _r("凶", "高", "R-TY-01",
                  f"算数断语「{'、'.join(xiong)}」主凶（缺三才/阴阳偏极）")
    if ji and not xiong:
        return _r("吉", "高", "R-TY-01",
                  f"算数断语「{'、'.join(ji)}」主吉（三才足数/上下和）")
    if ji and xiong:
        return _r("信号冲突", "中", "R-TY-01",
                  f"算数吉凶断语并存（吉「{'、'.join(ji)}」 vs 凶「{'、'.join(xiong)}」），降级")
    return _r("中", "中", "R-TY-01", f"算数断语「{'、'.join(tags)}」偏中")


def taiyi_zhuke(main_suan, guest_suan):
    """太乙主客胜负：主算 vs 客算 吉凶比较。R-TY-02
    主算吉客算凶→主利客不利（宜守/后发）；主算凶客算吉→客利主不利（宜先发）。"""
    mj = taiyi_suan(main_suan)["judgment"]
    gj = taiyi_suan(guest_suan)["judgment"]
    if "信号冲突" in (mj, gj):
        return _r("信号冲突", "中", "R-TY-02", f"主算/客算吉凶存疑（主{mj} 客{gj}），降级")
    if mj == "吉" and gj in ("凶", "中"):
        return _r("吉", "高", "R-TY-02",
                  f"主算{mj}客算{gj}：主方有利、客方不利，宜守不宜攻、宜后发不宜先发")
    if mj == "凶" and gj in ("吉", "中"):
        return _r("凶", "高", "R-TY-02",
                  f"主算{mj}客算{gj}：客方有利、主方不利，宜先发制人、抢先布局")
    if mj == "吉" and gj == "吉":
        return _r("吉", "中", "R-TY-02", f"主算客算皆吉：主客两利，可进可攻")
    if mj == "凶" and gj == "凶":
        return _r("凶", "高", "R-TY-02", f"主算客算皆凶：两不利，宜缓守静待时机")
    return _r("中", "中", "R-TY-02", f"主算{mj}客算{gj}：主客难分，需合格局/落宫再断")


_TAIYI_GEJU_XIONG = ("掩", "迫", "關", "囚", "擊", "格", "對", "閉")


def taiyi_geju(text):
    """太乙格局（掩/迫/关/囚/击/格/对）吉凶。R-TY-03
    text 可为文昌带格局（如「始擊掩」）、釋格局 dict 的 key、或断语文本。
    出处《太乙秘书》掩格、《太乙金镜式经》格局，断卦按格局名 Grep 原文佐证。"""
    s = str(text)
    hits = [g for g in _TAIYI_GEJU_XIONG if g in s]
    if hits:
        return _r("凶", "高", "R-TY-03",
                  f"犯凶格「{'、'.join(hits)}」：谋事受阻/受制/被动（出处《太乙秘书》，断卦 Grep 格局名原文佐证）")
    return _r("中", "低", "R-TY-03", f"未见掩迫关囚击格对凶格（text={s[:40]}）")


_TAIYI_WANG_JI = ("旺", "相")
_TAIYI_WANG_XIONG = ("死", "囚", "廢", "沒")


def taiyi_luogong_wangshuai(wangshuai):
    """太乙落宫旺衰吉凶。R-TY-04
    旺/相→吉（落宫有力）；死/囚/廢/沒→凶（落宫无力）；胎/休→中。"""
    if wangshuai in _TAIYI_WANG_JI:
        return _r("吉", "高", "R-TY-04", f"太乙落宫「{wangshuai}」有力，可进可主动")
    if wangshuai in _TAIYI_WANG_XIONG:
        return _r("凶", "高", "R-TY-04", f"太乙落宫「{wangshuai}」无力，宜守宜静待")
    return _r("中", "中", "R-TY-04", f"太乙落宫「{wangshuai}」平，合主客算/格局再断")


# —— 多维交叉验证 ——
def cross_validate(dimensions):
    """dimensions: [(维度名, judgment), ...]。多维一致才定论，不一致返回「信号冲突」。

    返回 dict: {verdict: 吉/凶/中/信号冲突, consistent: bool, detail: [...]}
    """
    if not dimensions:
        return {"verdict": "中", "consistent": False, "detail": [], "evidence": "R-XV-01"}
    names = [n for n, _ in dimensions]
    js = [j for _, j in dimensions]
    detail = [f"{n}={j}" for n, j in dimensions]
    uniq = set(js)
    if len(uniq) == 1:
        return {"verdict": js[0], "consistent": True, "detail": detail, "evidence": "R-XV-01",
                "basis": f"{'、'.join(names)} 一致"}
    # 吉/中 与 凶 并存 → 冲突
    if "吉" in uniq and "凶" in uniq:
        return {"verdict": "信号冲突", "consistent": False, "detail": detail, "evidence": "R-XV-01",
                "basis": f"{'、'.join(names)} 吉凶矛盾，仅供参考并降级"}
    if uniq <= {"吉", "中"}:
        return {"verdict": "中", "consistent": False, "detail": detail, "evidence": "R-XV-01",
                "basis": f"{'、'.join(names)} 偏吉但不一致"}
    return {"verdict": "中", "consistent": False, "detail": detail, "evidence": "R-XV-01",
            "basis": f"{'、'.join(names)} 偏凶但不一致"}


# —— 紫微斗数（格局聚合/冲突裁决） ——
def ziwei_geju_resolve(hits):
    """紫微格局命中聚合。R-ZW-01
    hits 为 ziwei_geju.judge_patterns 返回的命中列表（每项含 吉凶/破格）。
    全吉→吉；有凶→凶；吉凶并存→信号冲突降级；破格→降级说明。"""
    if not hits:
        return _r("中", "低", "R-ZW-01", "未见具名格局，按三方四正与主星庙旺断（标 [规则推演]）")
    jxs = {h["吉凶"] for h in hits}
    names = "、".join(h["格局"] for h in hits)
    broken = [h["格局"] for h in hits if h["破格"]]
    if broken:
        return _r("中", "中", "R-ZW-01",
                  f"格局「{names}」中「{'、'.join(broken)}」破格，成格不完整，按破格降级（出处《紫微斗数全书》）")
    if len(jxs) == 1:
        j = next(iter(jxs))
        return _r(j, "高", "R-ZW-01", f"格局「{names}」同向主{'吉' if j == '吉' else ('凶' if j == '凶' else '变动')}")
    if "吉" in jxs and "凶" in jxs:
        return _r("信号冲突", "中", "R-ZW-01",
                  f"格局吉凶并存（{names}），主格需按命宫三方四正再定，仅供参考降级")
    return _r("中", "中", "R-ZW-01", f"格局偏中（{names}）")


# —— 双法同参融合标记（借鉴 laoshifu-mcp） ——
def fusion_mark(verdict_a, verdict_b, same_aspect=True):
    """双法同参三态标记：一致 / 冲突 / 互补。

    - 一致：两法同断同方向；
    - 冲突：两法回答同一侧面（same_aspect=True）但吉凶相反；
    - 互补：两法回答不同侧面（same_aspect=False，如六爻断成败、奇门断时机方位）。
    返回 (标记, 说明)。
    """
    if not same_aspect:
        return "互补", "两法分答不同侧面（成败 vs 时机方位），互相补充不冲突"
    if verdict_a == verdict_b:
        return "一致", f"两法同断「{verdict_a}」"
    if {verdict_a, verdict_b} == {"吉", "凶"}:
        return "冲突", f"两法吉凶相反（{verdict_a} vs {verdict_b}），须降级并说明分歧"
    return "互补", f"两法结论不同但非直接矛盾（{verdict_a} vs {verdict_b}）"


# —— 统一用神接口（骨架：术法+问事 → 用神+出处，数据见 references/用神对应表.md） ——
_YONGSHEN_TABLE = {
    "六爻": {
        "求财": ("妻财", "《火珠林》:46「占求财事皆看财爻」"),
        "求官": ("官鬼", "《火珠林》:46「占求官事皆看官爻」"),
        "婚姻": ("妻财/官鬼", "《火珠林》:46「占婚问夫看官爻，占婚姻事看财爻」"),
        "子女": ("子孙", "《火珠林》:251「占小儿看子孙」"),
        "失物": ("妻财", "《火珠林》:251「失物看财」"),
        "文书": ("父母", "《火珠林》:252「失文书牌号以父母爻取」"),
        "疾病": ("官鬼", "《火珠林》:46「占病鬼祟看官爻」"),
        # —— 王虎应《六爻预测自修宝典》《六爻分类占验技法》事项分工补充 ——
        "考试": ("官鬼+父母", "王虎应·考学看官鬼(名次)+父母(成绩与录取)"),
        "考学": ("官鬼+父母", "王虎应·考学官鬼=名次、父母=成绩"),
        "升学": ("父母", "王虎应·读书上学不争名次，纯看父母(文书学籍)"),
        "诉讼": ("世应强弱", "王虎应·诉讼竞争比赛看世应强弱，对抗型喜我旺彼弱"),
        "官司": ("世应强弱", "王虎应·诉讼对抗型看世应强弱，非单看官鬼"),
        "寻人": ("所寻之人的六亲", "王虎应·行人走失看所寻之人六亲(找父看父母、找子看子孙)，旺相生合世则回"),
        "行人": ("所寻之人的六亲", "王虎应·行人看所寻之人六亲"),
        "寻宠": ("子孙", "《火珠林》:279 六畜以子孙为用"),
        "宠物": ("子孙", "《火珠林》:279 六畜以子孙为用"),
        "出行": ("世爻+父母", "王虎应·出行世爻=本人顺逆、父母=车船工具，出行动而逢合被绊"),
    },
    "大六壬": {
        "求财": ("青龙", "《六壬大全》:1872「求财以青龙为主」"),
        "婚姻": ("六合/青龙", "《六壬大全》:2375「六合喜庆婚姻，青龙应婚姻财宝」"),
        "官爵": ("白虎/太常", "《六壬大全》:1919/1937「占官爵要白虎，占官喜太常」"),
        "疾病": ("忌白虎", "《六壬大全》:1920「占病切忌白虎」"),
        "行人": ("白虎", "《六壬大全》:1920「占行人以虎为准」"),
        "盗贼": ("玄武", "《六壬大全》:1960「占盗贼责玄武」"),
        "文书": ("朱雀", "《六壬大全》:2375「朱雀文书口舌」"),
        "官司": ("勾陈", "《六壬大全》:2375「勾陈主斗讼」"),
        "阴私": ("太阴/天后", "《六壬大全》:2375「天后奸心暗昧，太阴隐晦阴私」"),
    },
    "奇门": {
        "婚姻": ("乙(女)庚(男)六合(媒)", "《秘笈大全》:1732「六乙为女六庚为男六合为媒」"),
        "失物": ("日干(失主)时干(失物)", "《秘笈大全》:1910「日干为失主时干为失物」"),
        "走失": ("时干(失主)六合(逃走之物)", "《秘笈大全》:1736"),
        "求财": ("生门", "《秘笈大全》:1748「生门所落之宫为用」"),
        "词讼": ("惊门/景门", "《秘笈大全》:1788「惊景二门主之」"),
    },
}


def yongshen(shufa, wenshi):
    """统一用神接口：按 术法+问事 返回用神（六爻六亲/六壬天将/奇门类神）+ 出处。
    命中返回 {用神, 出处, limitation}；未命中返回 None（流派分歧/未收录，标 Und 不臆造）。
    数据源：references/用神对应表.md（六爻《火珠林》+王虎应事项分工、六壬《六壬大全》、奇门《秘笈大全》）。"""
    table = _YONGSHEN_TABLE.get(shufa)
    if not table:
        return None
    if wenshi in table:
        ys, src = table[wenshi]
        return {"用神": ys, "出处": src,
                "limitation": "用神定位只是「取哪个为分析对象」，不得由用神名直接定吉凶，须看旺衰生克。"}
    for k, (ys, src) in table.items():
        if k in wenshi or wenshi in k:
            return {"用神": ys, "出处": src,
                    "limitation": "用神定位只是「取哪个为分析对象」，不得由用神名直接定吉凶，须看旺衰生克。"}
    return None


# —— 确定性标注（骨架：术法各计算方面 → Det/Sto/Und + note，借鉴 mingli declare.rs） ——
_DETERMINISM = {
    "八字": [("四柱", "Det", "历法+节气+干支，只有对错"), ("大运", "Det", "起运按节气折算"),
             ("十神/藏干", "Det", "规则确定"), ("旺衰量化", "Und", "扶抑/调候/病药流派分歧"),
             ("格局/喜忌", "Und", "月令定格流派")],
    "紫微": [("十二宫安星", "Det", "命宫起例确定"), ("四化", "Det", "生年四化确定"),
             ("闰月", "Und", "作本月/十五日分界流派分歧"), ("大限流年", "Und", "流派")],
    "六爻": [("摇卦", "Sto", "铜钱随机，留六爻可复现"), ("纳甲装卦", "Det", "世应六亲六神确定"),
             ("用神取法", "Det", "六亲定位确定"), ("吉凶", "Und", "旺衰生克流派")],
    "大六壬": [("四课三传", "Det", "九宗门确定"), ("涉害深浅", "Und", "涉害取用流派，--ref 独立交叉校验"),
               ("昼夜贵人", "Und", "昼贵夜贵流派"), ("九宗门边界", "Und", "涉害/比用/返吟/八专易误判"),
               ("神煞", "Det", "起法确定"), ("断课吉凶", "Und", "毕法赋流派")],
    "梅花": [("时间起卦", "Det", "年月日时确定"), ("数字起卦", "Und", "报数主观"),
             ("体用", "Det", "动爻定体用确定"), ("取象/吉凶", "Und", "万物类象多解")],
    "奇门": [("定局", "Und", "置闰/拆补/茅山流派"), ("排盘", "Det", "定局后九宫八门确定"),
             ("十干克应", "Det", "81格局确定"), ("断局吉凶", "Und", "流派")],
    "小六壬": [("落宫", "Det", "月日时顺数确定"),
               ("吉凶", "Und", "口诀断语流派传承，六宫口诀各版本字句异文")],
    "金口诀": [("四位", "Det", "人元贵神将神地分确定"), ("五动三动", "Det", "生克确定"),
               ("昼贵夜贵", "Und", "贵人起法流派"), ("断", "Und", "流派")],
    "七政四余": [("星曜黄经", "Det", "ephem精算"), ("四余", "Und", "紫气28年周期各派定义分歧"),
                 ("命宫", "Det", "确定"), ("相位吉凶", "Und", "流派")],
    "风水": [("命卦", "Det", "八宅确定"), ("游年九星", "Det", "大游年歌诀确定"),
             ("玄空飞星", "Und", "八宅/玄空两派，飞星起法流派"), ("吉凶", "Und", "流派")],
    "择日": [("建除黄道", "Det", "确定"), ("神煞", "Det", "确定"),
             ("建除起法", "Und", "正月建寅等流派"), ("宜忌", "Und", "流派")],
    "太乙": [("落宫", "Det", "太乙积年确定"), ("积年法", "Und", "统宗/金镜/淘金歌/太乙局 4 种积年流派"),
             ("主客算", "Det", "确定"), ("吉凶", "Und", "流派")],
}


def determinism(shufa):
    """返回某术法各计算方面的确定性标注 [{aspect, status, note}]。
    借鉴 mingli declare.rs 的 DetItem：Det=只有对错（错就报），Sto=随机可复现，Und=流派分歧不臆造。
    无盘术法（相术/天文占/测字/其他）返回 []，表示无 Det 计算层。"""
    return [{"aspect": a, "status": s, "note": n} for a, s, n in _DETERMINISM.get(shufa, [])]


# —— 盘面事实 limitation（骨架：fact+limitation，借鉴 mingyu meihua-evidence.ts） ——
_PAN_LIMITATION = {
    "梅花": "卦象事实只记录本/互/变卦的上下卦、卦名、动爻；不得由卦名或动爻推断现实事件、人物、吉凶、成败或应期。",
    "六爻": "爻象事实只记录六亲/六神/纳甲/世应/旺衰；不得由用神名或爻位推断吉凶、金额、具体日期或人物身份。",
    "大六壬": "课式事实只记录四课三传/天将/神煞/课体；不得由天将名或课体直接定吉凶、应期或人物。",
    "八字": "四柱事实只记录干支/十神/藏干/大运；不得由十神名直接推断性格、学历、精确年份或具体事件。",
    "紫微": "十二宫事实只记录宫位/星曜/四化；不得由星曜名直接推断吉凶、具体事件或人物。",
    "奇门": "九宫事实只记录八门九星八神/格局；不得由门星名直接定吉凶、方位成败或应期。",
}


def limitation(shufa):
    """返回某术法盘面事实的 limitation（不得往哪推断）。借鉴 mingyu 的 fact+limitation。
    盘面事实永远为真（Det），limitation 声明它「不得被用来推断什么」——能力边界绑在事实上，
    而非结论末尾一个段落。"""
    return _PAN_LIMITATION.get(shufa,
                               "盘面事实只记录排盘结果，不得直接推断现实吉凶、人物、日期；解读属独立释义层。")


def pan_meta(shufa):
    """盘面事实的骨架标注：确定性 + limitation。给各术法 pan_json 附加用。"""
    return {"确定性": determinism(shufa), "limitation": limitation(shufa)}