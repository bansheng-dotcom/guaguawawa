# -*- coding: utf-8 -*-
"""R07 夹具生成器：为 verify_loop 生成 29 干净夹具 + 29 脏夹具。

干净夹具 = 通过对应技能门禁（ok=True）；脏夹具 = 语义负例（ok=False，exit 1），
证明「门禁不是摆设」。夹具是静态 JSON，本脚本只用于重建，非运行路径依赖。

用法：python examples/gen_fixtures.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(os.path.dirname(_HERE))
for _p in (_HERE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _w(name: str, data) -> None:
    p = os.path.join(_HERE, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# S01 discover
# --------------------------------------------------------------------------- #
_w("jobstory.json", {
    "situation": "新用户首次登录", "motivation": "快速上手",
    "outcome": "在 10 分钟内创建第一个项目"})
_w("jobstory_dirty.json", {"situation": "新用户首次登录"})

_w("discover.json", {
    "problem": "新用户不会建首项目", "segment": "SaaS 试用用户",
    "why_now": "激活率偏低",
    "assumptions": [{"risk_type": "value"}],
    "validation_plan": [{"hypothesis": "h", "method": "A/B", "metric": "激活率"}]})
_w("discover_dirty.json", {"problem": "新用户不会建首项目"})

_w("interview.json", {
    "sections": {"opening": {"minutes": 2}, "warmup": {"minutes": 5},
                 "core": {"minutes": 18}, "wrapup": {"minutes": 4}},
    "mom_test_rules": {"no_pitching": True, "listen_ratio_80_20": True,
                       "ask_why_deep": True},
    "note_fields": ["participant", "biggest_pain", "desired_outcome",
                    "willingness_to_pay"]})
_w("interview_dirty.json", {})

# --------------------------------------------------------------------------- #
# S02 ost
# --------------------------------------------------------------------------- #
_w("ost.json", {
    "desired_outcome": "更快完成首个项目",
    "opportunities": [
        {"selected": True, "solutions": [
            {"experiments": [{"hypothesis": "h", "method": "A/B"}]},
            {"experiments": []}, {"experiments": []}]},
        {"selected": True, "solutions": [
            {"experiments": []}, {"experiments": []}, {"experiments": []}]},
        {"selected": False, "solutions": []}],
    "focus": ["opp0", "opp1"]})
_w("ost_dirty.json", {"desired_outcome": "x", "opportunities": []})

_w("poc.json", {"solutions": [
    {"name": "A", "feasibility": 5, "impact": 5, "market_fit": 5},
    {"name": "B", "feasibility": 2, "impact": 2, "market_fit": 2}]})
_w("poc_dirty.json", {"solutions": [
    {"name": "B", "feasibility": 1, "impact": 1, "market_fit": 1}]})

_w("assumption.json", {"assumptions": [
    {"name": "a", "impact": 0.9, "confidence": 0.2, "effort": 1.0}]})
_w("assumption_dirty.json", {"assumptions": []})

_w("research.json", {
    "interview_notes": {"participant": "p", "date": "2026-11-01",
                        "key_jobs": "k", "current_solution": "c",
                        "biggest_pain": "b", "desired_outcome": "d",
                        "willingness_to_pay": "w"},
    "feature_requests": [{"source": "工单", "frequency": "高频"}]})
_w("research_dirty.json", {})

# --------------------------------------------------------------------------- #
# S03 prd
# --------------------------------------------------------------------------- #
_w("story_user.json", {
    "story": "As a user, I want to X, so that Y.",
    "acceptance_criteria": ["a", "b", "c", "d"]})
_w("story_user_dirty.json", {
    "story": "As a user, I want X, so that Y.",
    "acceptance_criteria": ["a"]})

_w("acceptance.json", {"acceptance_criteria": [
    {"given": "g", "when": "w", "then": "t"}]})
_w("acceptance_dirty.json", {"acceptance_criteria": [
    {"given": "g", "when": "w"}]})

_w("prd_dirty.json", {
    "problem_statement": "优化某功能",
    "users": [], "scope": {"p0": [], "non_goals": []}})

# --------------------------------------------------------------------------- #
# S04 priority
# --------------------------------------------------------------------------- #
_w("opportunity.json", {"items": [
    {"name": "a", "importance": 8, "satisfaction": 0.3}]})
_w("opportunity_dirty.json", {"items": []})

_w("ice.json", {"items": [
    {"name": "a", "impact": 5, "confidence": 5, "ease": 5}]})
_w("ice_dirty.json", {})

_w("rice.json", {"items": [
    {"name": "A", "reach": 100, "impact": 0.8, "confidence": 70, "effort": 2}]})
_w("rice_dirty.json", {})

_w("backlog_dirty.json", {"items": [{"title": "缺验收标准", "score": 5}]})

# --------------------------------------------------------------------------- #
# S05 roadmap
# --------------------------------------------------------------------------- #
_w("roadmap.json", {"items": [
    {"segment": "试用户", "outcome": "完成首项目", "business_impact": "激活率+"}]})
_w("roadmap_dirty.json", {})

_w("releasenotes.json", {
    "title": "X v1.0",
    "sections": {"New Features": ["- item"], "Improvements": ["- item"],
                 "Bug Fixes": ["- item"], "Breaking Changes": ["- item"],
                 "Deprecations": ["- item"]}})
_w("releasenotes_dirty.json", {})

_w("premortem.json", {
    "tigers": ["上线即崩"],
    "action_plans": [{"risk": "崩溃", "mitigation": "灰度", "owner": "r09",
                      "due_date": "day-3"}]})
_w("premortem_dirty.json", {})

# --------------------------------------------------------------------------- #
# S06 metrics
# --------------------------------------------------------------------------- #
_w("northstar_dirty.json", {"north_star": "提升用户体验",
                            "input_metrics": ["a"]})

_w("metrics.json", {"metrics": [
    {"layer": "north_star", "definition": "7 日激活率", "data_source": "埋点"},
    {"layer": "input", "definition": "首日完成率", "data_source": "埋点"},
    {"layer": "guardrail", "definition": "引导放弃率", "data_source": "埋点"}]})
_w("metrics_dirty.json", {"metrics": []})

_w("okr.json", {"okr_sets": [
    {"objective": "O", "key_results": [
        {"metric": "m1"}, {"metric": "m2"}, {"metric": "m3"}]},
    {"objective": "O", "key_results": [
        {"metric": "m1"}, {"metric": "m2"}, {"metric": "m3"}]},
    {"objective": "O", "key_results": [
        {"metric": "m1"}, {"metric": "m2"}, {"metric": "m3"}]}],
    "confidence": 65})
_w("okr_dirty.json", {"okr_sets": [], "confidence": 65})

_w("vision.json", {"vision": "让每个团队 10 分钟建好首个项目",
                   "inspiring": "i", "achievable": "a", "emotional": "e",
                   "variants": ["v1", "v2", "v3"]})
_w("vision_dirty.json", {})

_w("canvas.json", {"sections": {
    "problem": "p", "solution": "s", "uvp": "u", "unfair_advantage": "ua",
    "segments": "seg", "channels": "c", "revenue": "r", "cost": "co",
    "key_metrics": "km"}})
_w("canvas_dirty.json", {})

# --------------------------------------------------------------------------- #
# S07 techbrief
# --------------------------------------------------------------------------- #
_w("techbrief.json", {
    "user_impact": "1", "frontend": "1", "backend": "1", "agent": "1",
    "failure": {"who_investigates": "r09", "recovery": "回滚",
                "manual_handling": "工单"}})
_w("techbrief_dirty.json", {})

_w("uibrief.json", {
    "page_goal": "g", "ia": "i", "user_actions": "a", "review_focus": "r",
    "states": {"empty": 1, "loading": 1, "success": 1, "failure": 1,
               "permission": 1}})
_w("uibrief_dirty.json", {})

_w("codetoprd.json", {
    "pages": [{"name": "任务台", "overview": "o",
               "fields": [{"name": "f", "type": "string"}]}],
    "apis": [{"method": "GET", "path": "/x", "business_logic": "b"}]})
_w("codetoprd_dirty.json", {})

_w("releasegate.json", {"checks": [
    {"name": "typecheck", "status": "pass"}, {"name": "e2e", "status": "pass"}]})
_w("releasegate_dirty.json", {"checks": [
    {"name": "security", "status": "block"}]})

# --------------------------------------------------------------------------- #
# S08 decision
# --------------------------------------------------------------------------- #
_w("decision.json", {
    "product_judgment": 1, "execution_spec": 1,
    "decision_gate": {"success": "s", "non_goals": "n", "stop_condition": "stop"}})
_w("decision_dirty.json", {})

_w("demand.json", {
    "demand_id": "D1", "problem": "p", "scope": "s", "non_goals": "n",
    "success_metric": "m", "acceptance": "a", "review_status": "已复核"})
_w("demand_dirty.json", {})

_w("experience.json", {
    "trigger": "t", "scope": "s", "rule": "r", "boundary": "b",
    "source_credibility": "c"})
_w("experience_dirty.json", {})

print("fixtures written to", _HERE)
