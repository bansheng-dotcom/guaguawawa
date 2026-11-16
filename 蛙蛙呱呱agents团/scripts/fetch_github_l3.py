# -*- coding: utf-8 -*-
"""抓取 GitHub 公共仓库真实数据（无需 token，注意 60 req/h）。

缓存 raw JSON 到 workspace/l3_data/github；输出 normalized.json 供五角色报告使用。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "python/cpython"
OUT = Path(r"D:\蛙蛙呱呱\workspace\l3_data\github")
OUT.mkdir(parents=True, exist_ok=True)
API = "https://api.github.com"
UA = {"User-Agent": "dsh-l3-report", "Accept": "application/vnd.github+json"}


def get(path: str, name: str, params: str = "") -> list | dict | None:
    url = f"{API}{path}" + (("?" + params) if params else "")
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
            (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(name, "ok", len(data) if isinstance(data, list) else "obj")
            return data
    except urllib.error.HTTPError as e:
        print(name, "HTTP", e.code, e.headers.get("X-RateLimit-Remaining"))
        (OUT / f"{name}.error.txt").write_text(f"{e.code}\n{e.read().decode('utf-8', 'ignore')}", encoding="utf-8")
    except Exception as e:
        print(name, "ERR", e)
    return None


def main() -> int:
    meta = {"repo": REPO, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "requests": []}
    # issues (includes PRs; filter later)
    issues = []
    for page in (1, 2, 3):
        d = get(f"/repos/{REPO}/issues", f"issues_p{page}", f"state=all&per_page=100&sort=updated&direction=desc&page={page}")
        if not d:
            break
        issues.extend(d)
    # pull requests
    pulls = []
    for page in (1, 2, 3):
        d = get(f"/repos/{REPO}/pulls", f"pulls_p{page}", f"state=all&per_page=100&sort=updated&direction=desc&page={page}")
        if not d:
            break
        pulls.extend(d)
    # review comments (repo-level)
    reviews = []
    for page in (1, 2, 3):
        d = get(f"/repos/{REPO}/pulls/comments", f"reviews_p{page}", f"per_page=100&sort=created&direction=desc&page={page}")
        if not d:
            break
        reviews.extend(d)
    # actions runs
    runs = []
    for page in (1, 2, 3):
        d = get(f"/repos/{REPO}/actions/runs", f"runs_p{page}", f"per_page=100&page={page}")
        if not d:
            break
        runs.extend(d.get("workflow_runs") or [])

    norm = {
        "repo": REPO,
        "fetched_at": meta["fetched_at"],
        "issues": [{
            "number": x.get("number"), "title": x.get("title"), "state": x.get("state"),
            "created_at": x.get("created_at"), "updated_at": x.get("updated_at"),
            "closed_at": x.get("closed_at"), "comments": x.get("comments"),
            "user": (x.get("user") or {}).get("login"), "labels": [l.get("name") for l in (x.get("labels") or [])],
            "is_pr": bool(x.get("pull_request")), "body_len": len(x.get("body") or ""),
        } for x in issues],
        "pulls": [{
            "number": x.get("number"), "title": x.get("title"), "state": x.get("state"),
            "created_at": x.get("created_at"), "updated_at": x.get("updated_at"),
            "closed_at": x.get("closed_at"), "merged_at": x.get("merged_at"),
            "user": (x.get("user") or {}).get("login"), "draft": bool(x.get("draft")),
            "comments": x.get("comments"), "review_comments": x.get("review_comments"),
            "commits": x.get("commits"), "additions": x.get("additions"),
            "deletions": x.get("deletions"), "changed_files": x.get("changed_files"),
            "labels": [l.get("name") for l in (x.get("labels") or [])],
        } for x in pulls],
        "reviews": [{
            "id": x.get("id"), "pr_number": x.get("pull_request_url", "").rstrip("/").split("/")[-1],
            "user": (x.get("user") or {}).get("login"), "created_at": x.get("created_at"),
            "path": x.get("path"), "body_len": len(x.get("body") or ""),
            "in_reply_to": x.get("in_reply_to_id"), "side": x.get("side"),
        } for x in reviews],
        "runs": [{
            "id": x.get("id"), "name": x.get("name"), "status": x.get("status"),
            "conclusion": x.get("conclusion"), "event": x.get("event"),
            "created_at": x.get("created_at"), "updated_at": x.get("updated_at"),
            "run_started_at": x.get("run_started_at"), "head_branch": x.get("head_branch"),
        } for x in runs],
        "counts": {"issues_raw": len(issues), "pulls": len(pulls), "reviews": len(reviews), "runs": len(runs)},
    }
    (OUT / "normalized.json").write_text(json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(norm["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
