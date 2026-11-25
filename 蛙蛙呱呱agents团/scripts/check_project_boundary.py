# -*- coding: utf-8 -*-
"""项目边界门禁：专家团里不许出现项目资产。

判定分三层：

    FAIL  项目过程目录/文件（projects,briefs,cards,claims,report,out,plan,coverage,data…）
          任意层级命中；`workspace/`、`*_test_*` 运行残留也算
    FAIL  已提交进 git 的过程文件（.gitignore 对已跟踪文件无效，必须单独查）
    INFO  在 `boundary_allowlist.yaml` 里登记过的"团队自身证据"（演进留证/通用资产）

夹具/文档区（tests/fixtures/samples/baselines/examples/docs/evals/agent-packs）不受目录规则限制，
但仍不允许出现 project.yaml / claims_*.json / report.html 之外的项目元数据。

用法：
    python scripts/check_project_boundary.py [--json]
退出码：0=通过，1=有越界。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

#: 夹具与文档目录：允许放样例 claims/report（测试需要）
FIXTURE_ROOTS = {"baselines", "examples", "evals", "tests", "fixtures",
                 "samples", "docs", "agent-packs"}
#: 项目过程目录名（任意层级出现都算，除非在该层 allowlist）
BAD_DIR_NAMES = {"projects", "briefs", "cards", "claims", "report",
                 "out", "out_v3", "plan", "coverage", "data", "workspace",
                 "artifacts"}
BAD_FILE_PATTERNS = ("project.yaml", "claims_*.json", "report.html")


def _rack(root: Path) -> set:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="ignore", timeout=30).stdout
        return {x.strip().replace("\\", "/") for x in out.splitlines() if x.strip()}
    except Exception:  # noqa: BLE001
        return set()


def _allowlist() -> list:
    p = TEAM / "boundary_allowlist.yaml"
    if not p.exists():
        return []
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return [str(x.get("path") or "").replace("\\", "/")
                for x in (data.get("allow") or []) if x.get("path")]
    except Exception:  # noqa: BLE001
        return []


def _allowed(rel: str, allow: list) -> bool:
    r = rel.rstrip("/")
    for a in allow:
        a2 = a.rstrip("/")
        if r == a2 or r.startswith(a2 + "/"):
            return True
    return False


def scan() -> list[str]:
    bad: list[str] = []
    allow = _allowlist()
    tracked = _rack(TEAM)

    for p in TEAM.rglob("*"):
        if any(part in {"__pycache__", ".git", ".pytest_cache"} for part in p.parts):
            continue
        rel = p.relative_to(TEAM).as_posix()
        first = rel.split("/")[0]
        if first in FIXTURE_ROOTS:
            continue
        if _allowed(rel, allow):
            continue

        if p.is_dir():
            if p.name in BAD_DIR_NAMES:
                mark = "（已提交）" if any(t.startswith(rel + "/") for t in tracked) else ""
                bad.append(f"团内出现过程目录：{rel}/{mark}")
            continue

        if any(p.match(pat) for pat in BAD_FILE_PATTERNS):
            mark = "（已提交）" if rel in tracked else ""
            bad.append(f"团内出现项目文件：{rel}{mark}")

    return bad


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    problems = scan()
    if "--json" in argv:
        print(json.dumps({"ok": not problems, "problems": problems},
                         ensure_ascii=False, indent=2))
    else:
        if problems:
            print("项目边界门禁 FAIL：")
            for p in problems:
                print(f"  - {p}")
        else:
            print("项目边界门禁 PASS：团内无项目资产")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
