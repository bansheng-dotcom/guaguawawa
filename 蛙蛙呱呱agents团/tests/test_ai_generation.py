# -*- coding: utf-8 -*-
"""R10 生成类能力测试：AI Hive 生图适配（S12）与 MiniMax H3 提示词（S13）。

只测确定性部分：不联网、不扣费、不需要 API Key。
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R10 = os.path.join(ROOT, "r10-wachengmei-design")
if R10 not in sys.path:
    sys.path.insert(0, R10)

from skills import s12_aihive, s13_h3prompt  # noqa: E402


def _t2va(**over):
    spec = {
        "mode": "t2va",
        "duration_sec": 8.0,
        "style": "Live-action, cinematic",
        "shots": [
            {"start_sec": 0.0, "text": "a wide shot frames a courier at the alley entrance."},
            {"start_sec": 3.5, "text": "the camera cuts to a close-up of a paper bag."},
        ],
        "soundscape": "Traffic hum, a bicycle bell, footsteps.",
        "music": "Sparse solo piano, unhurried.",
    }
    spec.update(over)
    return spec


def _build(spec):
    args = SimpleNamespace(action="build", input="x.json", out=None)
    checks, prompt, meta = s13_h3prompt._compose(spec)
    ok = all(c["ok"] for c in checks)
    return ok, checks, prompt, meta


# --------------------------------------------------------------------------- #
# H3 提示词
# --------------------------------------------------------------------------- #
def test_t2va_structure_and_timestamps():
    ok, checks, prompt, meta = _build(_t2va())
    assert ok, [c for c in checks if not c["ok"]]
    lines = prompt.splitlines()
    assert lines[0].startswith("integrated_multimodal_description: [Shot 1] ")
    assert "At 00:03.500" in prompt
    assert "overall_soundscape:" in prompt and "non_diegetic_music:" in prompt
    assert prompt.index("overall_soundscape:") < prompt.index("non_diegetic_music:")
    assert meta["shot_count"] == 2 and meta["duration_sec"] == 8.0


def test_i2va_requires_first_frame_instruction_and_label():
    # 没有参考标签 → 必须 FAIL
    ok, checks, _, _ = _build(_t2va(mode="i2va"))
    assert not ok
    assert any(c["dim"] == "h3.refs.required" for c in checks if not c["ok"])

    # 给了 <Picture 1> → PASS，且首行是关键帧指令
    ok2, checks2, prompt2, _ = _build(_t2va(
        mode="i2va",
        references=[{"label": "Picture 1", "role": "first_frame", "shot": 1}],
    ))
    assert ok2, [c for c in checks2 if not c["ok"]]
    assert prompt2.startswith("For the target video, at 0.00 seconds")


def test_fl2va_and_l2va_instruction_use_two_decimal_end():
    for mode in ("fl2va", "l2va"):
        spec = _t2va(mode=mode, references=[
            {"label": "Picture 1", "role": "first_frame", "shot": 1},
            {"label": "Picture 2", "role": "last_frame", "shot": 2},
        ])
        ok, checks, prompt, _ = _build(spec)
        assert ok, [c for c in checks if not c["ok"]]
        assert prompt.startswith("How the reference pictures align with the target video")
        assert "8.00-second" in prompt or "8.00" in prompt


@pytest.mark.parametrize("spec_patch", [
    {"duration_sec": 20.0},
    {"shots": []},
    {"soundscape": ""},
    {"music": ""},
    {"shots": [{"start_sec": 0.0, "text": "a shot"},
               {"start_sec": 0.0, "text": "another shot"}]},
])
def test_invalid_specs_fail(spec_patch):
    ok, checks, __, _ = _build(_t2va(**spec_patch))
    assert not ok
    assert any(not c["ok"] for c in checks)


def test_dialogue_requires_speaker_and_language_tag():
    spec = _t2va()
    spec["shots"][1]["text"] = "the close-up shows a letter, <d>[English] I get off here.</d>"
    ok, checks, __, _ = _build(spec)
    assert not ok
    assert any(c["dim"] == "h3.dialogue.speaker" for c in checks if not c["ok"])


def test_on_screen_text_must_be_quoted():
    spec = _t2va(on_screen_text=["营业中"])
    ok, checks, __, _ = _build(spec)
    assert not ok
    assert any(c["dim"] == "h3.on_screen_text" for c in checks if not c["ok"])


def test_ref2va_six_sections_in_order():
    spec = {
        "mode": "ref2va",
        "duration_sec": 10.0,
        "shots": [{"start_sec": 0.0, "text": "a shot"}],
        "references": [{"label": "Picture 1", "role": "subject"}],
        "sections": {
            "subject_definitions": "<Picture 1> defines the woman in a blue coat.",
            "summary": "A short walk becomes a conversation.",
            "retention_analysis": "<Picture 1> identity and coat color retained throughout.",
            "detailed_description": "[Shot 1] The woman from <Picture 1> walks...",
            "overall_soundscape": "Footsteps and wind.",
            "non_diegetic_music": "Warm strings, low mix.",
        },
    }
    ok, checks, prompt, _ = _build(spec)
    assert ok, [c for c in checks if not c["ok"]]
    order = [prompt.index(f"{k}:") for k in s13_h3prompt.REF2VA_SECTIONS]
    assert order == sorted(order)


# --------------------------------------------------------------------------- #
# AI Hive 生图适配
# --------------------------------------------------------------------------- #
def test_aihive_probe_reports_blocked_without_key(monkeypatch):
    monkeypatch.delenv("AI_HIVE_API_KEY", raising=False)
    monkeypatch.setenv("HOME", os.path.join(ROOT, ".nonexistent-home"))
    out = s12_aihive.run(SimpleNamespace(action="probe"))
    assert out["status"] in ("ready", "blocked")
    assert out["model"] == "public_model_nano_banana_pro"
    key_check = next(c for c in out["checks"] if c["dim"] == "aihive.key")
    assert key_check["ok"] is False


def test_aihive_preview_never_runs_and_caps_batch():
    ok_args = SimpleNamespace(action="preview", prompt="高级商业摄影风格", image=None,
                              batch=2, param=None, output_dir=None, routing="COST_FIRST")
    out = s12_aihive.run(ok_args)
    assert out["verdict"] == "PASS"
    assert out["model"] == "public_model_nano_banana_pro"
    assert "imagegen.py" in out["command"] and "--batch 2" in out["command"]

    too_big = SimpleNamespace(action="preview", prompt="x", image=None,
                              batch=9, param=None, output_dir=None, routing="COST_FIRST")
    out2 = s12_aihive.run(too_big)
    assert out2["verdict"] == "FAIL"


def test_aihive_generate_blocks_without_confirmation():
    args = SimpleNamespace(action="generate", prompt="x", image=None, batch=1,
                           param=None, output_dir=None, routing="COST_FIRST",
                           no_download=False, yes=False, allow_batch=False, timeout=5)
    out = s12_aihive.run(args)
    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert any(c["dim"] == "aihive.confirm" and not c["ok"] for c in out["checks"])
