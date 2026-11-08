# -*- coding: utf-8 -*-
"""
bushu 起盘统一入口 —— 确定性排盘，避免手工算错。

用法:
  python cast.py meihua-time                         梅花易数·时间起卦
  python cast.py meihua-num <a> [<b> [<c>]]          梅花易数·数字起卦
  python cast.py meihua-guanwu <物数>                 梅花易数·物数占(后天触机)
  python cast.py meihua-shengyin <声数>               梅花易数·声音占(后天触机)
  python cast.py meihua-zishu <字数>                  梅花易数·字占(后天触机)
  python cast.py meihua-duanfa <物卦> <方位卦>         梅花易数·端法后天起卦(物+方位)
  python cast.py xiaoliuren                          小六壬·月日时
  python cast.py liuyao                              六爻·铜钱摇卦(含纳甲装卦)
  python cast.py bazi [年 月 日 时 分 秒 性别]        八字(默认当前, 性别1男0女, --zishi same|next 子时换日)
  python cast.py liuren                              大六壬
  python cast.py jinkoujue [地分/方位]                大六壬·金口诀(四位:人元/贵神/将神/地分)
  python cast.py qimen                               奇门遁甲
  python cast.py taiyi [--ji 0-5] [--method 0-3] [--game] [--full]  太乙神数(计式×积年法, --full全字段)
  python cast.py zhiwei <年 月 日 时 [性别]>           紫微斗数(公历, 性别1男0女)
  python cast.py zhiwei-liunian <年 月 日 时 性别 流年>  紫微·流年化忌叠冲扫描(压力热力表)
  python cast.py zhiwei-yanqian <年 月 日 时 性别 "年:事,年:事">  紫微·验前事校验(婚/子/升/财/破财/病/灾)
  python cast.py qizheng                             七政四余·果老星宗(可 --time)
  python cast.py qizheng-liunian <出生年> <命宫地支> [流年年份]  七政四余·流年大限小限
  python cast.py fengshui [出生年] [坐向] [性别]       风水·八宅/玄空飞星
  python cast.py zeri [事项]                          择日·建除黄道神煞(可 --time)
  python cast.py zeri-month 2026-10 婚嫁 [数量]       择日·按月推荐吉日(月份 事项)
  python cast.py hehun 1990 5 15 1992 8 20          八字合婚(男女各年 月 日, 可加 [男时 女时])
  python cast.py bazi-liunian 2000 1 1 1 2026 10    八字·流年深度(出生年 月 日 性别 起始年 年数; 合冲刑害+岁运+喜忌+评分)
  python cast.py liuyue 2000 1 1 1 2026             八字·流月深度(出生年 月 日 性别 流年; 同上)
  python cast.py mingli-eval [--cat 类别]           MingLi-Bench 本地评测(分品类命中率+随机/众数基线)

  所有时间起盘的方法均可加 --time "YYYY-MM-DD HH:MM" 指定占时，缺省用当前系统时间。
"""
import os
import sys
import json
import datetime as _dt

# Windows 控制台默认 GBK，遇到 ·•→ 等符号会 UnicodeEncodeError；统一转 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 让 libs/ 下的模块(sxtwl 垫片、engines 引擎、各排盘方法)可导入
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
sys.path.insert(0, LIB)

