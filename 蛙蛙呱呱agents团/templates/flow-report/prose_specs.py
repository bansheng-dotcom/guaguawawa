# -*- coding: utf-8 -*-
"""flow 报告模板：文笔层（可选）。

有 SPECS 时，core.report_prose_gen 会用它覆盖 facts 里的 body：
每节按 判断 → 事实 → 证据 → 机理 → 替代解释 → 信号 → 含义 → 动作 → 停止线 → 边界 合成。
只用 spec 里的数字，不新增。

固定 11 字段：facts.SECTIONS 的 verdict / question + 下面的 9 个 spec 字段。
少一个字段，core.prose_spec 会记问题；`--prose-hard` 时直接 BLOCK。
"""

SPECS = {
    "s1": {
        "fact": "2025 年产量 354.9 万千升，2016 年 1358.4 万千升。",
        "evidence": "九年降 73.87%，只剩 26.13%。",
        "mechanism": "需求端场景收缩、供给端出清，价格靠提价撑住。",
        "alternative": "不是需求消失，而是场景换手",
        "signal": "下一期产量增速是否转正",
        "implication": "对进入者的含义：不要假设市场会变大。",
        "action": "先做最小验证",
        "stop": "产量转正且倒挂企业占比降到 30% 以下",
        "boundary": "规上口径，不含小作坊。",
    },
}
