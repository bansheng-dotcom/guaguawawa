# -*- coding: utf-8 -*-
"""从 meihuayishu 提取 64 卦逐卦精解 + 占例十四则，落盘到案例库，并升级六十四卦速查表。

数据来源（只用 ast 安全解析纯字面量，不执行外部代码）：
  - 白话精解 / 梅花断语 / 现代案例：qzp001/meihuayishu 的 content/gua_*.py（白话为其原创整理）
  - 占例十四则：qzp001/meihuayishu 的 content/classic_cases.py
  - 文言卦辞/彖传/大象传：现有 references/六十四卦速查.md（源自《周易》txt 提取，保留）

生成：
  1. 案例库/梅花/六十四卦精解/NN_卦名.md （64 个：白话精解 + 梅花断语 + 现代案例）
  2. 案例库/梅花/占例十四则精解.md （14 则占例白话全文）
  3. references/六十四卦速查.md （白话升级 + 追加梅花断语）
"""
import ast
import io
import os
import re

SRC = r"D:/卜算/参考项目/meihuayishu/meihua-yishu/content"
CASE_DIR = r"D:/卜算/国学czhengli/txt/案例库/梅花"
JINGJIE_DIR = os.path.join(CASE_DIR, "六十四卦精解")
SUCHA = r"D:/卜算/.claude/skills/卜算/references/六十四卦速查.md"

# 原速查表生成脚本只匹配了「君子以」结尾的大象传，漏掉了「先王以/后以/上以/大人以」
# 结尾的 11 卦。此处从《周易》txt 补齐（剥卦 txt 作「出附于地」，系 OCR 讹，依通行本订为「山附于地」）。
XIANG_FIX = {
    8: "地上有水，比。先王以建万国，亲诸侯。",
    11: "天地交，泰。后以财成天地之道，辅相天地之宜，以左右民。",
    16: "雷出地奋，豫。先王以作乐崇德，殷荐之上帝，以配祖考。",
    20: "风行地上，观。先王以省方观民设教。",
    21: "雷电，噬嗑。先王以明罚敕法。",
    23: "山附于地，剥。上以厚下安宅。",
    24: "雷在地中，复。先王以至日闭关，商旅不行，后不省方。",
    25: "天下雷行，物与无妄。先王以茂对时育万物。",
    30: "明两作，离。大人以继明照于四方。",
    44: "天下有风，姤。后以施命诰四方。",
    59: "风行水上，涣。先王以享于帝，立庙。",
}


