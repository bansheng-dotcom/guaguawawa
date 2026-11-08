# -*- coding: utf-8 -*-
"""R14 八个能力域技能模块注册表。

能力全景 R14 八能力域 → 八个可独立执行、可确定性校验的技能：
  s01 catalog      商品与电商后端
  s02 order        购物车与订单编排
  s03 billing      订阅与计量计费
  s04 payment      支付服务端集成
  s05 signature    电子签与签署审计
  s06 appointment  服务预约
  s07 workflow     交易状态编排
  s08 revenue      收入数据接口与交易自动化
"""
from __future__ import annotations

from . import (s01_catalog, s02_order, s03_billing, s04_payment,
               s05_signature, s06_appointment, s07_workflow, s08_revenue)

SKILLS = [
    s01_catalog,
    s02_order,
    s03_billing,
    s04_payment,
    s05_signature,
    s06_appointment,
    s07_workflow,
    s08_revenue,
]

SKILL_BY_NAME = {m.NAME: m for m in SKILLS}
