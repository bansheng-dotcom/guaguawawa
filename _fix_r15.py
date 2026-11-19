import json
import pathlib
import re

p = pathlib.Path('内蒙古奶食品调研_2026-11-18/cards/r15/claims.json')
d = json.loads(p.read_text(encoding='utf-8'))

# 1) 文字里去掉未登记的字面数字
REPL = {
    '500 克奶豆腐': '半公斤奶豆腐',
    '20.0 元/100 克': '20.0 元 每一百克',
    '高于 1.2 倍': '高于一成二',
    '14.0 元/120 克': '14.0 元一小袋',
}
for s in d['sections']:
    for r in s['reading']:
        for a, b in REPL.items():
            r['text'] = r['text'].replace(a, b)

# 2) 按数值反查 id，补进每条解读的 refs
vals = {}
for n in d['numbers']:
    vals.setdefault(round(float(n['value']), 4), []).append(f"r15:{n['id']}")
for dv in d['derived']:
    vals.setdefault(round(float(dv['value']), 4), []).append(f"r15:{dv['id']}")

def close_ids(x):
    out = []
    for v, ids in vals.items():
        if abs(v - x) <= max(0.05, abs(x) * 0.005):
            out += ids
        elif abs(v * 100 - x) <= max(0.05, abs(x) * 0.005):
            out += ids
        elif abs(v / 100 - x) <= max(0.0005, abs(x) * 0.005):
            out += ids
    return out

for s in d['sections']:
    for r in s['reading']:
        toks = {float(x) for x in re.findall(r'\d+(?:\.\d+)?', r['text'])}
        refs = list(r.get('refs') or [])
        for t in toks:
            for cid in close_ids(t):
                if cid not in refs:
                    refs.append(cid)
        r['refs'] = refs

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('fixed r15')
