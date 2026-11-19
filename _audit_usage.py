import glob
import json
import pathlib

notes = []
def add(*a):
    notes.append(' '.join(str(x) for x in a))

# 派出去的三份原始产出
raw_files = glob.glob(r'D:\蛙蛙呱呱\research_nmg_dairy_market_*.json') + \
            glob.glob(r'D:\蛙蛙呱呱\内蒙古奶食品调研_2026-11-18\price_channel_competitor_evidence.json')
raw_numbers = {}
for f in raw_files:
    try:
        d = json.loads(pathlib.Path(f).read_text(encoding='utf-8'))
    except Exception as e:
        add('读不了', f, e)
        continue
    ns = d.get('numbers') or []
    raw_numbers[pathlib.Path(f).name] = ns
    add('原始文件', pathlib.Path(f).name, '数字', len(ns), '来源', len(d.get('sources') or []),
        'findings', len(d.get('findings') or []), 'missing', len(d.get('missing') or []))

# 实际进报告的数字（三张卡）
used_names = set()
used_count = 0
for c in ('r03', 'r05', 'r15'):
    p = pathlib.Path(f'内蒙古奶食品调研_2026-11-18/cards/{c}/claims.json')
    d = json.loads(p.read_text(encoding='utf-8'))
    used_count += len(d.get('numbers') or [])
    for n in d.get('numbers') or []:
        used_names.add(str(n.get('name')))
    add(f'卡 {c}: 数字', len(d.get('numbers') or []), '来源', len(d.get('sources') or []))

# 原始指标名是否被采用（按名称粗匹配）
all_raw = [n for ns in raw_numbers.values() for n in ns]
missed = []
for n in all_raw:
    name = str(n.get('name') or '')
    key = name[:6]
    if not any(key and key in u for u in used_names):
        missed.append(name)

add('')
add('原始数字总数', len(all_raw), '｜进报告的数字总数', used_count)
add('原始指标名未被采用（粗匹配）', len(missed))
for m in missed[:40]:
    add('  未采用:', m)

out = pathlib.Path('交付/内蒙古奶食品调研_20261118/02-数据利用审计.md')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('# 数据利用审计\n\n```\n' + '\n'.join(notes) + '\n```\n', encoding='utf-8')
print('\n'.join(notes[:60]))
