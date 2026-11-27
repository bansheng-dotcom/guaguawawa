# -*- coding: utf-8 -*-
"""core.structure_guard —— 章节结构同构门禁。

为什么需要它：
    `prose_contract` 只看字数/关键词/数字密度，`check_11_fields` 只看字段齐不齐。
    两者都拦不住「十节写成同一副骨架」：每节都是
        「结论：… 事实：… 机理：… 反例：… 所以：…」
    这种稿子能拿满分，但读者一眼看出是模板。

判据（确定性、可解释、低误报）：
    1. 只认段首标签（结论/事实/机理/反例/判别/动作/边界/所以）；
    2. 取「标签序列 + 段数」作为结构指纹；
    3. 连续 >= min_run 节指纹完全一致，且指纹长度 >= min_blocks，判为同构；
    4. 两节相似只记 warning，不拦——拦的是「连续成片」。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

LABELS: Tuple[str, ...] = ("结论", "事实", "机理", "反例", "判别", "动作", "边界", "所以")

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "min_run": 3,
    "min_blocks": 3,
    "abs_path": "configs/report_prose.yaml",
}


def load_policy(root: Path | None = None) -> Dict[str, Any]:
    """从 configs/report_prose.yaml 的 structure_gate 段读取阈值。"""
    pol = dict(DEFAULTS)
    base = root or Path(__file__).resolve().parent.parent
    p = base / "configs" / "report_prose.yaml"
    try:
        import yaml  # noqa: PLC0415
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        pol.update({k: v for k, v in (raw.get("structure_gate") or {}).items()
                    if v is not None})
    except Exception:  # noqa: BLE001  配置缺失时用默认值，不让门禁因配置崩掉
        pass
    return pol


def _counts(text: str) -> Tuple[int, ...]:
    return tuple(str(text or "").count(w) for w in LABELS)


def _present_in_order(text: str, counts: Tuple[int, ...]) -> Tuple[str, ...]:
    """按标签在正文里首次出现的位置排序；没出现的标签不计。"""
    t = str(text or "")
    pos = [(t.find(w), w) for w, c in zip(LABELS, counts) if c > 0]
    return tuple(w for _, w in sorted(pos, key=lambda x: x[0]))


def signature(paragraphs: Sequence[str]) -> Dict[str, Any]:
    text = " ".join(str(p) for p in paragraphs)
    paras = len([p for p in paragraphs if str(p).strip()])
    c = _counts(text)
    return {"blocks": _present_in_order(text, c), "counts": c, "paras": paras}


def signature_text(text: str, paras: int) -> Dict[str, Any]:
    """从渲染后的整节文本取结构指纹。

    为什么不用「段首标签」：渲染器会把标签搬进 <span class="plabel">，
    或者把一条解读拆成多个 <p>，段首不再是标签。改用「标签计数 + 首次出现顺序」：
    模板稿的标签组合与次数完全一致，换过论证顺序的稿子顺序会变。
    """
    c = _counts(text)
    return {"blocks": _present_in_order(text, c), "counts": c, "paras": int(paras)}


def _fingerprint(sig: Dict[str, Any]) -> Tuple:
    return (sig.get("blocks", ()), sig.get("paras"))


def find_runs(signatures: Sequence[Dict[str, Any]], min_run: int,
              min_blocks: int) -> List[Dict[str, Any]]:
    """返回连续同构段：{start, end, fingerprint}（下标从 0 起）。"""
    runs: List[Dict[str, Any]] = []
    i = 0
    n = len(signatures)
    while i < n:
        fp = _fingerprint(signatures[i])
        j = i + 1
        while j < n and _fingerprint(signatures[j]) == fp:
            j += 1
        length = j - i
        if (length >= min_run and len(fp[0]) >= min_blocks and fp[1] >= min_blocks):
            runs.append({"start": i, "end": j - 1, "fingerprint": fp, "length": length})
        i = j
    return runs


def _fmt(run: Dict[str, Any]) -> str:
    blocks = "→".join(run["fingerprint"][0]) or "无标签"
    paras = run["fingerprint"][1]
    return (f"第 {run['start'] + 1}–{run['end'] + 1} 节结构完全同构"
            f"（{blocks}，均 {paras} 段）；"
            f"至少改掉其中一半的论证顺序、段数或切分方式")


def audit(paragraphs_by_section: Sequence[Sequence[str]],
          titles: Sequence[str] | None = None,
          policy: Dict[str, Any] | None = None) -> List[str]:
    """给定每节段落列表，返回问题清单；空列表 = 通过。"""
    return _audit_sigs([signature(ps) for ps in paragraphs_by_section], titles, policy)


def _audit_sigs(sigs: Sequence[Dict[str, Any]], titles: Sequence[str] | None,
                policy: Dict[str, Any] | None) -> List[str]:
    pol = policy or load_policy()
    if not pol.get("enabled", True):
        return []
    issues: List[str] = []
    for run in find_runs(sigs, int(pol.get("min_run", 3)),
                         int(pol.get("min_blocks", 3))):
        msg = _fmt(run)
        if titles:
            names = "、".join(str(titles[i])[:14] for i in range(run["start"], run["end"] + 1))
            msg += f"（{names}）"
        issues.append(msg)
    return issues


def paragraphs_from_claims(claims: Dict[str, Any]) -> tuple:
    """claims.sections → (每节段落, 标题)。"""
    out: List[List[str]] = []
    titles: List[str] = []
    for s in claims.get("sections") or []:
        texts = [str(r.get("text") or "") for r in (s.get("reading") or [])
                 if isinstance(r, dict) and str(r.get("text") or "").strip()]
        out.append(texts)
        titles.append(str(s.get("title") or ""))
    return out, titles


def sections_from_html(html: str) -> List[Dict[str, Any]]:
    """渲染后的 HTML → [{text, paras, title}]。只取业务章节（含 h2）。"""
    import re  # noqa: PLC0415
    raw = re.findall(r"<section[^>]*>[\s\S]*?</section>", html, re.I)
    out: List[Dict[str, Any]] = []
    for sec in raw:
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if not h:
            continue
        if re.search(r'id="appendix"', sec, re.I):
            continue
        if re.search(r'class="page (summary|cover|toc|back)"', sec, re.I):
            continue
        body = sec[h.end():]
        p_html = re.findall(r"<p[^>]*>([\s\S]*?)</p>", body, re.I)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        out.append({"text": text, "paras": len(p_html),
                    "title": re.sub(r"\s+", " ",
                                    re.sub(r"<[^>]+>", " ", h.group(1))).strip()})
    return out


def audit_html(html: str, policy: Dict[str, Any] | None = None) -> List[str]:
    secs = sections_from_html(html)
    sigs = [signature_text(s["text"], s["paras"]) for s in secs]
    return _audit_sigs(sigs, [s["title"] for s in secs], policy)


def paragraphs_from_html(html: str) -> tuple:
    """渲染后的 HTML → (每节段落, 标题)。只取业务章节（含 h2）。"""
    import re  # noqa: PLC0415
    raw = re.findall(r"<section[^>]*>[\s\S]*?</section>", html, re.I)
    out: List[List[str]] = []
    titles: List[str] = []
    for sec in raw:
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if not h:
            continue
        if re.search(r'id="appendix"', sec, re.I):
            continue
        if re.search(r'class="page (summary|cover|toc|back)"', sec, re.I):
            continue
        body = sec[h.end():]
        paras = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p)).strip()
                 for p in re.findall(r"<p[^>]*>([\s\S]*?)</p>", body, re.I)]
        paras = [p for p in paras if p]
        if not paras:
            continue
        out.append(paras)
        titles.append(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h.group(1))).strip())
    return out, titles
