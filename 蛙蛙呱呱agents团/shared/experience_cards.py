# -*- coding: utf-8 -*-
"""shared.experience_cards —— 项目级经验卡：存储、校验、检索、注入。

为什么要它：
    角色已经有 references/（方法）和 experience/thresholds.json（阈值），
    但没有「上一个项目踩过什么坑、下次怎么判」的可检索记忆。
    结果是同一类错误在每个项目重犯一次。

三层来源（后者优先）：
    1. <role>/experience/cards/*.yaml      角色通用经验
    2. <project>/experience/cards/*.yaml   项目经验（同 id 覆盖角色级）
    3. 关键词检索（trigger / title / do_instead），不建向量库

分档（照 RAG Gate，不默认读一堆）：
    L0 不读（无命中） / L1 读 1 条 / L2 读 3 条

卡片字段（缺 boundary / last_verified 直接拒收）：
    id, title, trigger, wrong_once, do_instead, boundary,
    last_verified, confidence, roles, source

治理（2026-11-26 补齐）：
    * 同 trigger 但做法不一致 → conflicts() 列出，只能按各自 boundary 择一；
    * 每个项目上限 MAX_PER_PROJECT 张，超出只保留最新的一批并报错；
    * 写入走 add_card()：source + reviewed_by 必填（谁写谁签），不接受匿名卡；
    * 注入预算 BRIEF_MAX_CHARS 字，超出按行截断并标 truncated；
    * stats() 给出过期占比等验收指标；
    * to_knowledge_items() 是与 knowledge_base 的接缝（默认不走向量）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:  # PyYAML 是项目既有依赖；缺失时退回 JSON 卡片
    import yaml  # noqa: PLC0415
except Exception:  # noqa: BLE001
    yaml = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD_FIELDS = ("id", "title", "trigger", "wrong_once", "do_instead",
               "boundary", "last_verified", "confidence", "roles", "source")
REQUIRED = ("id", "title", "trigger", "wrong_once", "do_instead",
            "boundary", "last_verified")
TTL_DAYS = 180
MAX_PER_PROJECT = 30
BRIEF_MAX_CHARS = 600
CONF_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
_TOKEN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]{2,}")


def _role_dir(role: str) -> str:
    from shared.prompt_pack import role_dir  # noqa: PLC0415
    return role_dir(str(role).lower().strip()) or ""


def _load_file(path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return None, f"{path}: 读不到（{exc}）"
    try:
        if path.endswith((".yaml", ".yml")) and yaml is not None:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        return None, f"{path}: 解析失败（{exc}）"
    if isinstance(data, dict) and isinstance(data.get("card"), dict):
        data = data["card"]
    if not isinstance(data, dict):
        return None, f"{path}: 不是对象"
    data["_file"] = path
    return data, ""


def validate(card: Dict[str, Any]) -> List[str]:
    miss = [f for f in REQUIRED if not str(card.get(f) or "").strip()]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(card.get("last_verified") or "")):
        miss.append("last_verified(YYYY-MM-DD)")
    if miss:
        return miss
    if not isinstance(card.get("roles"), (list, str)):
        miss.append("roles(list|*)")
    return miss


def _tokens(text: str) -> set:
    return {t.lower() for t in _TOKEN.findall(str(text or ""))}


def _age_days(card: Dict[str, Any], today: Optional[_dt.date] = None) -> int:
    try:
        return ((today or _dt.date.today())
                - _dt.date.fromisoformat(str(card.get("last_verified")))).days
    except ValueError:
        return TTL_DAYS * 2


def _ingest(d: str, found: Dict[str, Dict[str, Any]],
            errors: List[str]) -> None:
    """读一个 cards 目录进 found（同 id 后写覆盖）。"""
    if not os.path.isdir(d):
        return
    for name in sorted(os.listdir(d)):
        if not name.endswith((".yaml", ".yml", ".json")):
            continue
        card, err = _load_file(os.path.join(d, name))
        if err:
            errors.append(err)
            continue
        miss = validate(card)
        if miss:
            errors.append(f"{card['_file']}: 缺 {','.join(miss)}")
            continue
        found[str(card["id"])] = card


def load_cards(role: str, project: Optional[str] = None,
               today: Optional[_dt.date] = None) -> Tuple[List[Dict], List[str]]:
    """读角色级 + 项目级卡片；项目级同 id 覆盖，超上限只保留最新的 30 张。"""
    found: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    rd = _role_dir(role)
    if rd:
        _ingest(os.path.join(rd, "experience", "cards"), found, errors)
    if project:
        pdir = os.path.join(str(project), "experience", "cards")
        pfound: Dict[str, Dict[str, Any]] = {}
        _ingest(pdir, pfound, errors)
        if len(pfound) > MAX_PER_PROJECT:
            ranked = sorted(pfound.values(),
                            key=lambda c: (-_age_days(c, today), str(c.get("id"))))
            keep = [str(c["id"]) for c in ranked[:MAX_PER_PROJECT]]
            errors.append(f"{pdir}: 项目经验卡 {len(pfound)} 张，超过上限 "
                          f"{MAX_PER_PROJECT}，只保留最新 {MAX_PER_PROJECT} 张")
            pfound = {k: pfound[k] for k in keep}
        found.update(pfound)
    return list(found.values()), errors


def _roles_of(card: Dict[str, Any]) -> List[str]:
    roles = card.get("roles")
    if isinstance(roles, str):
        roles = [roles]
    return [str(r).lower() for r in (roles or [])]


def score(card: Dict[str, Any], query: set, role: str,
          today: _dt.date) -> float:
    roles = _roles_of(card)
    if roles and "*" not in roles and role not in roles:
        return 0.0
    q = query - {""}
    trig = _tokens(card.get("trigger"))
    title = _tokens(card.get("title"))
    body = _tokens(f"{card.get('wrong_once')} {card.get('do_instead')}")
    s = 2.0 * len(q & trig) + 1.0 * len(q & title) + 0.5 * len(q & body)
    if not s:
        return 0.0
    try:
        age = (today - _dt.date.fromisoformat(str(card["last_verified"]))).days
    except ValueError:
        age = TTL_DAYS * 2
    decay = 1.0 if age <= TTL_DAYS else max(0.3, TTL_DAYS / max(age, 1))
    conf = CONF_WEIGHT.get(str(card.get("confidence") or "medium").lower(), 0.7)
    return round(s * decay * conf, 3)


def retrieve(role: str, query: str, project: Optional[str] = None,
             limit: int = 3, today: Optional[_dt.date] = None) -> Dict[str, Any]:
    cards, errors = load_cards(role, project, today)
    q = _tokens(query)
    now = today or _dt.date.today()
    ranked = [(score(c, q, str(role).lower(), now), c) for c in cards]
    ranked = [x for x in ranked if x[0] > 0]
    ranked.sort(key=lambda x: (-x[0], str(x[1].get("id"))))
    top = [dict(c, _score=s) for s, c in ranked[:max(1, int(limit))]]
    tier = "L0" if not top else ("L1" if len(top) == 1 else "L2")
    text = brief(top)
    truncated = len(text) > BRIEF_MAX_CHARS
    if truncated:  # 注入预算：宁可少说一张，也不把提示词撑爆
        text = text[:BRIEF_MAX_CHARS].rsplit("\n", 1)[0]
    return {"ok": True, "tier": tier, "cards": top, "errors": errors,
            "loaded": len(cards), "hits": len(ranked),
            "brief": text, "brief_chars": len(text), "truncated": truncated,
            "conflicts": conflicts(cards)}


def conflicts(cards: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同 trigger 但做法不一致 → 冲突。有边界只是「可并列」，不是「可混用」。"""
    groups: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
    for c in cards:
        groups.setdefault(tuple(sorted(_tokens(c.get("trigger")))), []).append(c)
    out: List[Dict[str, Any]] = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        actions = {str(x.get("do_instead") or "").strip() for x in group}
        if len(actions) < 2:
            continue
        out.append({
            "ids": [str(x.get("id")) for x in group],
            "trigger": " ".join(key),
            "note": "同触发词但做法不一致：只能按各自 boundary 择一，不得混用",
        })
    return out


