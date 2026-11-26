# -*- coding: utf-8 -*-
"""expert_brief v2：卡是信封，brief 是内容。

为什么要有它
------------
任务卡只回答「做什么、交什么」；专家brief 回答「先问什么、哪些结论不能下、
证据到什么程度算够」。两者不能是两份独立产物，否则两边都写 acceptance，
角色不知道听谁的。所以对外只有一个 `CardBundle`：卡管 owner/deps/inputs/
outputs/non_goals，brief 管 question/must_answer/standards/…/acceptance_checks。

七层模型（每层最少条数见 `LAYER_MIN`）
-------------------------------------
    L0 决策语境  L1 定义与口径  L2 结构分解  L3 机制与归因
    L4 判断情景  L5 行动可逆  L6 反证不确定

生成约束
--------
* 不写死行业：只看角色（configs/rNN.yaml）与卡片，不写任何品类/地名/价格；
* 不写事实数字：brief 只写「怎么想、怎么验」，事实必须来自本次证据；
* 每条必答过五道门槛：answerable_by / evidence / owner / failure_impact / check；
* 单卡 must_answer 上限 18 条，超出进 parking_lot，不塞进卡。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

BRIEF_SCHEMA = "dsh.expert_brief/v2"
BRIEF_VERSION = "v2"
MAX_MUST_ANSWER = 18

LAYER_MIN = {"L0": 2, "L1": 2, "L2": 3, "L3": 2, "L4": 2, "L5": 2, "L6": 2}
LAYER_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]
LAYER_TITLE = {
    "L0": "决策语境", "L1": "定义与口径", "L2": "结构分解", "L3": "机制与归因",
    "L4": "判断与情景", "L5": "行动与可逆", "L6": "反证与不确定",
}

#: 任务类型 → 必答层（评审型额外加一条结论复核）
TASK_LAYERS: Dict[str, List[str]] = {
    "诊断型": ["L0", "L1", "L2", "L3", "L4", "L6"],
    "预测型": ["L0", "L1", "L2", "L4", "L5", "L6"],
    "决策型": list(LAYER_ORDER),
    "评审型": ["L0", "L1", "L6"],
    # 探源型：只问「要什么、去哪采、能不能采到」，不要求 L3–L6 的因果与行动
    "探源型": ["L0", "L1", "L2"],
}

ANSWERABLE = ("data", "source", "user", "assumption")


def _q(qid: str, ask: str, answerable: str, evidence: str,
       failure_impact: str, check: str, owner: str) -> Dict[str, str]:
    return {"id": qid, "ask": ask, "answerable_by": answerable,
            "evidence": evidence, "owner": owner,
            "failure_impact": failure_impact, "check": check}


def _templates(role: str) -> Dict[str, List[Dict[str, str]]]:
    """七层问题模板。只描述判断方式，不含任何行业事实。"""
    return {
        "L0": [
            _q("L0.1", "这份判断支持谁的哪个决策？判断错了，谁承担什么损失？",
               "user", "决策人、用途、错误代价（各一句）",
               "不知道为谁决策，会把精力花在错的指标上", "brief 头部写明决策人与错误代价",
               "user"),
            _q("L0.2", "成功的标准是什么？做到什么程度算可用，什么程度算不合格？",
               "user", "可判定的成功/失败门槛",
               "没有成功标准，验收只能靠感觉", "acceptance_checks 中有可判定门槛",
               "user"),
        ],
        "L1": [
            _q("L1.1", "关键指标的定义、分子分母、统计范围与时间窗分别是什么？",
               "data", "指标口径说明（指标卡或字段注释）",
               "口径不明会把不同的东西相加", "输出标注口径、范围与时间窗", role),
            _q("L1.2", "数据完整性如何：缺失、重复、迟到、口径变更各自怎么处理？",
               "data", "缺失率、重复率、口径变更记录",
               "带病数据会放大结论误差", "给出缺失/重复统计与处理方式", role),
        ],
        "L2": [
            _q("L2.1", "总量变化由量、价、结构哪几条线驱动？各自贡献多少？",
               "data", "量/价/结构三线切片",
               "把涨价当成增长，会误判经营健康度", "三线切片齐全且贡献可加总", role),
            _q("L2.2", "分渠道/客群/区域/时间的差异有多大？整体平均掩盖了什么？",
               "data", "至少两个维度的切片",
               "平均值会掩盖局部恶化", "至少两个维度切片，且与结论一致", role),
            _q("L2.3", "分布是集中还是长尾？是否由少数主体主导？",
               "data", "分布或集中度指标",
               "少数样本主导时会高估普遍性", "给出集中度或分布形态", role),
            _q("L2.4", "与可比基期或可比对象相比，差异是普遍还是局部？",
               "data", "基期与对照组切片",
               "没有对照就无法区分趋势与噪声", "给出基期/对照对比", role),
        ],
        "L3": [
            _q("L3.1", "最可能的驱动因素有哪些？每个因素对应什么证据？",
               "data", "因素→证据对照表",
               "只列因素不给证据，等于猜", "每个因素都有证据指向", role),
            _q("L3.2", "每个归因排除了哪个替代解释？反事实是什么？",
               "assumption", "替代解释与排除理由",
               "把相关当因果，行动会打空", "至少排除一个替代解释", role),
            _q("L3.3", "有没有口径变化、一次性事件或选择偏差被误当成机制？",
               "data", "事件与口径变更记录",
               "一次性事件会被当成长期趋势", "逐项排查并写明结论", role),
        ],
        "L4": [
            _q("L4.1", "这是一次性波动还是结构性变化？依据是什么？",
               "data", "剔除异常后的基线复算",
               "把波动当结构，会过度反应", "给出剔除异常后的基线", role),
            _q("L4.2", "基准/乐观/悲观三种情景的假设与结果区间是什么？",
               "assumption", "情景假设与区间",
               "单点预测无法支撑决策", "三种情景都有假设与区间", role),
            _q("L4.3", "结论对哪个假设最敏感？翻转点在哪里？",
               "assumption", "敏感性分析",
               "不知道翻转点就无法设止损", "指出最敏感假设与翻转条件", role),
        ],
        "L5": [
            _q("L5.1", "基于结论应该做什么、明确不做什么？",
               "assumption", "行动项与不做清单",
               "只给结论不给动作，落不了地", "行动项与不做清单非空", role),
            _q("L5.2", "用哪三个先行指标监测？什么条件下止损或推翻结论？",
               "data", "监测指标与阈值",
               "没有监测就无法及时纠偏", "三个先行指标 + 推翻条件", role),
            _q("L5.3", "这个行动可逆吗？最坏情况与回退方案是什么？",
               "assumption", "可逆性与回退路径",
               "不可逆动作没有回退会放大损失", "写明可逆性与回退方案", role),
        ],
        "L6": [
            _q("L6.1", "最强的反方观点是什么？它需要什么证据才能成立？",
               "data", "反方观点与触发证据",
               "只听一方会漏掉致命反例", "反方观点与触发证据非空", role),
            _q("L6.2", "最大的数据缺口与不确定性是什么？置信度多高、为什么？",
               "data", "缺口清单与置信度理由",
               "隐藏不确定性会误导决策", "缺口清单 + 置信度理由", role),
        ],
    }


def infer_task_type(card: Dict[str, Any]) -> str:
    """卡片给什么类型就用什么；没给则按措辞推断，默认诊断型。"""
    raw = str(card.get("task_type") or "").strip()
    if raw in TASK_LAYERS:
        return raw
    text = " ".join(str(card.get(k) or "") for k in
                    ("title", "goal", "question", "intent"))
    if any(w in text for w in ("评审", "审查", "复核", "review")):
        return "评审型"
    if any(w in text for w in ("预测", "预估", "forecast", "情景")):
        return "预测型"
    if any(w in text for w in ("决策", "是否", "选哪个", "要不要", "方案")):
        return "决策型"
    return "诊断型"


def _role_profile(role: str) -> Dict[str, Any]:
    """读团内角色通用知识（属工具资产）。缺失时返回空，不阻断。"""
    try:
        import yaml
        p = Path(__file__).resolve().parents[2] / "configs" / f"{role}.yaml"
        if not p.is_file():
            return {}
        with open(p, encoding="utf-8-sig") as f:
            doc = yaml.safe_load(f) or {}
        return doc if isinstance(doc, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _role_lens(role: str, cfg: Dict[str, Any]) -> str:
    title = str(cfg.get("role_title") or "专家")
    duties = cfg.get("core_duties") or []
    first = str(duties[0]) if duties else "先判断输入能不能用来做决策"
    return f"{title}，不是执行员：{first}。"


def _dedupe(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    for x in items:
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out


def _knowledge_refs(project: Any) -> List[str]:
    """只引用项目知识的框架快照，不读内容、不带事实。"""
    if project is None:
        return []
    root = getattr(project, "root", None)
    snap = getattr(project, "knowledge_snapshot", None)
    if snap:
        return [str(snap)]
    if root is not None:
        kdir = Path(root) / "knowledge"
        if kdir.is_dir() and any(kdir.iterdir()):
            return ["knowledge/（项目框架快照，事实须来自本次证据）"]
    return []


def _experience_refs(card: Dict[str, Any], role: str,
                     project: Any) -> Dict[str, Any]:
    """只记「这次用了哪几张卡」，不搬卡片正文（正文属怎么想，事实仍须来自证据）。"""
    refs: Dict[str, Any] = {"tier": "L0", "ids": [], "loaded": 0, "errors": []}
    root = str(getattr(project, "root", "") or "") if project is not None else ""
    if not root:
        return refs
    try:
        from shared import experience_cards  # noqa: PLC0415
        q = " ".join(str(card.get(k) or "") for k in
                     ("title", "goal", "question", "intent"))
        res = experience_cards.retrieve(role, q, root, limit=3)
        refs.update({"tier": res["tier"], "loaded": res["loaded"],
                     "ids": [str(c.get("id")) for c in res["cards"]],
                     "errors": res["errors"][:3],
                     "conflicts": len(res.get("conflicts") or [])})
    except Exception as exc:  # noqa: BLE001  经验卡不可用不影响 brief
        refs["errors"] = [f"experience_cards: {exc}"]
    return refs


def build_brief(card: Dict[str, Any], role: str, project: Any = None) -> Dict[str, Any]:
    """按七层模型生成 brief。输入只看 card + 角色通用配置 + 项目元数据。"""
    cfg = _role_profile(role)
    task_type = infer_task_type(card)
    layers = TASK_LAYERS[task_type]
    templates = _templates(role)

    must: List[Dict[str, str]] = []
    for layer in layers:
        must.extend(templates.get(layer, []))
    # 评审型：结论复核不是问题层，挂在验收上更合适
    if task_type == "评审型":
        must.append(_q("R1", "被评审对象引用的数字与来源能否复算？",
                       "data", "逐条复算记录",
                       "引用错数会让整份评审失效", "至少抽样复算引用数字", role))

    parking: List[Dict[str, str]] = []
    # 超上限时先削「有富余」的层（如 L2 有 4 条、下限 3），保证每层都够数，
    # 被削掉的问题进 parking_lot，不丢。
    while len(must) > MAX_MUST_ANSWER:
        drop_at = None
        for layer in reversed(LAYER_ORDER):
            idxs = [i for i, m in enumerate(must)
                    if str(m.get("id", "")).split(".")[0] == layer]
            if len(idxs) > LAYER_MIN.get(layer, 0):
                drop_at = idxs[-1]
                break
        if drop_at is None:
            break
        parking.insert(0, must.pop(drop_at))

    skills = [str(s) for s in (card.get("skills") or [])][:6]
    method_plan = [{"skill": s, "rule": "按该技能口径执行，切片见 must_answer"}
                   for s in skills]

    question = str(card.get("question") or card.get("goal")
                   or card.get("intent") or card.get("title") or "")
    task_id = str(card.get("task_id") or card.get("id") or "")

    standards = _dedupe([
        "先口径、后趋势；口径不清不下结论",
        "异常必须用第二个独立口径互证，禁止单指标判定",
        "证据不足时只列候选，不写因果",
        "结论必须可复算，平均值不得掩盖结构分化",
    ] + [str(x) for x in (cfg.get("key_principles") or [])])[:8]

    anti_patterns = _dedupe([
        "把一次性事件当成趋势",
        "用总量增长掩盖结构恶化",
        "只看同比、忽略环比拐点",
        "把相关当因果",
        "用全量平均掩盖分组分化",
        "只描述异常、不解释异常",
    ])

    brief: Dict[str, Any] = {
        "schema": BRIEF_SCHEMA,
        "version": BRIEF_VERSION,
        "brief_id": f"{task_id}:{role}" if task_id else role,
        "role": role,
        "task_type": task_type,
        "role_lens": _role_lens(role, cfg),
        "question": question,
        "must_answer": must,
        "parking_lot": parking,
        "standards": standards,
        "anti_patterns": anti_patterns,
        "evidence_rules": [
            "每个结论至少一个数据切片（维度 + 时间 + 口径）",
            "关键异常需两个独立口径互证",
            "外部因素需来源与日期",
            "归因结论至少排除一个替代解释",
        ],
        "output_contract": [
            "一页结论（不超过三条）",
            "证据清单（可复算）",
            "反证与分歧",
            "置信度（高/中/低 + 理由）",
            "行动项与监测指标",
        ],
        "method_plan": method_plan,
        "acceptance_checks": [
            f"must_answer 覆盖 {len(must)}/{len(must)}",
            "claims 证据绑定完整",
            "反证与分歧非空",
            "关键数值重跑一致",
            "未越过 non_goals",
        ],
        "non_goals": [str(x) for x in (card.get("non_goals") or [])],
        "knowledge_refs": _knowledge_refs(project),
        "experience_refs": _experience_refs(card, role, project),
    }
    return brief


_DIGIT_RUN = re.compile(r"\d{4,}")
_MONEY = re.compile(r"[¥$€]|\d+\s*(元|美元|欧元|日元)")


def _texts(brief: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("question", "role_lens"):
        if brief.get(key):
            out.append(str(brief[key]))
    for key in ("standards", "anti_patterns", "evidence_rules",
                "output_contract", "acceptance_checks"):
        out.extend(str(x) for x in (brief.get(key) or []))
    for item in (brief.get("must_answer") or []) + (brief.get("parking_lot") or []):
        for k in ("ask", "evidence", "failure_impact", "check"):
            if item.get(k):
                out.append(str(item[k]))
    return out


def validate_brief(brief: Dict[str, Any], task_type: Optional[str] = None) -> List[str]:
    """校验 brief 是否满足 v2 契约。返回问题清单（空=通过）。"""
    problems: List[str] = []
    if not isinstance(brief, dict):
        return ["brief 不是对象"]
    if brief.get("schema") != BRIEF_SCHEMA:
        problems.append(f"schema 必须是 {BRIEF_SCHEMA}")
    if brief.get("version") != BRIEF_VERSION:
        problems.append(f"version 必须是 {BRIEF_VERSION}")

    task_type = task_type or str(brief.get("task_type") or "诊断型")
    if task_type not in TASK_LAYERS:
        problems.append(f"未知任务类型：{task_type}")

    must = brief.get("must_answer") or []
    if not isinstance(must, list) or not must:
        problems.append("must_answer 为空")
        must = []
    if len(must) > MAX_MUST_ANSWER:
        problems.append(f"must_answer {len(must)} 条，超过上限 {MAX_MUST_ANSWER}")

    required_layers = TASK_LAYERS.get(task_type, [])
    have_layers = {str(m.get("id", "")).split(".")[0] for m in must}
    for layer in required_layers:
        if layer not in have_layers:
            problems.append(f"缺必答层 {layer} {LAYER_TITLE[layer]}")
        else:
            n = sum(1 for m in must
                    if str(m.get("id", "")).split(".")[0] == layer)
            if n < LAYER_MIN[layer]:
                problems.append(
                    f"{layer} 只有 {n} 条，低于最少 {LAYER_MIN[layer]} 条")

    seen_ids, seen_asks = set(), set()
    for i, m in enumerate(must, 1):
        if not isinstance(m, dict):
            problems.append(f"must_answer[{i}] 不是对象")
            continue
        qid = str(m.get("id") or "").strip()
        if not qid:
            problems.append(f"must_answer[{i}] 缺 id")
        elif qid in seen_ids:
            problems.append(f"must_answer id 重复：{qid}")
        seen_ids.add(qid)
        ask = str(m.get("ask") or "").strip()
        if not ask:
            problems.append(f"{qid or i} 缺 ask")
        elif ask in seen_asks:
            problems.append(f"问题重复（跨层重复应合并）：{ask}")
        seen_asks.add(ask)
        if m.get("answerable_by") not in ANSWERABLE:
            problems.append(f"{qid} answerable_by 必须是 {'/'.join(ANSWERABLE)}")
        for k in ("evidence", "owner", "failure_impact", "check"):
            if not str(m.get(k) or "").strip():
                problems.append(f"{qid} 缺 {k}")

    if len(brief.get("anti_patterns") or []) < 3:
        problems.append("anti_patterns 少于 3 条")
    if not brief.get("acceptance_checks"):
        problems.append("acceptance_checks 为空")

    # 经验只留引用（哪几张卡），不留正文：正文放 brief 就等于拿旧结论顶本期证据
    if "experience_refs" in brief:
        refs = brief.get("experience_refs")
        if not isinstance(refs, dict):
            problems.append("experience_refs 必须是对象")
        else:
            if str(refs.get("tier") or "") not in ("L0", "L1", "L2"):
                problems.append("experience_refs.tier 必须是 L0/L1/L2")
            ids = refs.get("ids")
            if not isinstance(ids, list):
                problems.append("experience_refs.ids 必须是列表")
            elif refs.get("tier") != "L0" and not ids:
                problems.append("experience_refs 标了 L1/L2 却没有卡 id")
    for leak in ("wrong_once", "do_instead"):
        if brief.get(leak):
            problems.append(f"brief 不得内联经验卡正文（{leak}）")

    # brief 不允许出现事实数字 / 价格 / 政策条款
    for text in _texts(brief):
        if _DIGIT_RUN.search(text):
            problems.append(f"brief 含四位以上数字（事实须来自证据）：{text[:30]}")
            break
    for text in _texts(brief):
        if _MONEY.search(text):
            problems.append(f"brief 含价格/金额：{text[:30]}")
            break
    return problems


def validate_bundle(card: Dict[str, Any], brief: Dict[str, Any]) -> List[str]:
    """卡与 brief 的权责校验：验收只有一处，版本必须一致。"""
    problems: List[str] = []
    if card.get("acceptance"):
        problems.append("卡里不得写 acceptance 明细（只允许 brief_ref）")
    if not str(card.get("brief_ref") or "").strip():
        problems.append("卡缺 brief_ref")
    cv = str(card.get("brief_version") or "")
    if cv != str(brief.get("version") or ""):
        problems.append(
            f"brief_version 不一致：卡={cv or '空'} brief={brief.get('version')}")
    for key in ("question", "must_answer", "standards"):
        if card.get(key):
            problems.append(f"卡里出现 brief 字段 {key}（brief 不得被卡覆盖）")
    return problems


def write_brief(brief: Dict[str, Any], project: Any, task_id: str) -> str:
    """把 brief 落盘到 `<PROJECT_ROOT>/briefs/<task_id>.yaml`，返回相对路径。"""
    import yaml
    root = Path(project.root)
    target = root / "briefs" / f"{task_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(brief, allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    return target.relative_to(root).as_posix()


def _scope(project: Any) -> Dict[str, Any]:
    if project is None:
        return {}
    return {"project_root": str(getattr(project, "root", project)),
            "industry": getattr(project, "industry", None),
            "snapshot": getattr(project, "knowledge_snapshot", None)}


def issue_bundle(card_dir: Path | str, role: str, task_id: str, question: str,
                 project: Any = None, task_type: Optional[str] = None,
                 skills: Optional[List[str]] = None,
                 non_goals: Optional[List[str]] = None) -> Dict[str, Any]:
    """生成 `CardBundle`（卡信封 + brief）写到 card_dir/bundle.json。

    卡只留 owner/deps/inputs/outputs/non_goals/brief_ref/brief_version；
    验收只在 brief 里。给了项目根（含 project.yaml）时 brief 额外落
    `<PROJECT_ROOT>/briefs/<task_id>.yaml`，卡里存相对引用。
    """
    d = Path(card_dir)
    d.mkdir(parents=True, exist_ok=True)
    card = {"task_id": task_id, "owner": role, "title": f"{role} 工单",
            "goal": question, "question": question, "task_type": task_type,
            "skills": skills or [], "non_goals": non_goals or []}
    eb = build_brief(card, role, project)

    brief_ref = f"cards/{d.name}/bundle.json#brief"
    proj_root = Path(getattr(project, "root", project)) if project is not None else None
    if proj_root is not None and (proj_root / "project.yaml").is_file():
        brief_ref = write_brief(eb, project, task_id)

    envelope = {"id": task_id, "owner": role, "deps": [], "inputs": [],
                "outputs": [], "non_goals": list(non_goals or []),
                "brief_ref": brief_ref, "brief_version": eb["version"],
                "knowledge_scope": _scope(project)}
    bundle = {"schema": "dsh.card_bundle/v1", "card": envelope, "brief": eb}
    (d / "bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    problems = (validate_brief(eb, eb["task_type"])
                + validate_bundle(envelope, eb))
    return {"bundle": bundle, "problems": [f"{role}: {p}" for p in problems]}

