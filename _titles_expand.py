import json
import pathlib

CARDS = ['r03', 'r05', 'r15']
TITLES = {
    '准入': '准入：小作坊只能做奶豆腐与奶皮子，面积三百平方米以下才算合规',
    '标准': '标准：水分、蛋白质两条死线，越线即判不合格',
    '产能': '产能：原奶极充裕而加工极薄，瓶颈不在奶源',
    '格局': '格局：锡林郭勒独占三分之一，品牌户均只到百万级',
    '大盘': '大盘：奶酪零售额在跌，不能讲增长故事',
    '价格带': '价格带：原料吃掉六到七成，加价空间不足两倍',
    '履约': '履约：运费比货贵，跨省直发必亏',
}
CLOSING = ('所以：这条结论只在你自己的拿货价、面积与客单价上成立，'
           '换一个盟市、换一个品类都要重算；先按最小可行单元跑一个月，'
           '用真实到账数据校正，再谈扩张。')

base = pathlib.Path('内蒙古奶食品调研_2026-11-18/cards')
for c in CARDS:
    p = base / c / 'claims.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    for s in d['sections']:
        old = s['title']
        for k, v in TITLES.items():
            if old.startswith(k):
                s['title'] = v
                break
        s['reading'].append({'text': CLOSING,
                             'refs': list(s.get('refs') or [])[:2],
                             'strong': '落点　'})
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print(c, 'titles+closing done')
