# -*- coding: utf-8 -*-
"""scripts/seed_role_ports.py —— 给 5 个只有契约、没有数据的端口补 DEMO 记录。

背景：r08/r10/r11/r16/r17 的端口只有 fields 没有 items，导致这几份报告只能拿
north-star 三个数画图。这里按各端口契约补一份与角色叙述一致的最小数据集，
全部标 DEMO，与其它端口口径一致。

用法：python scripts/seed_role_ports.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTS = ROOT / "datasets" / "ports"

DOCS = {
    "product_spec": {
        "generated_at": "2026-11-15", "source": "DEMO", "port": "product_spec",
        "system": "产品需求库 / 埋点平台",
        "note": "r08 需要：主路径、依赖接口、任务拆分与工时、成功/杀死标准、落地页要素、回滚与监控项。",
        "fields": ["user_path", "deps", "task_breakdown", "estimate_h", "kill_criteria",
                   "landing_elements", "competitor_pages", "rollback", "monitor"],
        "items": [
            {"id": "P01", "name": "结算页一键复购", "estimate_h": 26, "deps": ["order-api", "payment-gateway"],
             "kill_criteria": "7 天复购率提升 <2pp 即下线", "status": "running", "monitor": "复购率/支付成功率"},
            {"id": "P02", "name": "晚高峰库存提示", "estimate_h": 14, "deps": ["order-api"],
             "kill_criteria": "缺货投诉不降即回滚", "status": "pending", "monitor": "缺货率/客诉"},
            {"id": "P03", "name": "门店自提地图", "estimate_h": 34, "deps": ["map-sdk", "order-api"],
             "kill_criteria": "自提占比 <8% 即停", "status": "pending", "monitor": "自提占比/到店率"},
            {"id": "P04", "name": "退款原因码强制", "estimate_h": 9, "deps": ["payment-gateway"],
             "kill_criteria": "原因码缺失 >5% 即返工", "status": "blocked", "monitor": "缺失率/退款时长"},
        ],
    },
    "design_system": {
        "generated_at": "2026-11-15", "source": "DEMO", "port": "design_system",
        "system": "Figma / 设计令牌库",
        "note": "r10 需要：令牌、物料色值、对比度配对、字号、Logo 变体与尺寸、导出清单、版本对比。",
        "fields": ["design_tokens", "color_values", "fg_bg_pairs", "font_sizes", "logo_variants",
                   "pixel_sizes", "export_sizes", "formats", "version_diff", "review_notes"],
        "tokens": [
            {"name": "ink/900", "type": "color", "value": "#14231C", "contrast_on_paper": 14.8, "usage": "正文"},
            {"name": "ink/600", "type": "color", "value": "#5B6B62", "contrast_on_paper": 5.1, "usage": "次要文字"},
            {"name": "accent/600", "type": "color", "value": "#2F6F4F", "contrast_on_paper": 5.6, "usage": "强调"},
            {"name": "accent/400", "type": "color", "value": "#7FB79A", "contrast_on_paper": 2.4, "usage": "装饰"},
            {"name": "warn/600", "type": "color", "value": "#9A6A12", "contrast_on_paper": 4.6, "usage": "警示"},
            {"name": "critical/600", "type": "color", "value": "#B02A20", "contrast_on_paper": 6.3, "usage": "错误"},
        ],
        "font_sizes": [12, 13, 15, 19, 22, 27, 34],
        "logo_variants": ["primary", "mono", "reverse"],
        "pixel_sizes": [16, 32, 64, 128],
    },
    "content_platform": {
        "generated_at": "2026-11-15", "source": "DEMO", "port": "content_platform",
        "system": "内容平台后台 / 搜索指数",
        "note": "r11 需要：搜索量、竞品内容、大纲与标题、核心词位置、禁词表、选题分与排期。",
        "fields": ["search_volume", "competitor_content", "outline", "title", "core_keywords",
                   "keyword_positions", "ban_words", "ai_disclosure", "topic_score", "schedule"],
        "items": [
            {"id": "C01", "title": "社区生鲜怎么挑", "search_volume": 12800, "competitor": 46,
             "topic_score": 74, "keywords": 5, "schedule": "2026-11-18"},
            {"id": "C02", "title": "晚高峰买菜攻略", "search_volume": 6400, "competitor": 12,
             "topic_score": 68, "keywords": 4, "schedule": "2026-11-20"},
            {"id": "C03", "title": "退款多久到账", "search_volume": 9100, "competitor": 8,
             "topic_score": 81, "keywords": 3, "schedule": "2026-11-22"},
            {"id": "C04", "title": "门店自提值不值", "search_volume": 3200, "competitor": 31,
             "topic_score": 52, "keywords": 4, "schedule": "2026-11-25"},
            {"id": "C05", "title": "春季新品试吃", "search_volume": 2100, "competitor": 5,
             "topic_score": 61, "keywords": 3, "schedule": "2026-11-27"},
        ],
    },
    "hr_system": {
        "generated_at": "2026-11-15", "source": "DEMO", "port": "hr_system",
        "system": "HR 系统（花名册/考勤/薪酬）",
        "note": "r16 需要：人均产出、人力成本、招聘漏斗与到岗周期、薪酬带宽、合同考勤社保、目标评分。",
        "fields": ["output_per_head", "labor_cost", "recruit_funnel", "time_to_hire", "salary_band",
                   "market_percentile", "contract", "attendance", "social_insurance", "goals", "rating"],
        "employees": [
            {"id": "E01", "role": "运营", "output_per_head": 21.4, "labor_cost": 18.2, "time_to_hire": 32,
             "rating": 4.2, "attendance": 0.97, "contract": "正式"},
            {"id": "E02", "role": "采购", "output_per_head": 18.6, "labor_cost": 16.8, "time_to_hire": 45,
             "rating": 3.8, "attendance": 0.95, "contract": "正式"},
            {"id": "E03", "role": "仓配", "output_per_head": 15.2, "labor_cost": 12.4, "time_to_hire": 21,
             "rating": 3.5, "attendance": 0.91, "contract": "外包"},
            {"id": "E04", "role": "客服", "output_per_head": 13.8, "labor_cost": 11.1, "time_to_hire": 18,
             "rating": 3.2, "attendance": 0.93, "contract": "外包"},
            {"id": "E05", "role": "数据", "output_per_head": 24.2, "labor_cost": 22.6, "time_to_hire": 58,
             "rating": 4.5, "attendance": 0.98, "contract": "正式"},
        ],
        "recruit_funnel": {"applied": 120, "interviewed": 34, "offered": 11, "hired": 8},
    },
    "integration_log": {
        "generated_at": "2026-11-15", "source": "DEMO", "port": "integration_log",
        "system": "集成平台（API 网关 / Webhook 投递日志）",
        "note": "r17 需要：接口契约与端点、成功率、重试与死信、字段映射、凭据存放与轮换、补偿与回放。",
        "fields": ["api_contract", "webhook_path", "success_rate", "retry_log", "dead_letter",
                   "field_mapping", "sample_payload", "secret_store", "rotation_log", "compensation", "replay"],
        "events": [
            {"path": "/webhook/order", "method": "POST", "delivered": 4820, "success": 0.993,
             "retry": 34, "dead_letter": 6, "p95_ms": 210},
            {"path": "/webhook/refund", "method": "POST", "delivered": 640, "success": 0.972,
             "retry": 18, "dead_letter": 9, "p95_ms": 380},
            {"path": "/webhook/inventory", "method": "POST", "delivered": 2100, "success": 0.955,
             "retry": 62, "dead_letter": 21, "p95_ms": 640},
            {"path": "/webhook/customer", "method": "PUT", "delivered": 980, "success": 0.988,
             "retry": 11, "dead_letter": 2, "p95_ms": 180},
        ],
        "secret_store": "vault", "rotation_days": 90,
    },
}


def main() -> int:
    for name, doc in DOCS.items():
        p = PORTS / f"{name}.json"
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote", p.relative_to(ROOT), "records:",
              sum(len(v) for k, v in doc.items() if isinstance(v, list)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
