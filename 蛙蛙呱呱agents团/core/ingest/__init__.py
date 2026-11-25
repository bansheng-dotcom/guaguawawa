# -*- coding: utf-8 -*-
"""采集六层（P2）：Policy / Fetcher / Extractor / Validator / Store / Runner。

设计边界（照抄方案 §5，不引框架）：
  * 传输用 urllib，抽取用标准库 html.parser / json；不装 Scrapy、不装浏览器
  * 只做单机批次 / 断点 / 限速 / 退避；不做并发、代理池、分布式队列
  * 采集规格里**只允许** url / selector / 字段映射；
    「抓哪个指标」是项目侧筛选条件，不许写进团内代码

用法：
    from core import ingest
    res = ingest.run(spec, project_dir="<项目>", persist=True)
    # → data/staging/<source>/<batch>/{rows.jsonl,_state.json,dq_report.json}
"""
from __future__ import annotations

from .policy import DEFAULT_POLICY, load_policy, validate_policy  # noqa: F401
from .fetch import FetchResult, RateLimiter, http_get  # noqa: F401
from .extract import extract_records, iter_page_urls  # noqa: F401
from .store import (batch_id, read_staging, write_staging,  # noqa: F401
                    dq_report)
from .runner import run, run_many  # noqa: F401
