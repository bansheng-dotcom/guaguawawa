import json
import pathlib

base = pathlib.Path('内蒙古奶食品调研_2026-11-18/cards')

# r03 第1节：罚款两点 → 改成「三条门槛」表格（不同量纲不该画在一张图上）
p3 = base / 'r03' / 'claims.json'
d3 = json.loads(p3.read_text(encoding='utf-8'))
s = d3['sections'][0]
s.pop('chart', None)
s['table'] = {
    "caption": "三条硬门槛（量纲不同，用表不用图）",
    "columns": [{"text": "门槛"}, {"text": "数值"}, {"text": "出处"}],
    "rows": [
        [{"text": "小作坊面积上限"}, {"text": "300.0 平方米"}, {"text": "登记管理办法"}],
        [{"text": "罚款区间（货值不足一万）"}, {"text": "5000.0—20000.0 元"}, {"text": "条例第五十一条"}],
        [{"text": "平台备案时限"}, {"text": "30.0 个工作日"}, {"text": "27 号令第八条"}],
        [{"text": "网络经营报告时限"}, {"text": "10.0 个工作日"}, {"text": "78 号令"}]
    ]
}
p3.write_text(json.dumps(d3, ensure_ascii=False, indent=2), encoding='utf-8')

# r05：产能补第三条（流向大乳企）、格局补第三条（其余产值）
p5 = base / 'r05' / 'claims.json'
d5 = json.loads(p5.read_text(encoding='utf-8'))
d5['derived'].append({"id": "D15", "formula": "N6-N7", "value": 16.42,
                      "unit": "亿元", "note": "除品牌外的全盟产值"})
for s in d5['sections']:
    if s['title'].startswith('产能'):
        s['chart']['bars'] = [
            {"label": "全区牛奶产量", "value": 776.7},
            {"label": "流向大乳企", "value": 686.7},
            {"label": "特色奶食加工", "value": 90.0}]
        s['chart']['title'] = "原奶 776.7 万吨：686.7 进大乳企，90.0 进特色奶食"
        s['chart']['refs'] = ["N1", "D12", "N5"]
        s['refs'] = list(dict.fromkeys(s['refs'] + ["D12"]))
    if s['title'].startswith('格局'):
        s['chart']['bars'] = [
            {"label": "全盟产值", "value": 18.0},
            {"label": "品牌销售额", "value": 1.58},
            {"label": "其余散货", "value": 16.42}]
        s['chart']['title'] = "全盟 18.0 亿元：品牌 1.58，其余 16.42 仍是散货"
        s['chart']['refs'] = ["N6", "N7", "D15"]
        s['refs'] = list(dict.fromkeys(s['refs'] + ["D15"]))
    if s['title'].startswith('大盘'):
        s.pop('chart', None)
        s['table'] = {
            "caption": "奶酪零售额与特色奶食产值的两个盘子",
            "columns": [{"text": "口径"}, {"text": "2024"}, {"text": "2025"}],
            "rows": [
                [{"text": "中国奶酪零售"}, {"text": "92.38 亿元"}, {"text": "91.22 亿元"}],
                [{"text": "地方特色奶食产值"}, {"text": "50.0 亿元"}, {"text": "50.0 亿元（截至报道）"}]
            ]
        }
p5.write_text(json.dumps(d5, ensure_ascii=False, indent=2), encoding='utf-8')
print('charts fixed')
