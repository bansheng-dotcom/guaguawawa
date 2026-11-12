# -*- coding: utf-8 -*-
"""reportkit.cli —— 最小闭环：init / add-obs / build / seal / diff / audit / affected

用法：
  python -m reportkit.cli init  nmg_protein_2026Q4
  python -m reportkit.cli add-obs nmg_protein_2026Q4 --preset nmg
  python -m reportkit.cli build nmg_protein_2026Q4
  python -m reportkit.cli seal  nmg_protein_2026Q4 --build <id> --by 张三
  python -m reportkit.cli diff  nmg_protein_2026Q4 --from <id> --to <id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from reportkit import core  # noqa: E402
from reportkit import extras  # noqa: E402
from reportkit import render as R  # noqa: E402

CASE_ROOT = BASE / "cases"


def case_dir(name: str) -> Path:
    return CASE_ROOT / name


def load_case(name: str) -> dict:
    import yaml
    p = case_dir(name) / "case.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def cmd_init(args):
    d = case_dir(args.name)
    (d / "builds").mkdir(parents=True, exist_ok=True)
    (d / "sealed").mkdir(exist_ok=True)
    (d / "out").mkdir(exist_ok=True)
    tmpl = BASE / "templates" / "case.yaml"
    if not (d / "case.yaml").exists() and tmpl.exists():
        shutil.copy(tmpl, d / "case.yaml")
    print(f"initialized {d}")


def cmd_add_obs(args):
    d = case_dir(args.name)
    conn = core.db(d)
    DAILY = ["猪肉", "牛肉", "羊肉", "鸡蛋", "白条鸡", "鲫鱼", "鲤鱼", "白鲢鱼", "大带鱼"]
    total_ok = total_bad = 0

    if args.preset == "nmg":
        src = args.source_dir or Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12\底稿版")
        ok, bad = core.add_csv(conn, src / "data_daily.csv", "farm_daily", "全国", "元/公斤", "A", "批发均价", DAILY)
        total_ok += ok; total_bad += bad

        # 周度：每个 (week,item) 展开为 本周/上周/去年同期/环比/同比
        import csv
        rows = []
        for rec in csv.DictReader((src / "data_weekly.csv").open(encoding="utf-8-sig")):
            wk = rec["week"][:4] + "-" + rec["week"][4:6] + "-" + rec["week"][6:8]
            for spec, key, unit in [("本周", "this", "元/公斤"), ("上周", "last", "元/公斤"),
                                    ("去年同期", "yoy_base", "元/公斤"), ("环比", "mom_pct", "%"),
                                    ("同比", "yoy_pct", "%")]:
                v = (rec.get(key) or "").replace("%", "")
                if v in ("", None):
                    continue
                rows.append({"source": "farm_weekly", "market": "全国", "item": rec["item"], "date": wk,
                             "value": v, "unit": unit, "spec": spec, "grade": "A"})
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        # 全区旬度（硬编码自既有底稿，来源 S1—S4）
        retail = [("牛肉", 36.95, 37.17, 37.28), ("羊肉（去骨）", 39.27, 39.42, 39.56),
                  ("白条鸡", 11.89, 11.95, 11.97), ("鸡蛋", 5.68, 5.31, 5.18),
                  ("带鱼", 17.16, 17.16, 17.20), ("草鱼", 11.33, 11.32, 11.31),
                  ("鲤鱼", 8.92, 8.89, 8.86)]
        dates = ["2026-10-05", "2026-10-20", "2026-11-05"]
        rows = [{"source": "nmg_monitor", "market": "全区", "item": n, "date": d_, "value": v,
                 "unit": "元/斤", "spec": "零售采价", "grade": "A"}
                for n, a, b, c in retail for d_, v in zip(dates, (a, b, c))]
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        # 呼市周度
        hh = {
            "2026-10-19": {"牛肉": 39.23, "羊肉": 40.00, "鸡肉": 11.86, "鸡蛋": 5.30, "带鱼": 19.66, "草鱼": 12.28, "鲤鱼": 9.93, "猪精瘦": 13.11},
            "2026-10-26": {"牛肉": 39.36, "羊肉": 40.14, "鸡肉": 11.86, "鸡蛋": 5.02, "带鱼": 19.66, "草鱼": 12.26, "鲤鱼": 9.79, "猪精瘦": 13.11},
            "2026-10-30": {"牛肉": 39.36, "羊肉": 40.14, "鸡肉": 11.86, "鸡蛋": 5.03, "带鱼": 19.93, "草鱼": 12.13, "鲤鱼": 9.74, "猪精瘦": 13.02},
            "2026-11-04": {"牛肉": 39.28, "羊肉": 40.31, "鸡肉": 11.86, "鸡蛋": 5.31, "带鱼": 19.66, "草鱼": 12.25, "鲤鱼": 9.96, "猪精瘦": 13.11},
            "2026-11-06": {"牛肉": 39.36, "羊肉": 40.14, "鸡肉": 11.86, "鸡蛋": 5.11, "带鱼": 19.99, "草鱼": 11.94, "鲤鱼": 9.74, "猪精瘦": 12.93},
        }
        rows = [{"source": "hh_fgw", "market": "呼和浩特", "item": k, "date": dt, "value": v,
                 "unit": "元/斤", "spec": "零售采价", "grade": "A"} for dt, kv in hh.items() for k, v in kv.items()]
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        # 期货
        rows = []
        import csv as _csv
        for rec in _csv.DictReader((src / "data_futures.csv").open(encoding="utf-8-sig")):
            for spec in ("open", "high", "low", "close"):
                rows.append({"source": "futures", "market": "大商所", "item": rec["name"], "date": rec["date"],
                             "value": rec[spec], "unit": "元/吨", "spec": spec, "grade": "A"})
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        # 产地与批发实盘（进 store 但暂不进正文 → 用于演示"弃置率"）
        origin = [("赤峰敖汉旗", "2026-10-26", "育肥牛", 14.80), ("赤峰敖汉旗", "2026-11-09", "育肥牛", 14.50),
                  ("赤峰敖汉旗", "2026-11-09", "白条鸡", 8.90), ("赤峰敖汉旗", "2026-11-09", "下架鸡", 4.45),
                  ("赤峰敖汉旗", "2026-11-02", "鲜蛋装车", 4.11), ("赤峰敖汉旗", "2026-11-09", "鲜蛋装车", 4.33),
                  ("通辽开鲁", "2026-11-01", "白条鹅", 11.00), ("通辽（西门塔尔）", "2026-11-11", "活牛", 17.60),
                  ("通辽科左中旗", "2026-11-11", "肥牛", 13.20), ("乌兰察布集宁", "2026-11-10", "羔羊", 19.55),
                  ("锡林郭勒阿巴嘎", "2026-11-10", "绒山羊", 20.31)]
        rows = [{"source": "origin", "market": m_, "item": it, "date": dt, "value": v,
                 "unit": "元/斤", "spec": "出场/产地", "grade": "A"} for m_, dt, it, v in origin]
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        whole = [("东瓦窑", "牛肉", 72.0), ("东瓦窑", "羊肉", 72.0), ("东瓦窑", "白条鸡", 17.0),
                 ("东瓦窑", "活草鱼", 17.0), ("东瓦窑", "活鲤鱼", 13.0), ("保全庄", "鸭肉", 21.0),
                 ("保全庄", "对虾", 67.0), ("保全庄", "淡水虾", 165.0), ("保全庄", "带鱼", 32.0),
                 ("包头友谊", "羊肉", 58.0), ("包头友谊", "活鲤鱼", 14.0)]
        rows = [{"source": "wholesale", "market": mk, "item": it, "date": "2026-11-10", "value": v,
                 "unit": "元/公斤", "spec": "批发实盘", "grade": "B"} for mk, it, v in whole]
        ok, bad = core.upsert_obs(conn, rows); total_ok += ok; total_bad += bad

        # 冲突与失败（研究过程中真实发生的）
        conn.execute("DELETE FROM conflict")
        for row in [("鸡蛋（白皮）", "保全庄批发", 18.5, "政府零售口径折算", 23.0, -19.57, "单点报价噪声，降级为方向参考"),
                    ("牛肉", "发改委牛腩", 37.28, "商务预报牛腿肉", 35.03, 6.41, "部位口径差，不可相乘成趋势")]:
            conn.execute("INSERT INTO conflict(item,a_source,a_value,b_source,b_value,delta_pct,verdict) "
                         "VALUES(?,?,?,?,?,?,?)", row)
        conn.execute("DELETE FROM failed")
        for row in [("对虾 10 月价格", "证券之星/21food/全国批发接口", "10 月无该市场报价", "11 月起按周自采，补齐历史"),
                    ("鸭/鹅政府序列", "内蒙古价格监测平台 12 盟市", "目录内无此品类", "自建双周采价，先补保全庄单一市场"),
                    ("赤峰/包头/通辽周报", "三市发改委官网", "页面结构不统一，未做适配", "模板化抓取，下批处理")]:
            conn.execute("INSERT INTO failed(target,tried,reason,next_action) VALUES(?,?,?,?)", row)
        conn.commit()

    print(f"obs ok={total_ok} quarantined={total_bad}")
    n = conn.execute("SELECT COUNT(*) FROM obs").fetchone()[0]
    print(f"store rows={n}")


def ids_for(conn, source: str, item: str, spec: str) -> list[str]:
    rows = conn.execute("SELECT id FROM obs WHERE source=? AND item=? AND spec=? ORDER BY date",
                        (source, item, spec)).fetchall()
    if not rows:
        return []
    return [rows[0][0]] + ([rows[-1][0]] if len(rows) > 1 else [])


# ---------------------------------------------------------------- 批注
def load_anns(d: Path, m: dict) -> list[dict]:
    anns = core.parse_annotations(d / "annotations.md")
    changed = False
    for a in anns:
        cur = core.anchor_hash(m, a["anchor"])
        a["current"] = cur
        a["status"] = "new" if not a["hash"] else ("ok" if a["hash"] == cur else "stale")
        if a["status"] == "new":
            a["hash"] = cur
            changed = True
    if changed:
        write_anns(d, anns)
    return anns


def write_anns(d: Path, anns: list[dict]) -> None:
    parts = ["# 批注（人的判断，挂在数据锚点上）",
             "",
             "> 每条批注带 8 位数据指纹；数据变化后批注保留但标 ⚠，需人工复核。",
             ""]
    for a in anns:
        parts.append(f"## {a['anchor']}")
        parts.append(a["text"].strip())
        parts.append(f"<!-- hash: {a['hash']} -->")
        parts.append("")
    (d / "annotations.md").write_text("\n".join(parts), encoding="utf-8")


def build_claims(m: dict, conn=None) -> list[dict]:
    d, w = m["daily"], m["weekly"]
    out = [
        {"id": "C1", "section": "s2-1", "kind": "fact",
         "text": "全国鸡蛋 33 个交易日 {{daily.鸡蛋.change|pct}}，是九品类最大跌幅；牛肉 {{daily.牛肉.change|pct}} 为唯一显著上涨。",
         "obs": [d["鸡蛋"]["first_id"], d["鸡蛋"]["last_id"], d["牛肉"]["first_id"], d["牛肉"]["last_id"]]},
        {"id": "C2", "section": "s2-1", "kind": "fact",
         "text": "鸡蛋 CV {{daily.鸡蛋.cv|num2}}% 为九品类最高，牛肉 {{daily.牛肉.cv|num2}}%、羊肉 {{daily.羊肉.cv|num2}}% 最低。",
         "obs": [d["鸡蛋"]["first_id"], d["鸡蛋"]["last_id"]]},
        {"id": "C3", "section": "s2-2", "kind": "fact",
         "text": "周度同比三层分化：鸡蛋 {{weekly.鸡蛋.yoy|num2}}%、牛肉 {{weekly.牛肉.yoy|num2}}% 在高位，猪肉 {{weekly.猪肉.yoy|num2}}% 在低位。",
         "obs": (ids_for(conn, "farm_weekly", "鸡蛋", "同比") + ids_for(conn, "farm_weekly", "牛肉", "同比") + ids_for(conn, "farm_weekly", "猪肉", "同比")) if conn else []},
        {"id": "C4", "section": "s2-6", "kind": "inference",
         "text": "内蒙鸡蛋 {{retail.鸡蛋.change|pct}} 只跟了全国 {{daily.鸡蛋.change|pct}} 的一半，传导缺口 {{gap_egg|num2}} 个百分点。",
         "obs": [d["鸡蛋"]["first_id"], d["鸡蛋"]["last_id"]]},
        {"id": "C5", "section": "s2-5", "kind": "fact",
         "text": "生猪期货 {{futures.生猪主连.change|pct}}、豆粕 {{futures.豆粕主连.change|pct}}、玉米 {{futures.玉米主连.change|pct}}：成本端未涨。",
         "obs": (ids_for(conn, "farm_weekly", "鸡蛋", "同比") + ids_for(conn, "farm_weekly", "牛肉", "同比") + ids_for(conn, "farm_weekly", "猪肉", "同比")) if conn else []},
    ]
    return out


def used_obs_ids(conn, sources: list[str]) -> set[str]:
    q = "SELECT id FROM obs WHERE source IN (%s)" % ",".join("?" * len(sources))
    return {r[0] for r in conn.execute(q, sources)}


def cmd_build(args):
    d = case_dir(args.name)
    case = load_case(args.name)
    conn = core.db(d)
    if conn.execute("SELECT COUNT(*) FROM obs").fetchone()[0] == 0:
        raise SystemExit("store 为空，先跑 add-obs")

    part = extras.refresh_cache(conn, d)
    m = core.compute_metrics(conn)
    m["daily"] = extras.daily_from_cache(d, conn)
    claims = build_claims(m, conn)

    conn.execute("DELETE FROM claim")
    for c in claims:
        conn.execute("INSERT INTO claim(id,section,text,kind,obs_ids) VALUES(?,?,?,?,?)",
                     (c["id"], c["section"], c["text"], c["kind"], ",".join(c["obs"])))
    conn.commit()

    used = used_obs_ids(conn, ["farm_daily", "farm_weekly", "nmg_monitor", "hh_fgw", "futures"])
    gaps = []
    discarded = conn.execute(
        "SELECT source, COUNT(*) n FROM obs WHERE source NOT IN ('farm_daily','farm_weekly','nmg_monitor','hh_fgw','futures') GROUP BY source").fetchall()
    for r in discarded:
        gaps.append({"cell": f"未进正文：{r['source']}（{r['n']} 条）", "owner": "R05", "due": "下批",
                     "method": "并入批发/产地章节"})
    for cat in case["categories"]:
        n = conn.execute("SELECT COUNT(*) FROM obs WHERE item LIKE ?", (f"%{cat}%",)).fetchone()[0]
        if n == 0:
            gaps.append({"cell": f"{cat}.price_series", "owner": "待指派", "due": "待定", "method": "自建双周采价"})

    audit = core.audit(conn, case, used, gaps)
    snap = core.snapshot(conn, m)
    build_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    snap["build_id"] = build_id

    anns = load_anns(d, m)
    html = R.render(case, conn, m, audit, snap,
                    [dict(id=c["id"], section=c["section"], text=c["text"]) for c in claims],
                    conn.execute("SELECT * FROM conflict").fetchall(),
                    conn.execute("SELECT * FROM failed").fetchall(),
                    anns=anns)
    out_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
    html = html.replace("__HASH__", out_hash)
    snap["output_hash"] = out_hash

    bdir = d / "builds" / build_id
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "report.html").write_text(html, encoding="utf-8")
    manifest = {"build_id": build_id, "case": args.name, "mode": "draft",
                "snapshot": snap, "audit": {k: audit[k] for k in ("obs_total", "obs_used", "retention", "trace_rate", "discard", "coverage", "verdict")},
                "metrics": m, "template_version": "reportkit-1.1", "by": args.by or "auto",
                "source_stats": extras.source_stats(conn), "partition": part}
    (bdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(bdir / "report.html", d / "out" / "report.html")

    # diff vs 上一个 build
    prevs = sorted([p for p in (d / "builds").iterdir() if p.is_dir() and p.name != build_id])
    if prevs:
        prev = json.loads((prevs[-1] / "manifest.json").read_text(encoding="utf-8"))
        dff = core.diff(prev, manifest)
        (bdir / "diff.json").write_text(json.dumps(dff, ensure_ascii=False, indent=2), encoding="utf-8")
        (bdir / "diff.html").write_text(render_diff(dff, prev, manifest), encoding="utf-8")

    print(json.dumps({"build_id": build_id, "retention": audit["retention"], "trace": audit["trace_rate"],
                      "discard": audit["discard"], "coverage": audit["coverage"],
                      "obs": audit["obs_total"], "hash": out_hash}, ensure_ascii=False))


def render_diff(dff, prev, cur) -> str:
    rows = "".join(
        f'<tr><td>{c["key"]}</td><td class="num">{c["from"]}</td><td class="num">{c["to"]}</td></tr>'
        for c in dff.get("changes", []))
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>修订说明</title>
<style>body{{font-family:'Microsoft YaHei';max-width:820px;margin:40px auto;line-height:1.7}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #e5e7eb;padding:8px}}</style></head>
<body><h1>修订说明</h1>
<p>{dff.get("from")} → {dff.get("to")}｜新增观测 {dff.get("rows_delta", 0)} 条</p>
<table><tr><th>指标</th><th>上版</th><th>本版</th></tr>{rows or '<tr><td colspan=3>数值无变化</td></tr>'}</table>
<p style="color:#6B7280;font-size:12px">由 reportkit.diff 自动生成；仅列出变化 ≥ 0.01 的指标。</p></body></html>"""


