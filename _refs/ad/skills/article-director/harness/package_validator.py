"""
package_validator — 分包输出校验

对应 data-analysis-report-agent/harness/data_validator.py。
校验 writer 和 adversarial-reviewer 的包输出质量。

设计原则：
- 校验 against section-manifest（每个 section 的目标字数、结构要求）
- 硬约束：字数范围、section 覆盖、ai-tone-director 确定性证据词
- 软约束：tutorial step 结构（WARNING 而非 FAIL）
- 错误累积返回，不 raise
"""

import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from config import MIN_SECTION_CHAR_RATIO, MAX_SECTION_CHAR_RATIO, FORBIDDEN_ZH, FORBIDDEN_EN


def validate_package(
    package_text: str,
    section_manifest: dict,
    package_id: str,
    strategy: str = "knowledge-explainer",
) -> tuple[bool, list[str]]:
    """
    校验单个 writer 包输出。

    Args:
        package_text: writer 包的输出文本（Markdown）
        section_manifest: section-manifest.json 内容
        package_id: 包 ID（如 "package-01"）
        strategy: 当前策略

    Returns:
        (is_valid, errors)
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not package_text or not package_text.strip():
        return False, [f"包 {package_id} 输出为空"]

    # ── 1. 获取该包应覆盖的 section ──
    packages = section_manifest.get("packages", [])
    package = next((p for p in packages if p.get("package_id") == package_id), None)

    if package is None:
        # 如果 manifest 中没有该包信息，尝试从 sections 推断
        sections = section_manifest.get("sections", [])
        if not sections:
            return False, [f"section-manifest 中无 sections 数据"]
        expected_sections = sections
    else:
        section_ids = package.get("section_ids", [])
        section_map = {s["section_id"]: s for s in section_manifest.get("sections", [])}
        expected_sections = [section_map[sid] for sid in section_ids if sid in section_map]

    # ── 2. 字数检查 ──
    clean_chars = len(re.sub(r"[\s#>*`\-\[\]\(\)\|]", "", package_text))
    total_target = sum(int(s.get("target_word_count", 0) or 0) for s in expected_sections)

    if total_target > 0:
        ratio = clean_chars / max(total_target, 1)
        if ratio < MIN_SECTION_CHAR_RATIO:
            errors.append(
                f"包 {package_id} 字数过少：{clean_chars} 字，"
                f"目标 {total_target} 字，比率 {ratio:.2f} < 下限 {MIN_SECTION_CHAR_RATIO}"
            )
        elif ratio > MAX_SECTION_CHAR_RATIO:
            warnings.append(
                f"包 {package_id} 字数偏多：{clean_chars} 字，"
                f"目标 {total_target} 字，比率 {ratio:.2f} > 上限 {MAX_SECTION_CHAR_RATIO}"
            )

    # ── 3. Section block 覆盖检查 ──
    blocks = _split_section_blocks(package_text)
    if expected_sections and len(blocks) < len(expected_sections):
        errors.append(
            f"包 {package_id} section 块数不足：{len(blocks)} 块，"
            f"期望 {len(expected_sections)} 块"
        )

    # ── 4. ai-tone-director 确定性证据词检查 ──
    forbidden_hits = _check_forbidden_words(package_text)
    if forbidden_hits:
        errors.append(f"包 {package_id} 命中 AI 味确定性证据词：{', '.join(forbidden_hits[:5])}")

    # ── 5. Tutorial step 合约检查（teaching-playbook 策略）──
    if strategy == "teaching-playbook" and expected_sections:
        for section in expected_sections:
            if section.get("recommended_presentation") == "procedural-steps":
                _check_tutorial_contract(package_text, section, errors)

    is_valid = len(errors) == 0
    return is_valid, errors


def _split_section_blocks(text: str) -> list[tuple[str, str]]:
    """将文本按二级标题拆分为 section blocks"""
    blocks = []
    current_heading = ""
    current_lines = []

    for line in text.split("\n"):
        if re.match(r"^##\s+", line):
            if current_heading or current_lines:
                blocks.append((current_heading, "\n".join(current_lines)))
            current_heading = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading or current_lines:
        blocks.append((current_heading, "\n".join(current_lines)))

    return blocks


def _check_forbidden_words(text: str) -> list[str]:
    """检查 ai-tone-director 确定性证据词，返回命中列表"""
    hits = []
    for word in FORBIDDEN_ZH:
        if word in text:
            hits.append(f"[中]'{word}'")
    for word in FORBIDDEN_EN:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            hits.append(f"[英]'{word}'")
    return hits


def _check_tutorial_contract(text: str, section: dict, errors: list[str]) -> None:
    """检查 tutorial 类 section 的步骤结构"""
    required_markers = ["前提", "操作", "预期", "失败", "排查", "下一步"]
    marker_hits = sum(1 for marker in required_markers if marker in text)
    if marker_hits < 2 and "|" not in text:
        heading = section.get("heading", "unknown")
        errors.append(f"tutorial step 结构不足：section '{heading}' 缺少步骤标记")
