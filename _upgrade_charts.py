import json
import pathlib

base = pathlib.Path('内蒙古奶食品调研_2026-11-18/cards')

# 1) 产能 → 瀑布：原奶去哪了（期初→扣减→期末）
p5 = base / 'r05' / 'claims.json'
d5 = json.loads(p5.read_text(encoding='utf-8'))
for s in d5['sections']:
    if s['title'].startswith('产能'):
        s['chart'] = {
            "type": "waterfall",
            "title": "原奶 776.7 万吨：686.7 进大乳企、90.0 进特色奶食",
            "unit_meta": "万吨", "source": "S1/S8/S5",
            "refs": ["N1", "D12", "N5"],
            "baseline": {"label": "全区原奶", "value": 776.7},
            "annotate": [{"at": "特色奶食", "text": "只占 11.6%"}],
            "steps": [
                {"label": "全区原奶", "value": 776.7, "kind": "start"},
                {"label": "流向大乳企", "value": 776.7, "delta": -686.7, "kind": "delta"},
                {"label": "特色奶食", "value": 90.0, "kind": "end"},
            ],
        }
    if s['title'].startswith('格局'):
        s['chart'] = {
            "type": "pareto",
            "title": "全盟 18.0 亿元：品牌只占 1.58，其余 16.42 是散货",
            "unit_meta": "亿元", "source": "S5/S9",
            "refs": ["N6", "N7", "D15"],
            "threshold": 80,
            "baseline": {"label": "全盟产值", "value": 18.0},
            "annotate": [{"at": "其余散货", "text": "未被品牌覆盖"}],
            "items": [
                {"label": "其余散货", "value": 16.42},
                {"label": "品牌销售额", "value": 1.58},
            ],
        }
p5.write_text(json.dumps(d5, ensure_ascii=False, indent=2), encoding='utf-8')

# 2) 价格带 → 四点条图，带基线（出厂价）与标注
p15 = base / 'r15' / 'claims.json'
d15 = json.loads(p15.read_text(encoding='utf-8'))
for s in d15['sections']:
    if s['title'].startswith('价格带'):
        s['chart'] = {
            "type": "hbar",
            "title": "原料 48.0—60.0、出厂 57.1、零售 79.6 元每公斤",
            "unit_meta": "元/公斤", "source": "S5/S1/S11",
            "refs": ["D4", "D5", "N4", "D1"],
            "baseline": {"label": "出厂隐含均价", "value": 57.1},
            "annotate": [{"at": "零售", "text": "只比出厂高 39.4%"},
                         {"at": "原料下限", "text": "占零售 60.3%"}],
            "bars": [
                {"label": "原料下限", "value": 48.0},
                {"label": "原料上限", "value": 60.0},
                {"label": "出厂均价", "value": 57.1},
                {"label": "零售", "value": 79.6},
            ],
        }
p15.write_text(json.dumps(d15, ensure_ascii=False, indent=2), encoding='utf-8')
print('charts upgraded to 3 types')
