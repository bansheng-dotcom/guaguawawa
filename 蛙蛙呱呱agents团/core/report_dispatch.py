# -*- coding: utf-8 -*-
"""core.report_dispatch —— 拆卡、发卡、验卡（2026-11-20 起）。

三段，每段一个可审文件：

    clarify.json（意图已确认）
        │  report brief --dir <项目> --plan
        ▼
    plan.json / plan.md        ← 「问题 → 角色」映射表，先给人审
        │  report brief --dir <项目> --plan --confirm
        ▼
    cards/<role>/TASK.md + coverage/issued.json   ← 每张卡带 nonce + 签名

收卡时 `dispatch.collect` 校验 claims.json 里的 dispatch 块：
nonce 对不上 / role 不符 / 执行者填 r01 或编排器 → 整卡拒收。

为什么不只靠"纪律"：2026-11-20 的测试里，R01 自己写了 6 张卡的全部 claims，
再自称"4 个角色只交 claims.json"。没有 nonce 的时候，这句话在产物上无法反驳。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import report_clarify
from core.report_clarify import KEYWORD_ROLES, TYPE_HINT

SCHEMA_PLAN = "dsh.report.plan/v1"
SCHEMA_ISSUED = "dsh.report.issued/v1"

# 作者与验收人不下场执行：R01 是唯一出具人，R04 是独立验收
EXCLUDE_EXECUTORS = {"r01", "r04"}
# 这些执行者 id 视为"编排器自己写的"，直接拒收
SELF_WORKERS = {"r01", "solo", "solo_agent", "guagua", "orchestrator", "auto"}
MAX_ASKS_PER_ROLE = 3


# --------------------------------------------------------------------------- #
# 签名：nonce 不是密码学护城河，但它把"代写"从默认动作变成一次显式伪造
# --------------------------------------------------------------------------- #
def key_path() -> Path:
    p = Path.home() / ".guagua" / "dispatch_key"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _key(create: bool = True) -> bytes:
    p = key_path()
    if not p.is_file():
        if not create:
            return b""
        p.write_bytes(secrets.token_bytes(32))
        try:
            p.chmod(0o600)
        except OSError:
            pass
    return p.read_bytes()


def sign(role: str, nonce: str, qids: List[str]) -> str:
    msg = f"{role}|{nonce}|{','.join(qids)}".encode("utf-8")
    return hmac.new(_key(), msg, hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# 拆卡：问题 → 角色
# --------------------------------------------------------------------------- #
def _score(ask: Dict[str, Any], role: Dict[str, Any]) -> Tuple[float, List[str]]:
    txt = str(ask.get("text") or "")
    typ = str(ask.get("type") or "判断型")
    hints = TYPE_HINT.get(typ) or []
    s, why = 0.0, []
    if hints and role["id"] == hints[0]:
        s += 2.0
        why.append(f"类型「{typ}」首选")
    elif len(hints) > 1 and role["id"] == hints[1]:
        s += 1.0
        why.append(f"类型「{typ}」次选")
    for kw, roles in KEYWORD_ROLES.items():
        if kw in txt and role["id"] in roles:
            s += 1.5
            why.append(f"命中「{kw}」")
    for cap in role.get("capabilities") or []:
        if cap and cap in txt:
            s += 1.0
            why.append(f"能力「{cap}」")
    return s, why


def build_plan(clarify: Dict[str, Any], roster_data: Dict[str, Any]) -> Dict[str, Any]:
    roles = [r for r in (roster_data.get("roles") or {}).values()
             if r.get("enters_report") and r["id"] not in EXCLUDE_EXECUTORS]
    asks = [a for a in (clarify.get("asks") or [])]
    load: Dict[str, int] = {r["id"]: 0 for r in roles}
    rows = []
    for ask in asks:
        scored = []
        for r in roles:
            s, why = _score(ask, r)
            scored.append((s - 0.1 * load[r["id"]], s, r, why))
        scored.sort(key=lambda x: (-x[0], x[2]["id"]))
        best = scored[0]
        if best[1] <= 0:
            # 谁都不匹配：落到研究官，避免"没人负责"
            best = next(x for x in scored if x[2]["id"] == "r05")
        support = [x[2]["id"] for x in scored[1:3] if x[1] >= 1.0]
        load[best[2]["id"]] += 1
        rows.append({
            "qid": ask["id"], "question": ask["text"], "type": ask.get("type"),
            "must": bool(ask.get("must")),
            "primary": best[2]["id"], "primary_name": best[2].get("name"),
            "support": support,
            "why": "、".join(best[3]) or "缺省归属研究官",
        })

    # 负载均衡：一个角色最多 3 问；但只改派给**真有分数**的角色，
    # 不能把没人能答的问题丢给负载最低的人（2026-11-20：Q4 被丢给了 r20 SRE）。
    for _ in range(3):
        moved = False
        for r in roles:
            mine = [x for x in rows if x["primary"] == r["id"]]
            if len(mine) <= MAX_ASKS_PER_ROLE:
                continue
            for row in mine[MAX_ASKS_PER_ROLE:]:
                ask = next(a for a in asks if a["id"] == row["qid"])
                alts = sorted(
                    ((_score(ask, o)[0] - 0.1 * load[o["id"]], o["id"], _score(ask, o)[0])
                     for o in roles
                     if o["id"] != r["id"] and _score(ask, o)[0] > 0),
                    reverse=True)
                if alts:
                    row["primary"], row["primary_name"], row["why"] = (
                        alts[0][1], next(o.get("name") for o in roles
                                         if o["id"] == alts[0][1]),
                        "负载均衡改派（原主责 " + r["id"] + "）")
                    load[alts[0][1]] += 1
                    load[r["id"]] -= 1
                    moved = True
        if not moved:
            break

    by_role: Dict[str, List[str]] = {}
    for row in rows:
        by_role.setdefault(row["primary"], []).append(row["qid"])
    # support 问句如果能落在同一个主责身上，就并入它服务的 must 那节，
    # 不要单独开一节（不改渲染层的合并逻辑，在发卡话术里说清楚）。
    # 先给所有行定 tier，再算合并提示（同一批里后面还没遍历到的行也要能查到）
    for row in rows:
        ask = next(a for a in asks if a["id"] == row["qid"])
        row["tier"] = "must" if ask.get("must") else "support"
        row["merge_into"] = ""
    for row in rows:
        if row["tier"] != "support":
            continue
        same = [r for r in rows
                if r["primary"] == row["primary"] and r["tier"] == "must"]
        if same:
            row["merge_into"] = same[0]["qid"]
    cards = []
    for rid, qids in by_role.items():
        r = next(x for x in roles if x["id"] == rid)
        cards.append({
            "role": rid, "name": r.get("name"), "title": r.get("title"),
            "questions": qids,
            "merge_hints": [{"qid": x["qid"], "into": x["merge_into"]}
                            for x in rows
                            if x["primary"] == rid and x.get("merge_into")],
            "must_not": [x["qid"] for x in rows if x["qid"] not in qids],
        })
    warnings = []
    if len(cards) == 1 and len(rows) >= 4:
        warnings.append("4 问以上都落到同一个角色：拆卡可能没拆开")
    if len(rows) != len(asks):
        warnings.append("有问句没被分配")
    return {
        "schema": SCHEMA_PLAN,
        "intent": clarify.get("intent"),
        "status": "draft",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "clarify_sha": hashlib.sha256(
            json.dumps(clarify, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
        "mapping": rows,
        "cards": cards,
        "warnings": warnings,
    }


def render_plan_md(plan: Dict[str, Any]) -> str:
    L = [f"# 拆卡映射：{plan.get('intent', '')}", "",
         "> 这张表是**发卡依据**。不同意就把 `plan.json` 里的 `primary` 改掉，"
         "再跑 `report brief --dir <项目> --plan --confirm`。", "",
         "| 问题 | 类型 | 必答 | 主责 | 协办 | 为什么是他 |",
         "|---|---|---|---|---|---|"]
    for m in plan.get("mapping") or []:
        L.append(f"| {m['qid']} {m['question']} | {m['type']} | "
                 f"{'是' if m.get('must') else '否'} | {m['primary']} | "
                 f"{'、'.join(m.get('support') or []) or '-'} | {m['why']} |")
    L += ["", "## 每张卡要交什么", ""]
    for c in plan.get("cards") or []:
        L.append(f"- **{c['role']} {c.get('name')}**：答 "
                 f"{'、'.join(c['questions'])}；不归他："
                 f"{'、'.join(c['must_not']) or '无'}")
    if plan.get("warnings"):
        L += ["", "## 警告", ""] + [f"- {w}" for w in plan["warnings"]]
    L += ["", "---", "",
          "确认无异议后：`python guagua.py report brief --dir <项目> --plan --confirm` 发卡。"]
    return "\n".join(L)


def write_plan(base: str, confirm: bool = False,
               roster_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from core import roster
    c = report_clarify.load(base)
    if c.get("status") != "confirmed":
        return {"ok": False, "error": "clarify.json 还没确认",
                "hint": f"先看 {base}/clarify.md，改完跑 "
                        f"`report clarify --dir {base} --confirm`"}
    plan = build_plan(c, roster_data or roster.build())
    if confirm:
        plan["status"] = "confirmed"
        plan["confirmed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    p = Path(base) / "plan.json"
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(base) / "plan.md").write_text(render_plan_md(plan), encoding="utf-8")
    return {"ok": True, "plan": str(p), "status": plan["status"],
            "card_count": len(plan["cards"]),
            "cards": [{"role": c["role"], "questions": c["questions"]}
                      for c in plan["cards"]],
            "mapping": [{"qid": m["qid"], "primary": m["primary"],
                         "question": m["question"]} for m in plan["mapping"]],
            "warnings": plan["warnings"]}


_TASK_TAIL = """## 交数据的要求（决定图上能不能画出来）

