# -*- coding: utf-8 -*-
"""engines/intent_compiler.py - R10 视觉设计官 · L02 意图解构与提示词编译层 (Intent Compiler).

对标 DSPy / Ray DAG (Stars > 25k)：
1. 将自然语言复杂设计需求解构成结构化设计要素（产品主题、视觉风格、构图宽高比、品牌调性）；
2. 编译为严格遵循 Kahn 算法的 5 阶段交付 DAG 拓扑执行序与工时预算；
3. 输出面向外置生成引擎与排版流水线的确定性 Prompt Specification。
"""
from __future__ import annotations

import collections
import re
from typing import Any, Dict, List, Optional

from engines.prompter import DesignPrompter, get_design_prompter


class VisualIntentCompiler:
    """L02 视觉意图解构与 DAG 编译器。"""

    def __init__(self, prompter: Optional[DesignPrompter] = None):
        self.prompter = prompter or get_design_prompter()

    def decompile(self, query: str) -> Dict[str, Any]:
        """解构自然语言意图并编译为交付 DAG。"""
        # 1. 实体与调性提取
        extracted = self._extract_entities(query)

        # 2. 调度 DesignPrompter 进行提示词扩展
        spec = self.prompter.expand(
            brief=extracted["concept"],
            category_or_style=extracted["style"],
            aspect_ratio=extracted["aspect_ratio"]
        )

        # 3. 构造 5 阶段交付 DAG
        dag = self._build_delivery_dag(extracted)

        return {
            "ok": True,
            "layer": "L02",
            "query": query,
            "extracted_entities": extracted,
            "compiled_spec": spec,
            "dag": dag,
        }

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        # 风格推导
        style = "commercial-photography"
        if any(w in q for w in ["赛博", "科技", "霓虹", "cyber", "tech"]):
            style = "cyberpunk"
        elif any(w in q for w in ["极简", "商务", "高级", "editorial", "minimal"]):
            style = "minimalist"
        elif any(w in q for w in ["水彩", "插画", "手绘", "watercolor", "illustration"]):
            style = "watercolor"
        elif any(w in q for w in ["3d", "立体", "c4d", "render"]):
            style = "3d-render"
        elif any(w in q for w in ["扁平", "图标", "flat"]):
            style = "flat"

        # 尺寸与纵横比推导
        aspect_ratio = "1:1"
        if any(w in q for w in ["海报", "竖版", "小红书", "移动端", "手机"]):
            aspect_ratio = "9:16"
        elif any(w in q for w in ["banner", "横版", "宽屏", "通栏"]):
            aspect_ratio = "16:9"

        # 主题概念清洗
        concept = re.sub(r"(设计|生成|制作|需要|一张|一份|宣传|海报|主视觉|图片|图)", "", query).strip()
        if not concept:
            concept = "高端商业宣传主视觉"

        return {
            "concept": concept,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "target_media": "image",
            "safe_margin_required": True,
        }

    def _build_delivery_dag(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """构建 Kahn 拓扑 DAG 标准交付图。"""
        nodes = {
            "stage_01_brief_analysis": {
                "name": "需求解构与语义分析",
                "estimated_hours": 0.5,
                "dependencies": [],
            },
            "stage_02_prompt_expansion": {
                "name": "LLM创意大脑扩写与风格锁绑定",
                "estimated_hours": 0.8,
                "dependencies": ["stage_01_brief_analysis"],
            },
            "stage_03_engine_render": {
                "name": "外置引擎调度与确定性渲染",
                "estimated_hours": 1.5,
                "dependencies": ["stage_02_prompt_expansion"],
            },
            "stage_04_postprocess_polish": {
                "name": "Anti-Slop 质感精修与商用排版",
                "estimated_hours": 1.2,
                "dependencies": ["stage_03_engine_render"],
            },
            "stage_05_vlm_critic": {
                "name": "多模态 VLM 视觉质检与自愈闭环",
                "estimated_hours": 1.0,
                "dependencies": ["stage_04_postprocess_polish"],
            },
        }

        # Kahn 算法拓扑排序验证
        in_degree = {k: len(v["dependencies"]) for k, v in nodes.items()}
        graph = collections.defaultdict(list)
        for node, meta in nodes.items():
            for dep in meta["dependencies"]:
                graph[dep].append(node)

        queue = collections.deque([k for k, d in in_degree.items() if d == 0])
        topo_order: List[str] = []
        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for nxt in graph[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        is_dag = (len(topo_order) == len(nodes))
        total_hours = sum(n["estimated_hours"] for n in nodes.values())

        return {
            "is_dag": is_dag,
            "node_count": len(nodes),
            "topological_order": topo_order,
            "total_estimated_hours": round(total_hours, 2),
            "nodes": nodes,
        }
