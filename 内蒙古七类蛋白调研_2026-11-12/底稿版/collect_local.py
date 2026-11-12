# -*- coding: utf-8 -*-
"""采集层 2：盟市周度零售价（发改委价格监测）。

策略：抓页面 → 抽正文段落 → 只保留含「元/斤、元/公斤」且含品类的句子，
输出到 digest.txt 供人工核对后结构化（不做半可信的自动解析）。
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12\底稿版")
RAW = ROOT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}

PAGES = {
    # 呼和浩特市发改委 · 价格监测
    "hh_1019": "http://fgw.huhhot.gov.cn/ywgz/jggz/202610/t20261019_2043792.html",
    "hh_1026": "http://fgw.huhhot.gov.cn/ywgz/jggz/202610/t20261026_2045345.html",
    "hh_1030": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261102_2046832.html",
    "hh_1104": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261104_2047900.html",
    "hh_1106": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261106_2048691.html",
    "hh_out_1019": "http://fgw.huhhot.gov.cn/ywgz/jggz/202610/t20261019_2043790.html",
    "hh_out_1026": "http://fgw.huhhot.gov.cn/ywgz/jggz/202610/t20261026_2045338.html",
    "hh_out_1030": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261102_2046827.html",
    "hh_out_1106": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261106_2048690.html",
    "hh_feed_1104": "http://fgw.huhhot.gov.cn/ywgz/jggz/202611/t20261104_2047901.html",
    # 乌兰察布市发改委 · 价格监测
    "wlcb_1030": "https://fgw.wulanchabu.gov.cn/jgsf/2032221.html",
    "wlcb_1106": "https://fgw.wulanchabu.gov.cn/jgsf/2035331.html",
}

KEY = re.compile(r"牛肉|羊肉|猪肉|鸡肉|白条鸡|鸡蛋|鸭|鹅|鱼|虾|饲料|玉米|豆粕")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read()
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def sentences(html: str) -> list[str]:
    body = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", body)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = []
    for line in lines:
        for s in re.split(r"(?<=[。；])", line):
            s = s.strip()
            if len(s) < 8:
                continue
            if re.search(r"元/(斤|公斤|500克)", s) and KEY.search(s):
                out.append(s)
    return out


def main() -> None:
    digest = []
    for name, url in PAGES.items():
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001
            digest.append(f"### {name}  [FETCH FAIL {type(exc).__name__}] {url}")
            continue
        (RAW / f"{name}.html").write_text(html, encoding="utf-8", errors="replace")
        ss = sentences(html)
        # 去重（页面常见重复正文）
        seen, uniq = set(), []
        for s in ss:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        digest.append(f"### {name}  ({len(uniq)} 句)  {url}")
        digest.extend(uniq[:12])
        digest.append("")
    text = "\n".join(digest)
    (ROOT / "digest_local.txt").write_text(text, encoding="utf-8")
    print(text[:4000])
    print(f"\n... 总行数 {len(digest)}，写入 digest_local.txt")


if __name__ == "__main__":
    main()