def cmd_seal(args):
    d = case_dir(args.name)
    bdir = d / "builds" / args.build
    if not bdir.exists():
        raise SystemExit(f"build 不存在: {args.build}")
    man = json.loads((bdir / "manifest.json").read_text(encoding="utf-8"))
    sdir = d / "sealed" / f"{args.build}-{man['snapshot']['output_hash']}"
    if sdir.exists():
        shutil.rmtree(sdir)
    shutil.copytree(bdir, sdir)
    man["mode"] = "sealed"
    man["sealed_by"] = args.by or "unknown"
    man["sealed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    (sdir / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sealed": str(sdir), "output_hash": man["snapshot"]["output_hash"],
                      "rows": man["snapshot"]["rows"]}, ensure_ascii=False))


def cmd_diff(args):
    d = case_dir(args.name)
    a = json.loads((d / "builds" / args.from_ / "manifest.json").read_text(encoding="utf-8"))
    b = json.loads((d / "builds" / args.to / "manifest.json").read_text(encoding="utf-8"))
    dff = core.diff(a, b)
    out = d / "builds" / args.to / "diff.html"
    out.write_text(render_diff(dff, a, b), encoding="utf-8")
    print(json.dumps(dff, ensure_ascii=False, indent=2)[:800])
    print("→", out)


