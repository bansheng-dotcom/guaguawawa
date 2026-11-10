# -*- coding: utf-8 -*-
"""L08 局部差量层：Git Unified Diff 解析与增量切片审查引擎。
对标开源标杆：michaelliao/diff-match-patch (Stars: 3k+), reviewdog/reviewdog (Diff filters)

功能：
1. 摆脱每次代码变动必须对整个工程或全文件全量重审的高昂代价；
2. 真实解析标准 Unified Diff / Patch 格式文本；
3. 提取变更行集合 (Added / Modified Lines)；
4. 实现精准差量审查过滤：将 AST/静态检查发现的问题与 Diff 修改行进行坐标求交，
   仅针对本次提交真实改动的局部行发起拦截，未修改的历史遗留旧告警自动标记为历史存量不予阻断。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class DiffPatchReviewer:
    """Git Unified Diff 增量切片分析器"""

    # 正则提取 @@ -start,len +start,len @@
    HUNK_RE = re.compile(r"^@@\s+-(?:\d+)(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")

    def parse_diff(self, diff_text: str) -> Dict[str, Set[int]]:
        """解析 Unified Diff，返回各文件的修改/新增绝对行号集合"""
        changed_lines_by_file: Dict[str, Set[int]] = {}
        current_file: Optional[str] = None
        current_line: int = 0

        for line in diff_text.splitlines():
            # 匹配文件头: +++ b/path/to/file.py
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                if current_file not in changed_lines_by_file:
                    changed_lines_by_file[current_file] = set()
                continue
            elif line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                current_file = line[4:].strip()
                if current_file not in changed_lines_by_file:
                    changed_lines_by_file[current_file] = set()
                continue

            # 匹配块头 (Hunk Header)
            hunk_match = self.HUNK_RE.match(line)
            if hunk_match:
                start_line = int(hunk_match.group(1))
                current_line = start_line
                continue

            if current_file is None:
                continue

            if line.startswith("+") and not line.startswith("+++"):
                # 新增或修改行
                changed_lines_by_file[current_file].add(current_line)
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                # 删除行在目标版本不占用新行号
                pass
            elif line.startswith(" "):
                # 上下文未变更行
                current_line += 1

        return changed_lines_by_file

    def filter_incremental_findings(self, all_findings: List[Dict[str, Any]], diff_text: str) -> Dict[str, Any]:
        """将全量 findings 过滤为差量新引入 findings vs 历史存量 findings"""
        changed_map = self.parse_diff(diff_text)

        incremental_new: List[Dict[str, Any]] = []
        historical_legacy: List[Dict[str, Any]] = []

        for f in all_findings:
            target = str(f.get("target") or f.get("file") or f.get("path") or "").replace("\\", "/")
            line = int(f.get("line") or 0)

            # 查找是否命中了修改行号
            is_new = False
            # 路径归一化匹配
            for fpath, lines in changed_map.items():
                if target.endswith(fpath) or fpath.endswith(target):
                    if line in lines:
                        is_new = True
                        break

            if is_new:
                f_item = dict(f)
                f_item["is_incremental"] = True
                incremental_new.append(f_item)
            else:
                f_item = dict(f)
                f_item["is_incremental"] = False
                f_item["legacy_suppressed"] = True
                historical_legacy.append(f_item)

        return {
            "total_findings": len(all_findings),
            "incremental_count": len(incremental_new),
            "legacy_count": len(historical_legacy),
            "incremental_findings": incremental_new,
            "legacy_findings": historical_legacy,
            "can_pass_incremental": len([f for f in incremental_new if str(f.get("severity", "")).lower() in ("blocker", "critical")]) == 0,
        }
