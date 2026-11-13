# -*- coding: utf-8 -*-
"""案例库语义检索（TF-IDF + 字符 n-gram，纯离线、零外部模型）

补「Grep 关键词捞不到同类案例」的短板：按占事语义相关性给案例排序。

用法:
  python libs/case_search.py "测对象在干嘛" [大六壬] [10]   # 查询 / 术法过滤 / top-k
  import case_search; case_search.search("求财", k=10, method="六爻")

说明:
  - 用「字符 unigram + bigram」做中文词根（六合/天后/求财/婚姻…），无需分词器。
  - TF-IDF + 余弦相似度排序；只保留 df>=2 的词，去噪声。
  - 若要真·embedding 语义检索，替换 _tokenize / build 为向量模型即可，接口不变。
"""
import os
import re
import math
import sys
from collections import Counter

# 【案例主源已迁 IMA】相似案例主源 = IMA 知识库「卜算适配知识库」(ima_kb_lXz71gfe) 内 r_XXX_*.md，
# 经 ima-mcp 连接器 search_knowledge 语义检索。本脚本仅作本地遗留兜底，需本机挂载案例库才可用。
CASE_DIR = r"D:\卜算\国学czhengli\txt\案例库"


def _tokenize(text):
    """字符 unigram + bigram，作为中文词根近似。"""
    text = re.sub(r"[\s#*`|:：（）()\-—_]+", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    toks = list(text)
    toks += [text[i:i + 2] for i in range(len(text) - 1)]
    return toks


def _extract(path, method):
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return None
    title = ""
    m = re.search(r"#\s*案例[:：]\s*(.+)", txt)
    if m:
        title = m.group(1).strip()
    else:
        title = re.sub(r"^[\w]+_\d+_|^\d+_", "", os.path.splitext(os.path.basename(path))[0])
    question = ""
    m = re.search(r"问事[:：]\s*(.+)", txt)
    if m:
        question = m.group(1).strip()
    body = txt[:800]  # 正文前段够定位占事类别
    # 标题/问事加权（标题3x、问事2x），让占事类别主导排序，正文只作补充
    t = title
    q = question or title
    text = f"{t} {t} {t} {q} {q} {body}"
    return {"path": path, "method": method, "title": title,
            "question": question or title, "text": text}


def load(case_dir=CASE_DIR):
    cases = []
    for method in sorted(os.listdir(case_dir)):
        sub = os.path.join(case_dir, method)
        if not os.path.isdir(sub):
            continue
        for f in os.listdir(sub):
            if not f.endswith(".md") or f.startswith(("README", "_")):
                continue
            c = _extract(os.path.join(sub, f), method)
            if c:
                cases.append(c)
    return cases


def build(case_dir=CASE_DIR):
    """构建 TF-IDF 索引，返回 (cases, doc_vectors, idf)。"""
    cases = load(case_dir)
    N = len(cases)
    docs = [Counter(_tokenize(c["text"])) for c in cases]
    df = Counter()
    for d in docs:
        for t in d:
            df[t] += 1
    vocab = {t for t, c in df.items() if c >= 2}
    idf = {t: math.log((N + 1) / (df[t] + 1)) + 1.0 for t in vocab}
    vecs = []
    for d in docs:
        v = {}
        norm = 0.0
        for t, tf in d.items():
            if t in idf:
                w = (1 + math.log(tf)) * idf[t]
                v[t] = w
                norm += w * w
        vecs.append((v, math.sqrt(norm) or 1.0))
    return cases, vecs, idf


def _match_method(m, method):
    if not method:
        return True
    return m == method or method in m or m in method


def search(query, case_dir=CASE_DIR, k=10, method=None):
    """按相关性返回 top-k 相似案例（[{score, method, title, question, path}]）。"""
    cases, vecs, idf = build(case_dir)
    qt = Counter(_tokenize(query))
    qv = {}
    qn = 0.0
    for t, tf in qt.items():
        if t in idf:
            w = (1 + math.log(tf)) * idf[t]
            qv[t] = w
            qn += w * w
    qn = math.sqrt(qn) or 1.0
    scored = []
    for i, (v, dn) in enumerate(vecs):
        if not _match_method(cases[i]["method"], method):
            continue
        dot = sum(w * v[t] for t, w in qv.items() if t in v)
        if dot > 0:
            scored.append((dot / (dn * qn), i))
    scored.sort(reverse=True)
    out = []
    for sim, i in scored[:k]:
        c = cases[i]
        out.append({"score": round(sim, 3), "method": c["method"],
                    "title": c["title"], "question": c["question"][:40],
                    "path": c["path"]})
    return out


def search_ziwei(query, k=5):
    """检索紫微断语知识包（星曜/宫位/四化/格局），供紫微断卦补断语依据。"""
    from judge import ziwei_knowledge
    return ziwei_knowledge.search(query, k=k)


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = [x for x in sys.argv[1:] if not x.startswith("-")]
    if not a:
        print(__doc__)
        return
    q = a[0]
    method = a[1] if len(a) > 1 else None
    k = int(a[2]) if len(a) > 2 else 10
    print(f"[检索] {q}  术法={method or '全部'}  top-{k}\n")
    # 紫微：先查断语知识包（星曜/宫位/四化/格局），再查案例库
    if method and method in ("紫微", "ziwei", "紫微斗数"):
        print("[断语知识包]（星曜/宫位/四化/格局，出处《紫微斗数全书》）")
        for r in search_ziwei(q, k=k):
            jx = f"（{r['吉凶']}）" if r["吉凶"] else ""
            print(f"[{r['score']:.2f}] ({r['类型']}) {r['名称']}{jx}")
            print(f"    {r['断语']}")
            if r.get("原文"):
                print(f"    〔{r['原文']}〕")
        print()
    for r in search(q, k=k, method=method):
        print(f"[{r['score']:.3f}] ({r['method']}) {r['title']}")
        print(f"    问: {r['question']}")
        print(f"    {r['path']}\n")


if __name__ == "__main__":
    main()