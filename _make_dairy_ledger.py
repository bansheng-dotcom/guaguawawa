import json
import pathlib

base = pathlib.Path('内蒙古奶食品调研_2026-11-18')
cards = base / 'cards'
rows = [
    '# 证据台账：内蒙古奶食品一人公司线上生意',
    '',
    '> 每条证据带来源等级、原文引文、可点链接。',
    '> S=规范性文件原文；A=政府统计/主管部门；B=研报/协会经媒体转述；C=媒体引第三方。',
    '',
    '| 卡 | 编号 | 机构 | 等级 | 原文引文 | 链接 |',
    '|---|---|---|---|---|---|',
]
n = 0
for c in ('r03', 'r05', 'r15'):
    p = cards / c / 'claims.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    for s in d.get('sources') or []:
        q = str(s.get('quote') or '').replace('|', '／')[:110]
        rows.append(f"| {c} | {s.get('file')} | {s.get('org')} | {s.get('grade')} | {q} | {s.get('url')} |")
        n += 1

rows += ['', '## 口径冲突（已写进报告，没有抹平）', '']
rows += [
    '- 奶豆腐零售价：处罚案例 14.0 元/120 克（折 116.67 元/公斤）vs 京东 500 克装 39.8 元（折 79.6 元/公斤），差 1.47 倍。报告按市场价建模，案例价只作上限。',
    '- 线上销售占比：企业口径 30.0%—40.0%（27 户乳企）vs 区域品牌官方店 80.0%，不是同一群体。报告用前者描述行业，后者说明品牌店上限。',
    '- 锡盟乳制品产值：2024 年 18 亿元（盟口径）与 2023 年 1—7 月 27 户企业 9608 万元（企业口径）相差近十倍，两套口径不可通算。',
]
rows += ['', '## 没查到的（空白，不是零）', '']
for c in ('r03', 'r05', 'r15'):
    d = json.loads((cards / c / 'claims.json').read_text(encoding='utf-8'))
    for m in d.get('missing') or []:
        rows.append(f'- [{c}] {m}')

pathlib.Path('交付/内蒙古奶食品调研_20261118').mkdir(parents=True, exist_ok=True)
pathlib.Path('交付/内蒙古奶食品调研_20261118/01-证据台账.md').write_text(
    '\n'.join(rows), encoding='utf-8')
print('ledger:', n, 'sources')
