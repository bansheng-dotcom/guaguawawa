# -*- coding: utf-8 -*-
"""R02 机制单测：工作流引擎（重试 / 指数退避 / 死信 / 幂等 / 重放）。"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import workflow_engine as wf  # noqa: E402


def test_backoff_is_exponential_and_capped():
    p = wf.default_policy()
    assert [wf.backoff_delay(n, p) for n in (1, 2, 3, 4)] == [2.0, 4.0, 8.0, 16.0]
    capped = dict(p, max_delay_s=10)
    assert wf.backoff_delay(6, capped) == 10.0


def test_policy_rejects_unbounded_retry():
    bad = {"max_retries": 999, "retry_forever": True, "backoff": "exponential",
           "base_delay_s": 2, "max_delay_s": 60}
    codes = {v["code"] for v in wf.check_policy(bad)}
    assert "W01_UNBOUNDED_RETRY" in codes
    no_backoff = {"max_retries": 3, "backoff": "linear", "base_delay_s": 2,
                  "max_delay_s": 60}
    assert "W04_BACKOFF" in {v["code"] for v in wf.check_policy(no_backoff)}


def test_three_states_success_failure_replay():
    run = wf.demo_run()
    states = run["states"]
    assert states["t01-extract"] == "succeeded"
    assert states["t02-map"] == "succeeded"          # 重试 1 次后成功
    assert states["t05-publish"] == "failed" or states["t05-publish"] == "dead_letter"
    assert [d["task_id"] for d in run["dead_letters"]] == ["t05-publish"]
    assert run["outcome"] == "failed"

    replay = wf.replay(run)
    assert replay["outcome"] == "replayed"
    assert replay["replayed"][0]["task_id"] == "t05-publish"
    assert replay["resumed"] == ["t06-notify"]
    assert replay["dead_letters_open"] == []
    assert all(s == "succeeded" for s in replay["states"].values())


def test_idempotency_never_executes_twice():
    policy = wf.default_policy()
    tasks = [
        {"id": "a", "idempotency_key": "k-shared", "depends_on": [], "attempts_fail": 0},
        {"id": "b", "idempotency_key": "k-shared", "depends_on": [], "attempts_fail": 0},
    ]
    run = wf.run_workflow(policy, tasks)
    assert "W03_IDEMPOTENCY" in {v["code"] for v in run["violations"]}
    assert run["states"]["b"] == "succeeded"
    assert "b" in run["deduplicated"]


def test_blocked_dependency_never_runs():
    policy = wf.default_policy()
    tasks = [
        {"id": "a", "idempotency_key": "k-a", "depends_on": [], "attempts_fail": 9},
        {"id": "b", "idempotency_key": "k-b", "depends_on": ["a"], "attempts_fail": 0},
    ]
    run = wf.run_workflow(policy, tasks)
    assert run["states"]["a"] == "failed"
    assert run["states"]["b"] == "blocked"
    assert run["blocked"] == ["b"]


def test_misuse_cases_are_rejected():
    for name in ("unbounded-retry.json", "lost-dead-letter.json"):
        out = wf.check_case(os.path.join(HERE, "misuse", name))
        assert out["rejected"] is True, name
        assert out["as_expected"] is True, (name, out["hit"], out["expect"])


def test_golden_html_contract():
    out = wf.build_goldens()
    assert out["ok"] is True
    for name in ("coo-retry-dlq.html", "coo-process-retro.html"):
        html = open(os.path.join(HERE, "golden", name), encoding="utf-8").read()
        assert "@page" in html and "A4" in html
        assert 'data-theme="light"' in html
        assert html.count("<h1") == 1 and "<thead" in html
        assert "<br" not in html and "italic" not in html