from pan import meihua
from pan import xiaoliuren
from pan import liuyao
from util import liuyao_knowledge
from pan import bazi
from pan import liuren
from regress import liuren_regress
from pan import jinkoujue
from pan import qimen
from pan import taiyi
from pan import zhiwei
from judge import ziwei_geju
from pan import ziwei_liunian
from judge import ziwei_yanqian
from pan import qizheng
from pan import liunian
from pan import fengshui
from pan import zeri
from pan import hehun
from util import htmlpan
from lifa import almanac
from pan import ziwei_horoscope
from judge import trend
from pan import bazi_liunian
from pan import bazi_json
from util import mingli_eval
from judge import shefu_portrait
from judge import rules
from judge import miaogong_shefu
from judge import shiwu_xunren
from judge import bazi_chain
from judge import liuyao_duanyu
from judge import liuren_zhanshi
def _parse_time(args):
    """提取 --time/-t 占时、--lon 经度、--dst 夏令时回拨、--html 可视化、--ref 校验、--zishi 子时换日、--json 结构化双轨、--range 时间不确定枚举"""
    dt, lon, dst, html, ref, zishi, json_out, time_range = None, None, False, False, False, "same", False, None
    out = []
    i = 0
    while i < len(args):
        if args[i] in ("--time", "-t") and i + 1 < len(args):
            s = args[i + 1]
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = _dt.datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue
            i += 2
        elif args[i] == "--lon" and i + 1 < len(args):
            try:
                lon = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] in ("--dst", "-dst"):
            dst = True
            i += 1
        elif args[i] == "--html":
            html = True
            i += 1
        elif args[i] == "--ref":
            ref = True
            i += 1
        elif args[i] == "--zishi" and i + 1 < len(args):
            zishi = args[i + 1]
            i += 2
        elif args[i] == "--json":
            json_out = True
            i += 1
        elif args[i] == "--range" and i + 1 < len(args):
            time_range = args[i + 1]
            i += 2
        else:
            out.append(args[i])
            i += 1
    return out, dt, lon, dst, html, ref, zishi, json_out, time_range


