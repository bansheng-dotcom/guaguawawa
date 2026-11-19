import json
import pathlib

d = json.loads(pathlib.Path('内蒙古奶食品调研_2026-11-18/price_channel_competitor_evidence.json')
              .read_text(encoding='utf-8'))
ns = d.get('numbers') or []
print('R15 交付数字:', len(ns))
print('--- 与奶皮子/奶豆腐相关的价格点 ---')
for n in ns:
    nm = str(n.get('name'))
    if '奶皮子' in nm or '奶豆腐' in nm:
        print(' ', n.get('value'), n.get('unit', ''), '|', nm[:40])
