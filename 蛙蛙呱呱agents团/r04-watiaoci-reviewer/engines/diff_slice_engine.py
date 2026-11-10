# -*- coding: utf-8 -*-
"""L08 局部差量层：Git Unified Diff 增量切片审查与历史告警抑制引擎。
对标开源项目：reviewdog (Stars > 6.5k), google/diff-match-patch (Stars > 6k)。
解决病灶：文件修改 1 行却触发全量重新审查，导致历史遗留技术债全部误伤当前提交者；无法实现仅对当前 diff 增量切片进行精准挑刺。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set


class DiffSliceEngine:
    """Git Unified Diff 解析与增量审查告警抑制引擎。"""

    @classmethod
    def parse_unified_diff(cls, diff_text: str) -> Dict[str, Set[int]]:
        """解析 Unified Diff 文本，提取每个文件的变动行号集合（仅新增/修改行）。"""
        changed_lines_by_file: Dict[str, Set[int]] = {}
        current_file: str | None = None
        current_line: int = 0

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                changed_lines_by_file[current_file] = set()
            elif line.startswith("@@ "):
                # @@ -old_start,old_count +new_start,new_count @@
                m = re.search(r"\+(\d+)(?:,(\d+))?", line)
                if m:
                    current_line = int(m.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    changed_lines_by_file[current_file].add(current_line)
                current_line += 1
            elif line.startswith("-"):
                pass  # 删除行不消耗新文件行号
            else:
                current_line += 1

        return changed_lines_by_file

    @classmethod
    def filter_incremental_findings(cls, all_findings: List[Dict[str, Any]], diff_text: str) -> Dict[str, Any]:
        """将全量告警与 diff 进行交集比对，仅保留当前变更引入的问题，其余归入存量抑制池。"""
        changed_lines = cls.parse_unified_diff(diff_text)

        incremental_findings: List[Dict[str, Any]] = []
        suppressed_legacy_findings: List[Dict[str, Any]] = []

        for f in all_findings:
            file_name = f.get("file_path") or f.get("source") or ""
            # 路径归一化匹配
            file_key = file_name.replace("\\", "/").split("/")[-1]
            line = int(f.get("line") or f.get("line_number") or 0)

            # 检查是否有对应文件变动
            matched_diff_file = None
            for d_file in changed_lines:
                if d_file.endswith(file_key) or file_key.endswith(d_file):
                    matched_diff_file = d_file
                    break

            if matched_diff_file and line in changed_lines[matched_diff_file]:
                incremental_findings.append(f)
            else:
                suppressed_legacy_findings.append({
                    "finding": f,
                    "reason": "Suppressed: finding is outside current diff hunk (legacy issue)",
                })

        return {
            "total_findings": len(all_findings),
            "incremental_count": len(incremental_findings),
            "suppressed_count": len(suppressed_legacy_findings),
            "incremental_findings": incremental_findings,
            "suppressed_legacy_findings": suppressed_legacy_findings,
        }
