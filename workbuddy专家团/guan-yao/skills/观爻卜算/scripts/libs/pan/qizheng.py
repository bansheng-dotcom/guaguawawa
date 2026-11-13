#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 来源: https://github.com/dglijin-oss/chinese-metaphysics-skills (MIT License, Copyright (c) 2026 天工长老)
# 集成: 并入「卜算」skill，算法原样保留，由 cast.py 调用
"""
七政四余排盘工具 v3.0.0
天工长老开发

功能：七政（日月五星）四余（罗计孛气）星盘排布、十二宫、格局分析、自动化断语
v3.0.0 新增：精确天文算法（VSOP87 简化版）、相位分析、宫主星系统
"""

import argparse
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import ephem
from lunar_python import Solar

# ============== 天文引擎 ==============
# 七政地心黄经用 PyEphem 精算；四余用 Meeus《Astronomical Algorithms》多项式。
# 参考：h4x0r/stem-branch 的 seven-governors 与 goliajp/mingli 的 mingli-qizhengsiyu。


def _norm360(x: float) -> float:
    """归一到 [0, 360)。"""
    return x % 360.0


def _julian_centuries_from_j2000(dt_utc: datetime) -> float:
    """儒略世纪数 T（自 J2000.0 起），供 Meeus 多项式使用。"""
    jd = ephem.julian_date(ephem.Date(dt_utc))
    return (jd - 2451545.0) / 36525.0


def _mean_lunar_ascending_node_deg(T: float) -> float:
    """罗睺 = 月平升交点 Ω（Meeus AA 第 47 章 eq 47.7，精度约 0.5″）。"""
    return _norm360(
        125.0445479
        - 1934.1362891 * T
        + 0.0020754 * T ** 2
        + T ** 3 / 467441.0
        - T ** 4 / 60616000.0
    )


def _mean_lunar_perigee_deg(T: float) -> float:
    """月平近地点 Π（Meeus AA p.343）。"""
    return _norm360(
        83.3532465
        + 4069.0137287 * T
        - 0.0103200 * T ** 2
        - T ** 3 / 80053.0
        + T ** 4 / 18999000.0
    )


# 紫气 ≈ 28 年一周的虚星。各派定义分歧（28年闰余/月近地点/木余气…），
# 无统一可代入时间的公式（swisseph 亦不提供），此处取通行近似并诚实标注「近似」。
_PURPLE_QI_DAILY_RATE = 360.0 / 10195.5  # 约 27.9 年一周（与 stem-branch 同口径）


def _ecliptic_lon_deg(body, observer) -> float:
    """ephem 天体 → 地心黄经（度）。ephem 返回弧度，转度取模 360。"""
    body.compute(observer)
    return _norm360(float(ephem.Ecliptic(body).lon) * 180.0 / math.pi)


# ============== 二十八宿（真实距度，非等分）==============
# 距度：相邻距星的赤经差，单位「古度」（周天 365.25 古度 = 360 现代度）。
# 数值取自三部正史历志（《汉书·律历志》《新唐书》大衍历、《元史》授时历），
# 经 goliajp/mingli 的 mingli-qizhengsiyu 逐宿核对整理。
# 注意：宿度随岁差而变（觜宿：汉 2°→唐 1°→元 0.05°），并非恒定常数。
_XIU_DU_TABLES = {
    '汉': [
        12.0, 9.0, 15.0, 5.0, 5.0, 18.0, 11.0,          # 角亢氐房心尾箕（东 75）
        26.0, 8.0, 12.0, 10.0, 17.0, 16.0, 9.0,          # 斗牛女虚危室壁（北 98）
        16.0, 12.0, 14.0, 11.0, 16.0, 2.0, 9.0,          # 奎娄胃昴毕觜参（西 80）
        33.0, 4.0, 15.0, 7.0, 18.0, 18.0, 17.0,          # 井鬼柳星张翼轸（南 112）
    ],
    '大衍': [
        12.0, 9.0, 15.0, 5.0, 5.0, 18.0, 11.0,
        26.0, 8.0, 12.0, 10.0, 17.0, 16.0, 9.0,
        16.0, 12.0, 14.0, 11.0, 17.0, 1.0, 10.0,         # 毕 +1、觜 −1、参 +1、鬼 −1
        33.0, 3.0, 15.0, 7.0, 18.0, 18.0, 17.0,
    ],
    '授时': [
        12.1, 9.2, 16.3, 5.6, 6.5, 19.1, 10.4,
        25.2, 7.2, 11.35, 8.9575, 15.4, 17.1, 8.6,
        16.6, 11.8, 15.6, 11.3, 17.4, 0.05, 11.1,         # 觜只剩 0.05 古度
        33.3, 2.2, 13.3, 6.3, 17.25, 18.75, 17.3,
    ],
}
_GU_CIRCLE = 365.25  # 古度一圈对应的古度数


