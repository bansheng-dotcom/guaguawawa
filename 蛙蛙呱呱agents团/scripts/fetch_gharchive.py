# -*- coding: utf-8 -*-
"""GH Archive 1 小时真实 GitHub 公共事件流。

GitHub REST 匿名额度被共享 IP 耗尽（403 rate limit 0），改抓 GH Archive：
- URL: https://data.gharchive.org/2024-01-01-0.json.gz
- 1 小时、全 GitHub 公共事件；本地解析 Issues/PR/Review/Push 四类实体。
- 报告里明确写“sample: 1 小时事件流”，不冒充全量。
"""
from __future__ import annotations

import gzip
import json
import urllib.request
from collections import Counter
from pathlib import Path

OUT = Path(r"D:\蛙蛙呱呱\workspace\l3_data\github_archive")
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://data.gharchive.org/2024-01-01-0.json.gz"
GZ = OUT / "2024-01-01-0.json.gz"

if not GZ.exists():
    print("downloading", URL)
    req = urllib.request.Request(URL, headers={"User-Agent": "dsh-l3"})
    with urllib.request.urlopen(req, timeout=120) as r, GZ.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
print("size", GZ.stat().st_size)

issues, pulls, reviews, pushes = [], [], [], []
mix = Counter()
n = 0
with gzip.open(GZ, "rt", encoding="utf-8") as f:
    for line in f:
        n += 1
        try:
            e = json.loads(line)
        except Exception:
            continue
        typ = e.get("type")
        mix[typ] += 1
        repo = (e.get("repo") or {}).get("name")
        actor = (e.get("actor") or {}).get("login")
        created = e.get("created_at")
        p = e.get("payload") or {}
        if typ == "IssuesEvent" and len(issues) < 8000:
            it = p.get("issue") or {}
            issues.append({
                "repo": repo, "actor": actor, "action": p.get("action"), "number": it.get("number"),
                "title": it.get("title"), "state": it.get("state"), "created_at": it.get("created_at"),
                "closed_at": it.get("closed_at"), "comments": it.get("comments"),
                "labels": [x.get("name") for x in (it.get("labels") or [])],
                "body_len": len(it.get("body") or ""), "event_at": created,
            })
        elif typ == "PullRequestEvent" and len(pulls) < 8000:
            pr = p.get("pull_request") or {}
            pulls.append({
                "repo": repo, "actor": actor, "action": p.get("action"), "number": pr.get("number"),
                "title": pr.get("title"), "state": pr.get("state"), "created_at": pr.get("created_at"),
                "closed_at": pr.get("closed_at"), "merged_at": pr.get("merged_at"),
                "additions": pr.get("additions"), "deletions": pr.get("deletions"),
                "changed_files": pr.get("changed_files"), "comments": pr.get("comments"),
                "review_comments": pr.get("review_comments"), "commits": pr.get("commits"),
                "user": (pr.get("user") or {}).get("login"), "draft": pr.get("draft"),
                "event_at": created,
            })
        elif typ in ("PullRequestReviewEvent", "PullRequestReviewCommentEvent") and len(reviews) < 8000:
            rv = p.get("review") or {}
            pr = p.get("pull_request") or {}
            reviews.append({
                "repo": repo, "actor": actor, "action": p.get("action"),
                "pr_number": pr.get("number"), "state": rv.get("state"),
                "submitted_at": rv.get("submitted_at"), "body_len": len(rv.get("body") or ""),
                "event_at": created, "path": (p.get("comment") or {}).get("path"),
            })
        elif typ == "PushEvent" and len(pushes) < 8000:
            pushes.append({
                "repo": repo, "actor": actor, "size": p.get("size"),
                "distinct_size": p.get("distinct_size"), "ref": p.get("ref"),
                "commits": len(p.get("commits") or []), "event_at": created,
            })

norm = {
    "source": "GH Archive",
    "url": URL,
    "window": "2024-01-01 00:00—01:00 UTC",
    "sample": "1 小时全 GitHub 公共事件流",
    "events": n,
    "event_mix": dict(mix.most_common(20)),
    "issues": issues, "pulls": pulls, "reviews": reviews, "pushes": pushes,
    "counts": {"issues": len(issues), "pulls": len(pulls), "reviews": len(reviews), "pushes": len(pushes)},
}
(OUT / "normalized.json").write_text(json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"events": n, "counts": norm["counts"], "top": norm["event_mix"]}, ensure_ascii=False, indent=2))
