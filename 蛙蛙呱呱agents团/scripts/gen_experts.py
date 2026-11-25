#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/gen_experts.py —— 生成专家卡 `configs/experts.yaml`（单一事实来源）。

为什么要有这一层（P2）：
    当前报告的问题由「数据能算什么」反推（`decision.draft(intent, mounted)`），
    所以「问招聘、只有水果数据」会出一份水果报告，而且 binding=1.0、门禁全绿。

    修法：先由**意图**决定该谁出场，再由**数据**决定它能不能答。
    这一层需要一张「角色 → 能答什么 / 什么数据能答 / 什么情况不许开口」的表。

事实来源（不手写第二份）：
    1. `core/registry.py`           角色 id / 名字 / 职位 / 能力条目
    2. `rXX-*/prompt_profile.json`  业务域、动作、触发词（when）、所需输入
    3. `core/methods/`            方法 → 能力（needs）→ 产出（produces）
    4. 本文件 `ROLE_METHODS`       角色 → 方法 key（方法库是按业务域写的，需显式声明归属）

输出 `configs/experts.yaml`，由 `core/orchestrator.py` 读取。
`--check` 校验磁盘与事实来源是否漂移（CI 用）。

用法：
    python scripts/gen_experts.py
    python scripts/gen_experts.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "configs" / "experts.yaml"

# --------------------------------------------------------------------------- #
# 角色 → 方法 key（方法库按业务域写，归属关系只能显式声明一次）
# --------------------------------------------------------------------------- #
# 依据：core/methods/__init__.py 的 _reg() 与 generic/research/market/cheese 的 @method。
ROLE_METHODS: Dict[str, List[str]] = {
    "r01": [],                                   # 编排/决策，不做数据方法
    "r02": ["priority", "capacity"],             # 交付与产能
    "r03": [],                                   # 财务合规：靠角色技能，不产数据方法
    "r04": [],                                   # 独立评审：靠 artifact/criteria 门禁
    "r05": ["size", "growth", "demand", "concentration",
            "consistency", "coverage",],
                                                 # 研究：规模/格局/来源一致性 + 调味料族
    "r06": ["structure", "momentum", "trajectory", "contribution", "risk",
            "sample", "describe"],               # 分析：结构/节奏/轨迹/贡献
    "r07": ["review", "reviews", "priority"],    # 产品：需求与优先级
    "r08": [],                                   # MVP：不进报告（capability_graph blocked）
    "r09": [],                                   # 工程：不进报告
    "r10": [],                                   # 设计：不进报告
    "r11": ["content"],                          # 内容
    "r12": ["roi", "channel", "funnel"],         # 增长
    "r13": ["retention", "reviews", "sla"],      # 客成：留存/口碑/响应
    "r14": ["payment_mix"],                      # 交易
    "r15": ["economics", "transmission", "arbitrage", "breakeven", "unit_econ"],  # 供应链
    "r16": ["headcount"],                        # 人事：编制与人效
    "r17": [],                                   # 自动化：不进报告
    "r18": [],                                   # 数仓：数据工程，不产方法
    "r19": ["eval"],                             # 模型评估
    "r20": ["incidents", "capacity"],            # 稳定性
}

# 明确不答的域（写进卡片，编排器用它提前否决，避免「拿别的数据凑」）
ROLE_REFUSES: Dict[str, List[str]] = {
    "r16": ["价格行情", "供应链成本", "跨市价差"],
    "r15": ["招聘编制", "组织设计"],
    "r03": ["市场行情报价", "品类涨跌"],
    "r06": ["合同条款", "税务申报", "薪酬核算"],
    "r19": ["财务口径审计"],
    "r05": ["内部薪酬与编制"],
}

# 泛词：任何角色都会命中，不能用来判定业务域（否则「分析一下」20 个角色全出场）
GENERIC_TRIGGERS = {
    "分析", "看看", "如何", "怎么样", "情况", "问题", "数据", "指标", "报告",
    "对比", "变化", "拆分", "拆", "按", "各", "分布", "排名", "评估", "检查",
    "异常值", "缺失", "重复", "为什么", "原因", "归因", "贡献", "异动",
    "关注", "优化", "提升", "下降", "增长", "趋势", "走势", "下滑", "表现",
    "当前", "现在", "本期", "上期", "整体",
}

