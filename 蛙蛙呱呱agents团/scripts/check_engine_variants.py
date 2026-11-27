# -*- coding: utf-8 -*-
"""scripts/check_engine_variants.py —— 引擎台账门禁（T0 的“止血”版本）。

背景（2026-11-27 实测）：
    9 类通用引擎在 20 个角色间共有 143 个副本；逐个比对后发现它们并非字节级复制，
    而是吸收了各角色领域语义的变体。直接合并成一份实现会改变角色行为，不能机械删除。

因此 T0 拆成两步：
    1. 能合的先合：telemetry_watchdog 的 r11/r12 两个近似副本已收敛到 shared/engines/；
    2. 其余登记为 domain_variant，冻结哈希；新增/修改必须显式更新台账。

判据：
    - 每个 r*/engines/<name>.py 与 r*/<name>.py 必须在台账里，哈希一致；
    - 声明 shared_adapter 的文件必须真的 import shared.engines；
    - 与同名副本相似度 ≥0.98 的“近似副本”必须收敛，不允许继续留两份。

用法：
    python scripts/check_engine_variants.py            # 人读
    python scripts/check_engine_variants.py --check    # CI：未登记/漂移/近似副本即失败
    python scripts/check_engine_variants.py --write    # 更新台账与 docs/ENGINE-LEDGER.md
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs" / "engine_variants.json"
DOC = ROOT / "docs" / "ENGINE-LEDGER.md"
ENGINES = ("session_memory", "telemetry_watchdog", "scenario_matrix",
           "diff_patch_engine", "reflexive_healer", "asset_bundle",
           "spec_ledger", "verify_loop", "auto_evolve_runner")


def _files() -> List[Path]:
    out = []
    for role in sorted(ROOT.iterdir()):
        if not (role.is_dir() and role.name.startswith("r") and "-" in role.name):
            continue
        for name in ENGINES:
            for p in (role / "engines" / f"{name}.py", role / f"{name}.py"):
                if p.is_file():
                    out.append(p)
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _near(texts: Dict[str, str]) -> Dict[str, float]:
    """每个文件与同名其它副本的最高相似度。

    quick_ratio 是上界，先筛候选；≥0.95 的候选再用真实 ratio 复核，
    避免把“结构相似但内容不同”的领域变体误判为近似副本。
    """
    out = {}
    for path, text in texts.items():
        best = 0.0
        for other, ot in texts.items():
            if other == path:
                continue
            sm = difflib.SequenceMatcher(None, text, ot)
            quick = sm.quick_ratio()
            if quick < 0.95:
                best = max(best, quick)
                continue
            best = max(best, sm.ratio())
        out[path] = round(best, 3)
    return out


def census() -> List[dict]:
    by_engine: Dict[str, Dict[str, str]] = {n: {} for n in ENGINES}
    for p in _files():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        name = p.stem
        by_engine.setdefault(name, {})[rel] = _text(p)
    rows = []
    for name, texts in by_engine.items():
        near = _near(texts)
        for rel, text in texts.items():
            adapter = "shared.engines" in text
            rows.append({
                "engine": name,
                "role": rel.split("/")[0],
                "path": rel,
                "sha256": _sha(ROOT / rel),
                "lines": len(text.splitlines()),
                "status": "shared_adapter" if adapter else "domain_variant",
                "nearest_similarity": near.get(rel, 0.0),
            })
    rows.sort(key=lambda r: (r["engine"], r["role"]))
    return rows


def render(rows: List[dict]) -> str:
    total = len(rows)
    shared = [r for r in rows if r["status"] == "shared_adapter"]
    variants = [r for r in rows if r["status"] == "domain_variant"]
    lines = [
        "# 引擎台账（ENGINE-LEDGER）",
        "",
        "> 由 `python scripts/check_engine_variants.py --write` 生成，禁止手改。",
        "> T0 结论：143 个同名引擎并非字节级复制，只有 telemetry_watchdog 的 r11/r12 可安全收敛；",
        "> 其余登记为 domain_variant 并冻结哈希，禁止再新增未登记副本。",
        "",
        "## 汇总",
        "",
        f"- 总数：{total}",
        f"- 已收敛到 shared：{len(shared)}",
        f"- 领域变体：{len(variants)}",
        f"- 近似副本（≥0.98）：{sum(1 for r in variants if r['nearest_similarity'] >= 0.98)}",
        "",
        "## 按引擎",
        "",
        "| 引擎 | 副本数 | shared | 变体 | 最高相似度 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ENGINES:
        group = [r for r in rows if r["engine"] == name]
        if not group:
            continue
        lines.append(f"| `{name}` | {len(group)} | "
                     f"{sum(1 for r in group if r['status'] == 'shared_adapter')} | "
                     f"{sum(1 for r in group if r['status'] == 'domain_variant')} | "
                     f"{max(r['nearest_similarity'] for r in group):.3f} |")
    lines += ["", "## 明细", "",
              "| 引擎 | 角色 | 文件 | 行数 | 状态 | 同名最高相似度 |", "|---|---|---|---:|---|---:|"]
    for r in rows:
        lines.append(f"| `{r['engine']}` | {r['role']} | `{r['path']}` | {r['lines']} | "
                     f"{r['status']} | {r['nearest_similarity']:.3f} |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_engine_variants")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rows = census()
    if a.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"generated_by": "scripts/check_engine_variants.py",
                                   "count": len(rows), "engines": rows},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        DOC.write_text(render(rows), encoding="utf-8")
        print(f"[engine-ledger] 已写入 {OUT} 与 {DOC}（{len(rows)} 条）")
        return 0
    if not OUT.is_file():
        print("[engine-ledger] FAIL 台账不存在：先运行 --write")
        return 1
    ledger = {r["path"]: r for r in json.loads(OUT.read_text(encoding="utf-8")).get("engines", [])}
    current = {r["path"]: r for r in rows}
    problems = []
    for path in sorted(set(current) - set(ledger)):
        problems.append(f"未登记副本：{path}")
    for path in sorted(set(ledger) - set(current)):
        problems.append(f"台账有、磁盘无：{path}")
    for path in sorted(set(current) & set(ledger)):
        if current[path]["sha256"] != ledger[path]["sha256"]:
            problems.append(f"哈希漂移：{path}（改完请运行 --write）")
        if current[path]["status"] == "shared_adapter" and "shared.engines" not in _text(ROOT / path):
            problems.append(f"声明 shared 但未 import：{path}")
        if (current[path]["status"] == "domain_variant"
                and current[path]["nearest_similarity"] >= 0.98):
            problems.append(f"近似副本应合并：{path}（相似度 {current[path]['nearest_similarity']}）")
    shared = sum(1 for r in rows if r["status"] == "shared_adapter")
    print(f"[engine-ledger] {len(rows)} 个引擎文件：shared {shared} / "
          f"variant {len(rows) - shared}；问题 {len(problems)}")
    for p in problems[:12]:
        print(f"  - {p}")
    if a.check and problems:
        return 1
    if not a.check:
        for r in rows:
            if r["status"] == "domain_variant" and r["nearest_similarity"] >= 0.9:
                print(f"  [near] {r['path']} → {r['nearest_similarity']}")
    return 0 if not problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
