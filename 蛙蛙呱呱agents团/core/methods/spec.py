# -*- coding: utf-8 -*-
"""core/methods/spec —— 方法注册表：能力声明 + 自动挂载。

解决的问题：上一版 `analysis_methods.py` 把 12 个方法写死成一个 `collect()` 列表，
新增一类报告就要改 collect、改 compose、改测试。这里把「方法」变成声明：

    @method(key="funnel", family="growth",
            needs=["table.orders"], produces="转化漏斗",
            tags=("growth", "marketing"), priority=60)
    def m_funnel(ctx): ...

调度器只做三件事：
    plan(desk, views, profile, thesis)  → 哪些方法挂载、哪些跳过、为什么
    run(plan, ctx)                      → 依次执行，单点失败只记缺口
    catalog()                           → 给文档/CLI 用的能力清单

`needs` 是能力名，不是文件名。能力由 `register_need()` 注册成谓词，
谓词自己检查 desk/views 里有没有可用结构（列、序列、表）。
这样换项目不用改调度器，换报告类型只要加方法 + 加纲领。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 能力谓词
# --------------------------------------------------------------------------- #
_NEEDS: Dict[str, Callable[[Any], bool]] = {}


def register_need(name: str, fn: Callable[[Any], bool]) -> None:
    _NEEDS[name] = fn


def need_names() -> List[str]:
    return sorted(_NEEDS)


@dataclass
class Caps:
    """能力探针：把 desk / views / profile 包起来，供谓词查询。"""
    desk: Any
    views: Any
    profile: Dict[str, Any] = field(default_factory=dict)

    def has(self, name: str) -> bool:
        fn = _NEEDS.get(name)
        if fn is None:
            return False
        try:
            return bool(fn(self))
        except Exception:  # noqa: BLE001  能力探测失败视为不具备
            return False

    def missing(self, needs: Iterable[str]) -> List[str]:
        return [n for n in needs if not self.has(n)]


# --------------------------------------------------------------------------- #
# 方法声明
# --------------------------------------------------------------------------- #
@dataclass
class MethodSpec:
    key: str
    fn: Callable[[Any], Any]
    family: str = "analysis"
    needs: Tuple[str, ...] = ()
    produces: str = ""
    tags: Tuple[str, ...] = ()
    priority: int = 50
    min_points: int = 0
    optional: bool = True          # 缺能力时：True=跳过，False=记「关键缺口」
    description: str = ""

    def available(self, caps: Caps) -> bool:
        return not caps.missing(self.needs)


REGISTRY: Dict[str, MethodSpec] = {}


def method(key: str, family: str = "analysis", needs: Iterable[str] = (),
           produces: str = "", tags: Iterable[str] = (), priority: int = 50,
           optional: bool = True, description: str = ""):
    def deco(fn):
        REGISTRY[key] = MethodSpec(
            key=key, fn=fn, family=family, needs=tuple(needs),
            produces=produces, tags=tuple(tags), priority=priority,
            optional=optional, description=description or (fn.__doc__ or "").strip())
        return fn
    return deco


def register(spec: MethodSpec) -> None:
    REGISTRY[spec.key] = spec


# --------------------------------------------------------------------------- #
# 自动挂载
# --------------------------------------------------------------------------- #
def plan(desk, views, profile: Dict[str, Any],
         thesis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """按数据能力 + 纲领，决定这一轮挂哪些方法。

    返回 {"mounted": [...], "skipped": [{key, missing, optional}], "order": [...]}
    排序规则：纲领点名的顺序优先，其余按 priority 降序。
    """
    caps = Caps(desk=desk, views=views, profile=profile)
    wanted: List[str] = list((thesis or {}).get("order") or [])
    mounted, skipped = [], []
    for key, spec in REGISTRY.items():
        miss = caps.missing(spec.needs)
        if miss:
            skipped.append({"key": key, "missing": miss, "optional": spec.optional,
                            "produces": spec.produces})
            continue
        mounted.append({"key": key, "family": spec.family,
                        "produces": spec.produces, "needs": list(spec.needs)})

    def sort_key(item):
        key = item["key"]
        if key in wanted:
            return (0, wanted.index(key))
        return (1, -REGISTRY[key].priority)

    mounted.sort(key=sort_key)
    return {"schema": "dsh.method_plan/v1", "mounted": mounted,
            "skipped": skipped, "caps": sorted({n for m in mounted
                                                for n in m["needs"]})}


def run(plan_obj: Dict[str, Any], ctx) -> Tuple[Dict[str, Any], List[str]]:
    out: Dict[str, Any] = {}
    gaps: List[str] = []
    for item in plan_obj["mounted"]:
        key = item["key"]
        spec = REGISTRY[key]
        try:
            f = spec.fn(ctx)
        except Exception as exc:  # noqa: BLE001  单方法失败只降级
            gaps.append(f"{key} 计算失败：{type(exc).__name__}: {exc}")
            continue
        if f is None:
            gaps.append(f"{key} 未产出（数据不足）")
            continue
        out[key] = f
    for s in plan_obj["skipped"]:
        if not s["optional"]:
            gaps.append(f"{s['key']} 关键能力缺失：{', '.join(s['missing'])}")
    return out, gaps


def catalog() -> List[Dict[str, Any]]:
    return [{"key": s.key, "family": s.family, "needs": list(s.needs),
             "produces": s.produces, "tags": list(s.tags),
             "priority": s.priority, "optional": s.optional,
             "description": s.description}
            for s in sorted(REGISTRY.values(), key=lambda x: (x.family, x.key))]
