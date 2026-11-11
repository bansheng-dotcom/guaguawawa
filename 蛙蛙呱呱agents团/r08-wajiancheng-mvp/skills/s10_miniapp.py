# -*- coding: utf-8 -*-
"""S09 小程序工程脚手架（自有实现）。

把「一个多页小程序」的规格变成可运行的工程骨架（Taro 风格，React 语法）：
  plan      页数/路径/标题/tabBar 结构门禁
  scaffold  生成 package.json、project.config.json、app 配置与页面文件

只生成骨架与占位页面，不拉依赖、不联网、不发布。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from . import _common as c

NAME = "miniapp"
DESC = "小程序工程脚手架：plan/scaffold"

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}$")
PATH_RE = re.compile(r"^pages/[a-z0-9-]+/[a-z0-9-]+$")
MIN_PAGES, MAX_PAGES = 2, 20


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pl = act.add_parser("plan", help="校验小程序规格")
    pl.add_argument("--input", required=True)
    sc = act.add_parser("scaffold", help="生成工程骨架")
    sc.add_argument("--input", required=True)
    sc.add_argument("--out", required=True)
    sc.add_argument("--force", action="store_true", help="目标目录非空时仍写入")


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "plan":
        return _validate(data)
    return _scaffold(data, args.out, args.force)


# --------------------------------------------------------------------------- #
def _pages(data: Any) -> List[Dict[str, Any]]:
    pages = data.get("pages") if isinstance(data, dict) else None
    return [p for p in pages if isinstance(p, dict)] if isinstance(pages, list) else []


def _validate(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    name = str(data.get("name", "")).strip()
    checks.append(_ck(bool(NAME_RE.fullmatch(name)),
                      f"工程名合法（小写字母开头、3–31 位）: {name or '空'}", "miniapp.name"))
    pages = _pages(data)
    checks.append(_ck(MIN_PAGES <= len(pages) <= MAX_PAGES,
                      f"页数 {MIN_PAGES}–{MAX_PAGES}（实际 {len(pages)}）", "miniapp.pages"))
    paths = []
    for i, p in enumerate(pages):
        path = str(p.get("path", "")).strip()
        paths.append(path)
        checks.append(_ck(bool(PATH_RE.fullmatch(path)),
                          f"第 {i + 1} 页路径形如 pages/a/b（{path or '空'}）", "miniapp.path"))
        checks.append(_ck(bool(str(p.get("title", "")).strip()),
                          f"第 {i + 1} 页标题非空", "miniapp.title"))
    dup = sorted({x for x in paths if paths.count(x) > 1})
    checks.append(_ck(not dup, f"页面路径不重复（重复：{dup or '无'}）", "miniapp.unique"))

    tabbar = data.get("tabbar") or []
    if tabbar:
        checks.append(_ck(2 <= len(tabbar) <= 5, f"tabBar 2–5 项（实际 {len(tabbar)}）",
                          "miniapp.tabbar"))
        unknown = [t.get("page") for t in tabbar if t.get("page") not in paths]
        checks.append(_ck(not unknown, f"tabBar 页面均已声明（未知：{unknown or '无'}）",
                          "miniapp.tabbar.ref"))
    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    page_count=len(pages),
                    next="结构通过，可 scaffold" if ok else "按 checks 修正规格")


def _scaffold(data: Any, out_dir: str, force: bool) -> Dict[str, Any]:
    gate = _validate(data)
    if not gate.get("ok"):
        gate["next"] = "规格未过门禁，先修 plan"
        return gate
    abs_out = os.path.abspath(out_dir)
    existing = os.listdir(abs_out) if os.path.isdir(abs_out) else []
    if existing and not force:
        return c.result([_ck(False, f"目标目录非空（{len(existing)} 项），需 --force",
                             "miniapp.overwrite")], ok=False, verdict="FAIL")
    os.makedirs(abs_out, exist_ok=True)

    name = str(data["name"]).strip()
    pages = _pages(data)
    written: List[str] = []

    def write(rel: str, content: str) -> None:
        path = os.path.join(abs_out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        written.append(rel)

    page_entries = ",\n".join(
        f"    {{ path: '{p['path']}', title: '{p['title']}' }}" for p in pages)
    write("package.json", json.dumps({
        "name": name, "version": "0.1.0", "private": True,
        "scripts": {"dev": "taro build --type weapp --watch",
                    "build": "taro build --type weapp"},
        "dependencies": {"@tarojs/taro": "^3.6.0", "react": "^18.0.0"},
        "devDependencies": {"@tarojs/cli": "^3.6.0"},
    }, ensure_ascii=False, indent=2) + "\n")
    write("project.config.json", json.dumps({
        "miniprogramRoot": "dist/", "projectname": name, "appid": "touristappid",
        "setting": {"es6": True, "minified": True},
    }, ensure_ascii=False, indent=2) + "\n")
    write("src/app.config.ts",
          "export default {\n  pages: [\n" +
          "".join(f"    '{p['path']}',\n" for p in pages) +
          "  ],\n  window: { navigationBarTitleText: '" + str(data.get("title", name)) +
          "' },\n}\n")
    write("src/app.tsx",
          "import { PropsWithChildren } from 'react'\nimport './app.scss'\n\n"
          "function App({ children }: PropsWithChildren<any>) {\n  return children\n}\n\n"
          "export default App\n")
    write("src/app.scss", "page { background: #f8fafc; color: #0f172a; }\n")
    for p in pages:
        seg = p["path"].split("/")[1]
        write(f"src/{p['path']}/index.tsx",
              "import { View, Text } from '@tarojs/components'\n\n"
              f"export default function {seg.title().replace('-', '')}() {{\n"
              f"  return (\n    <View className='page'>\n"
              f"      <Text>{p['title']}</Text>\n    </View>\n  )\n}}\n")
        write(f"src/{p['path']}/index.scss", ".page { padding: 24px; }\n")

    checks = list(gate["checks"]) + [
        _ck(len(written) >= 5 + 2 * len(pages),
            f"生成文件 ≥{5 + 2 * len(pages)}（实际 {len(written)}）", "miniapp.files"),
        _ck(all(not rel.startswith("..") for rel in written), "无路径穿越", "miniapp.safe"),
    ]
    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    out=abs_out, file_count=len(written), files=written,
                    next="npm install && npm run dev 后在小程序开发者工具导入 dist/")
