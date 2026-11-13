# -*- coding: utf-8 -*-
"""排盘结果 -> 自包含 HTML 可视化（水墨·古籍风，无外部依赖）"""
import datetime
import shensha
import xingchong
from judge.qimen_angan import angan_from_sj

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Noto Serif SC','STSong','SimSun',serif; background:#f6f1e6; color:#2b2723; padding:28px; line-height:1.6; }
.wrap { max-width: 760px; margin: 0 auto; }
h1 { font-size: 26px; letter-spacing: 4px; color:#8c2f1f; border-bottom: 2px solid #8c2f1f; padding-bottom: 10px; margin-bottom: 6px; }
.sub { color:#7a7266; font-size: 14px; margin-bottom: 20px; }
.card { background:#fffdf6; border:1px solid #e3d9c4; border-radius:8px; padding:18px 20px; margin-bottom:16px; box-shadow:0 1px 4px rgba(0,0,0,.05); }
.card h2 { font-size: 16px; color:#8c2f1f; margin-bottom: 10px; letter-spacing: 2px; }
table { width:100%; border-collapse: collapse; }
th, td { padding: 8px 6px; text-align:center; font-size: 15px; border-bottom: 1px solid #eee6d4; }
th { color:#8c2f1f; font-weight:600; background:#f3ecda; }
.pillar { font-size: 22px; letter-spacing: 2px; }
.small { font-size: 12px; color:#8a8172; }
.grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.palace { border:1px solid #e3d9c4; border-radius:8px; padding:10px 8px; background:#fbf8ef; min-height:96px; }
.palace.ming { border:2px solid #8c2f1f; background:#f7ead8; }
.palace .name { color:#8c2f1f; font-weight:700; font-size:15px; margin-bottom:4px; }
.palace .gz { font-size:13px; color:#5a5247; margin-bottom:4px; }
.palace .stars { font-size:13px; color:#2b2723; }
.palace .fu { font-size:11px; color:#7a7266; margin-top:3px; }
.palace .dx { font-size:11px; color:#8c2f1f; margin-top:3px; }
.tag { display:inline-block; background:#8c2f1f; color:#fff; font-size:11px; padding:0 5px; border-radius:3px; margin-right:3px; }
.warn { color:#8c2f1f; font-size:13px; }
.gua-row { display:flex; gap:28px; align-items:flex-start; flex-wrap:wrap; }
.gua-col { text-align:center; min-width:96px; }
.gua-name { font-size:15px; color:#8c2f1f; font-weight:700; margin-bottom:8px; letter-spacing:2px; }
.gua-col svg { display:block; margin:0 auto 2px; }
"""


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _shensha_html(result):
    cats = [("贵人吉神", "贵人吉神"), ("文星学业", "文星学业"), ("禄财", "禄财"),
            ("婚姻感情", "婚姻感情"), ("动迁出行", "动迁出行"),
            ("特殊格局", "特殊格局"), ("凶煞", "凶煞")]
    out = []
    for key, label in cats:
        items = result.get(key, [])
        if not items:
            continue
        parts = []
        for it in items:
            loc = "".join(it.get("所在", [])) if isinstance(it.get("所在"), list) else it.get("所在", "")
            parts.append(f"{it['神煞']}（{it['吉凶']}）{loc}")
        out.append(f"<div class='small' style='margin:4px 0'><b>{_esc(label)}</b>：{_esc('　'.join(parts))}</div>")
    return "".join(out) if out else "—"


def _xingchong_html(result):
    labels = [("六合", "六合"), ("六冲", "六冲"), ("三合", "三合"), ("半三合", "半三合"),
              ("三刑", "三刑"), ("六害", "六害"), ("相破", "相破")]
    out = []
    for key, label in labels:
        for it in result.get(key, []):
            out.append(f"<div class='small' style='margin:2px 0'>【{_esc(label)}】{_esc(it['关系'])}"
                       f"（{_esc(it.get('位置', ''))}）— {_esc(it['含义'])}</div>")
    if not out:
        out.append("<div class='small'>四柱地支无明显刑冲合害，命局平和。</div>")
    out.append(f"<div class='warn' style='margin-top:6px'>{_esc(result['综合判断'])}</div>")
    return "".join(out)


def save(path, title, body):
    html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>{_esc(title)}</h1>
{body}
<div class="sub">本盘由 scripts/cast.py 确定性排盘生成，仅供传统文化研习与娱乐参考。</div>
</div></body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[已生成] {path}")


def bazi_html(b, gender, path):
    """八字 -> HTML"""
    lunar = b.getLunar()
    solar = lunar.getSolar()
    cols = [("年柱", b.getYear(), b.getYearShiShenGan(), b.getYearWuXing(), b.getYearNaYin()),
            ("月柱", b.getMonth(), b.getMonthShiShenGan(), b.getMonthWuXing(), b.getMonthNaYin()),
            ("日柱", b.getDay(), b.getDayShiShenGan(), b.getDayWuXing(), b.getDayNaYin()),
            ("时柱", b.getTime(), b.getTimeShiShenGan(), b.getTimeWuXing(), b.getTimeNaYin())]
    rows = "".join(
        f"<tr><th>{n}</th><td class='pillar'>{gz}</td><td>{ss}</td><td>{wx}</td><td class='small'>{ny}</td></tr>"
        for n, gz, ss, wx, ny in cols)
    ss_res = shensha.analyze(b, "男" if gender else "女")
    xc_res = xingchong.analyze(xingchong.from_eightchar(b))
    sub = f"公历 {solar.toYmdHms()}　农历 {lunar.toString()}　{'男' if gender else '女'}"
    body = f"""
<div class="sub">{_esc(sub)}</div>
<div class="card"><h2>四柱</h2><table>
<tr><th></th><th>干支</th><th>十神</th><th>五行</th><th>纳音</th></tr>{rows}</table></div>
<div class="card"><h2>日主</h2>
<p>日主 <b>{b.getDayGan()}{b.getDayZhi()}</b>　长生 {b.getDayDiShi()}　旬空 {b.getDayXunKong()}　命宫 {b.getMingGong()}　胎元 {b.getTaiYuan()}</p></div>
<div class="card"><h2>神煞</h2>{_shensha_html(ss_res)}</div>
<div class="card"><h2>刑冲合害</h2>{_xingchong_html(xc_res)}</div>"""
    save(path, f"八字命盘 · {b.getYear()}", body)


def zhiwei_html(r, path):
    """紫微斗数 -> HTML"""
    cells = []
    for p in r["十二宫"]:
        mains = " ".join(f"{n}({b}{s})" if s else f"{n}({b})" for n, b, s in p["主星"]) or "—"
        fus = " ".join(p["辅星"]) or "—"
        dx = f"{p['大限'][0]}-{p['大限'][1]}岁" if p["大限"] else "—"
        tag = '<span class="tag">命</span>' if p["命"] else ('<span class="tag">身</span>' if p["身"] else "")
        cls = "palace ming" if p["命"] or p["身"] else "palace"
        cells.append(
            f"<div class='{cls}'><div class='name'>{tag}{p['宫']}</div>"
            f"<div class='gz'>{p['干']}{p['支']}</div><div class='stars'>{_esc(mains)}</div>"
            f"<div class='fu'>{_esc(fus)}</div><div class='dx'>{dx}</div></div>")
    body = f"""
<div class="sub">{_esc(r['农历'])}　四柱 {_esc(r['四柱'])}</div>
<div class="card"><h2>命宫身宫</h2>
<p>命宫 <b>{r['命宫']}</b>　身宫 <b>{r['身宫']}</b>　五行局 <b>{r['五行局']}</b>　紫微在{r['紫微']}　天府在{r['天府']}</p>
<p>四化：{_esc(r['四化'])}</p></div>
<div class="card"><h2>十二宫</h2><div class="grid">{''.join(cells)}</div></div>"""
    save(path, f"紫微斗数命盘 · {r['四柱']}", body)


# —— 六爻卦图 ——
def _yao_svg(yang, dong=False):
    """单爻 SVG：阳=实线，阴=两短横；动爻加 ○（老阳）/×（老阴）标记。"""
    if yang:
        line = '<line x1="6" y1="8" x2="78" y2="8" stroke="#2b2723" stroke-width="5" stroke-linecap="round"/>'
        mark = '<text x="86" y="12" font-size="11" fill="#8c2f1f" text-anchor="middle">○</text>' if dong else ''
    else:
        line = ('<line x1="6" y1="8" x2="38" y2="8" stroke="#2b2723" stroke-width="5" stroke-linecap="round"/>'
                '<line x1="46" y1="8" x2="78" y2="8" stroke="#2b2723" stroke-width="5" stroke-linecap="round"/>')
        mark = '<text x="86" y="12" font-size="11" fill="#8c2f1f" text-anchor="middle">×</text>' if dong else ''
    return f'<svg width="94" height="16" viewBox="0 0 94 16">{line}{mark}</svg>'


def _hexagram_lines(name):
    """卦名 -> 6 爻阴阳（自下而上，1 阳 0 阴）。"""
    from gua import GUA64, YAO
    for (u, d), n in GUA64.items():
        if n == name:
            return YAO[d] + YAO[u]
    return [0] * 6


def liuyao_html(r, ben, bian, dong, path):
    """六爻卦图 -> HTML（本卦/变卦爻画 + 六亲干支 + 六神 + 世应动空）。"""
    bl = _hexagram_lines(ben)
    vl = _hexagram_lines(bian)
    dong_set = set(dong or [])
    rows = []
    for i in range(5, -1, -1):  # 上爻 → 初爻
        x = r["六爻"][i]
        tag = " ".join(filter(None, [x["世应"], x["动"], x["空"]]))
        ben_cell = (f'{_yao_svg(bl[i] == 1, (i + 1) in dong_set)}'
                    f'<div class="small">{_esc(x["本卦"])}</div>')
        bian_cell = (f'{_yao_svg(vl[i] == 1, False)}'
                     f'<div class="small">{_esc(x["变卦"] or "—")}</div>')
        rows.append(
            f"<tr><td class='small'>{_esc(x['六神'])}</td><td>{ben_cell}</td>"
            f"<td>{bian_cell}</td><td class='small'>{_esc(tag) or '—'}</td></tr>")
    body = f"""
<div class="sub">占时 {_esc(r.get('日辰', ''))}　月建 {_esc(r.get('月建', ''))}　旬空 {_esc(r.get('旬空', ''))}</div>
<div class="card"><h2>卦</h2>
<p>本卦 <b>{_esc(ben)}</b>　变卦 <b>{_esc(bian)}</b>　动爻 {_esc('、'.join(str(x) for x in (dong or [])) or '无(静卦)')}　{_esc(r.get('宫', ''))}　世爻第{r.get('世爻')}　应爻第{r.get('应爻')}</p></div>
<div class="card"><h2>爻（上→下）</h2><table>
<tr><th>六神</th><th>本卦（六亲 干支）</th><th>变卦（六亲 干支）</th><th>标</th></tr>{''.join(rows)}</table></div>"""
    save(path, f"六爻卦图 · {ben}", body)


# —— 流年趋势曲线 ——
def liunian_trend_html(t, path):
    """八字流年趋势 -> SVG 折线图（扶抑·得令简化模型）。"""
    data = t["data"]
    n = len(data)
    w, h = 760, 240
    pad_l, pad_r, pad_t, pad_b = 46, 18, 22, 34
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b

    def px(i):
        return pad_l + pw * i / (n - 1) if n > 1 else pad_l + pw / 2

    def py(score):
        return pad_t + ph * (1 - (score - 10) / 80)  # 10→底 90→顶

    # 网格线 + Y 轴标签
    grid = []
    for s in (10, 30, 50, 70, 90):
        y = py(s)
        color = "#8c2f1f" if s >= 70 else ("#2b2723" if s == 50 else "#b3a68c")
        grid.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" '
                    f'stroke="#e3d9c4" stroke-width="1"/>'
                    f'<text x="{pad_l - 6}" y="{y + 4:.1f}" font-size="11" fill="{color}" '
                    f'text-anchor="end">{s}</text>')
    # 数据点 + 折线
    pts = [(px(i), py(d["score"])) for i, d in enumerate(data)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = []
    labels = []
    for i, d in enumerate(data):
        x, y = pts[i]
        c = "#8c2f1f" if d["score"] >= 70 else ("#8a8172" if d["score"] <= 30 else "#5a5247")
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{c}"/>')
        labels.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" font-size="11" fill="{c}" '
                      f'text-anchor="middle">{d["score"]}</text>')
    # X 轴年份标签（每 N 年标一个）
    step = max(1, n // 12)
    xlabs = []
    for i in range(0, n, step):
        x, y = pts[i]
        xlabs.append(f'<text x="{x:.1f}" y="{h - 10}" font-size="11" fill="#7a7266" '
                     f'text-anchor="middle">{data[i]["year"]}</text>')
    svg = (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'{"" .join(grid)}'
           f'<polyline points="{poly}" fill="none" stroke="#8c2f1f" stroke-width="2"/>'
           f'{"" .join(dots)}{"" .join(labels)}{"" .join(xlabs)}</svg>')
    body = f"""
<div class="sub">日主 <b>{_esc(t['day_gan'])}{_esc(t['day_zhi'])}</b>（{_esc(t['wang'])}）
{_esc(t['start'])}~{_esc(t['start'] + t['n'] - 1)} 年　喜用按扶抑（旺喜克泄耗 / 弱喜生扶）</div>
<div class="card"><h2>流年趋势（喜忌得分）</h2>{svg}</div>
<div class="warn">本曲线为扶抑·得令简化模型（[规则推演/HEURISTIC]），只示喜忌起伏大方向，非精确吉凶；精确年份类问题按「不确定+低置信度」处理。</div>"""
    save(path, f"八字流年趋势 · {t['day_gan']}{t['day_zhi']}", body)


# —— 梅花易数三卦图 ——
def meihua_html(r, path):
    """梅花易数 -> HTML（本卦/互卦/变卦三列 + 动爻 + 体用）"""
    def col(name, dong_yao=None):
        lines = _hexagram_lines(name)
        rows = []
        for i in range(5, -1, -1):  # 上爻 → 初爻
            is_dong = dong_yao is not None and (i + 1) == dong_yao
            rows.append(_yao_svg(lines[i] == 1, is_dong))
        return f'<div class="gua-col"><div class="gua-name">{_esc(name)}</div>{"".join(rows)}</div>'

    body = f"""
<div class="sub">{_esc(r.get('note', ''))}</div>
<div class="card"><h2>卦象</h2>
<div class="gua-row">{col(r['本卦'], r['动爻'])}{col(r['互卦'])}{col(r['变卦'])}</div>
<p style="margin-top:14px">体卦 <b>{_esc(r['体卦'])}（{_esc(r['体五行'])}）</b>　用卦 <b>{_esc(r['用卦'])}（{_esc(r['用五行'])}）</b>　→　<b>{_esc(r['体用关系'])}</b></p>
<p class="small">动爻：第 {r['动爻']} 爻（○/× 标记）　上卦 {_esc(r['上卦'])}　下卦 {_esc(r['下卦'])}</p>
</div>"""
    save(path, f"梅花易数 · {r['本卦']}", body)


# —— 奇门遁甲九宫格 ——
_QIMEN_SHEN = {"符": "值符", "蛇": "螣蛇", "陰": "太阴", "合": "六合",
               "虎": "白虎", "玄": "玄武", "地": "九地", "天": "九天"}


def qimen_html(sj, path):
    """奇门遁甲 -> HTML（洛书九宫格：门/星/神/天盘干/地盘干）"""
    _fanti = {"離": "离", "兌": "兑"}
    def norm(d):
        return {_fanti.get(k, k): v for k, v in d.items()}
    men = norm(sj.get("門", {}) or {})
    xing = norm(sj.get("星", {}) or {})
    shen = norm(sj.get("神", {}) or {})
    tian = norm(sj.get("天盤", {}) or {})
    di = norm(sj.get("地盤", {}) or {})
    # 暗干（飞干）：值使加时干，阳顺阴逆飞九宫
    ag = angan_from_sj(sj)
    angan = {k: v for k, v in (ag[0] if ag else {}).items()}
    order = ["巽", "离", "坤", "震", "中", "兑", "艮", "坎", "乾"]  # 洛书，上南下北
    cells = []
    for g in order:
        if g == "中":
            cells.append(f'<div class="palace"><div class="name">中宫</div>'
                         f'<div class="gz">天盘 {_esc(tian.get("中", "—"))}　地盘 {_esc(di.get("中", "—"))}　暗干 {_esc(angan.get(5, "—"))}</div></div>')
            continue
        m = men.get(g, "—")
        x = xing.get(g, "—")
        if x == "禽":
            x = "芮·禽"
        s = _QIMEN_SHEN.get(shen.get(g, ""), shen.get(g, "—"))
        _gid = {"坎": 1, "坤": 2, "震": 3, "巽": 4, "乾": 6, "兑": 7, "艮": 8, "离": 9}.get(g)
        cells.append(f'<div class="palace"><div class="name">{_esc(g)}宫</div>'
                     f'<div class="stars">门 {_esc(m)} · 星 {_esc(x)} · 神 {_esc(s)}</div>'
                     f'<div class="gz">天盘 {_esc(tian.get(g, "—"))} / 地盘 {_esc(di.get(g, "—"))} / 暗干 {_esc(angan.get(_gid, "—"))}</div></div>')
    body = f"""
<div class="sub">{_esc(sj.get('干支', ''))}　{_esc(sj.get('排局', ''))}　{_esc(sj.get('節氣', ''))}　旬空 {_esc(str(sj.get('旬空', '')))}</div>
<div class="card"><h2>九宫（上南下北）</h2><div class="grid">{''.join(cells)}</div></div>"""
    save(path, f"奇门遁甲 · {sj.get('排局', '')}", body)


# —— 大六壬四课三传图 ——
_TIANJIANG_FULL = {"貴": "贵人", "蛇": "螣蛇", "雀": "朱雀", "合": "六合", "勾": "勾陈",
                   "龍": "青龙", "空": "天空", "虎": "白虎", "常": "太常", "玄": "玄武",
                   "陰": "太阴", "后": "天后"}
# 三传六亲简称 -> 全称
_LIUQIN_FULL = {"父": "父母", "財": "妻财", "财": "妻财", "官": "官鬼", "子": "子孙", "兄": "兄弟"}


def liuren_html(r, path):
    """大六壬 -> HTML（课体格局 + 三传六亲 + 四课 + 天地盘十二宫）"""
    def jiang_full(j):
        return _TIANJIANG_FULL.get(j, j)

    ju = r.get("格局", []) or []
    ju_tags = "".join(f'<span class="tag">{_esc(j)}</span>' for j in ju) or "—"

    chuan = r.get("三傳", {}) or {}
    chuan_cells = []
    for label, key in (("初传", "初傳"), ("中传", "中傳"), ("末传", "末傳")):
        item = chuan.get(key)
        if not item:
            continue
        liuqin = _LIUQIN_FULL.get(item[2], item[2]) if len(item) > 2 else ""
        extra = item[3] if len(item) > 3 else ""
        extra_label = "旬空" if extra == "空" else (f"遁{extra}" if extra else "")
        stars = f"{_esc(jiang_full(item[1]))} · {_esc(liuqin)}"
        if extra_label:
            stars += f" · <span class='dx'>{_esc(extra_label)}</span>"
        chuan_cells.append(f'<div class="palace"><div class="name">{label}</div>'
                           f'<div class="gz">{_esc(item[0])}</div>'
                           f'<div class="stars">{stars}</div></div>')

    ke = r.get("四課", {}) or {}
    ke_cells = []
    for label, key in (("四课", "四課"), ("三课", "三課"), ("二课", "二課"), ("一课", "一課")):
        item = ke.get(key)
        if not item:
            continue
        ke_cells.append(f'<div class="palace"><div class="name">{label}</div>'
                        f'<div class="gz">{_esc(item[0])}</div>'
                        f'<div class="stars">{_esc(jiang_full(item[1]))}</div></div>')

    dz = "子丑寅卯辰巳午未申酉戌亥"
    ztp = r.get("地轉天盤", {}) or {}
    ztj = r.get("地轉天將", {}) or {}
    pan = []
    for z in dz:
        pan.append(f'<div class="palace"><div class="name">{z}</div>'
                   f'<div class="gz">天 {_esc(ztp.get(z, "—"))}</div>'
                   f'<div class="stars">{_esc(jiang_full(ztj.get(z, ""))) or "—"}</div></div>')

    body = f"""
<div class="sub">{_esc(r.get('日期', ''))}　{_esc(r.get('節氣', ''))}　日马 {_esc(r.get('日馬', ''))}</div>
<div class="card" style="text-align:center"><h2>课体格局</h2><div style="font-size:22px;letter-spacing:4px;color:#8c2f1f">{ju_tags}</div></div>
<div class="card"><h2>三传（天将 · 六亲）</h2><div class="grid">{''.join(chuan_cells)}</div></div>
<div class="card"><h2>四课（上神 · 下神 · 天将）</h2><div class="grid">{''.join(ke_cells)}</div></div>
<div class="card"><h2>天地盘（地盘十二宫 · 天盘 · 天将）</h2><div class="grid">{''.join(pan)}</div></div>"""
    save(path, f"大六壬 · {r.get('日期', '')}", body)


# —— 太乙神数 ——
_TAIYI_GONG = {1: "乾", 2: "午", 3: "艮", 4: "卯", 5: "中", 6: "酉", 7: "坤", 8: "子", 9: "巽"}


def _ty_suan(v):
    """主算/客算/定算 list -> 短串"""
    if isinstance(v, list) and v:
        n = v[0]
        tags = [str(t) for t in (v[1] if len(v) > 1 and isinstance(v[1], list) else [])]
        return f"{n}" + ("（" + "、".join(tags) + "）" if tags else "")
    return str(v) if v not in (None, "", []) else "—"


def taiyi_html(r, path):
    """太乙神数 -> HTML（主客算胜负 + 太乙九宫格 + 主星三才 + 二十八宿灾异）"""
    ju = r.get("局式", {}) or {}
    ju_wen = ju.get("文", "")
    gz = "　".join(r.get("干支", []) or [])
    sub = f"{_esc(r.get('太乙計', ''))} / {_esc(r.get('太乙公式類別', ''))}　{_esc(ju_wen)}　积年 {_esc(ju.get('積年數', ''))}　干支 {_esc(gz)}"

    # 主客算对比表
    def row(label, val):
        return f"<tr><th>{label}</th><td>{_esc(_ty_suan(val))}</td></tr>"
    zhuke = "".join([
        row("主算", r.get("主算")), row("主将", r.get("主將")), row("主参", r.get("主參")),
        row("客算", r.get("客算")), row("客将", r.get("客將")), row("客参", r.get("客參")),
        row("定算", r.get("定算")),
    ])
    shengfu = _esc(r.get("推多少以占勝負", "") or r.get("推主客相闗法", ""))
    wujiang = _esc(r.get("推五將發不發", "") or "")

    # 太乙九宫格（太乙宫序，非洛书）
    men = r.get("八門分佈", {}) or {}
    wang = r.get("八宮旺衰", {}) or {}
    lg = r.get("太乙落宮")
    cells = []
    for n in range(1, 10):
        name = _TAIYI_GONG[n]
        cls = "palace ming" if n == lg else "palace"
        mark = "<div class='dx'>★太乙</div>" if n == lg else ""
        cells.append(f'<div class="{cls}"><div class="name">{name}宫({n})</div>'
                     f'<div class="stars">门 {_esc(men.get(n, "—"))} · {_esc(wang.get(n, "—"))}</div>{mark}</div>')

    # 主星
    def star(label, key):
        v = r.get(key)
        if isinstance(v, list):
            v = "、".join(str(x) for x in v)
        return f"<tr><th>{label}</th><td>{_esc(v if v not in (None, '', []) else '—')}</td></tr>" if (v not in (None, "", [])) else ""
    zhuxing = "".join([
        star("太乙落宫", "太乙"), star("天乙", "天乙"), star("地乙", "地乙"), star("直符", "直符"),
        star("四神", "四神"), star("文昌", "文昌"), star("始击", "始擊"), star("计神", "計神"),
        star("合神", "合神"), star("太尊", "太尊"), star("定目", "定目"), star("帝符", "帝符"),
    ])

    # 三才五福
    sancai = "".join([
        star("君基", "君基"), star("臣基", "臣基"), star("民基", "民基"), star("五福", "五福"),
        star("大游", "大游"), star("小游", "小游"), star("飞鸟", "飛鳥"),
    ])

    # 二十八宿 + 灾异
    xiu = []
    for label, key in (("二十八宿值日", "二十八宿值日"), ("太岁宿", "太歲二十八宿"), ("太岁值宿断事", "太歲值宿斷事"),
                       ("始击宿", "始擊二十八宿"), ("始击值宿断事", "始擊值宿斷事")):
        v = r.get(key)
        if v:
            xiu.append(f"<div class='small'><b>{label}</b>：{_esc(v)}</div>")
    zaiyi = []
    for label, key in (("阳九", "陽九"), ("百六", "百六"), ("岁中灾发", "歲中災發")):
        v = r.get(key)
        if v not in (None, "", []):
            zaiyi.append(f"<div class='small'><b>{label}</b>：{_esc(_ty_suan(v) if isinstance(v, (list, dict)) else v)}</div>")

    body = f"""
<div class="sub">{sub}</div>
<div class="card"><h2>主客算（胜负）</h2>
<table>{zhuke}</table>
<div class="warn" style="margin-top:8px">{shengfu}</div>
<div class="small" style="margin-top:4px">{wujiang}</div>
</div>
<div class="card"><h2>太乙九宫（太乙宫序 · 门/旺衰）</h2><div class="grid">{''.join(cells)}</div></div>
<div class="card"><h2>主星</h2><table>{zhuxing}</table></div>
<div class="card"><h2>三才五福</h2><table>{sancai}</table></div>
<div class="card"><h2>二十八宿</h2>{''.join(xiu) or '—'}</div>
<div class="card"><h2>灾异</h2>{''.join(zaiyi) or '—'}</div>"""
    save(path, f"太乙神数 · {ju_wen}", body)