- 每个判断至少 **3 个可比点**（不同规格 / 地区 / 期次 / 主体）
- 价格类：给完整阶梯（产地 → 出厂 → 批发 → 零售），不要只给一个价
- 趋势类：至少 4 期；不足 4 期就不要写趋势结论
- 2 个点画不成图，报告会退成表格——这是丢分项

## 来源要求（缺一条，整张卡拒收）

- 每条 source 必须带 `url`（http/https）、`date`（YYYY 或 YYYY-MM-DD）、`quote`（原文片段 ≥12 字）
- 每个数字必须指向本卡的某个 `source_file`；指向不存在的来源，整卡拒收
- 同一指标两个数，必须在 conflicts 里写清口径差

## 边界

- 只用公开可核来源；查不到写 `unanswered`（结构见上），不要编
- 你只对你负责的问句下结论；别人的问句不要抢，也不要写进 claims
"""

_WORKORDER_HEAD = """## 1. 你负责回答什么

每一问都要交**三段**，缺「反例」按没深入处理：

- **事实**：数字 + 口径 + 期次（可回溯到 source）
- **机理**：为什么是这样（受什么约束、驱动是什么）
- **反例**：什么情况下不成立 / 有没有例外（找不到反例也要写"未找到"，并说明怎么找的）
"""

_WORKORDER_CRITERIA = """## 2. 什么算答好（缺一条，这一问不算过）

