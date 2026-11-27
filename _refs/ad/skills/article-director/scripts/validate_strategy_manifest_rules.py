import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import infer_recommended_presentation
from strategy_profiles import get_strategy_profile


TEACHING_EXPECTATIONS = {
    "1. 目标与结果：这件事能不能做，做完后你会得到什么？": "checklist",
    "2. 目标用户与适用边界：你是不是这篇教程的目标读者？": "checklist",
    "3. 基础概念：只解释后面步骤会用到的最小概念集": "checklist",
    "4. 执行路径总览：应该走直连路径还是兼容路径？": "comparison-table",
    "5. 执行步骤 1：确认客户端能力与配置入口": "procedural-steps",
    "7. 执行步骤 3A：直连路径配置——让 Codex 直接指向 DeepSeek": "procedural-steps",
    "8. 执行步骤 3B：兼容路径配置——让 Codex 先接入 EchoBird，再由 EchoBird 连接 DeepSeek": "procedural-steps",
    "11. 代码样例规划：把配置、验证、排查所需样例独立出来": "checklist",
    "12. 附录 A：常见误解与边界声明": "checklist",
    "14. 名词预扫描": "checklist",
}


def validate_teaching_playbook() -> dict:
    get_strategy_profile("teaching-playbook")
    issues: list[str] = []
    passed: list[str] = []
    for heading, expected_mode in TEACHING_EXPECTATIONS.items():
        actual_mode, _, reason = infer_recommended_presentation(
            heading,
            "",
            [],
            [],
            "teaching-playbook",
        )
        if actual_mode != expected_mode:
            issues.append(f"{heading}: expected={expected_mode} actual={actual_mode} reason={reason}")
        else:
            passed.append(f"{heading}: {actual_mode}")
    return {
        "pass": not issues,
        "passed": passed,
        "issues": issues,
        "file": "references/strategies/teaching-playbook.json",
    }


def main() -> None:
    payload = validate_teaching_playbook()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
