# -*- coding: utf-8 -*-
"""L01 工具实体层：真实 AST 代码度量与圈复杂度静态审查引擎。
对标开源项目：PyCQA/radon (Stars > 1.3k), ast-grep (Stars > 5.5k)。
解决病灶：审查只做纯正则或写死字典判断，缺少真实代码语法树(AST)度量、圈复杂度分析与反模式量化。
"""
from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional


class CodeMetricVisitor(ast.NodeVisitor):
    """通过遍历 Python 抽象语法树计算圈复杂度 (Cyclomatic Complexity) 与代码异味。"""

    def __init__(self) -> None:
        self.complexity_by_func: Dict[str, int] = {}
        self.current_func: Optional[str] = None
        self.docstrings: Dict[str, bool] = {}
        self.loc: int = 0
        self.comments: int = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        prev = self.current_func
        name = node.name
        self.current_func = name
        self.complexity_by_func[name] = 1  # 基础复杂度为 1
        doc = ast.get_docstring(node)
        self.docstrings[name] = bool(doc)
        self.generic_visit(node)
        self.current_func = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        prev = self.current_func
        name = node.name
        self.current_func = name
        self.complexity_by_func[name] = 1
        doc = ast.get_docstring(node)
        self.docstrings[name] = bool(doc)
        self.generic_visit(node)
        self.current_func = prev

    def _increment(self) -> None:
        if self.current_func and self.current_func in self.complexity_by_func:
            self.complexity_by_func[self.current_func] += 1

    def visit_If(self, node: ast.If) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
        self._increment()
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        # and / or 每个操作数增加判断路径
        if self.current_func and self.current_func in self.complexity_by_func:
            self.complexity_by_func[self.current_func] += max(0, len(node.values) - 1)
        self.generic_visit(node)


class CodeMetricEngine:
    """真实代码静态度量引擎。"""

    @classmethod
    def analyze_source(cls, source_code: str, filename: str = "<memory>") -> Dict[str, Any]:
        lines = source_code.splitlines()
        loc = len(lines)
        sloc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
        comments = len([l for l in lines if l.strip().startswith("#")])

        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            return {
                "ok": False,
                "error": f"SyntaxError at line {e.lineno}: {e.msg}",
                "filename": filename,
                "loc": loc,
                "sloc": sloc,
                "complexity": {},
                "maintainability_index": 0.0,
            }

        visitor = CodeMetricVisitor()
        visitor.visit(tree)

        complexities = visitor.complexity_by_func
        avg_complexity = (
            sum(complexities.values()) / max(1, len(complexities))
            if complexities else 1.0
        )
        max_complexity = max(complexities.values()) if complexities else 1

        # 计算可维护性指数 Maintainability Index (简化对标 radon MI 经验公式 0-100)
        # MI = 171 - 5.2 * ln(V) - 0.23 * (C) - 16.2 * ln(LOC)
        import math
        mi = 100.0
        if sloc > 0:
            mi = max(0.0, min(100.0, 100.0 - (avg_complexity * 3.5) - (math.log(max(1, sloc)) * 4.0)))

        # 危险模式静态探测 (ast-grep 对标)
        smells: List[Dict[str, Any]] = []
        for node in ast.walk(tree):
            # 裸 except 检测
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    smells.append({
                        "type": "bare_except",
                        "line": getattr(node, "lineno", 0),
                        "severity": "high",
                        "message": "Found bare except clause without specific Exception type.",
                    })
            # 危险 eval/exec 检测
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec"):
                    smells.append({
                        "type": "dangerous_call",
                        "line": getattr(node, "lineno", 0),
                        "severity": "critical",
                        "message": f"Dangerous call to {node.func.id}() detected.",
                    })

        return {
            "ok": True,
            "filename": filename,
            "loc": loc,
            "sloc": sloc,
            "comments": comments,
            "functions_count": len(complexities),
            "complexity_by_func": complexities,
            "avg_complexity": round(avg_complexity, 2),
            "max_complexity": max_complexity,
            "maintainability_index": round(mi, 2),
            "smells": smells,
        }

    @classmethod
    def analyze_file(cls, filepath: str) -> Dict[str, Any]:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        return cls.analyze_source(code, filename=filepath)