# ---------------------------------------------------------------------------
# 安全求值：只接受字面量（含 dict()/list()/tuple() 调用形式），不执行任意代码
# ---------------------------------------------------------------------------
def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(e) for e in node.elts)
    if isinstance(node, ast.List):
        return [_safe_eval(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_safe_eval(k): _safe_eval(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        d = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise ValueError("dict(**kwargs) 不支持")
            d[kw.arg] = _safe_eval(kw.value)
        return d
    raise ValueError(f"不支持的节点类型: {type(node).__name__}")


def _load_assignments(path, names):
    """ast 解析源文件，提取顶层 `NAME = <字面量>` 赋值（不执行）。"""
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    result = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    result[t.id] = _safe_eval(node.value)
    return result


# ---------------------------------------------------------------------------
# 1. 读 gua_*.py -> DATA
# ---------------------------------------------------------------------------
def load_gua():
    data = {}
    files = [f"gua_{a:02d}_{b:02d}.py" for a, b in
             [(1, 8), (9, 16), (17, 24), (25, 32), (33, 40), (41, 48), (49, 56), (57, 64)]]
    for f in files:
        r = _load_assignments(os.path.join(SRC, f), {"DATA"})
        data.update(r.get("DATA", {}))
    return data


# ---------------------------------------------------------------------------
# 2. 读 classic_cases.py -> CASES + METHODS
# ---------------------------------------------------------------------------
def load_cases():
    r = _load_assignments(os.path.join(SRC, "classic_cases.py"), {"CASES", "METHODS"})
    return r.get("CASES", []), r.get("METHODS", [])


# ---------------------------------------------------------------------------
# 3. parse 现有速查表 -> 每卦文言 + 卦名 + 上下卦五行 + 生克
# ---------------------------------------------------------------------------
def parse_sucha():
    txt = io.open(SUCHA, encoding="utf-8").read()
    guas = {}
    cur = None
    for line in txt.splitlines():
        m = re.match(r"^### (\d+)\. (.+?)（(.+?) / (.+?)）· (.+)$", line)
        if m:
            cur = {"no": int(m.group(1)), "name": m.group(2),
                   "shang": m.group(3), "xia": m.group(4), "shengke": m.group(5),
                   "guaci": "", "tuan": "", "xiang": ""}
            guas[cur["no"]] = cur
            continue
        if cur is None:
            continue
        m2 = re.match(r"^- (卦辞|彖|象)：", line)
        if m2:
            key = {"卦辞": "guaci", "彖": "tuan", "象": "xiang"}[m2.group(1)]
            cur[key] = line[len(m2.group(0)):]
    return guas


# ---------------------------------------------------------------------------
# 生成 1：64 卦精解文件
# ---------------------------------------------------------------------------
def gen_jingjie(gua_data, sucha):
    os.makedirs(JINGJIE_DIR, exist_ok=True)
    written = 0
    for no in range(1, 65):
        g = gua_data.get(no)
        s = sucha.get(no)
        if not g or not s:
            print(f"[跳过] 卦 {no} 缺数据（gua={bool(g)} sucha={bool(s)}）")
            continue
        name = s["name"]
        parts = [f"# {name}（{no}/64）\n",
                 f"> 白话精解 + 梅花断语取自《梅花易数精解》（白话为其原创整理）。\n",
                 f"> 文言卦辞/彖传/大象传见 `references/六十四卦速查.md`（源自《周易》txt）。\n",
                 f"> 用途：断卦「精解层」，叠加而非替代——正式断语仍须 Grep 典籍原文 + 依动爻定体用。\n"]

        parts.append("## 白话精解\n")
        for p in g.get("baihua", []):
            parts.append(p + "\n")
        parts.append("\n")

        proverb = g.get("proverb")
        if proverb and len(proverb) >= 2:
            parts.append("## 梅花断语\n")
            parts.append(f"**断语**：{proverb[1]}\n")
            if len(proverb) >= 3 and proverb[2]:
                parts.append(f"\n**详解**：{proverb[2]}\n")
            parts.append("\n")

        cases = g.get("cases", [])
        if cases:
            parts.append("## 现代案例\n")
            for i, c in enumerate(cases, 1):
                dong = c.get("dong", "")
                scene = c.get("scene", "")
                parts.append(f"### 案例{i}：{c.get('title', '')}（{scene} · 动爻{dong}）\n")
                for p in c.get("paras", []):
                    parts.append(p + "\n")
                if c.get("note"):
                    parts.append(f"\n**点评**：{c['note']}\n")
                parts.append("\n")

        fn = os.path.join(JINGJIE_DIR, f"{no:02d}_{name}.md")
        io.open(fn, "w", encoding="utf-8").write("".join(parts))
        written += 1
    return written


# ---------------------------------------------------------------------------
# 生成 2：占例十四则精解
# ---------------------------------------------------------------------------
def gen_zhanli(cases, methods):
    parts = ["# 占例十四则精解\n",
             "> 出处：《梅花易数》卷一，白话为《梅花易数精解》原创整理。\n",
             "> 与案例库已有「康节占例（古籍原文）」互补：那份是古籍原文，这份是白话 + 取数 + 点评。\n"]

    idx = 1
    for c in cases:
        kind = c.get("kind", "")
        parts.append(f"## {idx}、{c.get('name', '')}（{kind}）\n")
        if c.get("tag"):
            parts.append(f"**小注**：{c['tag']}\n")
        parts.append(f"**出处**：{c.get('src', '')}\n")
        parts.append(f"**事由**：{c.get('cause', '')}\n")
        calc = c.get("calc", [])
        if calc:
            parts.append("**取数**：\n")
            for label, txt in calc:
                parts.append(f"- {label}：{txt}\n")
        parts.append(f"**卦象**：本卦{c.get('ben', '')}，动爻{c.get('dong', '')}，互卦{c.get('hu', '')}，变卦{c.get('bian', '')}\n")
        parts.append(f"**体用**：体={c.get('ti', '')}，用={c.get('yong', '')}，{c.get('rel', '')}\n")
        orig = c.get("orig", [])
        if orig:
            parts.append("\n**原文**：\n")
            for p in orig:
                parts.append("> " + p + "\n")
        baihua = c.get("baihua", [])
        if baihua:
            parts.append("\n**白话**：\n")
            for p in baihua:
                parts.append(p + "\n")
        parts.append(f"\n**断语**：{c.get('verdict', '')}\n")
        parts.append(f"**应验**：{c.get('proof', '')}\n")
        if c.get("gain"):
            parts.append(f"**一得**：{c['gain']}\n")
        parts.append("\n---\n\n")
        idx += 1

    for m in methods:
        parts.append(f"## {idx}、{m.get('name', '')}（占法）\n")
        if m.get("tag"):
            parts.append(f"**小注**：{m['tag']}\n")
        parts.append(f"**出处**：{m.get('src', '')}\n")
        parts.append(f"**总纲**：{m.get('lead', '')}\n")
        for title, lead, items in m.get("blocks", []):
            parts.append(f"\n**{title}**：{lead}\n")
            for k, v in items:
                parts.append(f"- {k}：{v}\n")
        if m.get("gain"):
            parts.append(f"\n**一得**：{m['gain']}\n")
        parts.append("\n---\n\n")
        idx += 1

    fn = os.path.join(CASE_DIR, "占例十四则精解.md")
    io.open(fn, "w", encoding="utf-8").write("".join(parts))
    return fn


# ---------------------------------------------------------------------------
# 生成 3：升级版六十四卦速查表
# ---------------------------------------------------------------------------
def gen_sucha(gua_data, sucha):
    parts = ["# 六十四卦速查（卦辞 + 彖传 + 大象传 + 白话精解 + 梅花断语 + 生克）\n",
             "> 卦辞/彖传/大象传：`[易藏] 周易.txt` 原文提取（可 Grep 佐证）；上下卦五行/生克：`gua.py` 确定性计算。\n",
             "> 白话精解 + 梅花断语：取自《梅花易数精解》（白话为其原创整理），精解层叠加非替代。\n",
             "> 用途：断卦「快速层」——正式断语仍须 Grep《周易》原文 + 依动爻定体用（本表「上下卦生克」不含动爻，不能直接当体用断）。\n"]

    parts.append("## 上经（1–30）\n")
    for no in range(1, 31):
        parts.append(_render_one(gua_data, sucha, no))
    parts.append("## 下经（31–64）\n")
    for no in range(31, 65):
        parts.append(_render_one(gua_data, sucha, no))

    parts.append("> 生成：`scripts/extract_meihua_jingjie.py`。白话精解取自 qzp001/meihuayishu（白话为其原创整理）。\n")
    io.open(SUCHA, "w", encoding="utf-8").write("".join(parts))
    return SUCHA


def _render_one(gua_data, sucha, no):
    s = sucha.get(no)
    g = gua_data.get(no)
    if not s:
        return ""
    out = [f"### {no}. {s['name']}（{s['shang']} / {s['xia']}）· {s['shengke']}\n"]
    if s["guaci"]:
        out.append(f"- 卦辞：{s['guaci']}\n")
    if s["tuan"]:
        out.append(f"- 彖：{s['tuan']}\n")
    xiang = s["xiang"] or XIANG_FIX.get(no, "")
    if xiang:
        out.append(f"- 象：{xiang}\n")
    if g:
        for p in g.get("baihua", []):
            out.append(f"- 白话：{p}\n")
        proverb = g.get("proverb")
        if proverb and len(proverb) >= 2:
            out.append(f"- 梅花断语：{proverb[1]}\n")
    out.append("\n")
    return "".join(out)


def main():
    print("加载 gua_*.py（ast 安全解析）...")
    gua_data = load_gua()
    print(f"  64 卦数据：{len(gua_data)} 卦")

    print("加载 classic_cases.py（ast 安全解析）...")
    cases, methods = load_cases()
    print(f"  占例：{len(cases)} 则，占法：{len(methods)} 则")

    print("parse 现有速查表 ...")
    sucha = parse_sucha()
    print(f"  速查表：{len(sucha)} 卦")

    print("生成 64 卦精解 ...")
    n = gen_jingjie(gua_data, sucha)
    print(f"  已写 {n} 个精解文件 -> {JINGJIE_DIR}")

    print("生成占例十四则精解 ...")
    f = gen_zhanli(cases, methods)
    print(f"  已写 -> {f}")

    print("升级速查表 ...")
    f2 = gen_sucha(gua_data, sucha)
    print(f"  已写 -> {f2}")

    print("完成。")


if __name__ == "__main__":
    main()
