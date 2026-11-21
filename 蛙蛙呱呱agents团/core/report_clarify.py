# -*- coding: utf-8 -*-
"""core.report_clarify —— 接任务先对齐意图，再拆卡（2026-11-20 起）。

问题出在哪（2026-11-20 个护测试复盘）：
- `brief` 的卡里写着「你要判断什么（自己定，不要等我给）」，
  `brief.json` 的 what_to_research 直接写「系统不预设问题清单」；
- 于是 6 张卡内容重叠、没人负责用户真正问的那几问；
- 用户也没机会在开工前说「我要的是品牌清单和爆品，不是宏观大盘」。

本模块只做第一段：把一句话变成一张**可审的澄清卡**——
我理解成什么、我准备答哪几问、我默认假设了什么、哪 3–5 件事需要你拍。
不拆卡、不发卡；拆卡在 `core.report_dispatch`。

产物：`<项目>/clarify.json` + `<项目>/clarify.md`
确认：人改 json（或直接接受默认）后 `report clarify --dir <项目> --confirm`
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "dsh.report.clarify/v1"

# 问题类型 → 默认主责角色（只作初值，plan 阶段还会按关键词与能力重排）
TYPE_HINT = {
    "清单型": ["r05", "r06"],
    "量化型": ["r06", "r05"],
    "排序型": ["r05", "r06"],
    "价格型": ["r14", "r05"],
    "机制型": ["r15", "r05"],
    "时间型": ["r07", "r12"],
    "增长型": ["r12", "r07"],
    "归因型": ["r06", "r05"],
    "判断型": ["r05"],
}

# 关键词 → 角色（用于 plan 阶段加权；不改角色定义）
KEYWORD_ROLES = {
    "品类": ["r05"], "品牌": ["r05"], "竞品": ["r05"], "市场": ["r05"],
    "行业": ["r05"], "格局": ["r05"], "份额": ["r05"],
    "价格": ["r14"], "定价": ["r14"], "渠道": ["r14"], "电商": ["r14"],
    "平台": ["r14"], "客单": ["r14"],
    "调拨": ["r15"], "供应链": ["r15"], "库存": ["r15"], "物流": ["r15"],
    "产地": ["r15"], "工厂": ["r15"], "仓": ["r15"], "周转": ["r15"],
    "营销": ["r12"], "投放": ["r12"], "增长": ["r12"], "复购": ["r12"],
    "内容": ["r12"], "私域": ["r12"],
    "周期": ["r07"], "新品": ["r07"], "产品": ["r07"], "试销": ["r07"],
    "上市": ["r07"], "迭代": ["r07"],
    "销售": ["r06"], "数据": ["r06"], "增速": ["r06"], "规模": ["r06"],
    "测算": ["r06"], "对比": ["r06"],
    "成本": ["r03"], "毛利": ["r03"], "预算": ["r03"], "财务": ["r03"],
    "组织": ["r16"], "招聘": ["r16"], "人效": ["r16"],
}

# 问句里出现这些，判定问题类型（顺序即优先级）
TYPE_PATTERNS = [
    ("排序型", ("卖得好", "畅销", "最好", "排名", "前几", "头部", "爆")),
    ("价格型", ("价格", "定价", "多少钱", "价位", "价格带")),
    ("机制型", ("调拨", "怎么走", "机制", "流程", "怎么运作", "链路")),
    ("时间型", ("周期", "多久", "几个月", "多久能", "节奏")),
    ("增长型", ("如何", "怎么帮", "怎么提高", "提升", "打法", "营销")),
    ("量化型", ("多少", "规模", "占比", "增速", "增长率", "亿", "%")),
    ("清单型", ("有哪些", "哪些", "清单", "包括", "都有什么")),
    ("归因型", ("为什么", "原因", "导致", "驱动")),
]

# 拆句：中文标点；问号保留语义，但不去重问号
_SPLIT = re.compile(r"[；;。！!？?\n]+|(?<=[，,])\s*以及|以及|还有就是")
_SEG_SEP = re.compile(r"[，,]")

# 指令性前缀不是问题：`Use Skill: wawaguagua-agents 调用专家团 …` 这类不该进问句表
_NOISE = re.compile(
    r"(use\s*skill\s*[:：]\s*[\w\-.]+|调用专家团|调用专家|给我产出报告|"
    r"给我出个报告|产出报告)", re.I)
# 连接词开头的短片段（"请根据报告结论"）不是独立问题
_CONNECTIVE = re.compile(r"^(请|那么|以及|另外|但|而且|同时|然后)")

DEFAULT_ASSUMPTIONS = [
    ("A1", "数据口径：只用公开可核来源；查不到写进缺口，不把推断写成实测", "高"),
    ("A2", "区域口径：全国与目标省/市分开写，市县级数据缺失就明说", "高"),
    ("A3", "时间窗：默认最近一个完整年度，跨年对比写清基期", "中"),
    ("A4", "交付形态：HTML + PDF，正文每节带边界与证伪条件", "中"),
]

DEFAULT_CONFIRM = [
    ("C1", "这份报告给谁看、要拿它做什么决定？", "业务负责人做选品/试销决策"),
    ("C2", "上面 Q1..Qn 里，哪几问是必须答的？", "全部标记为 must 的都必答"),
    ("C3", "拿不到的数据怎么办：写缺口，还是允许用代理指标推断？", "写缺口；推断必须标注"),
    ("C4", "结论要落到什么颗粒度？", "品类 + 品牌；不到 SKU 级"),
]

# 覆盖维度：问得全不全，用这六维检查，而不是无限追问。
# 2026-11-20 的个护 10 问里，「时间」和「边界」两维是空的——报告因此说不出
# "这个结论在什么条件下不成立"。
COVERAGE_DIMS = [
    ("规模", ("多少", "规模", "亿元", "占比", "增速", "%", "亿")),
    ("结构", ("有哪些", "构成", "细分", "品类", "结构")),
    ("主体", ("品牌", "玩家", "公司", "谁", "渠道", "经销商")),
    ("时间", ("周期", "多久", "同比", "趋势", "几周", "几个月", "期")),
    ("机制", ("怎么", "为什么", "如何", "机制", "驱动", "原因")),
    ("边界", ("在什么条件", "边界", "不成立", "反例", "例外", "风险", "前提")),
]


def coverage_of(asks: List[Dict[str, Any]]) -> Dict[str, Any]:
    got: Dict[str, List[str]] = {name: [] for name, _ in COVERAGE_DIMS}
    for a in asks:
        t = str(a.get("text") or "")
        for name, keys in COVERAGE_DIMS:
            if any(k in t for k in keys):
                got[name].append(a["id"])
    return {"covered": {k: v for k, v in got.items() if v},
            "missing": [k for k, v in got.items() if not v]} 


def tier_of(asks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """必答 / 支撑 / 探索：节数由"判断"决定，不由问数决定。

    must  → 正文节（一问一节或合并）
    support → 并进必答那节（口径/对照），不单独成节
    explore → 进「延伸发现」固定节
    """
    out = []
    for a in asks:
        t = str(a.get("text") or "")
        tier = "must" if a.get("must") else "support"
        if any(k in t for k in ("为什么", "反常", "意外", "没想", "顺便")):
            tier = "explore"
        out.append({**a, "tier": tier})
    return out


def _segments(intent: str) -> List[str]:
    intent = _NOISE.sub(" ", intent or "")
    segs: List[str] = []
    for chunk in _SPLIT.split(intent):
        for s in _SEG_SEP.split(chunk or ""):
            s = s.strip(" 　，,。;；")
            if len(s) >= 6:
                segs.append(s)
    # 去掉被更长句包含的碎片（用户常重复问同一件事）
    out: List[str] = []
    for s in segs:
        if any(s != o and (s in o or o in s) and len(s) < len(o) for o in segs):
            continue
        if (_CONNECTIVE.match(s) and len(s) < 14
                and not re.search(r"哪些|什么|怎么|为什么|如何|多少|吗|呢", s)):
            continue
        if s not in out:
            out.append(s)
    return out[:10]


def classify(text: str) -> str:
    for name, keys in TYPE_PATTERNS:
        if any(k in text for k in keys):
            return name
    return "判断型"


def _region(intent: str) -> str:
    for r in ("内蒙古", "呼和浩特", "包头", "鄂尔多斯", "赤峰", "全国"):
        if r in (intent or ""):
            return r
    return "未指定"


def draft(intent: str) -> Dict[str, Any]:
    """一句话 → 澄清卡（不拆卡、不发卡）。"""
    asks = []
    for i, seg in enumerate(_segments(intent), 1):
        typ = classify(seg)
        asks.append({
            "id": f"Q{i}", "text": seg, "type": typ,
            "must": i <= 5, "default_owner": (TYPE_HINT.get(typ) or ["r05"])[0],
        })
    if not asks:
        asks = [{"id": "Q1", "text": intent.strip() or "（意图为空）",
                 "type": "判断型", "must": True, "default_owner": "r05"}]
    asks = tier_of(asks)
    cov = coverage_of(asks)
    return {
        "schema": SCHEMA,
        "intent": intent.strip(),
        "status": "draft",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "understanding": {
            "goal": "把问题答成一份可下发、可回溯的报告（不是写一篇通稿）",
            "audience": "业务负责人",
            "deliverable": "HTML + PDF",
            "region": _region(intent),
            "scope": [a["text"] for a in asks],
            "out_of_scope": ["问题里没出现的品类/区域，不主动扩面"],
        },
        "asks": asks,
        # 覆盖维度：缺哪一维，报告就会缺一类判断（不是缺一节）
        "coverage": cov,
        "assumptions": [{"id": i, "text": t, "risk": r}
                        for i, t, r in DEFAULT_ASSUMPTIONS],
        "confirm": [{"id": i, "ask": q, "default": d, "answer": None}
                    for i, q, d in DEFAULT_CONFIRM],
    }


def render_md(c: Dict[str, Any]) -> str:
    L = [f"# 澄清卡：{c.get('intent', '')}", ""]
    u = c.get("understanding") or {}
    L += ["## 我理解成什么", "",
          f"- 目标：{u.get('goal', '')}",
          f"- 受众：{u.get('audience', '')}",
          f"- 区域：{u.get('region', '')}",
          f"- 交付：{u.get('deliverable', '')}",
          f"- 不做：{'；'.join(u.get('out_of_scope') or [])}", ""]
    L += ["## 我准备答哪几问（tier 决定去哪：must→正文 / support→并进正文 / explore→延伸发现）", "",
          "| # | 问题 | 类型 | tier | 必答 | 默认主责 |", "|---|---|---|---|---|---|"]
    for a in c.get("asks") or []:
        L.append(f"| {a['id']} | {a['text']} | {a['type']} | {a.get('tier', '-')} | "
                 f"{'是' if a.get('must') else '否'} | {a.get('default_owner')} |")
    cov = c.get("coverage") or {}
    if cov:
        L += ["", "## 覆盖检查（缺的维度就是报告会缺的判断）", "",
              "- 已覆盖：" + ("；".join(f"{k}→{'、'.join(v)}"
                                       for k, v in (cov.get("covered") or {}).items()) or "无"),
              "- **缺**：" + ("、".join(cov.get("missing") or []) or "无")]
        if cov.get("missing"):
            L.append("  - 缺的维度要么补问句，要么在 confirm 里明说「这维不做」")
    L += ["", "## 我默认假设了什么（不同意就改 assumptions）", ""]
    for a in c.get("assumptions") or []:
        L.append(f"- **{a['id']}**（风险 {a['risk']}）：{a['text']}")
    L += ["", "## 需要你拍的 3–5 件事（改 confirm[].answer）", ""]
    for x in c.get("confirm") or []:
        L.append(f"- **{x['id']}** {x['ask']}\n  - 默认：{x['default']}")
    L += ["", "---", "",
          "改完 `clarify.json` 后跑：`python guagua.py report clarify --dir <项目> --confirm`；",
          "然后 `report brief --dir <项目> --plan` 出「问题 → 角色」映射表。"]
    return "\n".join(L)


def write(intent: str, out_dir: str, force: bool = False) -> Dict[str, Any]:
    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    p = base / "clarify.json"
    if p.exists() and not force:
        return {"ok": False, "error": f"{p} 已存在；要重写加 --force",
                "hint": "已有澄清卡时，直接用 --confirm 确认，或 --force 重出"}
    c = draft(intent)
    p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    (base / "clarify.md").write_text(render_md(c), encoding="utf-8")
    return {"ok": True, "clarify": str(p), "asks": len(c["asks"]),
            "must": sum(1 for a in c["asks"] if a["must"]),
            "confirm": [{"id": x["id"], "ask": x["ask"], "default": x["default"]}
                        for x in c["confirm"]]}


def load(base: str) -> Dict[str, Any]:
    p = Path(base) / "clarify.json"
    if not p.is_file():
        raise FileNotFoundError(f"没有 {p}：先跑 `report clarify --intent … --out {base}`")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def confirm(base: str, by: str = "user", user_said: str = "") -> Dict[str, Any]:
    """把澄清卡标记为 confirmed（2026-11-22 起：必须有用户原话）。

    agent 自己确认、没有用户原话，一律拒；这样「R01 问、用户答」才是默认。
    """
    c = load(base)
    if str(by).lower() != "user":
        return {"ok": False, "error": "澄清卡只能由 user 确认；agent 不能代确认"}
    if len(str(user_said or "").strip()) < 6:
        return {"ok": False,
                "error": "缺用户原话：--user-said \"用户对目标的一句确认\""}
    c["status"] = "confirmed"
    c["confirmed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    c["confirmed_by"] = "user"
    c["user_said"] = str(user_said).strip()
    p = Path(base) / "clarify.json"
    p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    unanswered = [x["id"] for x in c.get("confirm") or []
                  if not str(x.get("answer") or "").strip()]
    return {"ok": True, "clarify": str(p), "status": "confirmed",
            "unanswered_confirm": unanswered,
            "asks": len(c.get("asks") or []),
            "must": sum(1 for a in (c.get("asks") or []) if a.get("must"))}


def answer(base: str, pairs: List[str], by: str = "user",
           user_said: str = "") -> Dict[str, Any]:
    """会话里问完，把「C1=答案」交回来；写完即确认。

    这样 R01 在对话里问、用户在对话里答，答案仍然落进 clarify.json，
    后面验收按它对齐——不是"问完就忘了"。
    """
    c = load(base)
    known = {x["id"]: x for x in c.get("confirm") or []}
    bad = []
    for raw in pairs:
        if "=" not in raw:
            bad.append(f"{raw}（应为 C1=答案）")
            continue
        k, v = raw.split("=", 1)
        k = k.strip().upper()
        if k not in known:
            bad.append(f"{k} 不在澄清卡里（可选 {', '.join(known)}）")
            continue
        known[k]["answer"] = v.strip()
        known[k]["answered_by"] = "user" if str(by).lower() == "user" else "agent"
    if bad:
        return {"ok": False, "error": "答案格式不对", "problems": bad}
    p = Path(base) / "clarify.json"
    p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    res = confirm(base, by=by, user_said=user_said)
    res["answered"] = [k for k, v in known.items()
                       if str(v.get("answer") or "").strip()]
    return res
