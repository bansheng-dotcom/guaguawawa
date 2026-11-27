# -*- coding: utf-8 -*-
"""R12 增长链（growth_chain）· 七段可复算流水线。

diagnose → experiment → attribution → retention → paid → selfmedia → mmm

每段产出确定性 JSON 工件，门禁不通过即失败；runner 汇总 7 份工件 +
growth_manifest.json（sha256 / 门禁 / 跨段一致性）。
"""
from __future__ import annotations

from . import (attribution, common, diagnose, experiment, mmm, paid,
               retention, runner, selfmedia)

STAGES = common.STAGES

__all__ = [
    "STAGES", "attribution", "common", "diagnose", "experiment", "mmm",
    "paid", "retention", "runner", "selfmedia",
]
