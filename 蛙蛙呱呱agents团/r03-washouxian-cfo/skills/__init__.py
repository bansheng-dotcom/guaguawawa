# -*- coding: utf-8 -*-
"""R03 八个能力域技能模块注册表。

能力全景 R03 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 financial  财务报表与月结（rollforward/recon/variance）
  s02 cfo        CFO 经营诊断（runway/unitecon/healthcheck）
  s03 tax        税务与申报边界（iso/rmd/safeharbor）
  s04 contract   合同与政策（scan/policy/redline）
  s05 privacy    隐私与数据安全（map/dsr/minimize）
  s06 aigov      AI 治理与披露（frameworks/aiclassify/disclose）
  s07 audit      认证与审计留痕（retention/mockaudit/evidence）
  s08 risk       广告/KYC-AML/投资风控（kyc/aml/adreview）
"""
from __future__ import annotations

from . import (s01_financial, s02_cfo, s03_tax, s04_contract,
               s05_privacy, s06_aigov, s07_audit, s08_risk)

SKILLS = [
    s01_financial,
    s02_cfo,
    s03_tax,
    s04_contract,
    s05_privacy,
    s06_aigov,
    s07_audit,
    s08_risk,
]
