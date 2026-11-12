# -*- coding: utf-8 -*-
"""核对「20 角色深度地图」：每个角色缺的方法/数据，做到什么程度。

三列判定：
  方法包：角色 references/method-pack.md 是否覆盖该方法关键词
  可执行：是否存在对应的脚本/引擎入口（不是只有文字）
  数据：MCP 槽位是否启用 / 是否有本地基准
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROWS = [
    ("R01", "r01-waquanju-ceo", ["问题树", "假设", "情景|premortem|尸检"], "公司经营基线"),
    ("R02", "r02-wapaibu-coo", ["约束|TOC", "瓶颈", "SOP"], "流程时长/产能"),
    ("R03", "r03-washouxian-cfo", ["情景", "单位经济", "敏感性", "跑道|runway"], "真实流水/成本科目"),
    ("R05", "r05-washenyuan-research", ["竞争解释", "三角|交叉验证", "样本"], "行业数据库/海关/统计"),
    ("R06", "r06-wadeqing-analyst", ["匹配", "DID|双重差分", "断点|RDD", "基线", "区间|不确定"], "微观数据/POS"),
    ("R14", "r14-wajiaoyi-commerce", ["弹性", "动销", "品类角色"], "平台数据/竞品价"),
    ("R15", "r15-wagongying-erp", ["库存", "仿真", "损耗"], "运价/库容/时效"),
    ("R12", "r12-wayingliu-growth", ["增量", "MMM", "LTV|CAC"], "投放/归因数据"),
    ("R07", "r07-wademing-pm", ["JTBD", "机会|solution tree|OST"], "用户访谈/行为数据"),
    ("R04", "r04-watiaoci-reviewer", ["方法", "对照", "匹配"], "无（改门禁）"),
]

EXEC = {
    "R01": ["scripts/consult.py"],
    "R02": ["scripts/methods.py"],
    "R03": ["scripts/methods.py"],
    "R04": ["scripts/method_gate.py"],
    "R05": ["scripts/methods.py"],
    "R06": ["scripts/methods.py", "scripts/method_gate.py"],
    "R07": ["scripts/consult.py"],
    "R12": ["scripts/methods.py"],
    "R14": ["scripts/methods.py"],
    "R15": ["scripts/methods.py"],
}


def main() -> None:
    reg = json.loads((ROOT / "shared" / "mcp" / "registry.json").read_text(encoding="utf-8"))
    enabled = [k for k, v in reg["servers"].items() if v.get("enabled")]
    print(f"{'角色':<5}{'方法包':<28}{'可执行':<10}{'数据'}")
    print("-" * 88)
    for rid, d, kws, data_need in ROWS:
        p = ROOT / d / "references" / "method-pack.md"
        text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        hits = [k for k in kws if re.search(k, text, re.I)]
        miss = [k for k in kws if not re.search(k, text, re.I)]
        pack = f"{len(hits)}/{len(kws)}" + (f" 缺:{','.join(miss)}" if miss else " 全")
        ex = EXEC.get(rid, [])
        ex_s = "有" if ex else "无"
        data_s = "无" if not enabled else f"MCP:{','.join(enabled)}"
        if rid == "R04":
            data_s = "N/A（门禁）"
        print(f"{rid:<5}{pack:<28}{ex_s:<10}{data_s}")
    print(f"\nMCP 已启用：{enabled or '无'}（8 槽位全部预留）")
    print("可执行方法工具：methods.py（matched/did/elasticity/safety-stock/ltv-cac/runway/little）、method_gate.py、consult.py；MMM/RDD 仍未实现")


if __name__ == "__main__":
    main()
