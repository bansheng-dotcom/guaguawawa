"""
harness — article-director 校验模块

三层防御模式（参考 data-analysis-report-agent/harness/）：
  Layer 1: outline_validator  — 大纲输出校验（对应 plan_validator）
  Layer 2: package_validator  — 分包输出校验（对应 data_validator）
  Layer 3: article_validator  — 终稿校验（对应 output_validator）

所有校验函数返回 (is_valid: bool, errors: list[str])。
错误累积在 list 中，不 raise，允许调用方将错误反馈给 LLM 修正。
"""

from .outline_validator import validate_outline
from .package_validator import validate_package
from .article_validator import validate_article

__all__ = ["validate_outline", "validate_package", "validate_article"]
