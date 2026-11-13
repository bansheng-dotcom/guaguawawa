# -*- coding: utf-8 -*-
"""六爻「用神旺衰七查」+「吉凶判断矩阵」——收口 docs/六爻纳甲.md 的旺衰七查规范。

docs/六爻纳甲.md 已写清「旺衰七查表」的规范（用神/原神/忌神/仇神/世爻 × 月令旺衰+
月建作用+日辰作用+空亡真假+月破真假+入墓+综合）与「吉凶判断矩阵」（用神状态 × 原神
能否生 × 忌神能否克 → 六档），此前只散在 `najia.yongshen_analysis`（只查用神+世应）与
`liuyao_duanyu.LiuyaoAdapter`（cond 条件），没有独立的「七查表 + 判断矩阵」函数。
本模块补上，复用 `najia` 的装卦结果 + 生克/冲/墓/用神定位。

原则：月令旺衰/月建日辰作用/月破/入墓 是确定性的（生克冲墓表）；空亡真假/综合/六档
是 [规则推演]（旺相得生为吉、休囚入墓为凶等通行断法），断卦仍 Grep 典籍原文佐证。

用法：
  from judge.liuyao_wangshuai import wangshuai_qicha, jixiong_juzhen
  r = najia.zhuang(本卦, 变卦, 动爻, 日干支, 月干支)
  wangshuai_qicha(r, "求财")   # 五爻七查表
  jixiong_juzhen(r, "求财")     # 吉凶判断矩阵六档
"""
import sys
import os

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

from pan import najia  # noqa: E402

# 出处（固化，断卦仍 Grep 原文佐证）：
#  月令旺相休囚死 → 《增删卜易》四时旺相章；墓库 → 《增删卜易》墓库章；
#  元神忌神 → 《增删卜易》元神忌神章（生克冲合）；判断矩阵 → 《增删卜易》四处生克章。
SOURCE = "《增删卜易》"

_WX = najia.ZHI_WX
_SHENG = najia.SHENG
_KE = najia.KE
_CHONG = najia.CHONG
_YUANSHEN = najia._YUANSHEN
_JISHEN = najia._JISHEN
# 墓库：木墓未、火墓戌、金墓丑、水土墓辰
_MU = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}


def _yueling_wangshuai(zhi, month_zhi):
    """月令旺相休囚死（月建单独定五态）。"""
    wx, rwx = _WX[zhi], _WX[month_zhi]
    if wx == rwx:
        return "旺"
    if _SHENG.get(rwx) == wx:
        return "相"
    if _SHENG.get(wx) == rwx:
        return "休"
    if _KE.get(wx) == rwx:
        return "囚"
    return "死"


def _zuoyong(zhi, ref_zhi):
    """某支 vs 月建/日辰 的作用（生/克/扶/泄/耗）。"""
    wx, rwx = _WX[zhi], _WX[ref_zhi]
    if wx == rwx:
        return "扶(比和)"
    if _SHENG.get(rwx) == wx:
        return "生(得生)"
    if _SHENG.get(wx) == rwx:
        return "泄(我生)"
    if _KE.get(rwx) == wx:
        return "克(受克)"
    return "耗(我克)"


def _rumu(zhi, month_zhi, day_zhi):
    """是否入墓（日墓/月墓）。木墓未、火墓戌、金墓丑、水土墓辰。返回 [] 或 [来源]。"""
    mu = _MU[_WX[zhi]]
    out = []
    if day_zhi == mu:
        out.append("日墓")
    if month_zhi == mu:
        out.append("月墓")
    return out


def _kong_status(x, r):
    """空亡真假：动而旺相=假空(有气)、静而休囚=真空。x 是爻 dict。"""
    zhi = x["本卦"].split()[1][-1]
    if zhi not in r["旬空"]:
        return None
    lv = najia._wx_level(zhi, r["月建"], r["日辰"])["等级"]
    if x["动"] or lv in ("旺", "相"):
        return "假空(动/旺相，出空即实)"
    return "真空(静而休囚)"


def _pick(r, ys):
    """某六亲的目标爻（显爻优先，其次伏神）。返回 (爻dict, 落, 是否伏) 或 (None,..)。"""
    lines = r["六爻"]
    target = [x for x in lines if x["本卦"].split()[0] == ys]
    if target:
        return target[0], target[0]["爻"], False
    for f in r.get("伏神", []):
        if f.get("六亲") == ys:
            return f, f"伏{f['伏爻']}", True
    return None, None, False


