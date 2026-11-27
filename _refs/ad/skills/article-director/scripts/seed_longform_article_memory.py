import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir


TOPIC_CATALOG = {
    "supervisor-mode": {
        "updated_at": "2026-05-21",
        "terms": [
            {
                "term": "Supervisor",
                "plain_explanation": "负责理解总任务、派发子任务、检查中间结果，并在必要时回退或重规划的中心 agent。",
                "deep_dive_required": True,
                "chapter_hint": "Supervisor 到底是什么",
            },
            {
                "term": "Router",
                "plain_explanation": "更接近一次性分流器，主要判断请求该送去哪里，不负责长流程闭环。",
                "deep_dive_required": True,
                "chapter_hint": "它和 Router、Pipeline、Swarm 的区别",
            },
            {
                "term": "Pipeline",
                "plain_explanation": "按固定顺序执行的一条链路，稳定但灵活性有限。",
                "deep_dive_required": False,
                "chapter_hint": "它和 Router、Pipeline、Swarm 的区别",
            },
            {
                "term": "Swarm / Handoff",
                "plain_explanation": "更分布式的 agent 协作方式，强调 agent 之间自主交接任务。",
                "deep_dive_required": False,
                "chapter_hint": "它和 Router、Pipeline、Swarm 的区别",
            },
            {
                "term": "Harness",
                "plain_explanation": "位于流程中的硬校验层，用来检查格式、字段、规则和数值是否满足要求。",
                "deep_dive_required": False,
                "chapter_hint": "数据分析Skill教学体系",
            },
            {
                "term": "Orchestrator",
                "plain_explanation": "持续跟踪进度、必要时改计划的上层控制者，很多框架里它就是 supervisor 的工程化名字。",
                "deep_dive_required": True,
                "chapter_hint": "理论依据",
            },
            {
                "term": "LangGraph",
                "plain_explanation": "把多步 agent 任务写成状态图和执行流程的开源运行时，适合表达节点、状态、分支和回退。",
                "deep_dive_required": True,
                "chapter_hint": "为什么会自然引出 LangGraph",
            },
            {
                "term": "CrewAI",
                "plain_explanation": "强调 manager 与 worker 分工的多 agent 工作流框架，常用来快速搭层级式协作。",
                "deep_dive_required": False,
                "chapter_hint": "开源实现",
            },
            {
                "term": "AutoGen",
                "plain_explanation": "微软开源的多 agent 对话框架，强调消息协议、角色交互和工具协作。",
                "deep_dive_required": False,
                "chapter_hint": "理论依据",
            },
            {
                "term": "Magentic-One",
                "plain_explanation": "AutoGen 路线下更接近通用 supervisor 的系统，突出总计划、进度账本和重规划。",
                "deep_dive_required": True,
                "chapter_hint": "理论依据",
            },
        ],
        "sources": [
            {
                "title": "Large Language Model based Multi-Agents: A Survey of Progress and Challenges",
                "url": "https://arxiv.org/abs/2402.01680",
                "note": "适合建立多 agent 研究的全景地图，理解 supervisor 属于更大协作版图中的哪一层。",
            },
            {
                "title": "Multi-Agent Collaboration Mechanisms: A Survey of LLMs",
                "url": "https://arxiv.org/abs/2501.06322",
                "note": "适合支撑“supervisor 不是唯一答案，而是中心化协作结构的一种实现”这个判断。",
            },
            {
                "title": "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation",
                "url": "https://arxiv.org/abs/2308.08155",
                "note": "适合解释为什么多 agent 先要有消息协议和角色交互约束，supervisor 才能真正管得住流程。",
            },
            {
                "title": "Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks",
                "url": "https://arxiv.org/abs/2411.04468",
                "note": "这篇最适合支撑“supervisor 不只是派活器，而是持续控制回路”这个核心论点。",
            },
            {
                "title": "Magentic-One Docs",
                "url": "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html",
                "note": "适合看 orchestrator、progress tracking 与 re-plan 在真实系统里的工程写法。",
            },
            {
                "title": "PANGAEA-GPT",
                "url": "https://arxiv.org/abs/2602.21351",
                "note": "适合把 supervisor 和类型路由、确定性执行、执行反馈、自修正这些硬约束连起来。",
            },
            {
                "title": "langchain-ai/langgraph",
                "url": "https://github.com/langchain-ai/langgraph",
                "note": "LangGraph 的源码入口，适合确认状态图、多节点控制和人工闸门如何落地。",
            },
            {
                "title": "crewAIInc/crewAI",
                "url": "https://github.com/crewAIInc/crewAI",
                "note": "CrewAI 的源码入口，适合理解 hierarchical process 和 manager 式编排。",
            },
            {
                "title": "microsoft/autogen",
                "url": "https://github.com/microsoft/autogen",
                "note": "AutoGen 的源码入口，适合理解多 agent 对话协议、角色协同和 Magentic-One 所在生态。",
            },
        ],
        "reading_order": [
            "先看 2024 和 2025 两篇综述，建立 supervisor 在多 agent 结构里的位置。",
            "再看 AutoGen 与 Magentic-One，理解真正可运行的 supervisor 为什么离不开协议、进度跟踪和重规划。",
            "最后看 LangGraph、CrewAI、AutoGen 三条开源路线，区分状态图 runtime、manager 流程和对话协议框架的差别。",
        ],
        "reader_questions": [
            "为什么 agent 一多，系统反而更容易乱？",
            "Supervisor 和 router 到底差在哪里？",
            "什么时候需要 supervisor，什么时候只是过度设计？",
            "为什么这件事会自然引出 LangGraph？",
        ],
    },
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip()).strip(" -:：")


