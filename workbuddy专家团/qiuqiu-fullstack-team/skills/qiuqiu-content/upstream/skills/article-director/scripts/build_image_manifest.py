import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_image_manifest_source, build_project_dir, read_json, write_json


def _find_section_id(section_manifest: dict, keywords: list[str], fallback_index: int) -> tuple[str, str]:
    sections = section_manifest.get("sections", [])
    for section in sections:
        heading = section.get("heading", "")
        body = section.get("body_text", "")
        joined = f"{heading}\n{body}"
        if all(keyword in joined for keyword in keywords):
            return section["section_id"], heading
    if sections:
        index = min(max(fallback_index, 0), len(sections) - 1)
        section = sections[index]
        return section["section_id"], section["heading"]
    return "section-01", "未匹配章节"


def build_topic_specific_manifest(topic_id: str, section_manifest: dict) -> dict | None:
    if topic_id != "multi-model-cost-reduction":
        return None

    workflow_section_id, workflow_heading = _find_section_id(section_manifest, ["数据分析"], 0)
    cost_section_id, cost_heading = _find_section_id(section_manifest, ["成本"], 1)
    experiment_section_id, experiment_heading = _find_section_id(section_manifest, ["实验"], 2)
    routing_section_id, routing_heading = _find_section_id(section_manifest, ["路由"], 3)

    return {
        "topic_id": topic_id,
        "images": [
            {
                "image_id": "image-01",
                "title": "数据分析工作流的多模型分工",
                "design_key": "data-analysis-workflow",
                "target_section_id": workflow_section_id,
                "target_heading": workflow_heading,
                "kind": "diagram",
                "panel_count": 1,
                "data_series_count": 1,
                "node_count": 8,
                "annotation_count": 5,
                "text_block_count": 4,
                "ui_component_count": 8,
                "requires_precise_numbers": False,
                "layout_density": 3,
                "visual_risk_tier": 2,
                "insert_after_heading": workflow_heading,
                "source": workflow_section_id,
                "purpose": "解释在数据加载、指标计算、趋势分析、维度切片、图表说明、总结汇总中，不同模型各自承担的工作。",
            },
            {
                "image_id": "image-02",
                "title": "成本、质量、返工的三因子关系",
                "design_key": "cost-quality-rework",
                "target_section_id": cost_section_id,
                "target_heading": cost_heading,
                "kind": "comparison",
                "panel_count": 2,
                "data_series_count": 3,
                "node_count": 6,
                "annotation_count": 6,
                "text_block_count": 5,
                "ui_component_count": 9,
                "requires_precise_numbers": True,
                "layout_density": 4,
                "visual_risk_tier": 3,
                "insert_after_heading": cost_heading,
                "source": cost_section_id,
                "purpose": "告诉读者为什么只看单价会误判，应同时观察单价、token 和返工。",
            },
            {
                "image_id": "image-03",
                "title": "本地实验的成本对比结果",
                "design_key": "experiment-comparison",
                "target_section_id": experiment_section_id,
                "target_heading": experiment_heading,
                "kind": "chart",
                "panel_count": 1,
                "data_series_count": 7,
                "node_count": 5,
                "annotation_count": 7,
                "text_block_count": 4,
                "ui_component_count": 8,
                "requires_precise_numbers": True,
                "layout_density": 5,
                "visual_risk_tier": 3,
                "insert_after_heading": experiment_heading,
                "source": experiment_section_id,
                "purpose": "展示基线、多种混合方案和压缩方案的成本、token 与节省比例。",
            },
            {
                "image_id": "image-04",
                "title": "模型路由与升级机制",
                "design_key": "routing-escalation",
                "target_section_id": routing_section_id,
                "target_heading": routing_heading,
                "kind": "diagram",
                "panel_count": 1,
                "data_series_count": 1,
                "node_count": 9,
                "annotation_count": 6,
                "text_block_count": 5,
                "ui_component_count": 9,
                "requires_precise_numbers": False,
                "layout_density": 4,
                "visual_risk_tier": 2,
                "insert_after_heading": routing_heading,
                "source": routing_section_id,
                "purpose": "说明如何根据难度、风险、证据要求和结构化程度，把请求送往不同模型，并在失败时升级。",
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic image manifest source")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_manifest = read_json(project_dir / "section-manifest.json", {"topic_id": args.topic_id, "sections": []})
    payload = build_topic_specific_manifest(args.topic_id, section_manifest) or build_image_manifest_source(section_manifest)
    output_path = project_dir / "image-manifest-source.json"
    write_json(output_path, payload)
    print(output_path)


if __name__ == "__main__":
    main()