def wangshuai_qicha(r, question=""):
    """五爻七查表：用神/原神/忌神/仇神/世爻 × 月令旺衰+月建作用+日辰作用+空亡+月破+入墓+综合。

    返回 {用神, 表: [{爻名, 六亲, 落, 月令, 月建, 日辰, 空亡, 月破, 入墓, 综合}, ...]}。
    用神不现（无显爻无伏神）时该行「落=不现」、其余列记「—」。
    """
    ys = najia.yongshen_for(question)
    if ys == "世":
        ys = "世"
    ys_qin = ys if ys in ("父母", "兄弟", "子孙", "妻财", "官鬼") else None
    yuanshen = _YUANSHEN.get(ys_qin) if ys_qin else None
    jishen = _JISHEN.get(ys_qin) if ys_qin else None
    choushen = _YUANSHEN.get(jishen) if jishen else None

    rows = []
    # 五爻：用神/原神/忌神/仇神/世爻
    entries = [("用神", ys_qin), ("原神", yuanshen), ("忌神", jishen), ("仇神", choushen)]
    for name, qin in entries:
        row = {"爻名": name, "六亲": qin}
        if not qin:
            row.update({k: "—" for k in ("落", "月令", "月建", "日辰", "空亡", "月破", "入墓", "综合")})
            rows.append(row)
            continue
        x, pos, is_fu = _pick(r, qin)
        if not x:
            row.update({"落": "不现", "月令": "—", "月建": "—", "日辰": "—",
                        "空亡": "—", "月破": "—", "入墓": "—", "综合": "不上卦（看伏神或待出空）"})
            rows.append(row)
            continue
        zhi = x["本卦"].split()[1][-1] if not is_fu else x["干支"][-1]
        row["落"] = pos
        row["月令"] = _yueling_wangshuai(zhi, r["月建"]) if r["月建"] else "—"
        row["月建"] = _zuoyong(zhi, r["月建"]) if r["月建"] else "—"
        row["日辰"] = _zuoyong(zhi, r["日辰"]) if r["日辰"] else "—"
        row["空亡"] = _kong_status(x, r) if not is_fu else "—"
        row["月破"] = "月破" if (r["月建"] and zhi == _CHONG.get(r["月建"])) else "否"
        mu = _rumu(zhi, r["月建"] or "", r["日辰"] or "")
        row["入墓"] = "、".join(mu) if mu else "否"
        row["综合"] = _zonghe(name, x, zhi, r, is_fu)
        rows.append(row)

    # 世爻
    shi = next((x for x in r["六爻"] if x["世应"] == "世"), None)
    row = {"爻名": "世爻", "六亲": shi["本卦"].split()[0] if shi else None}
    if shi:
        zhi = shi["本卦"].split()[1][-1]
        row["落"] = shi["爻"]
        row["月令"] = _yueling_wangshuai(zhi, r["月建"]) if r["月建"] else "—"
        row["月建"] = _zuoyong(zhi, r["月建"]) if r["月建"] else "—"
        row["日辰"] = _zuoyong(zhi, r["日辰"]) if r["日辰"] else "—"
        row["空亡"] = _kong_status(shi, r)
        row["月破"] = "月破" if (r["月建"] and zhi == _CHONG.get(r["月建"])) else "否"
        mu = _rumu(zhi, r["月建"] or "", r["日辰"] or "")
        row["入墓"] = "、".join(mu) if mu else "否"
        row["综合"] = "旺相宜动、休囚空破主无力"
    else:
        row.update({k: "—" for k in ("落", "月令", "月建", "日辰", "空亡", "月破", "入墓", "综合")})
    rows.append(row)
    return {"用神": ys_qin or ys, "表": rows}


def _zonghe(name, x, zhi, r, is_fu):
    """七查综合结论（规则推演）。通用空破墓优先，再按爻角色给「生用/克用/助忌/待扶」。"""
    lv = najia._wx_level(zhi, r["月建"], r["日辰"])["等级"]
    mu = _rumu(zhi, r["月建"] or "", r["日辰"] or "")
    kong = _kong_status(x, r)
    po = bool(r["月建"] and zhi == _CHONG.get(r["月建"]))
    if kong == "真空(静而休囚)":
        return "真空＝无用"
    if po and x["动"]:
        return "动而月破＝力减"
    if po:
        return "月破＝力减，当月缓"
    if lv in ("衰", "死") and mu:
        return "休囚入墓＝凶（如人被埋）"
    if lv in ("旺", "相") and mu:
        return "旺相入墓＝财库（暂伏）"
    if name == "世爻":
        return f"{lv}（旺相宜动、休囚空破主无力）"
    if name == "用神":
        return f"{lv}（{'得生可进' if lv in ('旺', '相') else '待生扶'}）"
    role = {"原神": "生用", "忌神": "克用", "仇神": "助忌"}.get(name, name)
    dong = "动" if x["动"] else "静"
    return f"{lv}{dong}（{role}{'有力' if lv in ('旺', '相') else '无力'}）"