def main():
    a, dt, lon, dst, html, ref, zishi, json_out, time_range = _parse_time(sys.argv[1:])
    cmd = a[0] if a else "meihua-time"
    if cmd in ("meihua-time", "meihua"):
        r = meihua.cast_time(dt)
        print()
        print(meihua.summary(r))
        print()
        print("【取象画像】（本卦/互卦/变卦 三卦合成）")
        print(shefu_portrait._fmt(shefu_portrait.portrait_meihua_pan(r)))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=meihua-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(meihua.pan_json(r), ensure_ascii=False, indent=2))
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "meihua-num":
        r = meihua.cast_num(a[1:])
        print()
        print(meihua.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=meihua-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(meihua.pan_json(r), ensure_ascii=False, indent=2))
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "meihua-guanwu":
        r = meihua.cast_guanwu(a[1], dt)
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "meihua-shengyin":
        r = meihua.cast_shengyin(a[1], dt)
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "meihua-zishu":
        r = meihua.cast_zishu(a[1], dt)
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "meihua-duanfa":
        r = meihua.cast_duanfa(a[1], a[2] if len(a) > 2 else "南", dt)
        if html:
            htmlpan.meihua_html(r, f"梅花易数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "xiaoliuren":
        gong = xiaoliuren.cast(dt)
        print()
        print(xiaoliuren.summary(gong))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=xiaoliuren-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(xiaoliuren.pan_json(gong), ensure_ascii=False, indent=2))
    elif cmd == "liuyao":
        q = a[1] if len(a) > 1 else "通用"
        ben, bian, dong, r = liuyao.cast(dt, question=q)
        # 一眼摘要卡 + 结构化双轨（借鉴八字/紫微升级）
        print()
        print(liuyao.summary(ben, bian, dong, r, q))
        # 13 类用神断语编译（tianzhi-core 式：断语→JSON规则→判定条件→命中/跳过）
        if q != "通用":
            print()
            print("【用神断语编译】典籍断语逐条判定（能判的判、判不了的标 skip）")
            hits, skipped = liuyao_duanyu.find_liuyao(r, q)
            for h in hits:
                print(f"  [{h['verdict']}] {h['text']}（{h['src']}）")
            if not hits:
                print("  （无命中断语）")
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=liuyao-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(liuyao.pan_json(ben, bian, dong, r, q), ensure_ascii=False, indent=2))
        if html:
            htmlpan.liuyao_html(r, ben, bian, dong,
                                f"六爻卦图_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "bazi":
        args = [int(x) for x in a[1:]]
        gender = args[6] if len(args) > 6 else 1
        # 时间不确定：逐分钟枚举候选（--range "HH:MM-HH:MM"），标稳定柱/变化柱
        if time_range and len(args) >= 3:
            print(bazi_json._fmt_range(bazi_json.enumerate_range(
                args[0], args[1], args[2], time_range,
                args[3] if len(args) > 3 else 1, lon=lon, dst=dst)))
        else:
            if args:
                b = bazi.cast(*args, lon=lon, dst=dst, zishi=zishi)
            else:
                b = bazi.cast(lon=lon, dst=dst, zishi=zishi)
            # 一眼摘要卡（五行统计/宫位/大运地势吉凶，借鉴卜易居/元亨利贞的「看得懂」层）
            if len(args) >= 3:
                print()
                print(bazi_json._fmt_summary(bazi_json.summary_card(
                    args[0], args[1], args[2],
                    args[3] if len(args) > 3 else 12,
                    args[4] if len(args) > 4 else 0,
                    args[5] if len(args) > 5 else 0,
                    gender, lon=lon, dst=dst)))
            # P1：旺衰量化得分 + 格局成破救应 + 干支合化判断
            if len(args) >= 3:
                print()
                bazi_liunian.mingli_analysis(args[0], args[1], args[2],
                                             args[3] if len(args) > 3 else 12,
                                             args[4] if len(args) > 4 else 0,
                                             args[5] if len(args) > 5 else 0,
                                             gender)
            # 推演链（tianzhi-core 式）：五行力量量化 → 旺衰五档 → 用神五法
            # 与上方「四指标加权」互补：本链是权威推演链，四指标作交叉印证
            if args:
                print()
                bazi_chain.print_chain_report(bazi_chain.quad_from_eightchar(b))
            # 结构化双轨：盘面事实层 JSON（--json，与散文并存，机读可校验）
            if json_out and len(args) >= 3:
                print()
                print("【盘面事实层 JSON】schema=bazi-panfact-v1（机读，与上方散文并存）")
                print(bazi_json._fmt_json(bazi_json.cast_json(
                    args[0], args[1], args[2],
                    args[3] if len(args) > 3 else 12,
                    args[4] if len(args) > 4 else 0,
                    args[5] if len(args) > 5 else 0,
                    gender, lon=lon, dst=dst)))
            if html:
                htmlpan.bazi_html(b, gender, f"八字命盘_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "liuren":
        q = a[1] if len(a) > 1 else ""
        r = liuren.cast(dt)
        print()
        print(liuren.summary(r))
        # 11 类类神分类占断（tianzhi-core 式：取类神→专条→三传始终→急迟应期）
        if q in liuren_zhanshi.SHI:
            print()
            res = liuren_zhanshi.zhanshi_from_dt(dt, r, q)
            print(f"【分类占断】问事={q} 总分{res['score']:+d} 趋势={res['trend']}")
            _ls = "、".join(f"{x['name']}({x['where']},{x['qi']})" for x in res["leishen"])
            print(f"  类神：{_ls}")
            for f in res["facts"]:
                print(f"    [{f['tone']:+d}] {f['code']}（{f['src']}）")
            for c in res["course"]:
                print(f"    [{c['tone']:+d}] {c['code']} {c['args'].get('shape','')}（{c['src']}）")
            if res["pace"]:
                print(f"    急迟：{res['pace']['code']}")
            if res["timing"]:
                print(f"    应期：{'、'.join(t['code'] for t in res['timing'])}")
        print()
        print("【取象画像】（三传地支+天将 合成）")
        print(shefu_portrait._fmt(shefu_portrait.portrait_liuren_sanchuan(r.get("三傳", {}))))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=liuren-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(liuren.pan_json(r), ensure_ascii=False, indent=2))
        if html:
            htmlpan.liuren_html(r, f"大六壬_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        if ref:
            print()
            print("【交叉校验 · 独立九宗门实现 vs 引擎】")
            print(liuren_regress.format_cross_check(liuren_regress.cross_check_ref(dt)))
    elif cmd == "jinkoujue":
        # 大六壬·金口诀：jinkoujue [地分/方位]（地分缺省取时支，可传子/午/北/南等）
        difen = a[1] if len(a) > 1 else None
        r = jinkoujue.cast(dt, difen)
        jinkoujue.print_pan(r)
        print()
        print(jinkoujue.summary(r))
        # 射覆门（测物/来意，不押物名；断卦以用爻为准，此处按地分/贵神/人元干展示原始信号）
        _four = r["四位"]
        _df_zhi = _four["地分"]["符号"]
        _gs_name = _four["贵神"]["名"]
        _ry_gan = _four["人元"]["符号"]
        print()
        print("【射覆门】（测物/来意，不押物名）")
        print(f"  地支类象：{rules.jinkoujue_shefu_zhilei(_df_zhi)['result'] or '—'}")
        print(f"  贵神类象：{rules.jinkoujue_shefu_guishen(_gs_name)['result'] or '—'}")
        print(f"  颜色/数目/所在：{rules.jinkoujue_shefu_yanse_shumu(_ry_gan, _df_zhi, _four['将神']['五行'])['result']}")
        _ly = shefu_portrait.jinkoujue_laiyi(_four["人元"]["五行"], _four["将神"]["五行"])
        print(f"  占来意：{_ly['来意']} [出处：{_ly['出处']}]")
        print()
        print("【多象合成画像】（四位三象源聚合：贵神+将神+地分）")
        print(shefu_portrait._fmt(shefu_portrait.portrait_jinkoujue(_four)))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=jinkoujue-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(jinkoujue.pan_json(r), ensure_ascii=False, indent=2))
    elif cmd == "qimen":
        r = qimen.cast(dt)
        print()
        print(qimen.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=qimen-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(qimen.pan_json(r), ensure_ascii=False, indent=2))
        if html:
            htmlpan.qimen_html(r.get("時家奇門", {}), f"奇门遁甲_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "taiyi":
        # 太乙神数：--ji 0-5(计式) --method 0-3(积年法) --game(运筹博弈) --full(全字段JSON)
        ji_style, method, game, full = 0, 0, False, False
        i = 1
        while i < len(a):
            if a[i] == "--ji" and i + 1 < len(a):
                ji_style = int(a[i + 1]); i += 2
            elif a[i] == "--method" and i + 1 < len(a):
                method = int(a[i + 1]); i += 2
            elif a[i] == "--game":
                game = True; i += 1
            elif a[i] == "--full":
                full = True; i += 1
            else:
                i += 1
        r = taiyi.cast(dt, ji_style=ji_style, method=method, game=game, full=full)
        print()
        print(taiyi.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=taiyi-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(taiyi.pan_json(r), ensure_ascii=False, indent=2))
        if html and r:
            htmlpan.taiyi_html(r, f"太乙神数_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "zhiwei":
        args = [int(x) for x in a[1:]]
        r = zhiwei.cast(args[0], args[1], args[2], args[3], args[4] if len(args) > 4 else 1, lon=lon, dst=dst)
        zhiwei.print_pan(r)
        # 一眼摘要卡（命宫/身宫/四化/三方四正，借鉴八字升级的「一眼看懂」层）
        print()
        print(zhiwei.summary(r))
        # 飞星四化全景（循环忌/忌冲，借鉴 mingli-skills）
        print()
        print(zhiwei.format_feixing(zhiwei.feixing_panorama(r)))
        # 结构化双轨：盘面事实层 JSON（--json，机读可校验，与散文并存）
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=ziwei-panfact-v1（机读，与上方散文并存）")
            print(json.dumps({"schema": "ziwei-panfact-v1", **r}, ensure_ascii=False, indent=2))
        # 格局判定（结构化规则，出处《紫微斗数全书》，断卦按格局名 Grep 原文佐证）
        _hits = ziwei_geju.judge_patterns(r)
        print()
        print("[紫微格局] " + ziwei_geju.format_patterns(_hits))
        # 运限（大限已随命盘输出；此处补流年/流月/流日/流时四化+流曜，引擎 py-iztro）
        _target = dt.strftime("%Y-%m-%d") if dt else None
        _gender = args[4] if len(args) > 4 else 1
        print()
        print(ziwei_horoscope.format_horoscope(
            ziwei_horoscope.horoscope(args[0], args[1], args[2], args[3], _gender, target=_target)))
        if html:
            htmlpan.zhiwei_html(r, f"紫微斗数命盘_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "zhiwei-liunian":
        args = [int(x) for x in a[1:]]
        _target_year = args[5] if len(args) > 5 else (dt.year if dt else _dt.datetime.now().year)
        _r = ziwei_liunian.diji_scan(args[0], args[1], args[2], args[3], args[4], _target_year)
        print(ziwei_liunian.format_scan(_r))
    elif cmd == "zhiwei-yanqian":
        args = [int(x) for x in a[1:6]]
        evs = a[6] if len(a) > 6 else ""
        events = [(int(y), t.strip()) for y, t in (p.split(":", 1) for p in evs.split(",") if ":" in p)]
        if not events:
            print("用法: zhiwei-yanqian 年 月 日 时 性别 \"年份:类型,年份:类型\"（类型: 婚/子/升/财/破财/病/灾）")
        else:
            _r = ziwei_yanqian.validate_events(args[0], args[1], args[2], args[3], args[4], events)
            print(ziwei_yanqian.format_validate(_r))
    elif cmd == "qizheng":
        # 七政四余·果老星宗（可 --time 指定占时）
        s = dt.strftime("%Y-%m-%d %H:%M") if dt else None
        r = qizheng.qizheng_pan(s, lon=lon) if lon is not None else qizheng.qizheng_pan(s)
        print(qizheng.format_output(r))
        # 一眼摘要卡 + 结构化双轨（借鉴八字/紫微升级）
        print()
        print(qizheng.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=qizheng-panfact-v1（机读，与上方散文并存）")
            print(json.dumps({"schema": "qizheng-panfact-v1", **r}, ensure_ascii=False, indent=2))
    elif cmd == "qizheng-liunian":
        # 七政四余·流年大限小限：<出生年> <命宫地支> [流年年份]
        birth_year = int(a[1]) if len(a) > 1 else _dt.datetime.now().year
        ming_gong = a[2] if len(a) > 2 else "子"
        ln_year = int(a[3]) if len(a) > 3 else _dt.datetime.now().year
        calc = liunian.LiuNianCalculator()
        birth_data = {"出生年份": birth_year, "命宫地支": ming_gong, "星曜位置": {}}
        print(json.dumps(calc.analyze_liu_nian(birth_data, ln_year), ensure_ascii=False, indent=2))
    elif cmd == "fengshui":
        # 风水·八宅/玄空飞星：<出生年> [坐向] [性别男/女]
        year = int(a[1]) if len(a) > 1 else _dt.datetime.now().year
        direction = a[2] if len(a) > 2 else None
        gender = a[3] if len(a) > 3 else "男"
        r = fengshui.fengshui_pan(year, direction, gender)
        print(fengshui.format_output(r))
        print()
        print(fengshui.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=fengshui-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(fengshui.pan_json(r), ensure_ascii=False, indent=2))
    elif cmd == "zeri":
        # 择日·建除黄道神煞（可 --time 指定查询日；[事项] 婚嫁/开业/动土/出行/搬家/考试/求医/祭祀）
        event = a[1] if len(a) > 1 else "general"
        if dt:
            y, m, d, h = dt.year, dt.month, dt.day, dt.hour
        else:
            now = _dt.datetime.now()
            y, m, d, h = now.year, now.month, now.day, now.hour
        r = zeri.get_day_summary(y, m, d, event, h)
        print(zeri.format_output(r, event))
        print()
        print(zeri.summary(r))
        if json_out:
            print()
            print("【盘面事实层 JSON】schema=zeri-panfact-v1（机读，与上方散文并存）")
            print(json.dumps(zeri.pan_json(r), ensure_ascii=False, indent=2))
        # 老黄历补全（彭祖百忌/值神/吉神方位/胎神/冲煞/宜忌，出处《协纪辨方书》）
        print()
        print(almanac.format_almanac(almanac.almanac(y, m, d)))
    elif cmd == "zeri-month":
        # 择日·按月推荐吉日：zeri-month <YYYY-MM> [事项] [数量]
        if dt:
            y, m = dt.year, dt.month
            event = a[1] if len(a) > 1 else "general"
            limit = int(a[2]) if len(a) > 2 else 10
        else:
            y, m = map(int, a[1].split("-")) if len(a) > 1 else (_dt.datetime.now().year, _dt.datetime.now().month)
            event = a[2] if len(a) > 2 else "general"
            limit = int(a[3]) if len(a) > 3 else 10
        ji = zeri.tui_jian_ji_ri(y, m, event, limit)
        print(f"【{y}年{m}月吉日推荐】（{event}）")
        for i, jr in enumerate(ji, 1):
            print(f"  {i}. {jr['日期']}  评分 {jr['综合评分']}/100（{jr['等级']}）建除:{jr['建除']} 黄道:{jr['黄道']}")
        if not ji:
            print("  本月无吉日推荐")
    elif cmd == "hehun":
        # 八字合婚：hehun <男年 男月 男日 女年 女月 女日> [男时 女时]（时可选，缺省按午时+降级）
        args = [int(x) for x in a[1:]]
        if len(args) < 6:
            print("用法: hehun <男年 男月 男日 女年 女月 女日> [男时 女时]")
        else:
            h1 = args[6] if len(args) > 6 else None
            h2 = args[7] if len(args) > 7 else None
            hehun.cast(args[0], args[1], args[2], args[3], args[4], args[5], h1, h2)
    elif cmd == "bazi-liunian":
        # 八字·流年深度：bazi-liunian <出生年 月 日 性别> [起始年] [年数]（合冲刑害+岁运+喜忌+评分）
        args = [int(x) for x in a[1:]]
        y = args[0] if len(args) > 0 else None
        mo = args[1] if len(args) > 1 else None
        d = args[2] if len(args) > 2 else None
        gender = args[3] if len(args) > 3 else 1
        start = args[4] if len(args) > 4 else None
        n = args[5] if len(args) > 5 else 10
        bazi_liunian.liunian_deep(y, mo, d, gender, start, n)
        if html and y is not None:
            t = trend.liunian_trend(y, mo, d, gender, start, n)
            htmlpan.liunian_trend_html(t, f"八字流年趋势_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    elif cmd == "liuyue":
        # 八字·流月深度：liuyue <出生年 月 日 性别> [流年]（合冲刑害+岁运+喜忌+评分）
        args = [int(x) for x in a[1:]]
        y = args[0] if len(args) > 0 else None
        mo = args[1] if len(args) > 1 else None
        d = args[2] if len(args) > 2 else None
        gender = args[3] if len(args) > 3 else 1
        year = args[4] if len(args) > 4 else None
        bazi_liunian.liuyue_deep(y, mo, d, gender, year)
    elif cmd == "mingli-eval":
        # MingLi-Bench 本地评测：mingli-eval [--cat 类别]（分品类/总体命中率 + 随机/众数基线）
        _filter = None
        if "--cat" in a:
            _i = a.index("--cat")
            if _i + 1 < len(a):
                _filter = a[_i + 1]
        mingli_eval.analyze(cat_filter=_filter)
    elif cmd == "liuyao-knowledge":
        # 六爻理法知识包（王虎应体系，MCP 未连接时离线 RAG 回退）
        q = a[1] if len(a) > 1 else ""
        if not q:
            print(liuyao_knowledge.__doc__)
        else:
            print(f"[六爻理法知识包] 检索「{q}」\n")
            for r in liuyao_knowledge.search(q):
                jx = f"（{r['吉凶']}）" if r["吉凶"] != "—" else ""
                print(f"[{r['score']:.1f}] ({r['类型']}) {r['名称']}{jx}")
                print(f"    {r['断语']}")
                print(f"    〔原文〕{r['原文']}  — {r['出处']}")
    elif cmd == "shefu":
        # 射覆：shefu liuren <天将...> / shefu meihua <卦...> / shefu miaogong <日干> <发用支> <发用天将> [课体] [旺相] [五行]
        sub = a[1] if len(a) > 1 else ""
        sig = a[2:]
        if sub == "liuren":
            print(shefu_portrait._fmt(shefu_portrait.portrait_liuren(sig)))
        elif sub == "meihua":
            print(shefu_portrait._fmt(shefu_portrait.portrait_meihua(sig)))
        elif sub == "miaogong":
            # 苗公射覆画像（大六壬：天将临辰物类 + 课体物性 + 形状/颜色/新旧/五行物类）
            if len(sig) < 3:
                print("用法：shefu miaogong <日干> <发用支> <发用天将> [课体] [旺相] [五行]")
            else:
                keti = sig[3] if len(sig) > 3 else ""
                ws = sig[4] if len(sig) > 4 else ""
                wx = sig[5] if len(sig) > 5 else ""
                print(miaogong_shefu._fmt(miaogong_shefu.portrait_liuren(sig[0], sig[1], sig[2], keti, ws, wx)))
        else:
            print(shefu_portrait._fmt(shefu_portrait.portrait([(x, 1.0) for x in sig])))
    elif cmd == "shiwu":
        # 失物·寻人：shiwu xiaoliuren <落宫> / shiwu liuyao <卦宫> <财爻状态> <官鬼状态> [子孙状态] [财爻五行] / shiwu jinkoujue <地支> [生克]
        sub = a[1] if len(a) > 1 else ""
        sig = a[2:]
        if sub == "xiaoliuren":
            print(shiwu_xunren._fmt(shiwu_xunren.portrait_shiwu("xiaoliuren", 落宫=sig[0] if sig else "")))
        elif sub == "jinkoujue":
            print(shiwu_xunren._fmt(shiwu_xunren.portrait_shiwu(
                "jinkoujue", 地支=sig[0] if sig else "", 生克=sig[1] if len(sig) > 1 else "")))
        elif sub == "liuyao":
            gong = sig[0] if sig else ""
            cai = sig[1] if len(sig) > 1 else ""
            gui = sig[2] if len(sig) > 2 else ""
            zisun = sig[3] if len(sig) > 3 else ""
            cai_wx = sig[4] if len(sig) > 4 else ""
            print(shiwu_xunren._fmt({
                "综合断": shiwu_xunren.liuyao_shiwu_duan(cai, gui, zisun, gong),
                "方位": shiwu_xunren.liuyao_shiwu_fangwei(gong) if gong else None,
                "藏处": shiwu_xunren.liuyao_shiwu_cangchu(cai_wx) if cai_wx else None,
            }))
        else:
            print("用法：shiwu xiaoliuren <落宫> / shiwu liuyao <卦宫> <财爻状态> <官鬼状态> [子孙状态] [财爻五行] / shiwu jinkoujue <地支> [生克]")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()