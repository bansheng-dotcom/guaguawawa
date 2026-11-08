import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize existing multi-model experiment files")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    raw_root = project_root / "tmp" / "multi_model_experiment"
    out_root = raw_root / "rebuilt"
    out_root.mkdir(parents=True, exist_ok=True)

    baseline = read_json(raw_root / "experiment_1" / "results.json", {})
    exp2 = read_json(raw_root / "experiment_2" / "results.json", {})
    exp3 = read_json(raw_root / "experiment_3" / "results.json", {})
    a3 = read_json(raw_root / "experiment_A3" / "results.json", {})
    b1 = read_json(raw_root / "experiment_B1" / "results.json", {})
    b2 = read_json(raw_root / "experiment_B2" / "results.json", {})
    b3 = read_json(raw_root / "experiment_B3" / "results.json", {})
    experiment_d = read_json(raw_root / "experiment_D" / "results.json", [])

    payload = {
        "topic_id": args.topic_id,
        "baseline_file": str(raw_root / "experiment_1" / "results.json"),
        "source_files": [
            str(raw_root / "experiment_1" / "results.json"),
            str(raw_root / "experiment_2" / "results.json"),
            str(raw_root / "experiment_3" / "results.json"),
            str(raw_root / "experiment_A3" / "results.json"),
            str(raw_root / "experiment_B1" / "results.json"),
            str(raw_root / "experiment_B2" / "results.json"),
            str(raw_root / "experiment_B3" / "results.json"),
            str(raw_root / "experiment_D" / "results.json"),
        ],
        "baseline": baseline,
        "scenarios": [exp2, exp3, a3, b1, b2, b3],
        "compression": experiment_d,
    }
    output_path = out_root / "experiment_manifest.json"
    write_json(output_path, payload)
    print(output_path)


if __name__ == "__main__":
    main()