def first_meaningful_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" -:：")
    if not cleaned:
        return ""
    pieces = re.split(r"[。！？!?]", cleaned)
    for piece in pieces:
        piece = piece.strip(" -:：")
        if len(piece) >= 8:
            return piece + "。"
    return cleaned[:80] + ("…" if len(cleaned) > 80 else "")


def collect_fallback_terms(topic_id: str, project_root: Path) -> list[dict]:
    detailed_outline = project_root / "tmp" / f"{topic_id}-detailed-outline.md"
    if not detailed_outline.exists():
        return []
    terms: list[dict] = []
    appendix_section = False
    for raw_line in detailed_outline.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            appendix_section = "附录" in line
            continue
        if appendix_section and line.startswith("- "):
            term = normalize_term(line[2:])
            if term:
                terms.append(
                    {
                        "term": term,
                        "plain_explanation": "需要结合正文与来源再解释的核心术语。",
                        "deep_dive_required": False,
                        "chapter_hint": "附录",
                    }
                )
    deduped = []
    seen = set()
    for item in terms:
        key = item["term"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def collect_fallback_sources(topic_id: str, project_root: Path) -> tuple[list[dict], list[str]]:
    files = [
        project_root / "tmp" / f"{topic_id}-research.md",
        project_root / "tmp" / f"{topic_id}-paper-close-reading.md",
    ]
    sources: list[dict] = []
    reading_order: list[str] = []
    seen = set()
    for path in files:
        if not path.exists():
            continue
        current_heading = path.stem
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("#"):
                current_heading = normalize_term(re.sub(r"^#+\s*", "", line))
                continue
            match = re.search(r"(https?://\S+)", line)
            if not match:
                continue
            url = match.group(1).rstrip(")。,，")
            title = line.replace(url, "").strip(" -:：")
            title = title or current_heading or url
            key = (title, url)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "title": title,
                    "url": url,
                    "note": f"和“{current_heading}”直接相关，适合回到原始资料核对定义、机制或案例。",
                }
            )
    if sources:
        reading_order = [
            "先看综述或总览资料，确认这个主题在多 agent 版图中的位置。",
            "再看最能支撑核心论点的论文或官方文档。",
            "最后看开源仓库，确认它在工程上是怎样落地的。",
        ]
    return sources, reading_order


def write_source_map(path: Path, payload: dict) -> None:
    lines = ["# Source Map", "", f"更新时间：`{payload['updated_at']}`", "", "## 官方资料", ""]
    for source in payload["sources"]:
        lines.append(f"- `{source['title']}`  ")
        lines.append(f"  {source['url']}")
        lines.append(f"  - {source['note']}")
    lines.extend(["", "## 延伸阅读顺序", ""])
    for item in payload["reading_order"]:
        lines.append(f"- {item}")
    write_text(path, "\n".join(lines))


def write_reader_questions(path: Path, questions: list[str]) -> None:
    lines = ["# Reader Questions", ""]
    for item in questions:
        lines.append(f"- {item}")
    write_text(path, "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed longform appendix memory for article-director")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    memory_dir = project_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    payload = TOPIC_CATALOG.get(args.topic_id)
    if payload is None:
        fallback_sources, fallback_reading_order = collect_fallback_sources(args.topic_id, project_root)
        payload = {
            "updated_at": "2026-05-21",
            "terms": collect_fallback_terms(args.topic_id, project_root),
            "sources": fallback_sources,
            "reading_order": fallback_reading_order,
            "reader_questions": [],
        }

    term_registry = {"topic_id": args.topic_id, "terms": payload["terms"]}
    write_json(memory_dir / "term-registry.json", term_registry)
    write_source_map(memory_dir / "source-map.md", payload)
    write_reader_questions(memory_dir / "reader-questions.md", payload.get("reader_questions", []))

    print(json.dumps(term_registry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
