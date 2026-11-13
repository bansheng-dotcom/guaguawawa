# -*- coding: utf-8 -*-
"""真太阳时校正 + 中国夏令时(1986-1991)回拨 + 节气边界敏感性提示。

真太阳时 = 标准北京时间 + 经度差修正(每度4分钟, 以东经120°为基准) + 均时差。
均时差用近似公式，误差约±1分钟，对排盘足够。
"""
import math
import datetime as _dt


def _day_of_year(dt):
    return dt.timetuple().tm_yday


def equation_of_time(dt):
    """均时差(分钟)，近似公式。正值=真太阳时快于平太阳时。"""
    n = _day_of_year(dt)
    b = 2 * math.pi * (n - 81) / 364.0
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def true_solar_time(dt, longitude=120.0):
    """标准时间 -> 真太阳时。longitude 为东经度数(北京=120)。
    返回 (真太阳时 datetime, 总修正分钟数)。"""
    lon_offset = (longitude - 120.0) * 4.0
    eot = equation_of_time(dt)
    total = lon_offset + eot
    return dt + _dt.timedelta(minutes=total), total


# 中国夏令时(1986-1991)：当年4月中旬至9月中旬，时钟拨快1小时(UTC+9)
_DST = {
    1986: ((4, 13), (9, 14)),
    1987: ((4, 12), (9, 13)),
    1988: ((4, 10), (9, 11)),
    1989: ((4, 16), (9, 17)),
    1990: ((4, 15), (9, 16)),
    1991: ((4, 14), (9, 15)),
}


def is_china_dst(dt):
    """该时刻是否处于1986-1991中国夏令时段(时钟已拨快1小时)。"""
    r = _DST.get(dt.year)
    if not r:
        return False
    (sm, sd), (em, ed) = r
    return _dt.datetime(dt.year, sm, sd) <= dt < _dt.datetime(dt.year, em, ed)


def correct(dt, longitude=None, apply_dst=True):
    """综合校正：夏令时回拨(如适用) + 真太阳时。返回 (校正后 datetime, 说明列表)。"""
    notes = []
    d = dt
    if apply_dst and is_china_dst(dt):
        d = d - _dt.timedelta(hours=1)
        notes.append("1986-1991夏令时，已回拨1小时")
    if longitude is not None:
        d, mins = true_solar_time(d, longitude)
        notes.append(f"经度{longitude}°真太阳时修正{mins:+.1f}分")
    return d, notes


def jieqi_warning(solar, window_hours=2):
    """出生时刻是否临近「节」(月柱分界)。临近则返回提示，否则 None。"""
    try:
        lunar = solar.getLunar()
        pj = lunar.getPrevJie()
        nj = lunar.getNextJie()
        base = _dt.datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                            solar.getHour(), solar.getMinute(), solar.getSecond())
        for jq in (pj, nj):
            s = jq.getSolar()
            t = _dt.datetime(s.getYear(), s.getMonth(), s.getDay(),
                             s.getHour(), s.getMinute(), s.getSecond())
            if abs((base - t).total_seconds()) <= window_hours * 3600:
                return f"⚠ 出生时刻距节气「{jq.getName()}」不足{window_hours}小时，月柱可能跨节，建议核对出生时间或双盘对照"
    except Exception:
        pass
    return None