def _mansion_from_longitude(lon_deg: float, spica_lon_deg: float, epoch: str = '授时') -> str:
    """黄经 → 二十八宿：以角宿一(Spica)为角宿起点，按距度累积入宿。

    近似与边界（诚实标注）：宿度为赤道距度，此处以黄经近似入宿；宿度随岁差而变，
    仅以「当前角宿一黄经」锚定起点，不逐星重测；授时历一圈 365.2575 古度（此按 365.25 折算）。
    """
    xiudu = _XIU_DU_TABLES.get(epoch, _XIU_DU_TABLES['授时'])
    rel = _norm360(lon_deg - spica_lon_deg)
    acc = 0.0
    for i, du in enumerate(xiudu):
        acc += du * 360.0 / _GU_CIRCLE
        if rel < acc:
            return ER_SHI_BA_XIU[i]
    return ER_SHI_BA_XIU[0]

# ============== 基础数据 ==============

# 十二宫
SHI_ER_GONG = [
    '命宫', '财帛', '兄弟', '田宅', '男女', '奴仆',
    '夫妻', '疾厄', '迁移', '官禄', '福德', '相貌'
]

# 地支
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 西洋星座（与 DI_ZHI 对齐：子=宝瓶、丑=摩羯 … 亥=双鱼）
WESTERN_ZODIAC = [
    '宝瓶', '摩羯', '人马', '天蝎', '天秤', '处女',
    '狮子', '巨蟹', '双子', '金牛', '白羊', '双鱼'
]

# 二十八宿
ER_SHI_BA_XIU = [
    '角', '亢', '氐', '房', '心', '尾', '箕',
    '斗', '牛', '女', '虚', '危', '室', '壁',
    '奎', '娄', '胃', '昴', '毕', '觜', '参',
    '井', '鬼', '柳', '星', '张', '翼', '轸'
]

# 七政
QI_ZHENG = ['太阳', '太阴', '木星', '火星', '土星', '金星', '水星']

# 四余
SI_YU = ['罗睺', '计都', '月孛', '紫气']

# 七政五行
QI_ZHENG_WUXING = {
    '太阳': '火', '太阴': '水', '木星': '木', '火星': '火',
    '土星': '土', '金星': '金', '水星': '水'
}

# 七政吉凶
QI_ZHENG_JI_XIONG = {
    '太阳': '大吉', '太阴': '吉', '木星': '吉', '火星': '凶',
    '土星': '凶', '金星': '吉', '水星': '中'
}

# 四余五行
SI_YU_WUXING = {'罗睺': '火', '计都': '土', '月孛': '水', '紫气': '木'}

# 四余吉凶
SI_YU_JI_XIONG = {'罗睺': '凶', '计都': '凶', '月孛': '凶', '紫气': '吉'}

# 星曜庙旺落陷
MIAO_WANG_XIAN = {
    '太阳': {'庙': '戌', '旺': '午', '陷': '辰', '喜': '寅卯'},
    '太阴': {'庙': '未', '旺': '卯', '陷': '酉', '喜': '戌亥'},
    '木星': {'庙': '未', '旺': '亥', '陷': '酉', '喜': '寅卯'},
    '火星': {'庙': '卯', '旺': '戌', '陷': '子', '喜': '巳午'},
    '土星': {'庙': '子', '旺': '酉', '陷': '卯', '喜': '辰戌丑未'},
    '金星': {'庙': '酉', '旺': '巳', '陷': '卯', '喜': '申酉'},
    '水星': {'庙': '巳', '旺': '申', '陷': '午', '喜': '亥子'},
}

# 天干
TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 地支
DI_ZHI_FULL = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']


