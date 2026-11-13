# -*- coding: utf-8 -*-
"""契约测试：每个技能动作都有可校验的输入/输出 schema 登记。

契约 API 缺失时不得静默通过（历史版本用 `if not hasattr(...): return`
早退，等于断言空转），这里一律硬断言。
"""
import importlib


def test_contracts_module_importable(role_dir):
    importlib.import_module("contracts")


def test_contracts_api_complete(role_dir):
    import contracts
    for name in ("skill_names", "get", "actions", "validate_input",
                 "validate_output", "output_schema"):
        assert hasattr(contracts, name), f"契约模块缺少 API: {name}"


def test_actions_enumerable(role_dir):
    import contracts
    names = contracts.skill_names()
    assert names, "契约表不得为空"
    assert len(names) >= 8, f"契约应至少覆盖 8 个核心技能（只增不减），实际 {len(names)}"
    total_actions = 0
    for skill in names:
        entry = contracts.get(skill)
        assert entry, f"契约 {skill} 缺定义"
        actions = contracts.actions(skill)
        assert actions, f"契约 {skill} 未登记任何动作"
        total_actions += len(actions)
        for action in actions:
            assert contracts.output_schema(skill, action), \
                f"{skill}/{action} 缺输出 schema"
            assert contracts.input_schema(skill, action), \
                f"{skill}/{action} 缺输入 schema"
    assert total_actions >= 29, f"动作总数应至少 29（只增不减），实际 {total_actions}"


def test_validate_output_rejects_bad_payload(role_dir):
    import contracts
    names = contracts.skill_names()
    first = names[0]
    actions = contracts.actions(first)
    out = contracts.validate_output(first, actions[0], {})
    assert out.get("ok") is False, "空 payload 必须判不通过"
    assert out.get("errors"), "不通过必须给出具体错误"


def test_validate_input_and_unknown_action(role_dir):
    import contracts
    bad = contracts.validate_output("prd", "not_exist", {"ok": True})
    assert bad["ok"] is False and bad["errors"]
    ok = contracts.validate_input("prd", "prd", {"problem_statement": "x"})
    assert ok["ok"] is True