1. 每问至少 **3 个可比点**（不同规格/地区/期次/主体），单点不算结论
2. 每节正文：**单段 ≤300 字（硬上限 330）**，2–4 条解读；节长不设上限（长度由判断数决定）；超过 330 字退回重写
3. 每条解读必须带 `refs`（指向本卡 numbers）——没有 refs 的数字视为编的
4. 每节必须有 `chart`（type/title/source/refs + 对应负载），**并声明 `relation` 与 `why_this_chart`**：`relation` 从 9 类里选一个，图型必须落在该关系的候选清单里（见下表）；不声明或图型不合法，S5 门禁直接拦。确实画不了写 `chart_skip_reason`
5. 每问有 **事实 / 机理 / 反例** 三段，缺反例 = 没深入
6. 每条主结论带 **falsifier**（什么可观测条件下作废）
7. 必须交 **2 条计划外发现**（见第 4 段），不能是主问的复述
8. 每个 `needs` 要么被回答，要么 `declined` 写清原因

### 图表选型：先定关系，再选图型（`relation` 必填）

| relation | 什么时候用 | 候选图型（第一个是默认） |
|---|---|---|
| `deviation` | 相对 0/目标/均值的正负偏离 | hbar · vbar · dot · lollipop · waterfall · area · control |
| `correlation` | 两个连续变量找关系 | scatter · bubble · heatmap · small_mult · parallel |
| `ranking` | 位次比绝对值重要 | hbar · vbar · grouped · dot · lollipop · slope · dumbbell · pareto · rose |
| `distribution` | 看形状、离散、异常 | histogram · box · violin · dot · ridge · error_bar · forest · radar |
| `change_over_time` | 看方向、拐点、节奏 | line · area · vbar · stream · dual_panels · cal_heatmap · small_mult · candle · gantt |
| `composition` | 部分与整体（加总≈100%） | stacked · pct_stacked · treemap · sunburst · pie · donut · waffle · rose |
| `magnitude` | 只比大小，不强调位次与时间 | vbar · hbar · grouped · bullet · gauge · kpi · target_band |
| `spatial` | 位置本身是信息 | choropleth · symbol · heatmap · geo_flow |
| `flow` | 量在节点/阶段之间移动 | sankey · waterfall · funnel · network · bridge · gantt |

