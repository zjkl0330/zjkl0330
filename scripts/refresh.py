#!/usr/bin/env python3
"""刷新 scripts/snapshot.json：语言字节 + 12 个月贡献日历。

需要环境变量 STATS_TOKEN（带 read:user 的 PAT 或 gho_ token）：
    STATS_TOKEN=xxx python scripts/refresh.py
    python scripts/build-assets.py

只用标准库。会把统计范围（仓库清单）和口径一起写进快照，便于追溯。
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot.json")

USER = "827802685"

# 只统计自己写的仓库；fork 与上游镜像仓（rsshub / lobe-chat / prompt-optimizer …）不计
SELF = [
    "job", "mini-flow", "cloud-api", "Hot-News", "personal-ai-mail",
    "Password-UUID-Generator", "web-clipboard", "tampermonkey", "extraction",
    "Live2D", "cloudflare", "checkin-hub", "ModelRadar", "blog-markdown",
    "freellmapi-cf", "domain-alert",
]

GRAPHQL = """
query {
  user(login: "%s") {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
""" % USER


def token():
    t = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not t:
        print("没有 STATS_TOKEN，本次跳过刷新，snapshot.json 保持不变。")
        sys.exit(0)
    return t


def call(url, tok, data=None):
    headers = {
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "827802685-profile-refresh",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def collect(tok):
    repos, page = [], 1
    while True:
        batch = call(
            f"https://api.github.com/user/repos?per_page=100&page={page}&affiliation=owner", tok
        )
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    want = {s.lower() for s in SELF}
    mine = [r for r in repos if r["name"].lower() in want]
    missing = want - {r["name"].lower() for r in mine}

    totals = {}
    for r in mine:
        for lang, size in call(r["languages_url"], tok).items():
            totals[lang] = totals.get(lang, 0) + size

    rows = [{"name": k, "bytes": v} for k, v in sorted(totals.items(), key=lambda kv: -kv[1])]

    g = call("https://api.github.com/graphql", tok, {"query": GRAPHQL})
    if "errors" in g:
        sys.exit("GraphQL 报错: " + json.dumps(g["errors"])[:300])
    cal = g["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]

    cur = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"] > 0:
            cur += 1
        elif i == 0:
            continue          # 今天还没提交，不算断
        else:
            break
    best = run = 0
    for d in days:
        if d["contributionCount"] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0

    return mine, missing, rows, days, cur, best


def main():
    tok = token()
    mine, missing, rows, days, cur, best = collect(tok)
    n = len(rows) and len(mine)
    today = days[-1]["date"]
    snap = {
        "generatedAt": today,
        "languages": {
            "scope": f"{n} 个自研仓库 · 按代码字节",
            "scopeEn": f"{n} owned repos · by code bytes",
            "note": f"统计范围：{n} 个自研仓库（不含 fork 与上游镜像仓），GitHub 语言字节 API · {today}",
            "noteEn": f"Scope: {n} repos I wrote (forks and upstream mirrors excluded) · GitHub languages API · {today}",
            "repos": [r["name"] for r in mine],
            "rows": rows,
        },
        "contributions": {
            "currentStreak": cur,
            "longestStreak": best,
            "days": [{"date": d["date"], "c": d["contributionCount"]} for d in days],
        },
    }
    with open(SNAP, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)

    total = sum(r["bytes"] for r in rows)
    print(f"仓库 {n} 个 · {total:,} 字节 · 语言 {len(rows)} 种")
    for r in rows[:6]:
        print(f"  {r['name']:12s} {r['bytes']:>11,}  {r['bytes']/total*100:6.2f}%")
    print(f"贡献 {sum(d['contributionCount'] for d in days):,} 次 · 当前连续 {cur} 天 · 最长 {best} 天")
    if missing:
        print("清单里这些仓在账号下拉不到，已跳过: " + ", ".join(sorted(missing)))
    print("wrote scripts/snapshot.json")


if __name__ == "__main__":
    main()
