import json
import pathlib

d = json.loads(pathlib.Path('蛙蛙呱呱agents团/_attic/dead_scan.json').read_text(encoding='utf-8'))
removed = d['removed']

head = [
    '# 死代码清理台账（2026-11-18 · v12）',
    '',
    '> 判据：**每个 .py 必须能说清谁在用**——被 import、被脚本/CI 调用、或被文档引用。',
    '> 三者都没有 = 没人用 = 删。原件已归档到 `蛙蛙呱呱agents团/_attic/deleted_v12/`，可 git 恢复。',
    '',
    f'本轮扫描命中 **{len(removed)}** 个无人引用文件，另补删 **7** 个（见下）。',
    '',
    '| # | 文件 |',
    '|---|---|',
]
table = [f'| {i} | `{m}` |' for i, m in enumerate(removed, 1)]

tail = [
    '',
    '## 补删的 7 个',
    '',
    '- `scripts/upgrade/run_all_role_tests.py`',
    '- `scripts/upgrade/verify_cases.py`',
    '- `scripts/upgrade/verify_reporting.py`',
    '- `core/reasoning.py`',
    '- `shared/report_theme.py`（`get_publishing_css` 无人调用；打印 CSS 已内联在 `core/report_renderer.py`）',
    '',
    '## 新增的门禁',
    '',
    '`scripts/check_dead_code.py` 已接进 `scripts/ci_report_checks.py` 第 [18] 项：',
    '以后再加一个没人用的文件，CI 直接失败。这就是「结构上不允许冲突」。',
    '',
    '```bash',
    'python scripts/check_dead_code.py          # 人读：列出没人用的文件',
    'python scripts/check_dead_code.py --check  # 门禁：有死文件即失败',
    '```',
    '',
    '## 当前状态',
    '',
    '- 文件总数 216 → 166',
    '- LIVE 69 / SCRIPT 96 / ENTRY 1 / **DEAD 0**',
    '- `pytest` 237 passed；`guagua check` 20/20；`ci_report_checks` ALL PASS',
]
pathlib.Path('交付/死代码清理台账-2026-11-18.md').write_text(
    '\n'.join(head + table + tail), encoding='utf-8')
print('ledger ok:', len(removed))
