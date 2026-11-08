import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json


ALLOWED_STATUS_CODES = {"401", "403", "404", "408", "409", "422", "429", "500", "502", "503", "504", "524"}
ALLOWED_LITERAL_NUMBERS = {"127.0.0.1", "53682", "1", "2", "3", "4", "5"}


def build_allowed_numbers(summary_table: dict) -> set[str]:
    allowed: set[str] = set(ALLOWED_STATUS_CODES) | set(ALLOWED_LITERAL_NUMBERS)
    baseline = summary_table.get("baseline", {})
    for key in ["total_tokens", "total_cost", "savings_pct_vs_baseline", "task_count"]:
        value = baseline.get(key)
        if value is not None:
            allowed.add(str(value))
            if isinstance(value, float):
                allowed.add(f"{value:.4f}")
                allowed.add(f"{value:.2f}")
    for item in summary_table.get("scenarios", []):
        for key in ["total_tokens", "total_cost", "savings_pct_vs_baseline", "task_count"]:
            value = item.get(key)
            if value is not None:
                allowed.add(str(value))
                if isinstance(value, float):
                    allowed.add(f"{value:.4f}")
                    allowed.add(f"{value:.2f}")
    for item in summary_table.get("compression", []):
        for bucket in ["pro", "qwen_normal", "qwen_caveman", "qwen_lowtemp"]:
            value = item.get(bucket, {}).get("tok")
            if value is not None:
                allowed.add(str(value))
    compression_case = summary_table.get("compression_case", {})
    for bucket in ["pro", "qwen_normal", "qwen_caveman", "qwen_lowtemp"]:
        block = compression_case.get(bucket, {})
        for key in ["tok", "cost"]:
            value = block.get(key)
            if value is not None:
                allowed.add(str(value))
                if isinstance(value, float):
                    allowed.add(f"{value:.8f}")
                    allowed.add(f"{value:.4f}")
    return allowed


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify extracted claims against traceable sources")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    claims_path = project_dir / "claim-extract-01" / "output.json"
    summary_table = read_json(project_root / "tmp" / "multi_model_experiment" / "rebuilt" / "summary_table.json", {})
    claims_payload = read_json(claims_path, {"claims": []})
    allowed_numbers = build_allowed_numbers(summary_table)

    issues: list[str] = []
    checked: list[str] = []
    for claim in claims_payload.get("claims", []):
        claim_id = claim["claim_id"]
        numbers = [str(item) for item in claim.get("numbers", [])]
        has_source_marker = bool(claim.get("has_source_marker"))
        claim_kind = claim.get("claim_kind", "")
        has_local_trace = bool(claim.get("has_local_trace"))
        excerpt = str(claim.get("excerpt", ""))

        if claim_kind in {"sourced-assertion", "sourced-numeric"} and has_source_marker:
            checked.append(claim_id)
            continue
        if claim_kind == "observed-status":
            unresolved = [number for number in numbers if number not in allowed_numbers]
            if unresolved:
                issues.append(f"{claim_id} unresolved status codes: {', '.join(unresolved)}")
                continue
            if any(token in excerpt for token in ["返回", "结果", "错误", "超时", "model_not_found", "404", "401", "429", "503", "524"]) or has_local_trace:
                checked.append(claim_id)
                continue
            issues.append(f"{claim_id} observed status lacks diagnostic context")
            continue
        if claim_kind == "traceable-numeric":
            unresolved = [number for number in numbers if number not in allowed_numbers and not number.endswith("%")]
            if unresolved:
                issues.append(f"{claim_id} unresolved numbers: {', '.join(unresolved)}")
                continue
            checked.append(claim_id)
            continue
        issues.append(f"{claim_id} unsupported claim kind: {claim_kind or 'unknown'}")

    output_path = project_dir / "claim-verify-01" / "output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pass": not issues,
        "passed": checked,
        "issues": issues,
        "file": str(claims_path),
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
