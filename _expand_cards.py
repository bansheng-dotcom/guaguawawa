import json
import pathlib

base = pathlib.Path('内蒙古奶食品调研_2026-11-18/cards')

# ---------- r05: 补两处派生 + 每节加一条对照/落点 ----------
p5 = base / 'r05' / 'claims.json'
d5 = json.loads(p5.read_text(encoding='utf-8'))
d5['derived'].append({"id": "D11", "formula": "N2/N14*100", "value": 4.32,
                      "unit": "%", "note": "特色奶食产值相当于伊利的比例"})
d5['derived'].append({"id": "D12", "formula": "N1- N5", "value": 686.7,
                      "unit": "万吨", "note": "流向大乳企的原奶"})
d5['sections'][0]['refs'] += ["D11", "D12"]
d5['sections'][0]['reading'].append({
    "text": "把镜头拉远：特色奶食 50.0 亿元产值只相当于伊利一家 1157.80 亿元的 4.32%；"
            "剩下 686.7 万吨原奶被大乳企消化。你要抢的不是奶源，是大乳企不做的那一小块——"
            "手工、短保、地域口味。",
    "refs": ["N2", "N14", "D11", "N1", "N5", "D12"], "strong": "落点　"})

d5['sections'][1]['reading'].append({
    "text": "把户均数放到全区看：99 家授权主体合计 1.58 亿元，只占全盟 18.0 亿元产值的 8.78%；"
            "也就是说剩下的 91.2% 仍是没进品牌体系的散货，谁先做出可复购的品牌，谁就吃这块空档。",
    "refs": ["N7", "N17", "N6", "D6"], "strong": "落点　"})

d5['sections'][2]['reading'].append({
    "text": "把两个盘子并排：奶酪零售 92.38 亿元在跌，地方特色奶食 50.0 亿元在做；"
            "一人公司的机会在后者，但后者的 50.0 亿元里还有 91.2% 是散货，可品牌化的空间远大于大盘增速。",
    "refs": ["N9", "N2", "N10", "D10"], "strong": "对照　"})
p5.write_text(json.dumps(d5, ensure_ascii=False, indent=2), encoding='utf-8')

# ---------- r03: 每节加一条 ----------
p3 = base / 'r03' / 'claims.json'
d3 = json.loads(p3.read_text(encoding='utf-8'))
d3['sections'][0]['reading'].append({
    "text": "再看网售这一步：持登记证的小作坊可以依法从事网络食品经营，平台方在通信主管部门批准后 "
            "30.0 个工作日内向省级监管部门备案；商家自己只需在平台入驻时出示登记证，"
            "不需要另办食品经营许可。",
    "refs": ["N4"], "strong": "落点　"})

d3['sections'][1]['reading'].append({
    "text": "把两类产品的限值并排看：奶豆腐靠蛋白质撑（不低于 30.0%），奶皮子靠脂肪撑（不低于 50.0%），"
            "水分一个卡 48.0%、一个卡 40.0%；同一口锅做两种产品，投料与火候必须分开记，否则两类都容易越线。",
    "refs": ["N6", "N7", "N10", "N11", "D3"], "strong": "对照　"})
p3.write_text(json.dumps(d3, ensure_ascii=False, indent=2), encoding='utf-8')

print('cards expanded')