def cmd_annotate(args):
    d = case_dir(args.name)
    case = load_case(args.name)
    conn = core.db(d)
    m = core.compute_metrics(conn)
    anns = core.parse_annotations(d / "annotations.md")
    h = core.anchor_hash(m, args.anchor)
    anns.append({"anchor": args.anchor, "text": args.text, "hash": h})
    write_anns(d, anns)
    print(json.dumps({"anchor": args.anchor, "hash": h, "total": len(anns)}, ensure_ascii=False))


def cmd_affected(args):
    d = case_dir(args.name)
    conn = core.db(d)
    builds = sorted([p for p in (d / "builds").iterdir() if p.is_dir()])
    if not builds:
        raise SystemExit("还没有 build")
    ref = builds[-1] if not args.from_ else (d / "builds" / args.from_)
    man = json.loads((ref / "manifest.json").read_text(encoding="utf-8"))
    anns = core.parse_annotations(d / "annotations.md")
    res = extras.affected(conn, man.get("source_stats", {}), anns)
    res["from"] = ref.name
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_backfill(args):
    ns = argparse.Namespace(name=args.name, preset="nmg", source_dir=args.source_dir)
    cmd_add_obs(ns)
    ns2 = argparse.Namespace(name=args.name, by=args.by)
    cmd_build(ns2)


