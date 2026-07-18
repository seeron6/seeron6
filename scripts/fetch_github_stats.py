#!/usr/bin/env python3
"""Fetch GitHub profile stats via the GraphQL API and write data/github-stats.json.

Token resolution: env GITHUB_TOKEN / GH_TOKEN (used by the GitHub Action), then
`gh auth token` as a local fallback. Only public data is read, so any valid
token works.

Usage:
  python scripts/fetch_github_stats.py [username]

Output:
  data/github-stats.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

OUT = Path("data/github-stats.json")

QUERY = """
query($login:String!){
  user(login:$login){
    name
    followers{totalCount}
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      totalCount
      nodes{
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}){
          edges{ size node{ name color } }
        }
      }
    }
    contributionsCollection{
      totalCommitContributions
      restrictedContributionsCount
    }
    pullRequests{ totalCount }
    issues{ totalCount }
  }
}
"""


def get_token() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(key):
            return os.environ[key]
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return None


def main() -> None:
    user = sys.argv[1] if len(sys.argv) > 1 else "seeron6"
    token = get_token()
    if not token:
        sys.exit("[stats] no GitHub token (set GITHUB_TOKEN or run `gh auth login`)")

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "seeron6-profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        sys.exit(f"[stats] GraphQL errors: {payload['errors']}")
    u = payload["data"]["user"]

    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    lang_size: dict[str, int] = {}
    lang_color: dict[str, str] = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            lang_size[name] = lang_size.get(name, 0) + e["size"]
            lang_color[name] = e["node"]["color"] or "#8b949e"
    total = sum(lang_size.values()) or 1
    top = sorted(lang_size.items(), key=lambda kv: -kv[1])[:6]
    languages = [
        {"name": n, "pct": round(100 * s / total, 1), "color": lang_color[n]}
        for n, s in top
    ]

    cc = u["contributionsCollection"]
    out = {
        "user": user,
        "name": u["name"],
        "stars": stars,
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "commits_year": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "languages": languages,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[stats] {user}: repos={out['repos']} stars={out['stars']} "
          f"commits(yr)={out['commits_year']} prs={out['prs']} "
          f"followers={out['followers']} langs={len(languages)}")


if __name__ == "__main__":
    main()
