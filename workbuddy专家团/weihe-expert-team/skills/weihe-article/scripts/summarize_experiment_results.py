import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize deterministic experiment results")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    rebuilt_root = project_root / "tmp" / "multi_model_experiment" / "rebuilt"
    normalized = read_json(rebuilt_root / "runs" / "normalized_runs.json", {})
    compression = read_json(rebuilt_root.parent / "experiment_D" / "results.json", [])
    compression_case = read_json(rebuilt_root.parent / "experiment_D" / "data_load.json", {})
    baseline = normalized.get("baseline", {})
    scenarios = normalized.get("scenarios", [])

    best_savings = max((item.get("savings_pct_vs_baseline", 0.0) for item in scenarios), default=0.0)
    payload = {
        "baseline": baseline,
        "scenarios": scenarios,
        "best_savings": best_savings,
        "compression_source": str(rebuilt_root.parent / "experiment_D" / "results.json"),
        "compression_case_source": str(rebuilt_root.parent / "experiment_D" / "data_load.json"),
        "source_files": normalized.get("source_files", []),
        "compression": compression,
        "compression_case": compression_case,
    }
    write_json(rebuilt_root / "summary_table.json", payload)

    lines = [
        "# Experiment Summary",
        "",
        f"- baseline cost: ${baseline.get('total_cost', 0.0):.4f}",
        f"- baseline tokens: {baseline.get('total_tokens', 0)}",
        f"- best scenario savings vs baseline: {best_savings:.2f}%",
        "",
        "| experiment | total_tokens | total_cost | savings_pct_vs_baseline |",
        "|---|---:|---:|---:|",
    ]
    for item in scenarios:
        lines.append(
            f"| {item.get('experiment', '')} | {item.get('total_tokens', 0)} | "
            f"${item.get('total_cost', 0.0):.4f} | {item.get('savings_pct_vs_baseline', 0.0):.2f}% |"
        )
    (rebuilt_root / "summary_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(rebuilt_root / "summary_table.json")


if __name__ == "__main__":
    main()