def stats(role: str, project: Optional[str] = None,
          today: Optional[_dt.date] = None) -> Dict[str, Any]:
    """验收指标：载入量 / 过期占比 / 注入字数 / 冲突数。"""
    now = today or _dt.date.today()
    cards, errors = load_cards(role, project, now)
    stale = [c for c in cards if _age_days(c, now) > TTL_DAYS]
    top = [dict(c) for c in cards[:3]]
    text = brief(top)
    if len(text) > BRIEF_MAX_CHARS:
        text = text[:BRIEF_MAX_CHARS].rsplit("\n", 1)[0]
    return {
        "role": role, "loaded": len(cards), "stale": len(stale),
        "stale_ratio": round(len(stale) / len(cards), 3) if cards else 0.0,
        "brief_chars": len(text), "conflicts": len(conflicts(cards)),
        "errors": errors,
    }


def add_card(scope_dir: str, card: Dict[str, Any], reviewer: str = "",
             replace: bool = False) -> Dict[str, Any]:
    """写入门：谁写谁签。scope_dir 是角色目录或项目目录。

    拒收条件：缺 boundary/last_verified/source；无 reviewer；同目录同 id 已存在
    且未声明 replace；项目目录已满 MAX_PER_PROJECT。
    """
    c = dict(card)
    miss = validate(c)
    if not str(c.get("source") or "").strip():
        miss.append("source")
    if not str(reviewer or "").strip():
        miss.append("reviewed_by")
    if miss:
        return {"ok": False, "errors": [f"缺 {m}" for m in miss]}
    d = os.path.join(str(scope_dir), "experience", "cards")
    ids = set()
    if os.path.isdir(d):
        ids = {str(x.get("id")) for x in _read_dir(d)[1]}
        if str(c["id"]) in ids and not replace:
            return {"ok": False, "errors": [f"同目录已有 id={c['id']}，"
                                            "确认要覆盖请传 replace=True"]}
        if len(ids) >= MAX_PER_PROJECT and str(c["id"]) not in ids:
            return {"ok": False, "errors": [f"已满 {MAX_PER_PROJECT} 张，"
                                            "先归档或合并旧卡"]}
    c["reviewed_by"] = str(reviewer)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{c['id']}.yaml")
    if yaml is not None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(c, f, allow_unicode=True, sort_keys=False)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
    return {"ok": True, "path": path}


