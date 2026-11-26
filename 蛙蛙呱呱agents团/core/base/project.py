# -*- coding: utf-8 -*-
"""项目资产根：读/建 `<PROJECT_ROOT>/project.yaml`，管好项目目录骨架。

项目根永远在专家团之外（见 `core/paths.py`）。本模块只做三件事：

    load()   —— 读项目元数据（缺失时返回默认对象，不阻断只读命令）
    init()   —— 建目录骨架 + 写 project.yaml（已存在则不覆盖）
    ensure() —— load，目录缺失时补建（幂等）

目录约定的唯一出处是 `SUBDIRS`；新增目录先改这里，再改文档。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from core import paths

PROJECT_FILE = "project.yaml"
SCHEMA = "dsh.project/v1"

#: 项目内标准目录（空目录也保留，避免每个命令自己猜路径）
SUBDIRS = (
    "inputs",      # 原始材料（用户给的文件）
    "data",        # 清洗后的数据 / 数据集
    "knowledge",   # 项目领域知识快照（framework，不含事实数字）
    "briefs",      # expert_brief（按 task_id 落盘）
    "cards",       # 任务卡 bundle
    "claims",      # 角色交回的 claims
    "artifacts",   # 中间产物
    "report",      # 报告成品
    "eval",        # 评测集与结果
    "runs",        # 任务账本（tasks/）与运行记录
)


@dataclass
class Project:
    root: Path
    slug: str = ""
    name: str = ""
    industry: Optional[str] = None
    knowledge_snapshot: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # ---------------- 路径工具 ---------------- #
    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def rel(self, p: Path | str) -> str:
        return paths.project_rel(p, self.root)

    def ensure_dirs(self) -> "Project":
        for name in SUBDIRS:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "slug": self.slug,
            "name": self.name,
            "industry": self.industry,
            "knowledge_snapshot": self.knowledge_snapshot,
            "root": str(self.root),
            **({"meta": self.meta} if self.meta else {}),
        }


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml
        with open(path, encoding="utf-8-sig") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001  坏文件不该阻断只读命令
        return {}


def load(root: str | Path | None = None) -> Project:
    """读取项目元数据。缺失 project.yaml 时返回默认对象（不报错）。"""
    p = paths.project_root(None if root is None else str(root))
    doc = _read_yaml(p / PROJECT_FILE)
    return Project(
        root=p,
        slug=str(doc.get("slug") or p.name),
        name=str(doc.get("name") or p.name),
        industry=doc.get("industry"),
        knowledge_snapshot=doc.get("knowledge_snapshot"),
        meta={k: v for k, v in doc.items()
              if k not in ("schema", "slug", "name", "industry",
                           "knowledge_snapshot")},
    )


def init(path: str | Path, industry: Optional[str] = None,
         name: Optional[str] = None) -> Dict[str, Any]:
    """建项目骨架。已存在则只补目录，不覆盖 project.yaml。

    返回 {"ok", "root", "created", "dirs"}。写团内会抛 BoundaryError。
    """
    root = Path(path).expanduser().resolve()
    # 守卫：项目根不能落在专家团里
    paths.assert_writable(root / PROJECT_FILE)

    created_dirs = []
    for sub in SUBDIRS:
        d = root / sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created_dirs.append(sub)

    target = root / PROJECT_FILE
    created = False
    if not target.exists():
        import yaml
        doc = {
            "schema": SCHEMA,
            "slug": root.name,
            "name": name or root.name,
            "industry": industry or "",
            "knowledge_snapshot": "",
        }
        target.write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
            encoding="utf-8")
        created = True

    return {"ok": True, "root": str(root), "created": created,
            "created_dirs": created_dirs, "project_file": str(target)}


def ensure(root: str | Path | None = None) -> Project:
    """load + 补建目录（幂等），用于运行期拿到一个可写的 Project。"""
    proj = load(root)
    proj.ensure_dirs()
    return proj
