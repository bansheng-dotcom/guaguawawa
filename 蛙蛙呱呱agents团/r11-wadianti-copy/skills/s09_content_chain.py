# -*- coding: utf-8 -*-
"""S09 内容生产线（七段链）—— 把写作从“终稿校验”升级为可审计工序。

动作：
  topic     选题候选（10 个 + Top3 理由）
  research  证据台账（sources / claims / quotes / gaps）
  outline   细纲契约（每节 6 字段）
  draft     单节三候选（多样性 + 分数 + 选稿理由）
  review    五维 findings（原文 + 改法）
  rewrite   200–400 字单元改写（覆盖率 + 数字/专名一致）
  final     终稿整合与四类终检
  run       一条命令跑完七段，产出 7 JSON + final.md/html + manifest
  audit     对已落盘产物做独立复核
"""
from __future__ import annotations

import os
from typing import Any, Dict

from content_chain import (draft as draft_stage, final as final_stage,
                           outline as outline_stage, research as research_stage,
                           review as review_stage, rewrite as rewrite_stage,
                           runner, topic as topic_stage)
from content_chain.common import FILES, read_json, write_json, write_text

from . import _common as c

NAME = "content_chain"
DESC = "内容生产线：topic/research/outline/draft/review/rewrite/final/run/audit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    t = act.add_parser("topic", help="选题候选")
    t.add_argument("--input", required=True, help="brief JSON")
    t.add_argument("--out", default="")

    r = act.add_parser("research", help="证据台账")
    r.add_argument("--brief", required=True)
    r.add_argument("--topic", required=True)
    r.add_argument("--out", default="")

    o = act.add_parser("outline", help="细纲契约")
    o.add_argument("--brief", required=True)
    o.add_argument("--research", required=True)
    o.add_argument("--out", default="")

    d = act.add_parser("draft", help="单节三候选")
    d.add_argument("--brief", required=True)
    d.add_argument("--outline", required=True)
    d.add_argument("--research", required=True)
    d.add_argument("--out", default="")

    v = act.add_parser("review", help="五维 findings")
    v.add_argument("--input", required=True, help="drafts.json")
    v.add_argument("--out", default="")

    w = act.add_parser("rewrite", help="单元改写")
    w.add_argument("--brief", required=True)
    w.add_argument("--input", required=True, help="drafts.json")
    w.add_argument("--review", required=True)
    w.add_argument("--out", default="")

    f = act.add_parser("final", help="终稿整合与终检")
    f.add_argument("--brief", required=True)
    f.add_argument("--outline", required=True)
    f.add_argument("--research", required=True)
    f.add_argument("--rewrite", required=True)
    f.add_argument("--out", default="")

    run = act.add_parser("run", help="一条命令跑完七段")
    run.add_argument("--input", required=True, help="brief JSON")
    run.add_argument("--out", default="")

    a = act.add_parser("audit", help="独立复核已落盘产物")
    a.add_argument("--out", required=True)


def _emit(artifact: Dict[str, Any], out: str, stage: str) -> Dict[str, Any]:
    if out:
        write_json(os.path.join(out, FILES[stage]), artifact)
    return artifact


def run(args) -> Dict[str, Any]:
    action = getattr(args, "action", "")
    if action == "topic":
        return _emit(topic_stage.build(c.load_json(args.input)),
                     args.out, "topic")
    if action == "research":
        return _emit(research_stage.build(c.load_json(args.topic), c.load_json(args.brief)),
                     args.out, "research")
    if action == "outline":
        return _emit(outline_stage.build(c.load_json(args.research), c.load_json(args.brief)),
                     args.out, "outline")
    if action == "draft":
        return _emit(draft_stage.build(c.load_json(args.outline),
                                       c.load_json(args.research),
                                       c.load_json(args.brief)), args.out, "draft")
    if action == "review":
        return _emit(review_stage.build(c.load_json(args.input)), args.out, "review")
    if action == "rewrite":
        return _emit(rewrite_stage.build(c.load_json(args.input),
                                         c.load_json(args.review),
                                         c.load_json(args.brief)), args.out, "rewrite")
    if action == "final":
        brief = c.load_json(args.brief)
        outline = c.load_json(args.outline)
        research = c.load_json(args.research)
        rewrite = c.load_json(args.rewrite)
        text = final_stage.compose({}, rewrite, research, brief)
        audit = final_stage.audit(text, outline, research, brief)
        if args.out:
            write_text(os.path.join(args.out, "final.md"), text)
            write_text(os.path.join(args.out, "final.html"),
                       final_stage.render_html(text, audit))
            write_json(os.path.join(args.out, FILES["final"]), audit)
        return audit
    if action == "run":
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.input)), "outputs")
        return runner.run(args.input, out)
    if action == "audit":
        return runner.audit_dir(args.out)
    return {"ok": False, "error": "未知动作: %s" % action}
