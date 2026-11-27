import argparse
import re
from pathlib import Path


LABEL_MAP = {
    "论点": "论点:",
    "读者卡点": "读者卡点:",
    "上下游承接": "上下游承接:",
    "逻辑难点": "逻辑难点:",
    "需要解释": "需要解释:",
    "需要引用": "需要引用:",
    "需要案例": "需要案例:",
    "提示词样例": "提示词样例:",
    "规范化前后": "规范化前后:",
    "展示方式": "展示方式:",
    "writer可执行信息": "writer可执行信息:",
    "写作执行信息": "writer可执行信息:",
    "待研究": "待研究:",
}


def normalize_line(line: str) -> str:
    stripped = line.strip()
    for raw, normalized in LABEL_MAP.items():
        patterns = [
            rf"^\*\*{re.escape(raw)}[：:]\*\*\s*$",
            rf"^\*\*{re.escape(raw)}[：:]\*\*\s+",
            rf"^{re.escape(raw)}[：:]\s*$",
            rf"^{re.escape(raw)}[：:]\s+",
        ]
        for pattern in patterns:
            if re.match(pattern, stripped):
                remainder = re.sub(pattern, "", stripped, count=1).strip()
                return normalized if not remainder else f"{normalized} {remainder}"
    return line.rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize detailed outline labels to stable machine-readable tags")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    path = project_root / "tmp" / f"{args.topic_id}-detailed-outline.md"
    if not path.exists():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")
    normalized_lines = [normalize_line(line) for line in text.splitlines()]
    path.write_text("\n".join(normalized_lines).rstrip() + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
