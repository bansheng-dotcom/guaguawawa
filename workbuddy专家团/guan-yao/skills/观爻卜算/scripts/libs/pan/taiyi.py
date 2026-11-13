# -*- coding: utf-8 -*-
"""太乙神数排盘（引擎: kentang2017/kintaiyi，MIT）

接线层：把引擎 `pan()` 返回的 100+ 字段分门别类打印（原本只打印 8 个）。

参数
----
ji_style : int
    0=年計 1=月計 2=日計 3=時計 4=分計 5=命法
method : int
    0=太乙統宗 1=太乙金鏡 2=太乙淘金歌 3=太乙局
game : bool
    是否附加「運籌博弈分析」（game_theory，Nash 均衡 + 線性規劃）

已知引擎边界（诚实标注，与六壬 liuren 同风格；上游 kintaiyi 2019 旧代码）：
- 命法(ji_style=5)：上游未完成，pan(5,*) 抛 TypeError，暂不支持。
- 日計×太乙局(2,3)：TypeError（list indices float）。
- 時計/分計 × 非統宗(3或4, 1/2/3)：部分组合可能死循环，慎用。
"""
import json
import datetime


_JI = {0: "年計", 1: "月計", 2: "日計", 3: "時計", 4: "分計", 5: "命法"}
_METHOD = {0: "太乙統宗", 1: "太乙金鏡", 2: "太乙淘金歌", 3: "太乙局"}


def _fmt(v, cap=70):
    """混合值 → 单行字符串（dict/list 压缩；超长截断）"""
    if isinstance(v, dict):
        if "文" in v and isinstance(v.get("文"), str):
            base = str(v["文"])
            extra = []
            for k in ("年", "積年數", "數"):
                if v.get(k) not in (None, "", []):
                    extra.append(f"{k}{v[k]}")
            s = base + ("（" + " ".join(extra) + "）" if extra else "")
        else:
            parts = []
            for k, vv in v.items():
                s = _fmt(vv, 24)
                parts.append(f"{k}={s}" if s else str(k))
            s = "  ".join(parts)
    elif isinstance(v, list):
        if v and isinstance(v[0], (int, float)) and len(v) > 1 and isinstance(v[1], list):
            tags = [str(x) for x in v[1] if x not in ("", None)]
            s = str(v[0]) + ("（" + "、".join(tags) + "）" if tags else "")
        else:
            s = "、".join(str(x) for x in v if x not in ("", None))
    elif v in (None, "", []):
        s = ""
    else:
        s = str(v)
    return s if len(s) <= cap else s[: cap - 1] + "…"


def _dump(v):
    """复杂嵌套 dict 的紧凑多行 dump"""
    return json.dumps(v, ensure_ascii=False, indent=2, default=str)


# (节标题, [(标签, 键), ...]) —— 只列引擎 pan() 确实返回的字段
_SECTIONS = [
    ("基本信息", [
        ("太乙計", "太乙計"), ("公式類別", "太乙公式類別"), ("公元日期", "公元日期"),
        ("干支", "干支"), ("農曆", "農曆"), ("年號", "年號"),
        ("局式", "局式"), ("紀元", "紀元"), ("太歲", "太歲"),
    ]),
    ("主星", [
        ("太乙落宮", "太乙落宮"), ("太乙", "太乙"), ("天乙", "天乙"), ("地乙", "地乙"),
        ("直符", "直符"), ("四神", "四神"), ("文昌", "文昌"), ("始擊", "始擊"),
        ("計神", "計神"), ("合神", "合神"), ("太尊", "太尊"), ("定目", "定目"), ("帝符", "帝符"),
    ]),
    ("主客算（勝負）", [
        ("主算", "主算"), ("主將", "主將"), ("主參", "主參"),
        ("客算", "客算"), ("客將", "客將"), ("客參", "客參"),
        ("定算", "定算"),
        ("推主客相闗法", "推主客相闗法"), ("推多少以占勝負", "推多少以占勝負"),
        ("推五將發不發", "推五將發不發"), ("推三門具不具", "推三門具不具"),
        ("推孤單以占成敗", "推孤單以占成敗"), ("推陰陽以占厄會", "推陰陽以占厄會"),
    ]),
    ("三才五福", [
        ("君基", "君基"), ("臣基", "臣基"), ("民基", "民基"),
        ("五福", "五福"), ("三風", "三風"), ("五風", "五風"), ("八風", "八風"),
        ("大游", "大游"), ("小游", "小游"), ("飛鳥", "飛鳥"),
    ]),
    ("八門九星", [
        ("八門值事", "八門值事"), ("八門分佈", "八門分佈"), ("八宮旺衰", "八宮旺衰"),
        ("太乙九星", "太乙九星"), ("文昌九星", "文昌九星"), ("九宮貴神", "九宮貴神"),
    ]),
    ("二十八宿", [
        ("二十八宿值日", "二十八宿值日"),
        ("太歲二十八宿", "太歲二十八宿"), ("太歲值宿斷事", "太歲值宿斷事"),
        ("始擊二十八宿", "始擊二十八宿"), ("始擊值宿斷事", "始擊值宿斷事"),
        ("始擊加臨二十八舍所主", "始擊加臨二十八舍所主"),
    ]),
    ("五運六氣", [
        ("五運六氣", "五運六氣"), ("五音之數", "五音之數"), ("五子元局", "五子元局"),
    ]),
    ("災異", [
        ("陽九", "陽九"), ("百六", "百六"), ("歲中災發", "歲中災發"),
        ("入轉日", "入轉日"), ("入轉餘", "入轉餘"), ("朓胸定數", "朓胸定數"),
        ("定朔大餘進退", "定朔大餘進退"), ("定朔小餘", "定朔小餘"),
    ]),
    ("軍事兵陣", [
        ("推太乙風雲飛鳥助戰法", "推太乙風雲飛鳥助戰法"), ("推回軍無言", "推回軍無言"),
        ("推猛虎相拒", "推猛虎相拒"), ("推獅子反擲", "推獅子反擲"),
        ("推白雲捲空", "推白雲捲空"), ("推白龍得雲", "推白龍得雲"),
        ("推臨津問道", "推臨津問道"), ("推雷公入水", "推雷公入水"),
    ]),
    ("格局", [
        ("釋格局", "釋格局"), ("文昌變化", "文昌變化"), ("始擊變化", "始擊變化"),
        ("十六宮分佈", "十六宮分佈"), ("三旗行宮", "三旗行宮"),
        ("十天干歲始擊落宮預測", "十天干歲始擊落宮預測"),
    ]),
    ("命法術（僅命計有內容）", [
        ("厄會行限", "厄會行限"),
        ("明五福吉算所主術", "明五福吉算所主術"), ("明五福太乙所主術", "明五福太乙所主術"),
        ("明君基太乙所主術", "明君基太乙所主術"), ("明臣基太乙所主術", "明臣基太乙所主術"),
        ("明民基太乙所主術", "明民基太乙所主術"), ("神將所主", "神將所主"),
    ]),
]

