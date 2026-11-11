#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蛙蛙呱呱 · 20 角色统一入口（零第三方依赖）。

这个文件解决三个问题：
1. 不用记 20 个目录：`roles` / `info` 一眼看清谁负责什么。
2. 不用记每个角色的参数：`call <角色> <子命令> ...` 原样转发，
   角色支持什么，就能调用什么（包括 --help 和所有技能动作）。
3. 不用手工串流程：`plan` / `dispatch` / `status` 直接驱动 R01 编排器，
   `chat` 生成知识注入 Prompt，`check` 一次体检全部角色。

示例：
    python guagua.py roles
    python guagua.py info r06
    python guagua.py call r06 --help
    python guagua.py call r06 semantics validate --input examples/model.json
    python guagua.py chat --role r06 --intent "分析订单漏斗与留存"
    python guagua.py plan "停车场一年营收最大化"
    python guagua.py dispatch --all
    python guagua.py check
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

# 让 core.registry 可导入；同时保持脚本可从任意目录启动。
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.registry import ROLES, by_id  # noqa: E402


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _display_width(text: str) -> int:
    """粗略计算终端显示宽度：中文/全角按 2 列。"""
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def _print_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    rows = [list(row) for row in rows]
    widths = [_display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _display_width(str(cell)))
    line = "  ".join(_pad(str(h), widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(_pad(str(cell), widths[i]) for i, cell in enumerate(row)))


def _env() -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # 兼容直接执行子目录 agent.py 时的 import core。
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _run(cmd: Sequence[str], cwd: Path) -> int:
    """同步执行并继承 stdout/stderr，返回退出码。"""
    try:
        proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=_env())
        return int(proc.returncode)
    except FileNotFoundError as exc:
        print(f"[guagua] 找不到命令: {exc}", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        print("\n[guagua] 已中断", file=sys.stderr)
        return 130


def _run_capture(cmd: Sequence[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd),
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# 角色解析
# ---------------------------------------------------------------------------

def resolve_role(token: str) -> Dict[str, Any]:
    """支持 r06 / 06 / 蛙得清 / r06-wadeqing-analyst / 数据分析师。"""
    raw = (token or "").strip()
    low = raw.lower()
    if not raw:
        raise SystemExit("[guagua] 角色不能为空，先运行: python guagua.py roles")

    candidates: List[Dict[str, Any]] = []
    for role in ROLES:
        values = {
            role["id"].lower(),
            role["name"].lower(),
            role["title"].lower(),
            role["dir"].lower(),
            role["id"][1:].lower(),
        }
        if low in values:
            candidates.append(role)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        ids = "、".join(r["id"] for r in candidates)
        raise SystemExit(f"[guagua] 角色“{raw}”有歧义：{ids}；请改用角色 ID。")

    # 允许模糊匹配中文名 / 目录名 / 标题。
    fuzzy = [r for r in ROLES if low in r["name"].lower() or low in r["dir"].lower() or low in r["title"].lower()]
    if len(fuzzy) == 1:
        return fuzzy[0]
    ids = "、".join(r["id"] for r in (fuzzy or ROLES))
    raise SystemExit(f"[guagua] 未找到角色“{raw}”。可选：{ids}")


def _role_agent(role: Dict[str, Any]) -> Path:
    return ROOT / role["dir"] / "agent.py"


def _require_agent(role: Dict[str, Any]) -> Path:
    agent = _role_agent(role)
    if not agent.exists():
        raise SystemExit(f"[guagua] 角色文件不存在: {agent}")
    return agent


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_roles(_: argparse.Namespace) -> int:
    rows = []
    for r in ROLES:
        rows.append([
            r["id"],
            r["name"],
            r["title"],
            r["status"],
            " + ".join(r["inputs"]),
            " + ".join(r["outputs"]),
            "、".join(r["capabilities"][:3]) + ("…" if len(r["capabilities"]) > 3 else ""),
        ])
    print("蛙蛙呱呱 · 20 角色总览\n")
    _print_table(["ID", "代号", "职位", "状态", "输入", "输出", "能力（前 3 项）"], rows)
    print("\n查看详情: python guagua.py info r06")
    print("调用角色: python guagua.py call r06 --help")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    role = resolve_role(args.role)
    print(f"{role['id']} · {role['name']}｜{role['title']}")
    print("=" * 72)
    print(f"目录    : {role['dir']}")
    print(f"状态    : {role['status']}")
    print(f"输入端口: {', '.join(role['inputs'])}")
    print(f"输出端口: {', '.join(role['outputs'])}")
    print("\n核心能力：")
    for i, cap in enumerate(role["capabilities"], 1):
        print(f"  {i:>2}. {cap}")
    print("\n推荐入口：")
    print(f"  python guagua.py call {role['id']} --help")
    print(f"  python guagua.py call {role['id']} manifest")
    print(f"  python guagua.py chat --role {role['id']} --intent \"你的目标\"")
    if role["id"] == "r01":
        print('  python guagua.py plan "你的经营目标"')
        print("  python guagua.py dispatch --all")
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    role = resolve_role(args.role)
    agent = _require_agent(role)
    forwarded = list(args.agent_args or [])
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        forwarded = ["--help"]
    # 关键：在角色目录执行，保证文档里的 examples/、workspace/ 相对路径可用。
    return _run([PYTHON, agent, *forwarded], cwd=agent.parent)


def cmd_chat(args: argparse.Namespace) -> int:
    role = resolve_role(args.role)
    cmd = [PYTHON, ROOT / "chat.py", "--role", role["id"], "--intent", args.intent]
    if args.domains:
        cmd += ["--domains", args.domains]
    if args.output:
        cmd += ["--output", args.output]
    if args.vector:
        cmd += ["--vector"]
    return _run(cmd, cwd=ROOT)


def cmd_plan(args: argparse.Namespace) -> int:
    role = by_id("r01")
    agent = _require_agent(role)
    return _run([PYTHON, agent, "plan", "--intent", args.intent], cwd=ROOT)


def cmd_dispatch(args: argparse.Namespace) -> int:
    role = by_id("r01")
    agent = _require_agent(role)
    cmd = [PYTHON, agent, "run"]
    if args.all:
        cmd.append("--all")
    if args.task:
        cmd += ["--task", args.task]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    if not args.all and not args.task:
        raise SystemExit("[guagua] 请指定 --all 或 --task <task_id>")
    return _run(cmd, cwd=ROOT)


def cmd_status(_: argparse.Namespace) -> int:
    role = by_id("r01")
    agent = _require_agent(role)
    proc = _run_capture([PYTHON, agent, "status"], cwd=ROOT, timeout=90)
    marker = "__AGENT_RESULT__ "
    line = next((x for x in (proc.stdout or "").splitlines() if x.startswith(marker)), "")
    if not line:
        # 解析失败时保留原始输出，不隐藏信息。
        sys.stdout.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        return int(proc.returncode)

    try:
        data = json.loads(line[len(marker):])
    except json.JSONDecodeError:
        print(line)
        return 0

    tasks = data.get("tasks", [])
    counts: Counter = Counter()
    attention: List[str] = []
    for task in tasks:
        m = re.match(r"^\S+\s+(\w+)\s+", task)
        status = m.group(1) if m else "unknown"
        counts[status] += 1
        if status in {"pending", "running", "failed"}:
            attention.append(task)

    print("R01 · 任务卡状态")
    print("=" * 72)
    print(f"总数: {data.get('task_count', len(tasks))}")
    for status, count in counts.most_common():
        print(f"  {status:<10} {count}")
    if attention:
        print("\n需要关注（pending / running / failed，最多显示 20 条）：")
        for task in attention[:20]:
            print(f"  {task}")
        if len(attention) > 20:
            print(f"  ... 另有 {len(attention) - 20} 条")
    else:
        print("\n没有 pending / running / failed 任务。")
    print("\n完整原始输出: python guagua.py call r01 status")
    return 0


def _demo_one(role: Dict[str, Any]) -> int:
    agent = _require_agent(role)
    if role["id"] == "r03":
        print(f"\n===== {role['id']} · {role['name']} · demo =====", flush=True)
        print("[skip] R03 未提供 demo 子命令；请直接调用专家技能，例如：")
        print("       python guagua.py call r03 aigov aiclassify --input examples/aigov_aiclassify.json")
        return 0
    print(f"\n===== {role['id']} · {role['name']} · demo =====", flush=True)
    return _run([PYTHON, agent, "demo"], cwd=agent.parent)


def cmd_demo(args: argparse.Namespace) -> int:
    if args.all:
        failed = []
        for role in ROLES:
            code = _demo_one(role)
            if code != 0:
                failed.append(role["id"])
        print("\n" + "=" * 72)
        if failed:
            print(f"[guagua] demo 完成，失败角色: {', '.join(failed)}")
            return 1
        print("[guagua] 全部角色 demo 完成。")
        return 0
    role = resolve_role(args.role or "r01")
    return _demo_one(role)


def cmd_check(args: argparse.Namespace) -> int:
    """逐个执行 `agent.py --help`，证明 20 个角色的入口都可启动。"""
    rows = []
    failed = []
    started = time.time()
    for role in ROLES:
        agent = _role_agent(role)
        if not agent.exists():
            rows.append([role["id"], role["name"], "MISSING", "-", ""])
            failed.append(role["id"])
            continue
        t0 = time.time()
        try:
            proc = _run_capture([PYTHON, agent, "--help"], cwd=agent.parent, timeout=60)
            ok = proc.returncode == 0
            detail = "" if ok else (proc.stderr or proc.stdout or "")[-300:].replace("\n", " ")
        except subprocess.TimeoutExpired:
            ok = False
            detail = "TIMEOUT"
        ms = int((time.time() - t0) * 1000)
        rows.append([role["id"], role["name"], "PASS" if ok else "FAIL", f"{ms}ms", detail])
        if not ok:
            failed.append(role["id"])
    print("蛙蛙呱呱 · 20 角色入口体检\n")
    _print_table(["ID", "代号", "结果", "耗时", "错误摘要"], rows)
    print(f"\n总耗时 {time.time() - started:.1f}s；通过 {len(ROLES) - len(failed)}/{len(ROLES)}")
    if failed:
        print(f"失败角色: {', '.join(failed)}")
        return 1
    print("全部角色入口可用。下一步: python guagua.py roles")
    return 0


def _memory_summary() -> Dict[str, Any]:
    """汇总全部角色记忆池的体积，供 doctor / gc 使用。"""
    from core.memory_guard import HARD_LIMIT_BYTES, SOFT_LIMIT_BYTES, file_size, iter_memory_files
    files = iter_memory_files(str(ROOT))
    sizes = [(path, file_size(path)) for path in files]
    total = sum(size for _, size in sizes)
    biggest = max(sizes, key=lambda item: item[1]) if sizes else (None, 0)
    return {"files": files, "sizes": sizes, "total": total,
            "biggest": biggest, "soft": SOFT_LIMIT_BYTES, "hard": HARD_LIMIT_BYTES}


def _memory_health(mem: Dict[str, Any]) -> Optional[str]:
    """记忆池体积哨兵：返回告警文案，正常时返回 None。"""
    if mem["biggest"][1] > mem["hard"]:
        return "[FAIL] 有记忆池超过 100 MB：python guagua.py gc"
    if mem["biggest"][1] > mem["soft"]:
        return "[WARN] 有记忆池超过 2 MB：建议 python guagua.py gc"
    return None


def cmd_gc(args: argparse.Namespace) -> int:
    """记忆池护栏：裁剪过期快照 / 隔离异常体积文件。"""
    from core.memory_guard import format_report, gc as run_gc
    summary = run_gc(str(ROOT), keep_last=args.keep_last, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_report(summary))
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    """能力目录：谁拥有、谁能用、是代码技能还是规范。"""
    from shared import capabilities as cap_mod

    if args.id:
        cap = cap_mod.get(args.id)
        if not cap:
            print(f"未找到能力：{args.id}")
            return 1
        print(f"{cap['id']} · {cap['title']}")
        print(f"  形态：{cap['kind']}   负责：{cap['owner']}   消费方：{', '.join(cap['consumers']) or '—'}")
        print(f"  触发词：{' / '.join(cap['triggers'])}")
        print(f"  能力卡：{cap['dir']}/README.md")
        if cap["entry"]:
            print(f"  命令：python agent.py {cap['entry']['skill']} {' / '.join(cap['entry']['actions'])}")
        else:
            print("  形态：规范（无独立命令，按能力卡规则执行）")
        print(f"  定位：{cap['summary']}")
        print("\n规则要点：")
        for rule in cap["rules"]:
            print(f"  - {rule}")
        return 0

    caps = cap_mod.list_caps(role=args.role, q=args.q, kind=args.kind)
    if not caps:
        print("没有匹配的能力。")
        return 0
    rows = []
    for cap in caps:
        mark = "代码" if cap["entry"] else "规范"
        missing = "" if os.path.isfile(cap_mod.card_path(cap)) else "（缺能力卡）"
        if args.probe:
            mark += "/就绪" if os.path.isfile(cap_mod.card_path(cap)) else "/缺失"
        rows.append([cap["id"], cap["owner"], cap["kind"], mark, cap["title"] + missing])
    print(f"蛙蛙呱呱 · 能力目录（{len(rows)} 项，role={args.role or 'all'}）\n")
    widths = [max(len(str(r[i])) for r in rows + [["能力", "负责", "类型", "形态", "说明"]])
              for i in range(5)]
    header = ["能力", "负责", "类型", "形态", "说明"]
    print("  ".join(h.ljust(widths[i]) for i, h in enumerate(header)))
    print("  ".join("-" * widths[i] for i in range(5)))
    for r in rows:
        print("  ".join(str(r[i]).ljust(widths[i]) for i in range(5)))
    print("\n查看详情：python guagua.py capabilities --id <能力>")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    print("蛙蛙呱呱 · 环境诊断")
    print("=" * 72)
    print(f"Python  : {sys.version.split()[0]}  ({PYTHON})")
    print(f"项目根  : {ROOT}")
    print(f"角色数  : {len(ROLES)}")
    print(f"chat.py : {'OK' if (ROOT / 'chat.py').exists() else 'MISSING'}")
    print(f"registry: {'OK' if (ROOT / 'core' / 'registry.py').exists() else 'MISSING'}")
    if (ROOT / 'core' / 'memory_guard.py').exists():
        mem = _memory_summary()
        print(f"记忆池  : {len(mem['files'])} 个文件，合计 {mem['total'] / 1024:.1f} KB")
        if mem["biggest"][0]:
            rel = Path(mem["biggest"][0]).relative_to(ROOT).as_posix()
            print(f"          最大 {rel}  {mem['biggest'][1] / 1024:.1f} KB")
        warning = _memory_health(mem)
        if warning:
            print(warning)
    missing = [r["id"] for r in ROLES if not _role_agent(r).exists()]
    if missing:
        print(f"缺失入口: {', '.join(missing)}")
        return 1
    print("20 个 agent.py 均存在。")
    if sys.version_info < (3, 10):
        print("[WARN] 建议 Python 3.10+。")
    return cmd_check(argparse.Namespace())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guagua.py",
        description="蛙蛙呱呱 20 角色统一入口：一个命令调用全部角色与全部技能。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "常用示例:\n"
            "  python guagua.py roles\n"
            "  python guagua.py call r06 --help\n"
            "  python guagua.py call r06 explore funnel --input examples/orders.csv\n"
            "  python guagua.py chat --role r06 --intent \"分析订单漏斗\"\n"
            '  python guagua.py plan "停车场一年营收最大化"\n'
            "  python guagua.py dispatch --all\n"
            "  python guagua.py check\n"
            "  python guagua.py gc --dry-run\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("roles", help="列出 20 个角色")
    p.set_defaults(func=cmd_roles)

    p = sub.add_parser("info", help="查看一个角色的契约、能力与入口")
    p.add_argument("role", help="角色 ID / 中文名 / 目录名，如 r06 或 蛙得清")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser(
        "call",
        help="调用角色的任意子命令（全部功能的总入口）",
        description="把参数原样转发给角色 agent.py；在角色目录执行，examples/ 路径可直接用。",
    )
    p.add_argument("role", help="角色 ID / 中文名 / 目录名")
    p.add_argument("agent_args", nargs=argparse.REMAINDER, help="传给 agent.py 的参数；为空则显示 --help")
    p.set_defaults(func=cmd_call)

    p = sub.add_parser("chat", help="生成某角色的知识注入 Prompt")
    p.add_argument("--role", required=True, help="角色 ID")
    p.add_argument("--intent", required=True, help="你的意图/问题")
    p.add_argument("--domains", default=None, help="限定知识域，逗号分隔")
    p.add_argument("--output", default=None, help="输出文件")
    p.add_argument("--vector", action="store_true", help="启用向量检索（如已配置）")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("plan", help="让 R01 把经营意图拆成任务卡")
    p.add_argument("intent", help="经营意图，如：停车场一年营收最大化")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("dispatch", help="让 R01 执行任务卡并验收")
    p.add_argument("--all", action="store_true", help="执行所有依赖就绪的任务")
    p.add_argument("--task", default=None, help="只执行指定 task_id")
    p.add_argument("--limit", type=int, default=None, help="最多执行几张卡")
    p.set_defaults(func=cmd_dispatch)

    p = sub.add_parser("status", help="查看任务卡依赖与状态")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("demo", help="运行角色自带的 demo")
    p.add_argument("role", nargs="?", default=None, help="角色 ID；默认 r01")
    p.add_argument("--all", action="store_true", help="依次运行全部角色 demo")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("check", help="体检全部 20 个角色入口")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("capabilities", help="能力目录：谁拥有 / 谁能用 / 形态（代码或规范）")
    p.add_argument("--role", default=None, help="角色 ID（如 r11）：查自己负责或可消费的能力")
    p.add_argument("--id", default=None, help="能力 ID（如 rednote-post）")
    p.add_argument("--q", default=None, help="按名称/触发词搜索")
    p.add_argument("--kind", default=None, choices=["skill", "multi", "mcp"])
    p.add_argument("--probe", action="store_true", help="显示就绪探测（本地只读，不联网）")
    p.set_defaults(func=cmd_capabilities)

    p = sub.add_parser("gc", help="记忆池护栏：裁剪过期快照 / 隔离异常体积文件",
        description="扫描全部 rXX-*/workspace/session_state*.json："
                    "超过 2 MB 裁到最近 N 条快照，超过 100 MB 整份隔离为 .bak。",
    )
    p.add_argument("--dry-run", action="store_true", help="只出报告，不改文件")
    p.add_argument("--keep-last", type=int, default=50, help="保留最近多少条快照（默认 50）")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    p.set_defaults(func=cmd_gc)

    p = sub.add_parser("doctor", help="环境诊断 + 全部角色入口体检")
    p.set_defaults(func=cmd_doctor)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
