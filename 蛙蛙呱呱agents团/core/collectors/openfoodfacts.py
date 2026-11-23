# -*- coding: utf-8 -*-
"""Open Food Facts 采集器（S2 / 选项 B：找一个真有 brand 字段的源）。

**业务无关**：它只知道「打这个 API、取 products 数组、按 fields 白名单取列」。
业务词（咖啡/奶粉/…）只出现在 query.params 里。

API 文档：https://openfoodfacts.github.io/openfoodfacts-server/api/
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from core.collectors import base
from core.collectors.web_search import check_rows

UA = "guagua-collector/1.0 (research; contact: local)"


@base.register
class OpenFoodFactsCollector:
    name = "openfoodfacts"

    def fetch(self, spec: Dict[str, Any],
              project_dir: str = "") -> List[Dict[str, Any]]:
        q = (spec or {}).get("query") or {}
        url = str(q.get("url") or "https://world.openfoodfacts.org/api/v2/search")
        params = dict(q.get("params") or {})
        if not params:
            raise ValueError("openfoodfacts 需要 query.params（搜索条件）")
        full = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(full, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            doc = json.loads(r.read().decode("utf-8", errors="replace"))
        products = doc.get("products") or []
        check_rows(products, html_len=len(products))
        return [self._flat(p) for p in products]

    @staticmethod
    def _flat(p: Dict[str, Any]) -> Dict[str, Any]:
        """把 API 的嵌套结构压平成一行（只做类型收敛，不改语义）。"""
        out: Dict[str, Any] = {}
        for k, v in (p or {}).items():
            if isinstance(v, (str, int, float)) or v is None:
                out[k] = v
            elif isinstance(v, list):
                out[k] = ",".join(str(x) for x in v if x is not None)
            elif isinstance(v, dict):
                out[k] = ",".join("%s" % x for x in v.keys())
            else:
                out[k] = str(v)
        return out
