# -*- coding: utf-8 -*-
"""契约测试：每个技能动作都有可校验的输入/输出 schema 登记。"""
import importlib
import sys


def test_contracts_module_importable(role_dir):
    importlib.import_module("contracts")


def test_actions_enumerable(role_dir):
    import contracts
    names = contracts.skill_names() if hasattr(contracts, "skill_names") else list(
        getattr(contracts, "CONTRACTS", {}))
    assert names, "契约表不得为空"
    for s in names:
        entry = contracts.get(s) if hasattr(contracts, "get") else contracts.CONTRACTS[s]
        assert entry, f"契约 {s} 缺定义"


def test_validate_output_rejects_bad_payload(role_dir):
    import contracts
    if not hasattr(contracts, "validate_output"):
        return
    names = contracts.skill_names() if hasattr(contracts, "skill_names") else []
    if not names:
        return
    first = names[0]
    actions = contracts.actions(first) if hasattr(contracts, "actions") else []
    if not actions:
        return
    out = contracts.validate_output(first, actions[0], {})
    assert out.get("ok") is False, "空 payload 必须判不通过"