# 复杂嵌套，单独以多行 dump 展示
_DEEP_SECTIONS = [
    ("運籌博弈分析（--game）", "運籌博弈分析"),
    ("軍事占斷", "軍事占斷"), ("軍事應用", "軍事應用"), ("軍事戰略", "軍事戰略"),
    ("國政章易", "國政章易"), ("金函玉鏡", "金函玉鏡"),
    ("卷八（太乙分野）", "卷八"), ("卷九（大遊軌運）", "卷九"), ("卷十（五運六氣）", "卷十"),
    ("卷十一（十六宮間變化）", "卷十一"), ("卷十二（統運入卦）", "卷十二"),
    ("卷十三（統運卦象）", "卷十三"), ("卷十四（行支編年）", "卷十四"), ("卷十八（十精落宮）", "卷十八"),
]


def _print_summary(r, ji_style, method, game):
    for title, fields in _SECTIONS:
        # 命法術节只在命計(5)时打印（其余计式多为空）
        if title.startswith("命法術") and ji_style != 5:
            continue
        lines = []
        for label, key in fields:
            if key not in r:
                continue
            v = _fmt(r[key])
            if v:
                lines.append(f"  {label}: {v}")
        if lines:
            print(f"━━━ {title} ━━━")
            print("\n".join(lines))
    # 复杂嵌套节
    for title, key in _DEEP_SECTIONS:
        if key not in r or not r[key]:
            continue
        print(f"━━━ {title} ━━━")
        print(_dump(r[key]))


def cast(dt=None, ji_style=0, method=0, game=False, full=False):
    """起盘。返回完整 dict（含 100+ 字段，供 rules/断卦层程序化调用）。"""
    dt = dt or datetime.datetime.now()
    # 引擎边界守卫（诚实标注，不硬算）
    if ji_style == 5:
        print("[太乙神数] 命法(ji_style=5) 上游 kintaiyi 未完成（pan 抛 TypeError），暂不支持。")
        print("  提示：可改用 qizheng（七政四余/果老）或 zhiwei（紫微）看终身命理。")
        return {}
    if ji_style not in _JI or method not in _METHOD:
        print(f"[太乙神数] 非法参数 ji_style={ji_style}(0-5) method={method}(0-3)")
        return {}
    if (ji_style, method) == (2, 3):
        print("[太乙神数] 日計×太乙局 引擎有 bug（TypeError），改用 method=0/1/2。")
        return {}
    if ji_style in (3, 4) and method != 0:
        print(f"[太乙神数] 提示：{_JI[ji_style]}×{_METHOD[method]} 引擎旧代码可能死循环，建议 method=0（統宗）。")

    from engines.taiyi.kintaiyi import Taiyi
    try:
        t = Taiyi(dt.year, dt.month, dt.day, dt.hour, dt.minute)
        r = t.pan(ji_style, method, enable_game_theory=game)
    except Exception as e:  # 引擎抛错时降级，不让 CLI 裸奔
        print(f"[太乙神数] 排盘失败 {type(e).__name__}: {str(e)[:120]}")
        print("  提示：该 ji_style×method 组合可能触及引擎已知 bug，换回 ji_style=0 method=0 试试。")
        return {}

    head = f"[太乙神数] {dt:%Y-%m-%d %H:%M}  {_JI[ji_style]} / {_METHOD[method]}"
    if game:
        head += " +運籌博弈"
    print(head)
    if full:
        print(_dump(r))
    else:
        _print_summary(r, ji_style, method, game)
    return r


def summary(r):
    """一眼摘要卡：局式/太乙落宫/主客算/胜负（借鉴八字/紫微升级的「一眼看懂」层）。"""
    ju = r.get("局式", {})
    ju_s = ju.get("文", str(ju)) if isinstance(ju, dict) else str(ju)

    def _suan(x):
        return str(x[0]) if isinstance(x, list) and x else str(x)

    return "\n".join([
        f"【一眼摘要】太乙神数 · {ju_s}",
        f"  太乙落宫 {r.get('太乙落宮', '')} · 主算{_suan(r.get('主算'))} 客算{_suan(r.get('客算'))}",
        f"  胜负：{r.get('推多少以占勝負', '')}",
    ])


def pan_json(r):
    """盘面事实层 JSON（机读，schema=taiyi-panfact-v1）。"""
    from judge.rules import pan_meta
    return {"schema": "taiyi-panfact-v1", **r, **pan_meta("太乙")}