# --------------------------------------------------------------------------- #
# 业务域补充词（人给的「域」表述，不是角色动作词）
#
# prompt_profile.json 的动作触发词描述的是「某个技能什么时候用」，
# 而报告要判的是「这句话属于哪个业务域」。两者不同：
#   用户说「水果经营诊断」→ 没有任何动作触发词命中，但它显然属于「价格与经营」。
# 所以这里补一层业务域词，仍然只写一次（生成到 experts.yaml，不散落在代码里）。
# --------------------------------------------------------------------------- #
DOMAIN_TRIGGERS: Dict[str, List[str]] = {
    "r01": ["决策", "取舍", "该不该做", "可逆", "优先级", "拍板"],
    "r02": ["排期", "交付", "产能", "瓶颈", "节奏", "sprint"],
    "r03": ["财务", "合规", "税务", "合同", "审计", "红线", "资金", "发票税率"],
    "r04": ["评审", "验收", "证据链", "pass", "fail", "独立复核"],
    "r05": ["调研", "行业", "竞品", "市场规模", "赛道", "格局", "产业链", "政策"],
    "r06": ["经营诊断", "趋势", "波动", "贡献", "分布", "离散", "口径", "指标",
            "销量", "同比", "环比", "异常", "样本", "留存", "漏斗", "分群",
            "水果", "蔬菜", "肉禽", "蛋", "品类", "行情"],
    "r07": ["产品", "需求", "prd", "功能", "优先级", "用户故事", "backlog"],
    "r08": ["原型", "mvp", "落地页", "最小切片"],
    "r09": ["工程", "代码", "架构", "测试", "发布", "回滚"],
    "r10": ["设计", "视觉", "品牌", "排版", "logo", "配色"],
    "r11": ["文案", "内容", "选题", "长文", "小红书", "脚本"],
    "r12": ["增长", "获客", "投放", "渠道", "转化率", "留存", "roi", "拉新"],
    "r13": ["客户成功", "续约", "流失", "客诉", "健康分", "qbr", "voc"],
    "r14": ["订单", "支付", "退款", "履约", "交易", "购物车"],
    "r15": ["供应链", "采购", "供应商", "库存", "到店成本", "tco", "物流",
            "损耗", "加价率", "直采", "产地", "中间价", "采购价",
            "停采", "换源", "换供应商", "比价", "采购策略", "毛利", "提价"],
    "r16": ["招聘", "人事", "编制", "组织", "薪酬", "绩效", "考勤", "人效", "headcount"],
    "r17": ["自动化", "工作流", "集成", "webhook", "回调"],
    "r18": ["数仓", "数据管道", "etl", "指标口径", "埋点"],
    "r19": ["模型", "评测", "回归", "训练", "评分器", "a/b 显著性"],
    "r20": ["稳定性", "故障", "可用性", "sla", "备份", "恢复", "监控"],
}


def _profile(role_dir: Path) -> Dict[str, Any]:
    p = role_dir / "prompt_profile.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _triggers(profile: Dict[str, Any]) -> List[str]:
    """从 actions 的 when 里收触发词（去重、保序、短词在前）。

    只保留「能区分业务域」的词：像「分析 / 怎么样 / 如何 / 看看」这种
    任何角色都会命中的泛词一律剔除，否则 20 个角色会被同一句话同时命中。
    """
    out: List[str] = []
    for a in (profile.get("actions") or []):
        for w in (a.get("when") or []):
            w = str(w).strip()
            if not w or w in GENERIC_TRIGGERS or w in out:
                continue
            if len(w) < 2:
                continue
            out.append(w)
    return sorted(out, key=lambda x: (len(x), x))


def _labels(profile: Dict[str, Any]) -> List[str]:
    """动作标签本身就是「这个专家能干什么」的人话表述，是强信号。"""
    out: List[str] = []
    for a in (profile.get("actions") or []):
        lb = str(a.get("label") or "").strip()
        if lb and lb not in out:
            out.append(lb)
    return out