class QiZhengPan:
    """七政四余排盘类"""
    
    @staticmethod
    def get_year_gan_zhi(year: int) -> Tuple[str, str]:
        """获取年干支"""
        gan_index = (year - 4) % 10
        zhi_index = (year - 4) % 12
        return TIAN_GAN[gan_index], DI_ZHI_FULL[zhi_index]
    
    @staticmethod
    def get_month_gan_zhi(year: int, month: int) -> Tuple[str, str]:
        """获取月干支（简化版）"""
        zhi_index = (month + 2) % 12
        zhi = DI_ZHI_FULL[zhi_index]
        
        year_gan, _ = QiZhengPan.get_year_gan_zhi(year)
        gan_map = {'甲': 2, '乙': 4, '丙': 6, '丁': 8, '戊': 0,
                   '己': 2, '庚': 4, '辛': 6, '壬': 8, '癸': 0}
        start = gan_map.get(year_gan, 0)
        gan_index = (start + month - 1) % 10
        gan = TIAN_GAN[gan_index]
        
        return gan, zhi
    
    @staticmethod
    def get_day_gan_zhi(date: datetime) -> Tuple[str, str]:
        """获取日干支（lunar_python 精确计算）"""
        _lunar = Solar.fromYmdHms(date.year, date.month, date.day, date.hour, date.minute, date.second).getLunar()
        gz = _lunar.getDayInGanZhi()
        return gz[0], gz[1]
    
    @staticmethod
    def get_hour_gan_zhi(day_gan: str, hour: int) -> Tuple[str, str]:
        """获取时干支"""
        zhi_index = ((hour + 1) // 2) % 12
        zhi = DI_ZHI_FULL[zhi_index]
        
        gan_map = {'甲': 0, '乙': 2, '丙': 4, '丁': 6, '戊': 8,
                   '己': 0, '庚': 2, '辛': 4, '壬': 6, '癸': 8}
        start = gan_map.get(day_gan, 0)
        gan_index = (start + zhi_index) % 10
        gan = TIAN_GAN[gan_index]
        
        return gan, zhi
    
    @classmethod
    def get_ming_gong(cls, month: int, hour: int) -> int:
        """
        计算命宫
        公式：寅起正月，顺数至生月；生时起逆数至卯
        """
        ming_gong = 2  # 寅的位置
        ming_gong = (ming_gong + month - 1) % 12
        hour_index = ((hour + 1) % 24) // 2
        ming_gong = (ming_gong - hour_index) % 12
        return ming_gong
    
    @classmethod
    def longitude_to_gong(cls, longitude: float) -> int:
        """
        黄经转地支序（0=子…11=亥）。

        口径（诚实标注）：此表为「回归黄道 30° 等分 → 西洋星座」的映射，
        非传统果老星宗的「十二次」恒星宫制。十二次度界历法五系并存、受岁差支配，
        无统一口径（mingli 亦标 Und），故此处沿用回归黄道，落次/恒星宫留待选定度界后再改。
        戌=白羊 0-30°、酉=金牛 30-60°、申=双子 60-90°、未=巨蟹 90-120°、
        午=狮子 120-150°、巳=处女 150-180°、辰=天秤 180-210°、卯=天蝎 210-240°、
        寅=人马 240-270°、丑=摩羯 270-300°、子=宝瓶 300-330°、亥=双鱼 330-360°
        """
        return (10 - int(longitude) // 30) % 12
    
    @classmethod
    def get_miao_wang(cls, star_name: str, gong_index: int) -> str:
        """判断星曜庙旺落陷"""
        gong_zhi = DI_ZHI[gong_index]
        miao_wang = MIAO_WANG_XIAN.get(star_name, {})
        
        if miao_wang.get('庙') == gong_zhi:
            return '庙'
        elif miao_wang.get('旺') == gong_zhi:
            return '旺'
        elif miao_wang.get('陷') == gong_zhi:
            return '陷'
        else:
            return '平'
    
    @classmethod
    def get_xiu(cls, longitude: float, spica_lon: float) -> str:
        """根据黄经计算二十八宿（按距度累积，角宿一起点，授时历古度）。"""
        return _mansion_from_longitude(longitude, spica_lon)
    
    @classmethod
    def check_ge_ju(cls, stars: Dict[str, float], ming_gong_index: int = 0) -> List[Dict]:
        """检查星盘格局（ming_gong_index 为命宫地支序 0=子…11=亥）。

        格局属经验规则层（HEURISTIC），给出处指针；断卦仍须 Grep《果老星宗》《星学大成》原文佐证。
        星神三则（日月夹命/禄存/火铃夹命）与 stem-branch seven-governors 同口径，出处标果老星宗。
        """
        ge_ju = []

        def gong_of(name: str) -> int:
            """星曜落宫（地支序 0=子…11=亥）。"""
            return cls.longitude_to_gong(stars[name])

        def adjacent(a: int, b: int) -> bool:
            """b 是否在 a 的前后邻宫。"""
            return b == (a + 1) % 12 or b == (a + 11) % 12

        # —— 星神三则（果老星宗）——
        sun_gong, moon_gong = gong_of('太阳'), gong_of('太阴')
        if adjacent(ming_gong_index, sun_gong) and adjacent(ming_gong_index, moon_gong):
            ge_ju.append({'名称': '日月夹命', '吉凶': '大吉', '说明': '日月夹命宫，光明护身',
                          '出处': '果老星宗', '原文': '日月夹命：日月夹命宫，日月夹命主'})
        # 木星入命：果老星宗称「木气朝垣」，亦名「禄存」（stem-branch 同作禄存）
        if gong_of('木星') == ming_gong_index:
            ge_ju.append({'名称': '木气朝垣（禄存）', '吉凶': '大吉', '说明': '木星入命，一生富贵',
                          '出处': '果老星宗', '原文': '木主寿长：木星照命入庙堂，亦且教人寿更长'})
        if adjacent(ming_gong_index, gong_of('火星')) and adjacent(ming_gong_index, gong_of('计都')):
            ge_ju.append({'名称': '火铃夹命', '吉凶': '凶', '说明': '火星计都夹命，防是非刑伤', '出处': '果老星宗'})

        # —— 日月格局 ——
        diff = abs(stars['太阳'] - stars['太阴'])
        if diff > 180:
            diff = 360 - diff
        if 115 <= diff <= 125:
            ge_ju.append({'名称': '日月拱照', '吉凶': '大吉', '说明': '日月三合，贵气临身',
                          '出处': '果老星宗', '原文': '日月拱命：日月拱命宫，日月拱命主'})
        if diff < 10:
            ge_ju.append({'名称': '日月合璧', '吉凶': '大吉', '说明': '日月同宫，光明之象',
                          '出处': '果老星宗', '原文': '日月合璧：太阳与太阴同宫，或对照，或三合照是也。然须庙旺方为贵。'})

        # —— 金水相生 ——
        diff_jw = abs(stars['金星'] - stars['水星'])
        if diff_jw > 180:
            diff_jw = 360 - diff_jw
        if diff_jw < 30:
            ge_ju.append({'名称': '金水相生', '吉凶': '吉', '说明': '金水同宫，聪明智慧',
                          '出处': '果老星宗', '原文': '金水从阳：金水掌吉，神居垣殿，昼生者奇'})

        # —— 火土相刑 ——
        diff_ht = abs(stars['火星'] - stars['土星'])
        if diff_ht > 180:
            diff_ht = 360 - diff_ht
        if 170 <= diff_ht <= 190:
            ge_ju.append({'名称': '火土相刑', '吉凶': '凶', '说明': '火土对冲，防口舌是非', '出处': '果老星宗'})

        # —— 罗计截路（罗睺计都夹命宫）——
        luo_gong, ji_gong = gong_of('罗睺'), gong_of('计都')
        _qian, _hou = (ming_gong_index - 1) % 12, (ming_gong_index + 1) % 12
        if (luo_gong == _qian and ji_gong == _hou) or (luo_gong == _hou and ji_gong == _qian):
            ge_ju.append({'名称': '罗计截路', '吉凶': '凶', '说明': '罗计夹命，运势受阻', '出处': '果老星宗'})

        # —— 五星聚（多星同宫）：5 星＝五星连珠，3–4 星＝聚 ——
        gong_counts = {}
        for star, lon in stars.items():
            if star in QI_ZHENG:
                g = cls.longitude_to_gong(lon)
                gong_counts.setdefault(g, []).append(star)
        for g, slist in gong_counts.items():
            n = len(slist)
            if n >= 5:
                ge_ju.append({'名称': '五星连珠', '吉凶': '大吉', '说明': f'{"、".join(slist)}五星聚{DI_ZHI[g]}，大贵之象',
                              '出处': '果老星宗', '原文': '五曜连珠：五星连续无间，顺度相生者奇'})
            elif n >= 3:
                ge_ju.append({'名称': f'{"、".join(slist)}聚{DI_ZHI[g]}', '吉凶': '吉', '说明': f'{"、".join(slist)}同宫，能量集中', '出处': '果老星宗'})

        # —— 紫气临命 ——
        if gong_of('紫气') == ming_gong_index:
            ge_ju.append({'名称': '紫气临命', '吉凶': '吉', '说明': '紫气入命，福寿双全', '出处': '果老星宗'})

        return ge_ju
    
    @classmethod
    def get_phase_name(cls, diff: float) -> Tuple[str, str]:
        """
        v3.0.0 根据角度差获取相位名称和吉凶
        
        参数：
            diff: 两星角度差（0-180）
        
        返回：
            (相位名称，吉凶)
        """
        if diff < 8:
            return ('合相', '中')
        elif 55 <= diff <= 65:
            return ('六合', '吉')
        elif 85 <= diff <= 95:
            return ('刑', '凶')
        elif 115 <= diff <= 125:
            return ('拱', '大吉')
        elif 175 <= diff <= 185:
            return ('冲', '凶')
        else:
            return ('无相位', '平')
    
    @classmethod
    def analyze_phases_v3(cls, stars: Dict[str, float]) -> Dict:
        """
        v3.0.0 完整相位分析
        
        参数：
            stars: 星曜黄经字典
        
        返回：
            相位分析结果
        """
        result = {
            '重要相位': [],
            '相位总数': 0,
            '吉相数量': 0,
            '凶相数量': 0,
            '相位详解': []
        }
        
        star_names = list(stars.keys())
        
        # 遍历所有星曜对
        for i, star1 in enumerate(star_names):
            for star2 in star_names[i+1:]:
                lon1 = stars[star1]
                lon2 = stars[star2]
                
                # 计算角度差
                diff = abs(lon1 - lon2)
                if diff > 180:
                    diff = 360 - diff
                
                # 获取相位名称
                phase_name, ji_xiong = cls.get_phase_name(diff)
                
                if phase_name != '无相位':
                    result['相位总数'] += 1
                    result['重要相位'].append({
                        '星曜': f'{star1}-{star2}',
                        '相位': phase_name,
                        '角度': round(diff, 1),
                        '吉凶': ji_xiong
                    })
                    
                    # 统计吉凶
                    if ji_xiong in ['吉', '大吉']:
                        result['吉相数量'] += 1
                    elif ji_xiong == '凶':
                        result['凶相数量'] += 1
                    
                    # 相位详解
                    detail = cls.get_phase_detail(star1, star2, phase_name, ji_xiong)
                    if detail:
                        result['相位详解'].append(detail)
        
        # 综合判断
        if result['吉相数量'] > result['凶相数量']:
            result['综合判断'] = '吉相居多，运势有利'
        elif result['凶相数量'] > result['吉相数量']:
            result['综合判断'] = '凶相居多，需谨慎行事'
        else:
            result['综合判断'] = '吉凶相当，平稳发展'
        
        return result
    
    @classmethod
    def get_phase_detail(cls, star1: str, star2: str, phase: str, ji_xiong: str) -> str:
        """
        v3.0.0 获取相位详细解释
        
        参数：
            star1, star2: 星曜名称
            phase: 相位名称
            ji_xiong: 吉凶
        
        返回：
            相位解释
        """
        details = {
            '太阳-太阴': {
                '合相': '日月同辉，光明之象，但防过刚',
                '拱': '日月拱照，贵气临身，大吉',
                '冲': '日月对冲，阴阳失调，防情绪波动'
            },
            '太阳-木星': {
                '合相': '日木合，贵气加身，事业有利',
                '拱': '日木拱，贵人相助，大吉'
            },
            '太阳-土星': {
                '合相': '日土合，压力大，需坚持',
                '冲': '日土冲，阻力大，防挫折'
            },
            '金星-水星': {
                '合相': '金水合，聪明智慧，利文书',
                '拱': '金水拱，人缘好，利交际'
            },
            '火星-土星': {
                '合相': '火土合，阻力大，需耐心',
                '冲': '火土冲，冲突多，防意外'
            },
            '木星-土星': {
                '拱': '木土拱，扩张与稳定平衡，吉'
            }
        }
        
        key = f'{star1}-{star2}'
        if key in details and phase in details[key]:
            return f'{star1}{phase}{star2}：{details[key][phase]}'
        
        # 通用解释
        general = {
            '合相': f'{star1}与{star2}合相，能量集中，影响力增强',
            '六合': f'{star1}与{star2}六合，和谐有利',
            '拱': f'{star1}与{star2}拱照，吉相，事易成',
            '刑': f'{star1}与{star2}相刑，冲突矛盾，需谨慎',
            '冲': f'{star1}与{star2}对冲，对立冲突，防变故'
        }
        
        return general.get(phase, '')
    
    @classmethod
    def get_duan_yu(cls, result: Dict, ming_gong_index: int = 0) -> List[str]:
        """生成断语"""
        duan_yu = []
        
        ming_gong = result['命宫']
        qi_zheng = result['七政']
        ge_ju = result['格局']
        
        # 命宫主星判断
        tai_yang = qi_zheng.get('太阳', {})
        if tai_yang.get('庙旺') in ['庙', '旺']:
            duan_yu.append('太阳旺相，光明磊落，事业有成')
        elif tai_yang.get('庙旺') == '陷':
            duan_yu.append('太阳落陷，宜韬光养晦，待时而动')
        
        # 太阴判断
        tai_yin = qi_zheng.get('太阴', {})
        if tai_yin.get('庙旺') in ['庙', '旺']:
            duan_yu.append('太阴旺相，情感丰富，贵人相助')
        
        # 木星判断（财帛宫）
        mu_xing = qi_zheng.get('木星', {})
        if mu_xing.get('宫位') == (ming_gong_index + 1) % 12:  # 财帛宫（命宫下一宫）
            duan_yu.append('木星照财帛，财运亨通，宜投资')
        
        # 火星判断
        huo_xing = qi_zheng.get('火星', {})
        if huo_xing.get('庙旺') == '庙':
            duan_yu.append('火星入庙，行动力强，宜开拓')
        elif huo_xing.get('庙旺') == '陷':
            duan_yu.append('火星落陷，防冲动行事')
        
        # 格局断语
        for ge in ge_ju:
            if ge['吉凶'] == '大吉':
                duan_yu.append(f"得{ge['名称']}，{ge['说明']}")
            elif ge['吉凶'] == '凶':
                duan_yu.append(f"防{ge['名称']}，{ge['说明']}")
        
        # 综合建议
        if len(duan_yu) < 3:
            duan_yu.append('星盘平稳，宜守正出奇，顺势而为')
        
        return duan_yu


def qizheng_pan(
    date_str: Optional[str] = None,
    lat: float = 39.9,
    lon: float = 116.4
) -> Dict:
    """七政四余排盘主函数"""
    
    # 解析时间
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    else:
        dt = datetime.now()
    
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    # 保存入参经纬度：下方 for 循环的循环变量 lon 会遮蔽形参 lon（原脚本 bug）
    _lat, _lon = lat, lon

    # 四柱（lunar_python 精确排柱：年月按节气换月，与八字脚本同源）
    _bazi = Solar.fromYmdHms(year, month, day, hour, dt.minute, dt.second).getLunar().getEightChar()
    year_gan, year_zhi   = _bazi.getYear()[0],  _bazi.getYear()[1]
    month_gan, month_zhi = _bazi.getMonth()[0], _bazi.getMonth()[1]
    day_gan, day_zhi     = _bazi.getDay()[0],   _bazi.getDay()[1]
    hour_gan, hour_zhi   = _bazi.getTime()[0],  _bazi.getTime()[1]
    
    # 命宫（lunar_python 精确，按农历月 + 时辰）
    ming_gong_index = DI_ZHI.index(_bazi.getMingGong()[1])
    
    # 十二宫位
    gong_wei = []
    for i in range(12):
        gong_index = (ming_gong_index + i) % 12
        gong_wei.append({
            '宫名': SHI_ER_GONG[i],
            '地支': DI_ZHI[gong_index],
            '星座': WESTERN_ZODIAC[gong_index]
        })
    
    # —— 时区：入参为本地北京时间(UTC+8)，转 UTC 供 ephem 计算（月亮每小时约走 0.5°，时区不可省）——
    _TZ_HOURS = 8.0
    dt_utc = dt - timedelta(hours=_TZ_HOURS)

    # 观测者：经纬度真正参与计算（地心黄经含视差，太阳/月亮尤明显）
    observer = ephem.Observer()
    observer.lat = str(_lat)
    observer.lon = str(_lon)
    observer.elevation = 0.0
    observer.date = ephem.Date(dt_utc)

    # 七政位置（地心黄经，ephem 精算）
    star_longitudes = {
        '太阳': _ecliptic_lon_deg(ephem.Sun(), observer),
        '太阴': _ecliptic_lon_deg(ephem.Moon(), observer),
        '木星': _ecliptic_lon_deg(ephem.Jupiter(), observer),
        '火星': _ecliptic_lon_deg(ephem.Mars(), observer),
        '土星': _ecliptic_lon_deg(ephem.Saturn(), observer),
        '金星': _ecliptic_lon_deg(ephem.Venus(), observer),
        '水星': _ecliptic_lon_deg(ephem.Mercury(), observer),
    }
    
    # 四余位置（Meeus 多项式；紫气为通行近似，标注流派分歧）
    _T = _julian_centuries_from_j2000(dt_utc)
    luo_hou = _mean_lunar_ascending_node_deg(_T)
    ji_du = _norm360(luo_hou + 180.0)      # 计都 = 降交点（近代/印度对位；沈括古法为月远地点，不采）
    yue_bo = _norm360(_mean_lunar_perigee_deg(_T) + 180.0)  # 月孛 = 月平远地点
    _jd = ephem.julian_date(ephem.Date(dt_utc))
    zi_qi = _norm360(_PURPLE_QI_DAILY_RATE * (_jd - 2451545.0))
    yu_longitudes = {'罗睺': luo_hou, '计都': ji_du, '月孛': yue_bo, '紫气': zi_qi}

    # 角宿一(Spica)黄经：二十八宿的起点锚（角宿起于角宿一）
    _spica = ephem.star('Spica')
    _spica.compute(observer)
    spica_lon = _norm360(float(ephem.Ecliptic(_spica).lon) * 180.0 / math.pi)

    # 七政落宫
    qi_zheng_wei = {}
    for star, lon in star_longitudes.items():
        gong_index = QiZhengPan.longitude_to_gong(lon)
        miao_wang = QiZhengPan.get_miao_wang(star, gong_index)
        xiu = QiZhengPan.get_xiu(lon, spica_lon)
        qi_zheng_wei[star] = {
            '黄经': round(lon, 2),
            '恒星黄经': round(_norm360(lon - spica_lon), 2),
            '宫位': gong_index,
            '宫名': SHI_ER_GONG[(gong_index - ming_gong_index) % 12],
            '地支': DI_ZHI[gong_index],
            '星座': WESTERN_ZODIAC[gong_index],
            '宿': xiu,
            '庙旺': miao_wang,
            '五行': QI_ZHENG_WUXING[star],
            '吉凶': QI_ZHENG_JI_XIONG[star]
        }
    
    # 四余落宫
    si_yu_wei = {}
    for yu, lon in yu_longitudes.items():
        gong_index = QiZhengPan.longitude_to_gong(lon)
        xiu = QiZhengPan.get_xiu(lon, spica_lon)
        si_yu_wei[yu] = {
            '黄经': round(lon, 2),
            '恒星黄经': round(_norm360(lon - spica_lon), 2),
            '宫位': gong_index,
            '宫名': SHI_ER_GONG[(gong_index - ming_gong_index) % 12],
            '地支': DI_ZHI[gong_index],
            '星座': WESTERN_ZODIAC[gong_index],
            '宿': xiu,
            '五行': SI_YU_WUXING[yu],
            '吉凶': SI_YU_JI_XIONG[yu]
        }
    
    # 格局
    all_longitudes = {**star_longitudes, **yu_longitudes}
    ge_ju = QiZhengPan.check_ge_ju(all_longitudes, ming_gong_index)
    
    # v3.0.0 相位分析
    phase_analysis = QiZhengPan.analyze_phases_v3(star_longitudes)
    
    # 断语
    temp_result = {
        '命宫': gong_wei[0],
        '七政': qi_zheng_wei,
        '格局': ge_ju,
        '相位': phase_analysis
    }
    duan_yu = QiZhengPan.get_duan_yu(temp_result, ming_gong_index)
    
    from judge.rules import pan_meta
    result = {
        **pan_meta("七政四余"),
        '公历时间': dt.strftime("%Y 年 %m 月 %d 日 %H 时 %M 分"),
        '农历四柱': f'{year_gan}{year_zhi}  {month_gan}{month_zhi}  {day_gan}{day_zhi}  {hour_gan}{hour_zhi}',
        '地点': f'北纬{_lat}°，东经{_lon}°',
        '命宫': gong_wei[0],
        '十二宫': gong_wei,
        '七政': qi_zheng_wei,
        '四余': si_yu_wei,
        '格局': ge_ju,
        '相位分析': phase_analysis,
        '断语': duan_yu,
    }
    
    return result


def format_output(result: Dict) -> str:
    """格式化输出"""
    output = []
    
    output.append("【七政四余星盘】")
    output.append(f"• 公历时间：{result['公历时间']}")
    output.append(f"• 农历四柱：{result['农历四柱']}")
    output.append(f"• 地点：{result['地点']}")
    output.append(f"• 命宫：{result['命宫']['宫名']}（{result['命宫']['地支']}宫 / {result['命宫']['星座']}座）")
    output.append("• 口径：宿按恒星黄道（角宿一锚点）入宿；宫按回归黄道 30° 等分（西洋星座），非十二次恒星宫制")
    output.append("")

    output.append("【七政落宫】")
    output.append("星曜  黄经(恒星)  宫位  地支  庙旺  宿度")
    output.append("─" * 50)
    for star, info in result['七政'].items():
        output.append(f"{star}  {info['黄经']:6.1f}°({info['恒星黄经']:5.1f}°)  {info['宫名']}  {info['地支']}  {info['庙旺']}  {info['宿']}")
    output.append("")
    
    output.append("【四余落宫】")
    for yu, info in result['四余'].items():
        output.append(f"• {yu}：{info['宫名']}（{info['地支']}）黄经{info['黄经']}° 宿{info['宿']}")
    output.append("")
    
    if result['格局']:
        output.append("【星盘格局】")
        for ge in result['格局']:
            _src = ge.get('出处', '')
            _yuan = ge.get('原文', '')
            output.append(f"• {ge['名称']}：{ge['吉凶']} — {ge['说明']}" + (f"〔{_src}〕" if _src else ""))
            if _yuan:
                output.append(f"    [原文] {_yuan}")
        output.append("")
    
    # v3.0.0 相位分析
    if result.get('相位分析'):
        phase = result['相位分析']
        output.append("【相位分析】v3.0.0")
        output.append(f"• 相位总数：{phase.get('相位总数', 0)}")
        output.append(f"• 吉相：{phase.get('吉相数量', 0)}")
        output.append(f"• 凶相：{phase.get('凶相数量', 0)}")
        if phase.get('重要相位'):
            output.append("• 重要相位：")
            for p in phase['重要相位'][:5]:  # 显示前 5 个
                output.append(f"  - {p['星曜']} {p['相位']}（{p['角度']}°）{p['吉凶']}")
        if phase.get('相位详解'):
            output.append("• 相位详解：")
            for d in phase['相位详解'][:3]:  # 显示前 3 个
                output.append(f"  - {d}")
        if phase.get('综合判断'):
            output.append(f"• 综合判断：{phase['综合判断']}")
        output.append("")
    
    if result['断语']:
        output.append("【断语】[规则推演]")
        for duan in result['断语']:
            output.append(f"• {duan}")

    return "\n".join(output)


def summary(result: Dict) -> str:
    """一眼摘要卡：命宫/七政庙旺落宫/四余/相位吉凶概览（借鉴八字/紫微升级的「一眼看懂」层）。"""
    mg = result.get("命宫", {})
    lines = [
        f"【一眼摘要】七政四余 · {result.get('农历四柱', '').strip()}",
        f"  命宫：{mg.get('宫名', '')}（{mg.get('地支', '')}宫 / {mg.get('星座', '')}）",
    ]
    qz = result.get("七政", {})
    stars = "  ".join(f"{n}({v.get('庙旺', '')}·{v.get('宫名', '')})" for n, v in qz.items())
    lines.append(f"  七政：{stars}")
    sy = result.get("四余", {})
    yu = "  ".join(f"{n}({v.get('宫名', '')})" for n, v in sy.items())
    lines.append(f"  四余：{yu}")
    xw = result.get("相位分析", {})
    if xw:
        lines.append(f"  相位：吉{xw.get('吉相数量', 0)} 凶{xw.get('凶相数量', 0)} · {xw.get('综合判断', '')}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='七政四余排盘工具 v3.0.0')
    parser.add_argument('--date', '-d', type=str, help='日期时间 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--lat', type=float, default=39.9, help='纬度')
    parser.add_argument('--lon', type=float, default=116.4, help='经度')
    parser.add_argument('--json', '-j', action='store_true', help='输出 JSON 格式')
    
    args = parser.parse_args()
    
    try:
        result = qizheng_pan(args.date, args.lat, args.lon)
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_output(result))
            
    except Exception as e:
        print(f"排盘错误：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())