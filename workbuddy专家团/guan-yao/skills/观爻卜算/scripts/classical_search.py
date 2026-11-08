# -*- coding: utf-8 -*-
"""经典检索：段落 ID 引用 + 全文检索 + 原样复核（纯离线、零外部依赖）

把断卦引经从「书名+行号」升级成「稳定段落 ID」，一条命令即可原样复核，杜绝编造经文。

用法:
  python scripts/classical_search.py --build-index
      扫描典籍 txt（顶层 *.txt，不含案例库/去重备份子目录），生成元数据索引
  python scripts/classical_search.py --passage-id 三命通会:1009
      按 ID 原样返回该段 + 前后各 1 行上下文 + 书名/文件路径
  python scripts/classical_search.py --passage-id 三命通会:1009 --context 2
      同上，前后各 2 行上下文
  python scripts/classical_search.py --search 伤官佩印 --book 子平真诠 --limit 5
      全文检索，返回带段落 ID 的命中（book 可省略=全库）
  python scripts/classical_search.py --validate
      校验索引与语料一致（文件数/抽样复核/索引可解析）
  python scripts/classical_search.py --books
      列出已索引书目（slug → 文件）

ID 格式:「书名:行号」，如 三命通会:1009。
  书名 = 文件名去掉「[分类] 」前缀与「.txt」后缀；重名时加分类前缀消歧（如「易藏.某书」）。
  行号 = 文件内 1-based 行号（与 Grep -n 一致），内容为 UTF-8 原样。

索引只存元数据（slug→文件路径+行数+文件指纹），正文在复核时直读源文件，不缓存全文。
"""
import os
import re
import sys
import json
import hashlib

# 【典籍主源已迁 IMA】典籍检索主源 = IMA 知识库「卜算适配知识库」(ima_kb_lXz71gfe)，
# 经 ima-mcp 连接器 search_knowledge 检索。本脚本仅作本地遗留兜底，需本机挂载典籍 txt 才可用。
TXT_DIR = r"D:\卜算\国学czhengli\txt"
INDEX_PATH = os.path.join(TXT_DIR, ".classical_index.json")
# 不索引的子目录（案例库是占验案例，不是典籍原文）
SKIP_DIRS = {"案例库", "_去重备份", "_去重"}
SKIP_PREFIXES = (".", "_")


def _reconf():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _locate_corpus():
    """定位典籍目录；路径不符时用 Glob 兜底。"""
    if os.path.isdir(TXT_DIR):
        return TXT_DIR
    # 兜底：找任意含「三命通会」的 txt 目录
    for base in (r"D:\卜算", r"D:/卜算"):
        for root, _dirs, files in os.walk(base):
            if any("三命通会" in f and f.endswith(".txt") for f in files):
                return root
    return None


def _slug_of(filename):
    """[易藏] 三命通会.txt -> 三命通会；[易藏] 三命通会.txt 重名时调用方加分类消歧。"""
    name = filename[:-4] if filename.endswith(".txt") else filename
    m = re.match(r"^\[([^\]]+)\]\s*(.+)$", name)
    return (m.group(1), m.group(2)) if m else ("", name)


def list_books(corpus=None):
    """扫描顶层 *.txt，返回 [{slug, category, file}]；重名 slug 加「分类.」前缀消歧。"""
    corpus = corpus or _locate_corpus()
    if not corpus:
        return []
    seen, out = {}, []
    for f in sorted(os.listdir(corpus)):
        if not f.endswith(".txt"):
            continue
        if f.startswith(SKIP_PREFIXES):
            continue
        full = os.path.join(corpus, f)
        if not os.path.isfile(full):
            continue
        cat, slug = _slug_of(f)
        if not slug:
            continue
        seen.setdefault(slug, []).append((cat, full))
    for slug, lst in seen.items():
        for i, (cat, full) in enumerate(lst):
            key = slug if len(lst) == 1 else f"{cat}.{slug}"
            out.append({"slug": key, "category": cat, "file": full})
    out.sort(key=lambda b: b["slug"])
    return out


def build_index(corpus=None):
    """生成元数据索引：{slug: {file, lines, sha1, category}}。"""
    corpus = corpus or _locate_corpus()
    if not corpus:
        raise SystemExit(f"未找到典籍目录（试过 {TXT_DIR}），请先用 Glob 定位后传入 corpus 参数")
    books = list_books(corpus)
    idx = {"corpus": corpus, "books": {}}
    for b in books:
        try:
            with open(b["file"], encoding="utf-8") as fp:
                raw = fp.read()
        except Exception as e:
            print(f"  [跳过] {b['slug']}: {e}", file=sys.stderr)
            continue
        idx["books"][b["slug"]] = {
            "file": b["file"],
            "category": b["category"],
            "lines": len(raw.splitlines()),
            "sha1": hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12],
        }
    with open(INDEX_PATH, "w", encoding="utf-8") as fp:
        json.dump(idx, fp, ensure_ascii=False, indent=1)
    return idx