def _actions(profile: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for a in (profile.get("actions") or []):
        skill, action = str(a.get("skill") or ""), str(a.get("action") or "")
        if not skill:
            continue
        out.append({"skill": skill, "action": action,
                    "label": str(a.get("label") or f"{skill}/{action}")})
    return out


def _method_index() -> Dict[str, Dict[str, Any]]:
    from core import methods
    return {k: {"family": s.family, "needs": list(s.needs),
                "produces": s.produces, "priority": s.priority}
            for k, s in methods.REGISTRY.items()}


def build() -> Dict[str, Any]:
    from core import registry

    m_idx = _method_index()
    experts: Dict[str, Any] = {}
    for r in registry.ROLES:
        rid = r["id"]
        role_dir = ROOT / r["dir"]
        prof = _profile(role_dir)
        mkeys = [k for k in ROLE_METHODS.get(rid, []) if k in m_idx]
        needs = sorted({n for k in mkeys for n in m_idx[k]["needs"]})
        produces = [m_idx[k]["produces"] for k in mkeys if m_idx[k]["produces"]]
        dom_words = [w for w in DOMAIN_TRIGGERS.get(rid, []) if w not in GENERIC_TRIGGERS]
        experts[rid] = {
            "id": rid,
            "name": r["name"],
            "title": r["title"],
            "domain": str(prof.get("domain") or r["title"]),
            "domains": [str(c) for c in (r.get("capabilities") or [])][:8],
            "domain_triggers": dom_words,
            "triggers": _triggers(prof),
            "labels": _labels(prof),
            "actions": _actions(prof),
            "methods": mkeys,
            "needs": needs,
            "produces": produces,
            "inputs": list(r.get("inputs") or []),
            "outputs": list(r.get("outputs") or []),
            "refuses": ROLE_REFUSES.get(rid, []),
            "enters_report": bool(r.get("enters_report", True)),
            "output_form": "finding（带数字的判断 + refs）" if mkeys else "review/judgement",
        }
    return {
        "schema": "dsh.experts/v1",
        "generated_by": "scripts/gen_experts.py",
        "note": "由 core/registry.py + rXX/prompt_profile.json + core/methods 生成，勿手改",
        "roles": experts,
    }


def _yaml_dump(obj: Any, indent: int = 0) -> str:
    """极简 YAML 输出（只支持 dict/list/str/int/bool/None，避免引入 PyYAML 依赖）。

    键名与字符串一律双引号包裹，避免中文与 `:` 被误解析。
    """
    pad = "  " * indent
    lines: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f'{pad}"{k}":')
                lines.append(_yaml_dump(v, indent + 1))
            elif isinstance(v, (dict, list)):
                lines.append(f'{pad}"{k}": ' + ("{}" if isinstance(v, dict) else "[]"))
            else:
                lines.append(f'{pad}"{k}": {_scalar(v)}')
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                inner = _yaml_dump(v, indent + 1).splitlines()
                if inner:
                    lines.append(f"{pad}- " + inner[0].lstrip())
                    lines.extend(inner[1:])
                else:
                    lines.append(f"{pad}- " + ("{}" if isinstance(v, dict) else "[]"))
            else:
                lines.append(f"{pad}- {_scalar(v)}")
    return "\n".join(lines)


def _scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace('"', '\\"')
    return f'"{s}"'


def write(data: Dict[str, Any]) -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# 专家卡（由 scripts/gen_experts.py 生成，勿手改）\n"
                   + _yaml_dump(data) + "\n", encoding="utf-8")
    return OUT


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gen_experts")
    ap.add_argument("--check", action="store_true", help="只校验磁盘与事实来源是否漂移")
    a = ap.parse_args(argv)
    data = build()
    if a.check:
        if not OUT.exists():
            print(f"[FAIL] 缺少 {OUT.relative_to(ROOT)}，先跑 python scripts/gen_experts.py")
            return 1
        disk = OUT.read_text(encoding="utf-8")
        want = ("# 专家卡（由 scripts/gen_experts.py 生成，勿手改）\n"
                + _yaml_dump(data) + "\n")
        if disk != want:
            print(f"[FAIL] {OUT.relative_to(ROOT)} 与事实来源漂移，重跑 gen_experts.py")
            return 1
        print(f"[PASS] expert cards 无漂移（{len(data['roles'])} 角色）")
        return 0
    p = write(data)
    print(f"wrote {p.relative_to(ROOT)}（{len(data['roles'])} 角色）")
    for rid, e in data["roles"].items():
        print(f"  {rid} {e['name']:<4} methods={len(e['methods'])} "
              f"needs={len(e['needs'])} triggers={len(e['triggers'])} "
              f"enters={e['enters_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
