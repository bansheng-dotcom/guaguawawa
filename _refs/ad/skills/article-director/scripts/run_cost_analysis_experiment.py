import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import read_json, write_json


def normalize_scenario(item: dict, baseline_cost: float) -> dict:
    if not item:
        return {}
    total_cost = float(item.get("total_cost", 0.0) or 0.0)
    savings_pct = round((baseline_cost - total_cost) / baseline_cost * 100, 2) if baseline_cost else 0.0
    return {
        "experiment": item.get("experiment", ""),
        "name": item.get("name", ""),
        "total_tokens": item.get("total_tokens", 0),
        "total_cost": total_cost,
        "savings_pct_vs_baseline": savings_pct,
        "task_count": len(item.get("tasks", [])),
        "models": sorted({task.get("model", "") for task in item.get("tasks", []) if task.get("model")}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic experiment runs from normalized manifests")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    rebuilt_root = project_root / "tmp" / "multi_model_experiment" / "rebuilt"
    manifest = read_json(rebuilt_root / "experiment_manifest.json", {})
    baseline = manifest.get("baseline", {})
    baseline_cost = float(baseline.get("total_cost", 0.0) or 0.0)

    runs_dir = rebuilt_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    normalized = {
        "topic_id": args.topic_id,
        "baseline": normalize_scenario(baseline, baseline_cost),
        "scenarios": [normalize_scenario(item, baseline_cost) for item in manifest.get("scenarios", []) if item],
        "source_files": manifest.get("source_files", []),
    }
    output_path = runs_dir / "normalized_runs.json"
    write_json(output_path, normalized)
    print(output_path)


if __name__ == "__main__":
    main()
