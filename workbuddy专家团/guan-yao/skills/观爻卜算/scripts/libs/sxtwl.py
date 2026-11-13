# -*- coding: utf-8 -*-
"""
sxtwl(寿星天文历) 的兼容垫片 —— 用 lunar_python 替代，避免 C++ 编译。
实现 kinqimen / kintaiyi 用到的接口：
  fromSolar(y, m, d) -> Day
    .getYearGZ()/.getMonthGZ()/.getDayGZ()/.getHourGZ(hour) -> (.tg 天干索引, .dz 地支索引)
    .getLunarYear()/.getLunarMonth()/.getLunarDay()
    .hasJieQi() / .getJieQi()(节气索引1-24) / .getJieQiJD()
    .before(n) / .after(n)
  JD2DD(jd) -> Time(.Y .M .D .h .m .s)
"""
from lunar_python import Solar

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
# 与 kintaiyi/jieqi.py 的 jqmc 同序(传统), 索引 1-24
JQ = ['小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满',
      '芒种', '夏至', '小暑', '大暑', '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
      '立冬', '小雪', '大雪', '冬至']


class _GZ:
    def __init__(self, s):
        self.tg = GAN.index(s[0])
        self.dz = ZHI.index(s[1])

    def __repr__(self):
        return f"{GAN[self.tg]}{ZHI[self.dz]}"


class _Time:
    def __init__(self, solar):
        self.Y = solar.getYear()
        self.M = solar.getMonth()
        self.D = solar.getDay()
        self.h = solar.getHour()
        self.m = solar.getMinute()
        self.s = solar.getSecond()


class _Day:
    def __init__(self, solar):
        self._solar = solar
        self._lunar = solar.getLunar()

    def getYearGZ(self):
        return _GZ(self._lunar.getYearInGanZhiExact())

    def getMonthGZ(self):
        return _GZ(self._lunar.getMonthInGanZhiExact())

    def getDayGZ(self):
        return _GZ(self._lunar.getDayInGanZhi())

    def getHourGZ(self, hour):
        s = Solar.fromYmdHms(self._solar.getYear(), self._solar.getMonth(),
                             self._solar.getDay(), int(hour), 0, 0)
        return _GZ(s.getLunar().getTimeInGanZhi())

    def getLunarYear(self):
        return self._lunar.getYear()

    def getLunarMonth(self):
        return self._lunar.getMonth()

    def getLunarDay(self):
        return self._lunar.getDay()

    def hasJieQi(self):
        return bool(self._lunar.getJieQi())

    def getJieQi(self):
        # 返回 sxtwl 原生索引：0=冬至, 1=小寒, ..., 23=大雪（与 jieqi.py 的
        # _NAME_TO_SXTWL 约定一致）。JQ 尾项「冬至」index 23+1=24 → 取模归 0。
        name = self._lunar.getJieQi()
        if name in JQ:
            return (JQ.index(name) + 1) % 24
        return 0

    def getJieQiJD(self):
        name = self._lunar.getJieQi()
        if not name:
            return 0.0
        # 按日期匹配节气表中的正确条目：lunar_python 的 getJieQiTable() 中文键
        # 「冬至」指向上一节气年(如 2024-12-21 冬至会错配到 2023-12-22)，
        # 正确时间在英文键 DONG_ZHI 下；按「节气发生日 == 当日」匹配可避开年界错位。
        y, m, d = self._solar.getYear(), self._solar.getMonth(), self._solar.getDay()
        for solar in self._lunar.getJieQiTable().values():
            if (solar.getYear(), solar.getMonth(), solar.getDay()) == (y, m, d):
                return solar.getJulianDay()
        solar = self._lunar.getJieQiTable().get(name)
        return solar.getJulianDay() if solar else 0.0

    def before(self, n):
        return _Day(self._solar.next(-int(n)))

    def after(self, n):
        return _Day(self._solar.next(int(n)))


def fromSolar(year, month, day):
    return _Day(Solar.fromYmd(int(year), int(month), int(day)))


def JD2DD(jd):
    return _Time(Solar.fromJulianDay(jd))


def Time(year, month, day, hour, minute, second):
    return _Time(Solar.fromYmdHms(int(year), int(month), int(day),
                                  int(hour), int(minute), int(second)))


def toJD(time_obj):
    return Solar.fromYmdHms(time_obj.Y, time_obj.M, time_obj.D,
                            time_obj.h, time_obj.m, time_obj.s).getJulianDay()