# -*- coding: utf-8 -*-
"""把巨型案例章节 ch44/64/66 按案例边界拆成子文件。"""
import re, os

BASE = r"D:/cc/natural-flow-system/references/book/chapters"
BOUNDARY = re.compile(r"^以下为|^.{0,20}案例[:：]|^案例起点|^.{0,20}的完整拆解")
SPLIT_TARGETS = ["ch44", "ch64", "ch66"]

report = []
for stem in SPLIT_TARGETS:
    path = os.path.join(BASE, f"{stem}.md")
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    # 找标题行（第一行 # ...），其余按边界切
    title = lines[0] if lines[0].startswith("#") else f"# {stem}"
    body = lines[1:] if lines[0].startswith("#") else lines

    # 找边界索引
    bounds = [i for i, ln in enumerate(body) if BOUNDARY.match(ln.strip())]
    # 去重 + 只保留间隔足够大的边界（>20行），避免把字段名当边界
    clean_bounds = []
    last = -999
    for b in bounds:
        if b - last > 20:
            clean_bounds.append(b)
            last = b

    if not clean_bounds:
        report.append(f"{stem}: 未找到边界，跳过")
        continue

    # 拆分：概览 = 第一个边界之前；之后每个边界一个子文件
    parts = []
    overview = body[:clean_bounds[0]]
    parts.append(("", overview))  # 概览
    for i, b in enumerate(clean_bounds):
        end = clean_bounds[i + 1] if i + 1 < len(clean_bounds) else len(body)
        seg = body[b:end]
        # 子文件标题用边界行前 20 字
        tag = body[b].strip()[:20].rstrip("：:")
        parts.append((tag, seg))

    # 写文件：概览覆盖原文件，其余写 chXX-pN.md
    with open(path, "w", encoding="utf-8") as f:
        f.write(title + "\n\n")
        f.write("\n".join(parts[0][1]) + "\n")

    subfiles = []
    for i, (tag, seg) in enumerate(parts[1:], 1):
        fn = f"{stem}-p{i}.md"
        with open(os.path.join(BASE, fn), "w", encoding="utf-8") as f:
            f.write(f"{title}（{tag}）\n\n")
            f.write("\n".join(seg) + "\n")
        subfiles.append((tag, fn, len("\n".join(seg))))

    report.append(f"{stem}: 概览 {len(parts[0][1])}行 + {len(parts)-1} 个子文件 -> " +
                  ", ".join(f"{t}({s}字节)" for t, _, s in subfiles))

print("\n".join(report))