负载形状必须与图型匹配：时序类给 `points`（≥4 期）、构成类给 `categories`+`series`、
分布类给 `values`/`groups`、排名与量级类给 `items`/`bars`；形状不匹配会被降级成表格。

## 3. 你可以向谁要什么（卡间协商）

先想清楚"这一问缺了谁的数据就答不了"，写进 `needs.json`：

```json
{"needs": [{"id": "N1", "to": "r06", "what": "四城社零分品类",
            "why": "Q9 要判断节点城市，缺品类社零只能猜", "status": "open"}]}
```

- 发出去后跑 `python guagua.py report exchange --dir <项目>`，系统会把请求投到对方 INBOX
- 对方回 `answers.json`（带 source_file）；回不了就写 `declined` + 原因
- **open 的 need 会让整卡收不进来**——不要挂一个你其实不需要的依赖

## 4. 发散槽（硬性交付，不是建议）

交 `explore` 数组，2 条：

```json
{"explore": [{"text": "A 主体是唯一正号：可能与 XX 有关", "value": 9.1, "unit": "%",
              "source_file": "S2", "why_important": "如果成立，选品要按主体分组"}]}
```

要求：带数字、带来源、**不是你负责问句的复述**。
业务上的关键原因常常不在这 10 个问句里，这一栏就是留给它的。

## 5. 交不了怎么办

```json
{"unanswered": [{"qid": "Q3", "tried": ["url1", "url2"],
                 "why": "内蒙品牌级零售无公开数据，省级社零不含品牌"}]}
```

`unanswered` 会进报告首页的「未答清单」，不会静默消失。
"""


def _role_identity(rid: str) -> Dict[str, str]:
    """角色名/职称唯一出处 core.report_roles（其又从 core.registry 归一）。"""
    try:
        from core.report_roles import ROLE_REPORT
        meta = ROLE_REPORT.get(rid) or {}
        return {"name": str(meta.get("name") or ""),
                "title": str(meta.get("title") or "")}
    except Exception:  # noqa: BLE001
        return {"name": "", "title": ""}


_PERSPECTIVE_HEAD = """## 1. 你负责回答什么

你不答题，只做**口径校核**。每个视角格交一条「改判」：

- **边界**：主卡的数字在什么口径下不成立（GMV vs 零售、含税/不含税、抽佣前后…）
- **结构**：主卡的加总在什么维度上会漏项（品类×渠道、性别×品类…）
- **改判**：这条边界一旦成立，主卡哪句结论要改、改成什么
"""

_PERSPECTIVE_CRITERIA = """## 2. 什么算答好（缺一条，这一格不算过）