def _read_dir(d: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    errs: List[str] = []
    got: Dict[str, Dict[str, Any]] = {}
    _ingest(d, got, errs)
    return errs, list(got.values())


def to_knowledge_items(cards: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """与 shared/knowledge_base 的接缝：卡片 → 可注入条目（带内容 hash 审计）。

    说明：本模块不默认走向量检索（`knowledge_base` 里那条路径保持关闭），
    只把卡片整理成同一形状，便于将来接向量或外部知识库时零改造迁移。
    """
    import hashlib  # noqa: PLC0415
    out = []
    for c in cards:
        text = brief([c])
        out.append({
            "id": str(c.get("id")), "title": str(c.get("title")),
            "text": text, "source": str(c.get("source") or ""),
            "roles": _roles_of(c),
            "hash": hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
        })
    return out


def brief(cards: Iterable[Dict[str, Any]]) -> str:
    lines = []
    for c in cards:
        lines.append(
            f"- [{c.get('id')}] {c.get('title')}\n"
            f"  触发：{c.get('trigger')}\n"
            f"  上次错法：{c.get('wrong_once')}\n"
            f"  正确做法：{c.get('do_instead')}\n"
            f"  适用边界：{c.get('boundary')}（核验：{c.get('last_verified')}）")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="experience_cards")
    ap.add_argument("--role", required=True)
    ap.add_argument("--query", default="")
    ap.add_argument("--project", default=None)
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--stats", action="store_true", help="只看验收指标")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.stats:
        res = stats(a.role, a.project)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    res = retrieve(a.role, a.query, a.project, a.limit)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"[{res['tier']}] 载入 {res['loaded']} 张，命中 {res['hits']} 张"
              f"；注入 {res['brief_chars']} 字"
              + ("（已截断）" if res["truncated"] else ""))
        for e in res["errors"]:
            print("  ! " + e)
        for c in res["conflicts"]:
            print("  × 冲突 " + "|".join(c["ids"]) + "：" + c["note"])
        print(res["brief"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
