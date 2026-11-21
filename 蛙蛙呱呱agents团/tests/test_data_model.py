# -*- coding: utf-8 -*-
"""data_model 自测：行/度量/单位/冲突/覆盖/导出。"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import data_model as dm  # noqa: E402

OK, FAIL = [], []


def check(name, cond, msg=""):
    (OK if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {msg}" if msg and not cond else ""))


def main() -> int:
    nums = [
        {"id": "r05:N1", "name": "中国宠物消费市场规模（城镇犬猫）",
         "value": 3126, "unit": "亿元", "period": "2025", "source_file": "r05:S1"},
        {"id": "r05:N2", "name": "中国宠物消费市场规模（城镇犬猫）",
         "value": 3002, "unit": "亿元", "period": "2024", "source_file": "r05:S1"},
        {"id": "r06:N1", "name": "北京宠物店数量（走访口径）",
         "value": 1.2, "unit": "万家", "period": "2025", "source_file": "r06:S3"},
        # 同键冲突：同指标同城同期不同值
        {"id": "r06:N2", "name": "北京宠物店数量（走访口径）",
         "value": 1.5, "unit": "万家", "period": "2025", "source_file": "r06:S4"},
        {"id": "r03:N1", "name": "毛利率", "value": 45, "unit": "%",
         "period": "2025", "source_file": "r03:S1"},
    ]
    srcs = [{"file": "r05:S1", "grade": "A"}, {"file": "r06:S3", "grade": "B"},
            {"file": "r06:S4", "grade": "C"}, {"file": "r03:S1", "grade": "B"}]
    raw = dm.build_raw(nums, srcs)
    cov = raw["coverage"]
    print("coverage", cov)
    check("rows_4", cov["rows"] == 4, cov)
    check("conflict_1", cov["conflicts"] == 1, raw["conflicts"])
    check("metrics_3", cov["metrics"] == 3, raw["metrics"])
    check("role_from_id", {r["role"] for r in raw["rows"]} == {"r05", "r06", "r03"},
          {r["role"] for r in raw["rows"]})
    check("unit_base", any(r["unit_base"] == "元" and r["scale"] == 1e8 for r in raw["rows"]))
    check("city_entity", any(r["entity"] == "北京" for r in raw["rows"]))
    check("source_grade", any(r["grade"] == "A" for r in raw["rows"]))
    check("all_traceable", all(r["source_id"] for r in raw["rows"]))
    check("conflict_rule", "高等级优先" in raw["conflicts"][0]["rule"])

    with tempfile.TemporaryDirectory() as td:
        paths = dm.export(raw, Path(td), srcs, title="自测")
        check("xlsx_written", Path(paths["raw.xlsx"]).is_file(), paths)
        check("csv_written", Path(paths["raw.csv"]).is_file(), paths)
        check("json_written", Path(paths["raw.json"]).is_file(), paths)
        if Path(paths["raw.xlsx"]).is_file():
            from openpyxl import load_workbook
            wb = load_workbook(paths["raw.xlsx"], read_only=True)
            names = list(wb.sheetnames)
            wb.close()
            check("six_sheets", len(names) == 6 and "01 原始数据" in names, names)

    print(f"\n{len(OK)}/{len(OK)+len(FAIL)} passed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