1. 每格至少 **2 个可比口径**（同一指标不同算法/来源/维度），单口径不算校核
2. 每格必须写「主卡原结论 → 你的改判」，没有改判就是没校核
3. 每条判断带 `refs`（指向本卡 numbers）与 **falsifier**
4. 每格必须带 `chart` 或 `chart_skip_reason`
5. 必须交 **2 条计划外发现**（第 4 段）
6. 不写 Q1–Q9 的结论；那是主答角色的活
"""


def issue(base: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """按已确认的映射表发卡：每张卡带 nonce + 签名 + 分配到的问句 + 协商协议。"""
    root = Path(base)
    pp = root / "plan.json"
    if not pp.is_file():
        return {"ok": False, "error": "没有 plan.json",
                "hint": f"先跑 `report brief --dir {base} --plan`"}
    plan = json.loads(pp.read_text(encoding="utf-8-sig"))
    if plan.get("status") != "confirmed":
        return {"ok": False, "error": "映射表还没确认",
                "hint": f"看 {base}/plan.md，改完跑 "
                        f"`report brief --dir {base} --plan --confirm`"}
    c = report_clarify.load(base)
    asks = {a["id"]: a for a in c.get("asks") or []}

    # v1.5：发卡前先过拆卡 SOP 门禁（S7）。不过门禁就不发卡。
    from core import card_issue
    gate = card_issue.pre_issue_gates(root)
    if not gate.get("ok"):
        return {"ok": False, "stage": "card_spec",
                "error": "拆卡门禁未过，拒绝发卡（拆卡升级 SOP v1.4 · S7）",
                "gates": gate,
                "hint": f"先跑 `report brief --dir {base} --plan` 生成五轴，"
                        f"看 plan/pre_issue_gates.json"}

    contracts = card_issue.contracts_by_role(root)
    cells_by_role = card_issue.cells_by_role(root)
    if only:
        contracts = {k: v for k, v in contracts.items() if k in only}
        cells_by_role = {k: v for k, v in cells_by_role.items() if k in only}
    # R02 签发：问句优先取 plan 的 role→questions；只有 plan 没写才由格子反推。
    # 格子必须裁到该角色负责的问句，避免「每张卡都被塞进 9 问」。
    plan_cards = {c.get("role"): c for c in (plan.get("cards") or [])}
    if contracts:
        cards_iter = []
        for rid, ct in contracts.items():
            # 2026-11-23 修：问句以**拆卡格子**为准。
            # 原来优先取 plan.json 的 role→questions（老映射表），可它和拆卡的
            # plan/dispatch.json 是两套算法，经常打架：拆卡把 Q2 分给 r05，
            # 老映射却写成 Q2→r14，结果 r05 的卡丢了 Q2、r14 根本没格子没卡。
            # 格子才是这角色要填的东西，所以格子优先，plan.json 只作兜底。
            qids: List[str] = []
            for cell in cells_by_role.get(rid) or []:
                q = str(cell.get("qid") or "")
                if q and q not in qids:
                    qids.append(q)
            if not qids:
                qids = list((plan_cards.get(rid) or {}).get("questions") or [])
            allowed = set(qids)
            if allowed:
                filtered = [c for c in (cells_by_role.get(rid) or [])
                            if str(c.get("qid") or "") in allowed]
                if filtered:
                    cells_by_role[rid] = filtered
            ident = _role_identity(rid)
            cards_iter.append({"role": rid, "questions": qids,
                               "name": ident["name"] or rid,
                               "title": ident["title"], "contract": ct})
        peers = list(contracts)
    else:
        cards_iter = plan.get("cards") or []
        peers = [x["role"] for x in plan.get("cards") or []]

    issued: Dict[str, Any] = {}
    for card in cards_iter:
        rid = card["role"]
        qids = list(card["questions"])
        my_cells = cells_by_role.get(rid) or []
        ct = card.get("contract") or contracts.get(rid) or {}
        nonce = secrets.token_hex(8)
        sig = sign(rid, nonce, qids)
        d = root / "cards" / rid
        d.mkdir(parents=True, exist_ok=True)
        dims = {str(c.get("dim") or "") for c in my_cells}
        # 视角卡（边界/结构）：plan 没给它问句，格子只做口径校核，不领问句
        perspective = (rid not in plan_cards and bool(dims)
                       and dims <= {"边界", "结构"})
        lines = [
            f"# 工单：{rid} {card.get('name')}（{card.get('title')}）",
            "",
            f"- 总任务：{plan.get('intent')}",
        ]
        if perspective:
            lines += [
                f"- 你负责 **{len(my_cells)} 个视角格**（边界/结构校核，不领问句）",
                "- 你不是主答角色：**不要**写 Q1–Q9 的结论，也不要抢主卡的判断；",
                "  每格交一条「这个口径/边界会让主卡的结论怎么改判」，并给 falsifier。",
                "",
                f"- 参照问句（只用来定位，不必逐条答）：{'、'.join(qids)}",
            ]
        else:
            lines.append(f"- 你负责 **{len(qids)} 问**（逐条答，答不了交 `unanswered`）：")
        if not perspective:
            for q in qids:
                a = asks.get(q) or {}
                lines.append(f"  - **{q}**（{a.get('type', '')}"
                             f"{'，必答' if a.get('must') else '，支撑'}）：{a.get('text', '')}")
        hints = {h["qid"]: h["into"] for h in (card.get("merge_hints") or [])}
        for q, into in hints.items():
            lines.append(f"    - {q} 是 {into} 的对照：请写进 {into} 那一节的解读里"
                         f"（标「对照」），**不要单开一节**")
        other = [q for q in card.get("must_not") or []]
        if other:
            lines.append(f"- 不归你（别抢，也不要写进 claims）：{'、'.join(other)}")

        if my_cells:
            lines += ["", f"## 你负责的 {len(my_cells)} 个格子（按格交，不许跳格）", "",
                      "| cell_id | 维度 | 度量 | grain | 期次 | 因果阶 |",
                      "|---|---|---|---|---|---|"]
            for cell in my_cells:
                lines.append(
                    f"| `{cell.get('cell_id')}` | {cell.get('dim')} | {cell.get('measure')} "
                    f"| {cell.get('grain')} | {cell.get('period')} | {cell.get('causal_level')} |")
            lines += ["", "> 每格按 `cells[]` 交：cell_id / value / unit / period / "
                          "source_file / grade / quality 六维 / causal_level；"
                          "填不了写 `unavailable` + tried + why。"]

        if ct:
            lines += ["", "## R02 任务契约（签发即生效）", "",
                      f"- task_id：`{ct.get('task_id')}`",
                      f"- 验收门禁：{', '.join(ct.get('acceptance') or []) or '—'}",
                      f"- 截止 / 升级：{ct.get('deadline') or '—'} / {ct.get('escalate_to') or 'r02'}",
                      f"- 契约指纹：`{ct.get('content_sha')}`"]
        lines += ["",
                  _PERSPECTIVE_HEAD if perspective else _WORKORDER_HEAD, "",
                  _PERSPECTIVE_CRITERIA if perspective else _WORKORDER_CRITERIA, "",
                  f"可协商的同伴：{'、'.join(p for p in peers if p != rid)}",
                  "",
                  "## 6. 交什么、交到哪", "",
                  f"写到 `cards/{rid}/claims.json`；同目录下放 `needs.json` / "
                  f"`answers.json` / `explore`（可并入 claims）。",
                  "每问对应一节，节里加 `\"answers\": [\"" + "\", \"".join(qids[:1])
                  + "\"]` 声明这节回答的是哪一问——没有这个字段，报告对不上账。"
                  if not perspective else
                  "每个视角格对应一节，节里按 `cells[]` 交改判；视角节不挂 "
                  "`answers`（你不答题），但要挂 `refs` 与 `falsifier`。",
                  "", "## 7. dispatch 块（不填或填错，整卡拒收）", "",
                  "```json",
                  json.dumps({"dispatch": {"nonce": nonce, "role": rid,
                                           "by": "<你的执行者 id>",
                                           "questions": qids}},
                             ensure_ascii=False, indent=2),
                  "```", "",
                  "- `by` 写真正执行这张卡的智能体 id；填 `r01` / `solo` 视为代写，直接拒收",
                  "- `questions` 必须和上面分配的一致", "",
                  _TASK_TAIL]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "needs.json").write_text(json.dumps(
            {"needs": [{"id": "N1", "to": "", "what": "", "why": "",
                       "status": "open"}]}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        (d / "answers.json").write_text(json.dumps(
            {"answers": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "schema": "dsh.agent.claims/v1",
            "contract": "v2",
            "card_spec": True,
            "role": rid,
            "dispatch": {"nonce": nonce, "role": rid, "by": "", "questions": qids},
            "meta": {"title": plan.get("intent") or c.get("intent"),
                     "intent": plan.get("intent") or c.get("intent"),
                     "doc_type": "调研报告", "profile": "research"},
            "numbers": [{"id": "N1", "name": "", "value": 0, "unit": "",
                         "source_file": "S1"}],
            "sources": [{"file": "S1", "kind": "web", "title": "", "org": "",
                         "url": "", "date": "", "quote": ""}],
            "sections": [{"title": "（结论 + 数字）", "question": "",
                          "answers": qids,
                          "refs": ["N1"],
                          "boundary": "口径与适用范围",
                          "reading": [
                              {"strong": "事实　", "text": "≤300 字", "refs": ["N1"]},
                              {"strong": "机理　", "text": "≤300 字", "refs": ["N1"]},
                              {"strong": "反例　", "text": "≤300 字", "refs": ["N1"]}],
                          "chart": {"type": "hbar", "relation": "magnitude",
                                    "why_this_chart": "这张图编码了本节要回答的比较",
                                    "title": "（含数字）",
                                    "source": "机构名", "refs": ["N1"],
                                    "bars": [{"label": "…", "value": 0}]},
                          "falsifier": "什么情况下这条作废"}],
            "cells": [
                {"cell_id": cell.get("cell_id"), "qid": cell.get("qid"),
                 "measure": cell.get("measure"), "grain": cell.get("grain"),
                 "period": cell.get("period"), "causal_level": cell.get("causal_level"),
                 "status": "open", "value": None, "unit": "", "source_file": "",
                 "grade": "", "quality": {}, "tried": [], "why": ""}
                for cell in my_cells
            ] or [{"cell_id": "Q1.对象.待定", "status": "open", "value": None,
                   "unit": "", "source_file": "", "grade": "", "quality": {},
                   "tried": [], "why": ""}],
            "explore": [{"text": "", "value": 0, "unit": "", "source_file": "S1",
                         "why_important": ""}],
            "unanswered": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        issued[rid] = {"nonce": nonce, "sig": sig, "questions": qids,
                       "name": card.get("name"),
                       "contract": ct.get("task_id"),
                       "cells": len(my_cells)}

    cov = root / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA_ISSUED,
        "intent": plan.get("intent") or c.get("intent"),
        "issued_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "plan_sha": hashlib.sha256(pp.read_bytes()).hexdigest()[:16],
        "card_spec": {
            "schema": gate.get("schema"),
            "passed": gate.get("passed"),
            "total": gate.get("total"),
            "failed": [x for x in (gate.get("checks") or []) if not x.get("ok")],
        },
        "cards": issued,
    }
    (cov / "issued.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return {"ok": True, "issued": str(cov / "issued.json"),
            "cards": [{"role": k, "questions": v["questions"]}
                      for k, v in issued.items()]}


# --------------------------------------------------------------------------- #
# 收卡校验
# --------------------------------------------------------------------------- #
def load_issued(base: str) -> Optional[Dict[str, Any]]:
    for p in (Path(base) / "coverage" / "issued.json",
              Path(base) / "issued.json"):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                return None
    return None


def verify_claims(claims: Dict[str, Any], role: str,
                  issued: Dict[str, Any]) -> Tuple[bool, str]:
    """一张 claims 是不是**这张卡**被**别人**执行出来的。"""
    rec = (issued.get("cards") or {}).get(role)
    if not rec:
        return False, f"{role}: 没有发过卡（issued.json 里没有这个角色）"
    d = claims.get("dispatch") or {}
    if not isinstance(d, dict) or not d:
        return False, f"{role}: 缺 dispatch 块（不是按 nonce 执行的卡）"
    if str(d.get("role") or "") != role:
        return False, f"{role}: dispatch.role={d.get('role')} 与卡不符"
    if str(d.get("nonce") or "") != rec["nonce"]:
        return False, f"{role}: nonce 不匹配（串卡或事后补写）"
    qids = [str(x) for x in (d.get("questions") or [])]
    if qids and set(qids) != set(rec["questions"]):
        return False, f"{role}: 回填问句 {qids} 与卡 {rec['questions']} 不一致"
    if not hmac.compare_digest(sign(role, rec["nonce"], rec["questions"]), rec["sig"]):
        return False, f"{role}: 签名不匹配（卡被动过）"
    by = str(d.get("by") or "").strip()
    if not by:
        return False, f"{role}: 缺 dispatch.by（谁执行的）"
    if by.lower() in SELF_WORKERS:
        return False, (f"{role}: 执行者填的是 {by}（编排/作者自己），"
                       "视为代写，拒收")
    return True, ""
