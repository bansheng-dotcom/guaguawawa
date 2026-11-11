# -*- coding: utf-8 -*-
"""R15 七个能力域技能模块注册表。

能力全景 R15 七能力域 → 七个可独立执行、可确定性校验的技能：
  s01 procurement   采购与供应商
  s02 inventory     库存与仓库
  s03 fulfillment   销售与履约记录
  s04 production    生产/服务资源（BOM/物料请求）
  s05 finance       ERP 财务业务接口
  s06 masterdata    主数据与权限
  s07 report        运营报表
"""
from __future__ import annotations

from . import (s01_procurement, s02_inventory, s03_fulfillment, s04_production,
               s05_finance, s06_masterdata, s07_report, s08_tco)

SKILLS = [
    s01_procurement,
    s02_inventory,
    s03_fulfillment,
    s04_production,
    s05_finance,
    s06_masterdata,
    s07_report,
    s08_tco,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}
