# -*- coding: utf-8 -*-
"""T6 契约层：24 个动作的确定性 JSON Schema 输入契约。

用法：python contracts.py [skill [action]] —— 打印 JSON Schema。
run_tests.py 会校验 examples/ 下 24 个夹具全部通过对应契约。
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

_ACCOUNT = {
    "type": "object",
    "required": ["account", "opening", "closing"],
    "properties": {
        "account": {"type": "string"},
        "opening": {"type": "number"},
        "additions": {"type": "number"},
        "accruals": {"type": "number"},
        "reversals": {"type": "number"},
        "payments": {"type": "number"},
        "reclass": {"type": "number"},
        "fx": {"type": "number"},
        "closing": {"type": "number"},
    },
}

_ENTRY = {
    "type": "object",
    "required": ["key", "amount"],
    "properties": {
        "key": {"type": "string"},
        "amount": {"type": "number"},
        "quantity": {"type": "number"},
        "local_amount": {"type": "number"},
        "posting_date": {"type": "string"},
    },
}

CONTRACTS: Dict[str, Dict[str, Any]] = {
    "financial": {
        "rollforward": {
            "type": "object",
            "required": ["accounts"],
            "properties": {"accounts": {"type": "array",
                                        "items": _ACCOUNT}},
        },
        "recon": {
            "type": "object",
            "required": ["gl_entries", "subledger_entries"],
            "properties": {
                "gl_entries": {"type": "array", "items": _ENTRY},
                "subledger_entries": {"type": "array", "items": _ENTRY},
            },
        },
        "variance": {
            "type": "object",
            "required": ["variances"],
            "properties": {
                "variances": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["account", "variance"],
                        "properties": {
                            "account": {"type": "string"},
                            "variance": {"type": "number"},
                            "budget": {"type": "number"},
                            "driver": {"type": "string"},
                        },
                    },
                },
                "budget_by_account": {"type": "object"},
            },
        },
    },
    "cfo": {
        "runway": {
            "type": "object",
            "required": ["starting_cash", "starting_mrr",
                         "monthly_headcount_cost", "gross_margin_pct"],
            "properties": {
                "starting_cash": {"type": "number"},
                "starting_mrr": {"type": "number"},
                "monthly_headcount_cost": {"type": "number"},
                "monthly_other_opex": {"type": "number"},
                "gross_margin_pct": {"type": "number"},
                "mrr_growth_rate": {"type": "number"},
                "model_months": {"type": "integer"},
                "amt_budget": {"type": "number"},
            },
        },
        "unitecon": {
            "type": "object",
            "required": ["cohorts"],
            "properties": {
                "cohorts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["customers_acquired",
                                     "total_cac_spend", "monthly_revenue"],
                        "properties": {
                            "label": {"type": "string"},
                            "customers_acquired": {"type": "integer"},
                            "total_cac_spend": {"type": "number"},
                            "monthly_revenue": {"type": "array",
                                                "items": {"type": "number"}},
                            "gross_margin_pct": {"type": "number"},
                        },
                    },
                },
            },
        },
        "healthcheck": {
            "type": "object",
            "required": ["balance_sheet", "cash_flow", "income_statement"],
            "properties": {
                "balance_sheet": {"type": "object"},
                "cash_flow": {"type": "object"},
                "income_statement": {"type": "object"},
            },
        },
    },
    "tax": {
        "iso": {
            "type": "object",
            "required": ["exercises"],
            "properties": {
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["grant_date", "exercise_date", "shares",
                                     "strike", "exercise_fmv"],
                        "properties": {
                            "label": {"type": "string"},
                            "grant_date": {"type": "string"},
                            "exercise_date": {"type": "string"},
                            "sale_date": {"type": "string"},
                            "termination_date": {"type": "string"},
                            "shares": {"type": "number"},
                            "strike": {"type": "number"},
                            "exercise_fmv": {"type": "number"},
                            "grant_fmv": {"type": "number"},
                        },
                    },
                },
                "regular_income": {"type": "number"},
                "regular_tax": {"type": "number"},
                "amt_budget": {"type": "number"},
            },
        },
        "rmd": {
            "type": "object",
            "required": ["accounts"],
            "properties": {
                "year": {"type": "number"},
                "accounts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["prior_year_dec31_balance"],
                        "properties": {
                            "label": {"type": "string"},
                            "age": {"type": "number"},
                            "roth": {"type": "boolean"},
                            "prior_year_dec31_balance": {"type": "number"},
                            "withdrawn_ytd": {"type": "number"},
                            "corrected_in_window": {"type": "boolean"},
                        },
                    },
                },
            },
        },
        "safeharbor": {
            "type": "object",
            "required": ["current_year_tax", "prior_year_tax",
                         "withholding_and_estimates_paid"],
            "properties": {
                "current_year_tax": {"type": "number"},
                "prior_year_tax": {"type": "number"},
                "prior_year_agi": {"type": "number"},
                "withholding_and_estimates_paid": {"type": "number"},
                "rsu_vests": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["shares", "vest_fmv"],
                        "properties": {
                            "shares": {"type": "number"},
                            "vest_fmv": {"type": "number"},
                            "marginal_rate": {"type": "number"},
                        },
                    },
                },
            },
        },
    },
    "contract": {
        "scan": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "pending": {"type": "boolean"},
            },
        },
        "policy": {
            "type": "object",
            "required": ["policy"],
            "properties": {
                "policy": {
                    "type": "object",
                    "required": ["purpose", "scope", "owner",
                                 "review_cycle_days", "enforcement"],
                    "properties": {
                        "purpose": {"type": "string"},
                        "scope": {"type": "string"},
                        "owner": {"type": "string"},
                        "review_cycle_days": {"type": "integer"},
                        "enforcement": {"type": "string"},
                    },
                },
            },
        },
        "redline": {
            "type": "object",
            "required": ["findings"],
            "properties": {
                "findings": {"type": "array", "items": {"type": "object"}},
                "fixes": {"type": "object"},
            },
        },
    },
    "privacy": {
        "map": {
            "type": "object",
            "required": ["data_flows"],
            "properties": {
                "data_flows": {"type": "array", "items": {"type": "object"}},
                "privacy_notice": {"type": "object"},
            },
        },
        "dsr": {
            "type": "object",
            "required": ["requests"],
            "properties": {
                "requests": {"type": "array", "items": {"type": "object"}},
                "breach": {"type": "object"},
            },
        },
        "minimize": {
            "type": "object",
            "required": ["collected_fields"],
            "properties": {
                "collected_fields": {"type": "array",
                                     "items": {"type": "object"}},
                "access_review": {"type": "object"},
            },
        },
    },
    "aigov": {
        "frameworks": {
            "type": "object",
            "required": ["profile"],
            "properties": {"profile": {"type": "object"}},
        },
        "aiclassify": {
            "type": "object",
            "required": ["system"],
            "properties": {"system": {"type": "object"}},
        },
        "disclose": {
            "type": "object",
            "required": ["disclosure"],
            "properties": {"disclosure": {"type": "object"}},
        },
    },
    "audit": {
        "retention": {
            "type": "object",
            "required": ["records"],
            "properties": {"records": {"type": "array",
                                       "items": {"type": "object"}}},
        },
        "mockaudit": {
            "type": "object",
            "required": ["findings"],
            "properties": {"findings": {"type": "array",
                                        "items": {"type": "object"}}},
        },
        "evidence": {
            "type": "object",
            "required": ["controls"],
            "properties": {"controls": {"type": "array",
                                        "items": {"type": "object"}}},
        },
    },
    "risk": {
        "kyc": {
            "type": "object",
            "required": ["applicant"],
            "properties": {
                "applicant": {
                    "type": "object",
                    "required": ["risk_factors", "documents"],
                    "properties": {
                        "risk_factors": {"type": "object"},
                        "documents": {"type": "object"},
                        "beneficial_owners": {
                            "type": "array", "items": {"type": "object"}},
                    },
                },
            },
        },
        "aml": {
            "type": "object",
            "required": ["transactions"],
            "properties": {
                "transactions": {"type": "array", "items": {"type": "object"}},
                "ongoing_suspicious_activity": {"type": "boolean"},
                "days_since_last_sar": {"type": "number"},
            },
        },
        "adreview": {
            "type": "object",
            "required": ["ad"],
            "properties": {"ad": {"type": "object"}},
        },
    },
}


def contracts_for(skill: str = None, action: str = None) -> Dict[str, Any]:
    if skill:
        if skill not in CONTRACTS:
            raise SystemExit(f"unknown skill: {skill}")
        if action:
            if action not in CONTRACTS[skill]:
                raise SystemExit(f"unknown action: {skill}.{action}")
            return CONTRACTS[skill][action]
        return CONTRACTS[skill]
    return CONTRACTS


if __name__ == "__main__":
    skill = sys.argv[1] if len(sys.argv) > 1 else None
    action = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(contracts_for(skill, action), ensure_ascii=False,
                     indent=2))