def load_index(rebuild=False):
    if rebuild or not os.path.exists(INDEX_PATH):
        return build_index()
    try:
        with open(INDEX_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return build_index()


def _parse_id(pid):
    """'三命通会:1009' -> (slug, line)。行号必须是 1-based 整数。"""
    m = re.match(r"^(.+?):(\d+)$", pid.strip())
    if not m:
        return None, None
    return m.group(1).strip(), int(m.group(2))


def passage(pid, context=1, corpus=None, rebuild=False):
    """按 ID 返回 {slug, line, text, context_before, context_after, file}；找不到返回 None。"""
    idx = load_index(rebuild)
    slug, line = _parse_id(pid)
    if slug is None or line is None or slug not in idx["books"]:
        return None
    meta = idx["books"][slug]
    try:
        with open(meta["file"], encoding="utf-8") as fp:
            lines = fp.read().splitlines()
    except Exception:
        return None
    if not (1 <= line <= len(lines)):
        return None
    before = lines[max(0, line - 1 - context):line - 1]
    after = lines[line:line + context]
    return {
        "slug": slug, "line": line, "text": lines[line - 1],
        "context_before": before, "context_after": after,
        "file": meta["file"],
    }


def search(query, book=None, limit=10, corpus=None):
    """全文检索，返回 [{id, text, book, line}]（命中子串，含行号即段落 ID）。"""
    books = list_books(corpus)
    if book:
        books = [b for b in books if b["slug"] == book or book in b["slug"]]
    out = []
    pat = query
    for b in books:
        try:
            with open(b["file"], encoding="utf-8") as fp:
                lines = fp.read().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            if pat in ln:
                out.append({"id": f"{b['slug']}:{i}", "book": b["slug"],
                            "line": i, "text": ln})
                if len(out) >= limit:
                    return out
    return out


def validate(corpus=None):
    """校验索引完整性：可解析、书目数匹配、抽样 ID 能原样命中。"""
    idx = load_index()
    books = list_books(corpus)
    issues = []
    if set(idx["books"]) != {b["slug"] for b in books}:
        issues.append("索引书目与语料不一致，需 --build-index 重建")
    sample = "三命通会:1009"
    p = passage(sample)
    if not p:
        issues.append(f"抽样复核失败: {sample}")
    else:
        ok = "六戊日诗" in p["text"]
        issues.append(None if ok else f"抽样命中但内容不符: {sample}")
    return {"ok": all(i is None for i in issues),
            "books": len(idx["books"]),
            "issues": [i for i in issues if i]}


def _fmt_passage(p, ctx):
    """格式化一段 + 上下文。"""
    lines = []
    for i, t in enumerate(p["context_before"], p["line"] - len(p["context_before"])):
        lines.append(f"  {p['slug']}:{i}  {t}")
    lines.append(f"> {p['slug']}:{p['line']}  {p['text']}")
    for i, t in enumerate(p["context_after"], p["line"] + 1):
        lines.append(f"  {p['slug']}:{i}  {t}")
    lines.append(f"\n[出处] {os.path.basename(p['file'])}  ({p['file']})")
    return "\n".join(lines)


def main():
    _reconf()
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "--build-index":
        idx = build_index()
        print(f"[索引] 已建 {len(idx['books'])} 部书 → {INDEX_PATH}")
    elif cmd == "--passage-id" and len(a) >= 2:
        ctx = 1
        if "--context" in a:
            ctx = int(a[a.index("--context") + 1])
        p = passage(a[1], context=ctx)
        print(_fmt_passage(p, ctx) if p else f"[未命中] {a[1]}")
    elif cmd == "--search" and len(a) >= 2:
        q = a[1]
        book = None
        limit = 10
        if "--book" in a:
            book = a[a.index("--book") + 1]
        if "--limit" in a:
            limit = int(a[a.index("--limit") + 1])
        hits = search(q, book=book, limit=limit)
        print(f"[检索] 「{q}」 book={book or '全库'} 命中 {len(hits)} 段（最多 {limit}）\n")
        for h in hits:
            print(f"> {h['id']}  {h['text'][:120]}")
    elif cmd == "--validate":
        r = validate()
        print(f"[校验] {'通过' if r['ok'] else '未通过'}（{r['books']} 部书）")
        for i in r["issues"]:
            print(f"  ✗ {i}")
    elif cmd == "--books":
        for b in list_books():
            print(f"{b['slug']}\t{b['category']}\t{os.path.basename(b['file'])}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
