# -*- coding: utf-8 -*-
"""案例库管理：预注册预测 → 后验回填 → 命中统计（case-v1 闭环）。

借鉴 yueyuan-bazi（MIT）的「预注册预测 + 后验验证」：断卦前先把预测写死，应期后再回填
实际结果与命中判定，避免「事后诸葛」式的自我解释。这是衡量「推理强没强」的唯一闭环标尺——
规则/代码判定对了就是 100% 对规则，比任何 LLM 都强。

与同目录其它件的关系：
  - trace.py    记「过程」（规则命中/引文出处），案例记「预注册+后验」，feedback.py 记「问题」。
  - mingli_eval.py 是对案例库 benchmark 表的批量评测；本件是**单案 CLI**，两者互补。

数据：cases/cases.jsonl（JSONL，一条一案例，可追加）。
schema（case-v1）：
  {id, 问事, 术法, 预测, 预测依据, created, status, 结果, 命中, 应期, 后验, resolved}

用法：
  python cases/manage.py new "跳槽成不成" 六爻 --predict 吉 --basis "用神旺相生世"
  python cases/manage.py list [--status 预注册]
  python cases/manage.py resolve <id> --result 应验 --hit 命中 --note "3个月后成功跳槽"
  python cases/manage.py stats [--method 六爻]
"""
import os
import sys
import json
import datetime

DEFAULT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(DEFAULT_DIR, "cases.jsonl")

_STATUS = ("预注册", "已后验", "无法后验")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _next_id(rows):
    """生成下一个案例 id：C-YYYYMMDD-NNN。"""
    day = datetime.date.today().strftime("%Y%m%d")
    n = sum(1 for r in rows if r.get("id", "").startswith(f"C-{day}"))
    return f"C-{day}-{n + 1:03d}"


def _load(path=None):
    p = path or DEFAULT_PATH
    if not os.path.isfile(p):
        return [], p
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out, p


def _save(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _arg(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def new(rows, path, args):
    """预注册：断卦前先写死预测。问事、术法、预测、预测依据。"""
    if len(args) < 2:
        print("用法: new \"问事\" <术法> [--predict 预测] [--basis 依据]")
        return rows
    shi, method = args[0], args[1]
    predict = _arg(args, "--predict")
    basis = _arg(args, "--basis")
    if predict is None:
        print("⚠ 未给 --predict，预测记为空（后验时命中=否）")
    rec = {
        "id": _next_id(rows),
        "问事": shi,
        "术法": method,
        "预测": predict or "",
        "预测依据": basis or "",
        "created": _now(),
        "status": "预注册",
        "结果": None,
        "命中": None,
        "应期": None,
        "后验": None,
        "resolved": None,
    }
    rows.append(rec)
    _save(rows, path)
    print(f"[预注册] {rec['id']}  问「{shi}」({method})  预测={predict or '未填'}")
    print(f"  应验后回填: python cases/manage.py resolve {rec['id']} --result <结果> --hit 命中/未中")
    return rows


def resolve(rows, path, args):
    """后验回填：应期后补实际结果与命中判定。"""
    if not args:
        print("用法: resolve <id> [--result 结果] [--hit 命中|未中|无法判定] [--yingqi 应期] [--note 说明]")
        return rows
    cid = args[0]
    result = _arg(args, "--result")
    hit = _arg(args, "--hit")
    yingqi = _arg(args, "--yingqi")
    note = _arg(args, "--note")
    for r in rows:
        if r["id"] == cid:
            r["结果"] = result or r["结果"]
            r["命中"] = hit or r["命中"]
            r["应期"] = yingqi or r["应期"]
            r["后验"] = note or r["后验"]
            r["resolved"] = _now()
            r["status"] = "已后验"
            _save(rows, path)
            print(f"[后验] {cid}  结果={r['结果']}  命中={r['命中']}  应期={r['应期'] or '—'}")
            return rows
    print(f"⚠ 找不到案例 {cid}（先 list 看 id）")
    return rows


def _fmt_stat(rows, method=None):
    rs = [r for r in rows if r["status"] == "已后验" and r["命中"] in ("命中", "未中")]
    if method:
        rs = [r for r in rs if r["术法"] == method]
    total = len(rs)
    hit = sum(1 for r in rs if r["命中"] == "命中")
    return total, hit


def stats(rows, args):
    method = _arg(args, "--method")
    total, hit = _fmt_stat(rows, method)
    title = f"[{method}]" if method else "[全部]"
    rate = f"{hit/total:.0%}" if total else "—"
    print(f"[案例统计]{title} 已后验 {total} 例，命中 {hit} 例，命中率 {rate}")
    by_method = {}
    for r in rows:
        if r["status"] == "已后验" and r["命中"] in ("命中", "未中"):
            m = r["术法"]
            by_method.setdefault(m, [0, 0])
            by_method[m][0] += 1
            by_method[m][1] += r["命中"] == "命中"
    if by_method and not method:
        print("  分术法：")
        for m, (t, h) in sorted(by_method.items()):
            print(f"    {m:<8} {h}/{t} = {h/t:.0%}" if t else f"    {m:<8} —")


def _list(rows, args):
    status = _arg(args, "--status")
    for r in rows:
        if status and r["status"] != status:
            continue
        hit = r["命中"] or "—"
        print(f"  {r['id']}  [{r['status']}]  {r['问事']}({r['术法']})  预测={r['预测'] or '—'}  命中={hit}")


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd, rest = a[0], a[1:]
    rows, path = _load()
    if cmd == "new":
        rows = new(rows, path, rest)
    elif cmd == "list":
        _list(rows, rest)
    elif cmd == "resolve":
        rows = resolve(rows, path, rest)
    elif cmd == "stats":
        stats(rows, rest)
    else:
        print(f"未知命令 {cmd!r}。可用：new / list / resolve / stats")
        print(__doc__)


if __name__ == "__main__":
    main()
