"""
操作日志生成器
==============
每次任务完成后调用 `generate_log()` 生成 Markdown 格式的操作日志。

用法:
    from log_generator import LogSession

    session = LogSession("Week 03 PDF 批量转换")
    session.read("ipynb_to_pdf.py", "了解脚本用法")
    session.edit("week_03/day_01/xxx.ipynb", "修复 SyntaxError")
    session.write("week_03/day_01/xxx.ipynb", "补全 execution_count")
    session.install("some-package", "满足依赖")
    session.generate_pdf("pdf/week_03/day_01/xxx.pdf", "1.5M")
    session.problem("问题描述", "修复方案")
    session.done()
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent  # analyst_thinking_learn/
LOGS_DIR = SCRIPT_DIR / "logs"


class LogSession:
    """一次任务的日志会话"""

    def __init__(self, title: str):
        self.title = title
        self.timestamp = datetime.now()
        self.reads: list[dict] = []
        self.edits: list[dict] = []
        self.writes: list[dict] = []
        self.installs: list[dict] = []
        self.pdfs: list[dict] = []
        self.problems: list[dict] = []
        self.notes: list[str] = []

    # ── 记录方法 ──

    def read(self, path: str, reason: str = ""):
        """记录读取的文件"""
        self.reads.append({"path": path, "reason": reason})

    def edit(self, path: str, detail: str):
        """记录编辑的文件"""
        self.edits.append({"path": path, "detail": detail})

    def write(self, path: str, detail: str):
        """记录覆写的文件"""
        self.writes.append({"path": path, "detail": detail})

    def install(self, package: str, reason: str, uninstalled: bool = False):
        """记录安装/卸载的包"""
        action = "卸载" if uninstalled else "安装"
        self.installs.append({"package": package, "action": action, "reason": reason})

    def generate_pdf(self, path: str, size: str = ""):
        """记录生成的 PDF"""
        self.pdfs.append({"path": path, "size": size})

    def problem(self, issue: str, fix: str):
        """记录遇到的问题和修复"""
        self.problems.append({"issue": issue, "fix": fix})

    def note(self, text: str):
        """附加备注"""
        self.notes.append(text)

    # ── 输出 ──

    def done(self, output_path: Optional[str] = None) -> str:
        """生成日志文件，返回文件路径"""
        if output_path is None:
            date_str = self.timestamp.strftime("%Y-%m-%d")
            title_slug = self.title.replace(" ", "_").replace("/", "-")[:40]
            filename = f"{date_str}_{title_slug}.md"
            output_path = str(LOGS_DIR / filename)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        content = self._render()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[log] {output_path}")
        return output_path

    def _render(self) -> str:
        lines = []
        dt = self.timestamp.strftime("%Y-%m-%d %H:%M")
        lines.append(f"# Session Log — {dt}  {self.title}")
        lines.append("")

        if self.reads:
            lines.append("## 读取的文件")
            lines.append("| 文件 | 说明 |")
            lines.append("|------|------|")
            for r in self.reads:
                lines.append(f"| `{r['path']}` | {r['reason']} |")
            lines.append("")

        if self.edits:
            lines.append("## 编辑的文件")
            lines.append("| 文件 | 操作 | 说明 |")
            lines.append("|------|------|------|")
            for e in self.edits:
                lines.append(f"| `{e['path']}` | 编辑 | {e['detail']} |")
            lines.append("")

        if self.writes:
            lines.append("## 覆写的文件")
            lines.append("| 文件 | 操作 | 说明 |")
            lines.append("|------|------|------|")
            for w in self.writes:
                lines.append(f"| `{w['path']}` | 覆写 | {w['detail']} |")
            lines.append("")

        if self.installs:
            lines.append("## 安装/卸载")
            lines.append("| 包 | 操作 | 原因 |")
            lines.append("|----|------|------|")
            for i in self.installs:
                lines.append(f"| `{i['package']}` | {i['action']} | {i['reason']} |")
            lines.append("")

        if self.pdfs:
            lines.append("## 生成的 PDF")
            lines.append("| 路径 | 大小 |")
            lines.append("|------|------|")
            for p in self.pdfs:
                lines.append(f"| `{p['path']}` | {p['size']} |")
            lines.append("")

        if self.problems:
            lines.append("## 遇到的问题与修复")
            for i, p in enumerate(self.problems, 1):
                lines.append(f"{i}. **{p['issue']}** → {p['fix']}")
            lines.append("")

        if self.notes:
            lines.append("## 备注")
            for n in self.notes:
                lines.append(f"- {n}")
            lines.append("")

        return "\n".join(lines)


# ── 命令行快捷用法 ──
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python log_generator.py \"任务标题\"")
        print("示例: python log_generator.py \"Week 03 PDF 批量转换\"")
        sys.exit(0)

    # 创建一个空日志模板（手动填充内容）
    session = LogSession(sys.argv[1])
    session.note("（在此补充操作记录）")
    session.done()
