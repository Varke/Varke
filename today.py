"""Refresh the profile SVGs (dark_mode.svg / light_mode.svg) with live GitHub stats.

Runs daily via GitHub Actions. Uses only the standard library.

Env:
    ACCESS_TOKEN  - GitHub token (repo + read:user) for the GraphQL / REST API
    USER_NAME     - GitHub login (default: Varke)
"""
from __future__ import annotations

import calendar
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date

TOKEN = os.environ["ACCESS_TOKEN"]
USER = os.environ.get("USER_NAME", "Varke")
BIRTHDAY = date(1999, 2, 13)

LINE_W = 56   # panel width in characters, must match the SVG layout
LEFT_W = 26   # left column width of two-stat lines

API = "https://api.github.com"


def call(url: str, data: dict | None = None) -> tuple[int, dict | list]:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{url} -> HTTP {e.code}: {e.read()[:300]!r}") from e


def graphql(query: str, variables: dict) -> dict:
    _, payload = call(f"{API}/graphql", {"query": query, "variables": variables})
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def uptime() -> str:
    today = date.today()
    years = today.year - BIRTHDAY.year
    months = today.month - BIRTHDAY.month
    days = today.day - BIRTHDAY.day
    if days < 0:
        months -= 1
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        days += calendar.monthrange(prev_year, prev_month)[1]
    if months < 0:
        years -= 1
        months += 12

    def plural(n: int, word: str) -> str:
        return f"{n} {word}{'' if n == 1 else 's'}"

    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def fetch_user() -> dict:
    data = graphql(
        """
        query($login: String!) {
          user(login: $login) {
            followers { totalCount }
            repositoriesContributedTo(contributionTypes: [COMMIT]) { totalCount }
          }
        }
        """,
        {"login": USER},
    )
    return data["user"]


def fetch_repos() -> list[dict]:
    repos, cursor = [], None
    while True:
        data = graphql(
            """
            query($login: String!, $cursor: String) {
              user(login: $login) {
                repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
                  nodes { nameWithOwner stargazerCount isFork }
                  pageInfo { hasNextPage endCursor }
                }
              }
            }
            """,
            {"login": USER, "cursor": cursor},
        )
        block = data["user"]["repositories"]
        repos.extend(block["nodes"])
        if not block["pageInfo"]["hasNextPage"]:
            return repos
        cursor = block["pageInfo"]["endCursor"]


def count_loc(repos: list[dict]) -> tuple[int, int, int]:
    """Lines added / deleted and commits by USER across owned non-fork repos.

    Counted from /stats/contributors (default branch), the same way the LOC
    number is built, so commits and LOC always agree with each other.
    """
    added = deleted = commits = 0
    for repo in repos:
        if repo["isFork"]:
            continue
        url = f"{API}/repos/{repo['nameWithOwner']}/stats/contributors"
        for attempt in range(6):
            status, stats = call(url)
            if status != 202:
                break
            time.sleep(4)  # GitHub is still computing the stats
        else:
            print(f"warning: stats never became ready for {repo['nameWithOwner']}")
            continue
        if not isinstance(stats, list):
            continue
        for contributor in stats:
            if (contributor.get("author") or {}).get("login") == USER:
                commits += contributor["total"]
                for week in contributor["weeks"]:
                    added += week["a"]
                    deleted += week["d"]
    return added, deleted, commits


def dots(prefix: str, value: str, width: int, suffix: str = "") -> str:
    """Filler so that `prefix + ' ' + dots + ' ' + value + suffix` is `width` chars."""
    n = width - len(prefix) - len(value) - len(suffix) - 1
    return "." * max(n, 2)


def set_tspan(svg: str, tspan_id: str, text: str) -> str:
    pattern = rf'(<tspan[^>]*id="{tspan_id}"[^>]*>)[^<]*(</tspan>)'
    new_svg, n = re.subn(pattern, rf"\g<1>{text}\g<2>", svg)
    if n != 1:
        raise RuntimeError(f"expected exactly one tspan #{tspan_id}, found {n}")
    return new_svg


def update_svg(path: str, values: dict) -> None:
    with open(path, encoding="utf-8") as f:
        svg = f.read()

    age = values["age"]
    svg = set_tspan(svg, "age_data", age)
    svg = set_tspan(svg, "age_data_dots", f" {dots('. Uptime: ', age, LINE_W)} ")

    repos, contrib = values["repos"], values["contrib"]
    svg = set_tspan(svg, "repo_data", repos)
    svg = set_tspan(svg, "repo_data_dots", f" {dots('. Repos: ', repos, LEFT_W)} ")
    svg = set_tspan(svg, "contrib_data", contrib)
    svg = set_tspan(svg, "contrib_data_dots",
                    f" {dots(' | Contributed: ', contrib, LINE_W - LEFT_W)} ")

    stars, followers = values["stars"], values["followers"]
    svg = set_tspan(svg, "star_data", stars)
    svg = set_tspan(svg, "star_data_dots", f" {dots('. Stars: ', stars, LEFT_W)} ")
    svg = set_tspan(svg, "follower_data", followers)
    svg = set_tspan(svg, "follower_data_dots",
                    f" {dots(' | Followers: ', followers, LINE_W - LEFT_W)} ")

    commits = values["commits"]
    svg = set_tspan(svg, "commit_data", commits)
    svg = set_tspan(svg, "commit_data_dots", f" {dots('. Commits: ', commits, LINE_W)} ")

    loc, loc_add, loc_del = values["loc"], values["loc_add"], values["loc_del"]
    suffix = f" ( {loc_add}++, {loc_del}-- )"
    svg = set_tspan(svg, "loc_data", loc)
    svg = set_tspan(svg, "loc_data_dots",
                    f" {dots('. Lines of Code: ', loc, LINE_W, suffix)} ")
    svg = set_tspan(svg, "loc_add", loc_add)
    svg = set_tspan(svg, "loc_del", loc_del)

    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def main() -> None:
    user = fetch_user()
    repos = fetch_repos()
    added, deleted, commits = count_loc(repos)

    values = {
        "age": uptime(),
        "repos": f"{len(repos):,}",
        "contrib": f"{user['repositoriesContributedTo']['totalCount']:,}",
        "stars": f"{sum(r['stargazerCount'] for r in repos):,}",
        "followers": f"{user['followers']['totalCount']:,}",
        "commits": f"{commits:,}",
        "loc": f"{added - deleted:,}",
        "loc_add": f"{added:,}",
        "loc_del": f"{deleted:,}",
    }
    print(json.dumps(values, indent=2, ensure_ascii=False))

    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("dark_mode.svg", "light_mode.svg"):
        update_svg(os.path.join(base, name), values)
        print(f"updated {name}")


if __name__ == "__main__":
    main()