def jixiong_juzhen(r, question=""):
    """吉凶判断矩阵：用神状态 × 原神能否生 × 忌神能否克 → 大吉/吉/平/小凶/凶/大凶。

    规则（docs/六爻纳甲.md 判断矩阵 + 增删卜易四处生克章）：
      用神旺相 + 原神动生 − 忌神克 = 大吉；用神旺相无制 = 吉；
      用神休囚 + 原神生 = 平（有救）；用神休囚无生无克 = 小凶；
      用神休囚 + 忌神克 = 凶；用神休囚 + 忌神克 + 原神无力 = 大凶。
    """
    ys = najia.yongshen_for(question)
    ys_qin = ys if ys in ("父母", "兄弟", "子孙", "妻财", "官鬼") else None
    x, pos, is_fu = _pick(r, ys_qin) if ys_qin else (None, None, False)
    if not x:
        return {"档": "不现", "判": "用神不上卦，看伏神或待出空", "用神状态": "不现"}
    zhi = x["本卦"].split()[1][-1] if not is_fu else x["干支"][-1]
    lv = najia._wx_level(zhi, r["月建"], r["日辰"])["等级"]
    wang = lv in ("旺", "相")

    yuanshen = _YUANSHEN.get(ys_qin)
    jishen = _JISHEN.get(ys_qin)
    yuan_dong = bool(yuanshen) and any(y["动"] for y in _qin(r, yuanshen))
    yuan_wang = bool(yuanshen) and any(najia._wx_level(y["本卦"].split()[1][-1], r["月建"], r["日辰"])["等级"] in ("旺", "相")
                                        for y in _qin(r, yuanshen))
    ji_dong = bool(jishen) and any(y["动"] for y in _qin(r, jishen))
    ji_wang = bool(jishen) and any(najia._wx_level(y["本卦"].split()[1][-1], r["月建"], r["日辰"])["等级"] in ("旺", "相")
                                    for y in _qin(r, jishen))
    yuan_ke_sheng = yuan_dong or yuan_wang
    ji_ke_ke = ji_dong or ji_wang

    if wang and yuan_ke_sheng and not ji_ke_ke:
        dang, pan = "大吉", "用神旺相、原神得力、忌神无力，所求可成"
    elif wang and not ji_ke_ke:
        dang, pan = "吉", "用神旺相、无克，事顺"
    elif wang and ji_ke_ke:
        dang, pan = "平", "用神旺但忌神有力，成中有阻，看动变"
    elif not wang and yuan_ke_sheng and not ji_ke_ke:
        dang, pan = "平", "用神休囚但原神得力，有救，先难后成"
    elif not wang and not yuan_ke_sheng and not ji_ke_ke:
        dang, pan = "小凶", "用神休囚、无生无克，无力，难成"
    elif not wang and ji_ke_ke and yuan_ke_sheng:
        dang, pan = "凶", "用神休囚、忌神克、原神有救，凶多吉少"
    else:
        dang, pan = "大凶", "用神休囚、忌神克、原神无力，诸占大凶"
    return {"档": dang, "判": pan, "用神状态": lv,
            "原神": "动" if yuan_dong else ("旺相" if yuan_wang else "无力"),
            "忌神": "动" if ji_dong else ("旺相" if ji_wang else "无力")}


def _qin(r, qin):
    return [x for x in r["六爻"] if x["本卦"].split()[0] == qin]


def _fmt_qicha(q):
    lines = [f"【旺衰七查表】用神：{q['用神']}"]
    for row in q["表"]:
        lines.append(f"  {row['爻名']:3s} {row['六亲'] or '—':4s} 落{row['落']:>4s} | "
                     f"月令{row['月令']:2s} 月建{row['月建']} 日辰{row['日辰']} | "
                     f"空{row['空亡'] or '否':>12s} 破{row['月破']:2s} 墓{row['入墓']:4s} | {row['综合']}")
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    if len(a) < 4:
        print(__doc__)
        return
    ben, bian = a[0], a[1]
    dong = [int(x) for x in a[2].split(",")] if a[2] else []
    day_gz, month_gz = a[3], (a[4] if len(a) > 4 else "")
    q = a[5] if len(a) > 5 else "求财"
    r = najia.zhuang(ben, bian, dong, day_gz, month_gz)
    print(_fmt_qicha(wangshuai_qicha(r, q)))
    jz = jixiong_juzhen(r, q)
    print(f"\n【吉凶判断矩阵】{jz['档']} —— {jz['判']}（用神{jz['用神状态']}，原神{jz['原神']}，忌神{jz['忌神']}）")


if __name__ == "__main__":
    main()