def cmd_audit(args):
    d = case_dir(args.name)
    man = json.loads((d / "builds" / args.build / "manifest.json").read_text(encoding="utf-8"))
    print(json.dumps(man["audit"], ensure_ascii=False, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="reportkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("name"); s.set_defaults(func=cmd_init)

    s = sub.add_parser("add-obs"); s.add_argument("name")
    s.add_argument("--preset", default="nmg"); s.add_argument("--source-dir", default=None)
    s.set_defaults(func=cmd_add_obs)

    s = sub.add_parser("build"); s.add_argument("name"); s.add_argument("--by", default=None)
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("seal"); s.add_argument("name"); s.add_argument("--build", required=True)
    s.add_argument("--by", default=None); s.set_defaults(func=cmd_seal)

    s = sub.add_parser("diff"); s.add_argument("name")
    s.add_argument("--from", dest="from_", required=True); s.add_argument("--to", required=True)
    s.set_defaults(func=cmd_diff)

    s = sub.add_parser("annotate"); s.add_argument("name")
    s.add_argument("--anchor", required=True); s.add_argument("--text", required=True)
    s.set_defaults(func=cmd_annotate)

    s = sub.add_parser("affected"); s.add_argument("name")
    s.add_argument("--from", dest="from_", default=None); s.set_defaults(func=cmd_affected)

    s = sub.add_parser("backfill"); s.add_argument("name")
    s.add_argument("--source-dir", default=None); s.add_argument("--by", default=None)
    s.set_defaults(func=cmd_backfill)

    s = sub.add_parser("audit"); s.add_argument("name"); s.add_argument("--build", required=True)
    s.set_defaults(func=cmd_audit)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
