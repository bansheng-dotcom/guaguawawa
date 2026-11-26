# -*- coding: utf-8 -*-
"""手工 CSV 采集器（S2）。

最可控、最不容易出事的一条采集路径：人先把数据整理成 CSV，
采集器只负责「读进来 + 校验列齐不齐」，不猜业务。

spec:
    {"id": "...", "source": "manual_csv",
     "query": {"path": "data/staging/xxx.csv"}}
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from core.collectors import base
from core import grain as g
from core.sources import source_profile as sp


@base.register
class CsvManualCollector:
    name = "csv_manual"

    def fetch(self, spec: Dict[str, Any],
              project_dir: str = "") -> List[Dict[str, Any]]:
        q = (spec or {}).get("query") or {}
        raw = str(q.get("path") or "")
        if not raw:
            raise ValueError("csv_manual 需要 query.path")
        p = Path(raw)
        if not p.is_absolute():
            p = Path(project_dir or ".") / p
        if not p.is_file():
            raise FileNotFoundError("找不到 CSV: %s" % p)
        with p.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        # 列校验：源声明的原子粒度列必须都在
        src = sp.load(str(spec.get("source") or ""))
        if src:
            missing = sp.covers(src, g.atomic_of(src))
            if missing:
                raise ValueError("源画像声明的原子粒度列缺失: %s" % missing)
        return rows
