# -*- coding: utf-8 -*-
"""Fetcher 层：单 URL 抓取（限速 / robots / 超时 / 字节上限 / 退避重试）。

失败分类是硬要求（C-8）：调用方要能回答「为什么这条源没数据」，
所以这里不抛异常，一律返回 `FetchResult(kind=...)`。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

RETRYABLE = ("http_429", "http_5xx", "timeout", "error")


@dataclass
class FetchResult:
    url: str
    kind: str                 # ok / robots_blocked / http_404 / http_5xx / timeout / too_large / error
    status: int = 0
    body: str = ""
    nbytes: int = 0
    elapsed: float = 0.0
    attempts: int = 0
    error: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.kind == "ok"

    def to_dict(self) -> Dict[str, Any]:
        return {"url": self.url, "kind": self.kind, "status": self.status,
                "bytes": self.nbytes, "elapsed": round(self.elapsed, 3),
                "attempts": self.attempts, "error": self.error, **self.meta}


class RateLimiter:
    """同域最小间隔 = 1/rps；只做单进程，不做分布式。"""

    def __init__(self, rps: float = 1.0):
        self.interval = (1.0 / float(rps)) if float(rps or 0) > 0 else 0.0
        self._last: Dict[str, float] = {}

    def wait(self, url: str) -> float:
        host = urllib.parse.urlsplit(url).netloc
        now = time.monotonic()
        last = self._last.get(host)
        slept = 0.0
        if last is not None and self.interval > 0:
            gap = self.interval - (now - last)
            if gap > 0:
                time.sleep(gap)
                slept = gap
        self._last[host] = time.monotonic()
        return slept


class RobotsCache:
    """robots.txt 按域缓存；抓不到时按「允许」处理并留痕（保守但不瘫）。"""

    def __init__(self, policy: Dict[str, Any], max_bytes: int = 200_000):
        self.policy = policy
        self.max_bytes = max_bytes
        self._cache: Dict[str, Any] = {}

    def _load(self, scheme: str, netloc: str):
        key = f"{scheme}://{netloc}"
        if key in self._cache:
            return self._cache[key]
        import urllib.robotparser as rp
        parser = rp.RobotFileParser()
        url = key + "/robots.txt"
        text = ""
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": str(self.policy.get("user_agent") or "GuaguaBot/1.0")})
            with urllib.request.urlopen(req, timeout=float(self.policy.get("timeout") or 20)) as r:
                text = r.read(self.max_bytes).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 robots 不可得 → 不拦，但记在 meta
            text = ""
        if text:
            parser.parse(text.splitlines())
        else:
            parser.parse([])
        self._cache[key] = (parser, bool(text))
        return self._cache[key]

    def allowed(self, url: str) -> bool:
        u = urllib.parse.urlsplit(url)
        if not self.policy.get("respect_robots", True):
            return True
        parser, _ = self._load(u.scheme or "https", u.netloc)
        return parser.can_fetch(str(self.policy.get("user_agent") or "*"), url)

    def had_robots(self, url: str) -> bool:
        u = urllib.parse.urlsplit(url)
        _, got = self._load(u.scheme or "https", u.netloc)
        return got


def _classify(status: int) -> str:
    if 200 <= status < 300:
        return "ok"
    if status in (401, 403, 412):
        return "http_%d" % status
    if status == 404 or status == 410:
        return "http_404"
    if status == 429:
        return "http_429"
    if 500 <= status < 600:
        return "http_5xx"
    return "http_%d" % status


def http_get(url: str, policy: Dict[str, Any],
             limiter: Optional[RateLimiter] = None,
             robots: Optional[RobotsCache] = None,
             sleep=time.sleep) -> FetchResult:
    """抓一个 URL。返回 FetchResult，不抛异常。"""
    ua = str(policy.get("user_agent") or "GuaguaBot/1.0")
    timeout = float(policy.get("timeout") or 20)
    max_bytes = int(policy.get("max_bytes") or 2_000_000)
    retries = int(policy.get("retries") or 0)
    backoff = float(policy.get("backoff") or 1.5)

    if robots is not None and not robots.allowed(url):
        return FetchResult(url=url, kind="robots_blocked",
                           meta={"robots": "disallow"})

    attempts = 0
    last: Optional[FetchResult] = None
    while attempts <= retries:
        attempts += 1
        if limiter is not None:
            limiter.wait(url)
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua,
                "Accept-Language": str(policy.get("accept_language") or "zh-CN")})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(max_bytes + 1)
                status = int(getattr(r, "status", 200) or 200)
                if len(raw) > max_bytes:
                    last = FetchResult(url=url, kind="too_large", status=status,
                                       nbytes=len(raw), attempts=attempts,
                                       elapsed=time.monotonic() - t0,
                                       meta={"max_bytes": max_bytes})
                else:
                    return FetchResult(
                        url=url, kind="ok", status=status,
                        body=raw.decode("utf-8", "replace"), nbytes=len(raw),
                        elapsed=time.monotonic() - t0, attempts=attempts)
        except urllib.error.HTTPError as exc:
            kind = _classify(int(exc.code))
            last = FetchResult(url=url, kind=kind, status=int(exc.code),
                               attempts=attempts, elapsed=time.monotonic() - t0,
                               error=str(exc))
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            kind = "timeout" if "timed out" in reason.lower() else "error"
            last = FetchResult(url=url, kind=kind, attempts=attempts,
                               elapsed=time.monotonic() - t0, error=reason)
        except Exception as exc:  # noqa: BLE001
            last = FetchResult(url=url, kind="error", attempts=attempts,
                               elapsed=time.monotonic() - t0,
                               error="%s: %s" % (type(exc).__name__, exc))
        if last and last.kind in RETRYABLE and attempts <= retries:
            sleep(backoff * (2 ** (attempts - 1)))
            continue
        break
    return last or FetchResult(url=url, kind="error", error="no attempt")
