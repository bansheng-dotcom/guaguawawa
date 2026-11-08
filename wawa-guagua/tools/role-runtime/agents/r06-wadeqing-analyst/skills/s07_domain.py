# -*- coding: utf-8 -*-
"""S07 专业领域分析（生物信息学）—— 能力域 7。

整合自 Starlitnightly__omicverse（`.claude/skills/` 下 31 个 SKILL.md +
`seeker` 文档→技能 生成 API）。这是**重依赖**领域（需 omicverse/scanpy/anndata），
所以本技能做成「领域技能注册表 + 后端门禁 + 管线脚手架」：能 import 就进入
真实分析，不能则如实返回 blocked + 安装/领域审查提示，绝不假装会算。

边界（能力全景 R06 边界）：仅在具备真实数据 + 领域审查时支持；否则只出
可复算流程骨架，不产出假结论。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "domain"
DESC = "专业领域分析：omicverse 生信技能注册表 / 后端门禁 / 管线脚手架"

# omicverse `.claude/skills/` 里的真实技能名（去重后的核心清单）
OMICVERSE_SKILLS = [
    "datasets-loading", "data-io-loading", "data-transform", "data-export-excel",
    "data-export-pdf", "data-stats-analysis", "data-viz-plots",
    "single-preprocessing", "single-clustering", "single-annotation",
    "single-popv-annotation", "single-trajectory", "single-cellfate-analysis",
    "single-cellphone-db", "single-scenic-grn", "single-downstream-analysis",
    "single-multiomics", "single-to-spatial-mapping", "spatial-tutorials",
    "bulk-combat-correction", "bulk-deg-analysis", "bulk-deseq2-analysis",
    "bulk-wgcna-analysis", "bulk-stringdb-ppi", "bulk-to-single-deconvolution",
    "bulk-trajblend-interpolation", "fastq-analysis", "gsea-enrichment",
    "tcga-preprocessing", "biocontext-knowledge",
]

PIPELINE_STAGES = ["load", "qc", "normalize", "reduce", "cluster",
                   "annotate", "differential", "visualize"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    l = act.add_parser("list", help="列出 omicverse 可用领域技能")
    l.add_argument("--filter", default=None, help="按子串过滤技能名")

    r = act.add_parser("run", help="跑管线脚手架（门禁检查 omicverse/anndata）")
    r.add_argument("--data", required=True, help="输入数据路径（h5ad/csv）")
    r.add_argument("--pipeline", default="preprocess",
                   choices=["preprocess", "cluster", "deg", "full"],
                   help="管线类型")


def run(args) -> Dict[str, Any]:
    if args.action == "list":
        return _list(args.filter)
    if args.action == "run":
        return _run(args.data, args.pipeline)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _list(filt):
    skills = [s for s in OMICVERSE_SKILLS if not filt or filt.lower() in s.lower()]
    return {"domain": "bioinformatics", "backend": "omicverse",
            "skill_count": len(skills), "skills": skills}


def _run(data, pipeline):
    backends = {}
    for mod in ("omicverse", "anndata", "scanpy"):
        try:
            __import__(mod)
            backends[mod] = "available"
        except ImportError:
            backends[mod] = "unavailable"
    ready = all(v == "available" for v in backends.values())
    stages = {
        "preprocess": ["load", "qc", "normalize"],
        "cluster": ["load", "qc", "normalize", "reduce", "cluster", "annotate"],
        "deg": ["load", "qc", "normalize", "differential"],
        "full": PIPELINE_STAGES,
    }[pipeline]
    if not ready:
        return {
            "status": "blocked",
            "backends": backends,
            "reason": "缺少重依赖 omicverse/anndata/scanpy；需 pip 安装 + 领域审查",
            "pipeline": pipeline, "stages": stages,
            "data": data,
            "note": "未做真实生信分析，不产出任何可复用结论",
        }
    # 后端齐备时给出可复算流程骨架（领域数据仍需人工审查）
    return {
        "status": "scaffold",
        "backends": backends, "pipeline": pipeline, "stages": stages,
        "data": data,
        "note": "后端就绪，下一步按 stages 逐一执行并留痕；领域结论需人工审查",
        "skill_hint": [s for s in OMICVERSE_SKILLS if pipeline in s or
                       any(st in s for st in stages)][:6],
    }