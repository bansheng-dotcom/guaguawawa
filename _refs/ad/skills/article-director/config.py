# config.py — article-director 全局配置
# 所有阈值集中于此，修改此文件即可调整系统行为
# 与 workflows/topology.yaml 的 thresholds section 保持同步
#
# 设计参考：data-analysis-report-agent/config.py

# ── LLM 温度 ─────────────────────────────────────────────
# 来源：init_workflow.py NODE_DEFS + compile_expanded_workflow.py
import json
from pathlib import Path

AI_TONE_DIRECTOR_DIR    = Path(r"D:\知识库\skills\内容生产\ai-tone-director")
AI_TONE_PATTERNS_FILE   = AI_TONE_DIRECTOR_DIR / "references" / "deterministic-patterns.json"


def _load_ai_tone_patterns() -> dict:
    if not AI_TONE_PATTERNS_FILE.exists():
        raise FileNotFoundError(f"AI tone deterministic patterns not found: {AI_TONE_PATTERNS_FILE}")
    return json.loads(AI_TONE_PATTERNS_FILE.read_text(encoding="utf-8"))


_AI_TONE_PATTERNS = _load_ai_tone_patterns()

DIRECTOR_TEMP           = 0.00   # director agent：严格审查
TOPIC_ARCHITECT_TEMP    = 0.20   # 选题规划：需要创意但保持稳定
WRITER_TEMP             = 0.30   # 写作 agent：需要创意
ADVERSARIAL_TEMP        = 0.00   # 对抗审查：严格确定性
REVIEW_A_TEMP           = 0.00   # 双审-A：严格
REVIEW_B_TEMP           = 0.15   # 双审-B：读者体验视角
STYLE_HARMONIZER_TEMP   = 0.10   # 风格统一：轻微创意
SECTION_REVIEW_TEMP     = 0.00   # 段落审查：确定性
SECTION_REVISER_TEMP    = 0.30   # 段落修改：保留一定表达弹性

# ── 段落并行与预算 ─────────────────────────────────────
MAX_PARALLEL_SECTIONS   = 3      # 最多同时推进 3 个二级章节
SECTION_SOFT_TOKEN_CAP  = 24000  # 质量优先：软上限，触发上下文压缩/提示
SECTION_HARD_TOKEN_CAP  = 40000  # 质量优先：硬上限，触发人工进度报告

# ── 文章质量阈值 ─────────────────────────────────────────
# 来源：check_article.py + validate_package_output.py + compiler_lib.py
MIN_CHARS               = 2000   # 最少字符数（标准 profile）
MIN_CHARS_SHORT         = 1000   # 最少字符数（短文 profile）
MIN_PACKAGES            = 2      # 最少分包数（compiler_lib.py MIN_ARTICLE_PACKAGES）
MAX_PACKAGES            = 6      # 最多分包数（compiler_lib.py MAX_ARTICLE_PACKAGES）
MIN_SECTION_CHAR_RATIO  = 0.05   # section 最小字符占比（validate_package_output.py）
MAX_SECTION_CHAR_RATIO  = 2.60   # section 最大字符占比（validate_package_output.py）

# ── 双审共识阈值 ─────────────────────────────────────────
# 来源：review_diff.py
REVIEW_SCORE_PASS       = 70     # 双审通过分数线
REVIEW_MAX_RETRIES      = 3      # 双审修订最大重试

# ── 节点重试 ─────────────────────────────────────────────
# 来源：workflow_runner.py mark_failed()
MAX_NODE_RETRIES        = 3      # 单节点最大重试次数
MAX_REVISION_CHAIN      = 5      # 修订链最大长度

# ── 去 AI 味确定性证据词表 ───────────────────────────────
# 唯一事实源：D:\知识库\skills\内容生产\ai-tone-director\references\deterministic-patterns.json
# 这里保留常量名是为了兼容 harness，不在 article-director 内维护词表正文。
FORBIDDEN_ZH = tuple(_AI_TONE_PATTERNS.get("forbidden_zh", []))
FORBIDDEN_EN = tuple(_AI_TONE_PATTERNS.get("forbidden_en", []))

# ── 路径配置 ─────────────────────────────────────────────
STRATEGIES_DIR          = "references/strategies"
SCHEMAS_DIR             = "references/schemas"
PROMPTS_FILE            = "prompts.yaml"
TOPOLOGY_FILE           = "workflows/topology.yaml"
STYLE_PROFILES_DIR      = "style-profiles"
STYLE_GUIDE_FILE        = "style-profiles/style-guide.md"
COGNITIVE_STYLE_GUIDE_FILE = "style-profiles/cognitive-style-guide.md"
AUTHOR_SOUL_FILE        = "style-profiles/author-soul.md"
STYLE_EXEMPLARS_DIR     = "style-profiles/exemplars"
STYLE_ANTI_PATTERNS     = "style-profiles/anti-patterns.json"
AI_TONE_DIRECTOR_SKILL  = str(AI_TONE_DIRECTOR_DIR / "SKILL.md")
AI_TONE_DIRECTOR_INTEGRATION = str(AI_TONE_DIRECTOR_DIR / "workflows" / "article-director-integration.md")
AI_TONE_AUDIT_SCHEMA    = str(AI_TONE_DIRECTOR_DIR / "schemas" / "ai-tone-audit.schema.json")
AI_TONE_REPAIR_TEMPLATE = str(AI_TONE_DIRECTOR_DIR / "templates" / "ai-tone-repair-plan.md")
AI_TONE_REGRESSION_SCHEMA = str(AI_TONE_DIRECTOR_DIR / "schemas" / "ai-tone-regression.schema.json")
AI_TONE_JUDGE_RUBRIC    = AI_TONE_DIRECTOR_SKILL  # deprecated alias; keep for old scripts

# ── 正式存稿配置 ─────────────────────────────────────────
# 人工审批后的正式稿优先进入知识库 docs，而不是旧 platforms/ 目录。
KNOWLEDGE_DOCS_ARCHIVE_DIR = r"D:\知识库\knowledge\docs\知识星球-ai数据分析社区"
DEFAULT_ARTICLE_SERIES_DIR = r"D:\知识库\knowledge\docs\知识星球-ai数据分析社区\大模型工作流系列"
