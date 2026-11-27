"""
outline_validator — 大纲输出校验

对应 data-analysis-report-agent/harness/plan_validator.py。
校验 topic-architect 输出的大纲质量。

设计原则：
- 错误累积返回，不 raise（允许 LLM 自修正）
- 硬约束由代码断言，非 prompt 软提示
- LLM 不可覆盖校验规则
"""

import re
import sys
from pathlib import Path

# 确保可以导入 config
_SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from config import MIN_CHARS_SHORT, FORBIDDEN_ZH


def validate_outline(outline_text: str, strategy: str = "knowledge-explainer") -> tuple[bool, list[str]]:
    """
    校验大纲输出。

    Args:
        outline_text: topic-architect 输出的大纲文本（Markdown）
        strategy: 当前策略（knowledge-explainer / teaching-playbook）

    Returns:
        (is_valid, errors)
        is_valid=False 表示存在结构性问题，需要修正
    """
    errors: list[str] = []

    if not outline_text or not outline_text.strip():
        return False, ["大纲为空"]

    # ── 1. 必须包含至少一个一级标题 ──
    h1_count = len(re.findall(r"^#\s+.+", outline_text, re.MULTILINE))
    if h1_count < 1:
        errors.append("缺少一级标题（# 开头），至少需要 1 个")

    # ── 2. 必须包含至少 3 个二级标题 ──
    h2_count = len(re.findall(r"^##\s+.+", outline_text, re.MULTILINE))
    if h2_count < 3:
        errors.append(f"二级标题不足：{h2_count} 个，至少需要 3 个（结构骨架）")

    # ── 3. 字数下限 ──
    clean_text = re.sub(r"[#\*\-\|\>\`\[\]\(\)\~\s]", "", outline_text)
    if len(clean_text) < MIN_CHARS_SHORT:
        errors.append(f"大纲字数不足：{len(clean_text)} 字，下限 {MIN_CHARS_SHORT} 字")

    # ── 4. 策略关键 section 检查 ──
    if strategy == "knowledge-explainer":
        _check_knowledge_sections(outline_text, errors)
    elif strategy == "teaching-playbook":
        _check_teaching_sections(outline_text, errors)

    # ── 5. ai-tone-director 确定性证据词检查 ──
    _check_forbidden_words(outline_text, errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def _check_knowledge_sections(text: str, errors: list[str]) -> None:
    """knowledge-explainer 策略：必须有「问题」「概念」「机制」类 section"""
    lower = text.lower()
    has_problem = bool(re.search(r"问题|为什么|原因|背景|动机", text))
    has_concept = bool(re.search(r"概念|定义|是什么|含义|本质", text))
    has_mechanism = bool(re.search(r"机制|原理|如何|怎么|方法|实现", text))

    missing = []
    if not has_problem:
        missing.append("问题/背景")
    if not has_concept:
        missing.append("概念/定义")
    if not has_mechanism:
        missing.append("机制/原理")
    if missing:
        errors.append(f"knowledge-explainer 策略缺少关键 section：{'、'.join(missing)}")


def _check_teaching_sections(text: str, errors: list[str]) -> None:
    """teaching-playbook 策略：必须有「步骤」类 section"""
    has_steps = bool(re.search(r"步骤|操作|实践|动手|实战|step", text, re.IGNORECASE))
    if not has_steps:
        errors.append("teaching-playbook 策略缺少「步骤/操作/实践」类 section")


def _check_forbidden_words(text: str, errors: list[str]) -> None:
    """检查 ai-tone-director 确定性证据词"""
    hits = [word for word in FORBIDDEN_ZH if word in text]
    if hits:
        errors.append(f"大纲命中 AI 味确定性证据词：{', '.join(hits[:5])}")
