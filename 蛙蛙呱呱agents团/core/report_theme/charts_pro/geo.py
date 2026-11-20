# -*- coding: utf-8 -*-
"""geo —— 内蒙古 12 市/盟真实边界（阿里 DataV GeoAtlas，150000_full）。

投影：Web-Mercator（x = λ·cos45°，y = ln tan(45°+φ/2)），等比缩放到图框。
只做中国单省，不引第三方投影库。
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

GEO = Path(__file__).with_name("data") / "im_cities.geojson"
CITIES12 = ["呼和浩特", "包头", "乌海", "赤峰", "通辽", "鄂尔多斯",
            "呼伦贝尔", "巴彦淖尔", "乌兰察布", "兴安盟", "锡林郭勒盟", "阿拉善盟"]


def _merc(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon) * math.cos(math.radians(45))
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


@lru_cache(maxsize=1)
def _raw():
    g = json.loads(GEO.read_text(encoding="utf-8"))
    feats = []
    for f in g["features"]:
        name = f["properties"]["name"]
        short = name
        for s in ("市", "盟"):
            if short.endswith(s):
                short = short[:-1]
        short = {"兴安": "兴安盟", "锡林郭勒": "锡林郭勒盟", "阿拉善": "阿拉善盟"}.get(short, short)
        centroid = f["properties"].get("centroid") or f["properties"].get("center")
        geom = f["geometry"]
        rings = []
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"]]
        else:
            rings = geom["coordinates"]
        feats.append((short, rings, centroid))
    pts = [_merc(*c) for _, _, c in feats]
    for _, rings, _ in feats:
        for poly in rings:
            for ring in poly:
                pts += [_merc(lon, lat) for lon, lat in ring]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return feats, (min(xs), max(xs), min(ys), max(ys))


def project(box=(24, 40, 616, 300)):
    """返回 (paths, centroids)；paths: {city: d}，centroids: {city: (x, y)}。"""
    feats, (x0, x1, y0, y1) = _raw()
    bx0, by0, bx1, by1 = box
    s = min((bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0))
    ox = bx0 + ((bx1 - bx0) - (x1 - x0) * s) / 2
    oy = by0 + ((by1 - by0) - (y1 - y0) * s) / 2

    def P(lon, lat):
        x, y = _merc(lon, lat)
        return ox + (x - x0) * s, oy + (y1 - y) * s

    paths, cents = {}, {}
    for name, rings, centroid in feats:
        d = []
        for poly in rings:
            for ring in poly:
                pts = [P(lon, lat) for lon, lat in ring]
                d.append("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z")
        paths[name] = " ".join(d)
        cents[name] = P(*centroid)
    return paths, cents
