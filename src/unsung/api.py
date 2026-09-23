"""GitHub GraphQL data collection for unsung.

Fetches the "unsung" contribution numbers -- the open-source work that does not
show up on the green contribution graph: reviews given, and pull requests and
issues opened on repositories the user does *not* own.

Pure standard library (urllib). No third-party dependencies.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

GRAPHQL_URL = "https://api.github.com/graphql"

_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!){
  user(login:$login){
    login
    name
    createdAt
    contributionsCollection(from:$from, to:$to){
      totalPullRequestReviewContributions
      totalPullRequestContributions
      totalIssueContributions
      pullRequestReviewContributionsByRepository(maxRepositories:100){
        repository{ nameWithOwner isPrivate owner{ login } }
        contributions{ totalCount }
      }
      pullRequestContributionsByRepository(maxRepositories:100){
        repository{ nameWithOwner isPrivate owner{ login } }
        contributions{ totalCount }
      }
      issueContributionsByRepository(maxRepositories:100){
        repository{ nameWithOwner isPrivate owner{ login } }
        contributions{ totalCount }
      }
    }
  }
}
"""


class ApiError(RuntimeError):
    """Raised when the GitHub API cannot be queried."""


@dataclass
class Stats:
    """Aggregated unsung contribution numbers for one user over one window."""

    login: str
    name: str | None
    reviews_given: int = 0
    prs_to_others: int = 0
    issues_for_others: int = 0
    projects_helped: int = 0
    top_helped: list[tuple[str, int]] = field(default_factory=list)
    since_label: str = "the last year"

    @property
    def total_help(self) -> int:
        return self.reviews_given + self.prs_to_others + self.issues_for_others


def _post(token: str, variables: dict) -> dict:
    body = json.dumps({"query": _QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "unsung (+https://github.com/ingrid-owusu/unsung)",
        },
    )
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            detail = exc.read().decode(errors="replace")[:300]
            if exc.code in (403, 429, 502, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                last_err = ApiError(f"HTTP {exc.code}: {detail}")
                continue
            raise ApiError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network
            last_err = ApiError(f"network error: {exc.reason}")
            time.sleep(2 * (attempt + 1))
    else:
        raise last_err or ApiError("request failed")
    if "errors" in payload and payload["errors"]:
        msg = "; ".join(e.get("message", "?") for e in payload["errors"])
        raise ApiError(f"GraphQL error: {msg}")
    data = payload.get("data", {}).get("user")
    if not data:
        raise ApiError(f"user not found: {variables.get('login')!r}")
    return data


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _windows(login_created: datetime, since: str, now: datetime):
    """Yield (from, to) datetime windows to query.

    GitHub caps contributionsCollection at one year, so 'all' iterates by year.
    """
    if since == "all":
        start = login_created
        cur = now
        while cur > start:
            frm = max(start, cur - timedelta(days=365))
            yield frm, cur
            cur = frm - timedelta(seconds=1)
    else:  # "year" (default): trailing 365 days
        yield now - timedelta(days=365), now


def _accumulate(cc: dict, login: str, agg: dict) -> None:
    login_l = login.lower()

    def add(entries, bucket):
        for entry in entries or []:
            repo = entry["repository"]
            if repo.get("isPrivate"):
                continue
            owner = (repo.get("owner") or {}).get("login", "")
            if owner.lower() == login_l:
                continue  # own repo -> already on the contribution graph
            n = entry["contributions"]["totalCount"]
            name = repo["nameWithOwner"]
            bucket[name] = bucket.get(name, 0) + n
            agg["per_repo"][name] = agg["per_repo"].get(name, 0) + n

    add(cc.get("pullRequestReviewContributionsByRepository"), agg["reviews"])
    add(cc.get("pullRequestContributionsByRepository"), agg["prs"])
    add(cc.get("issueContributionsByRepository"), agg["issues"])


def collect(login: str, token: str, since: str = "year", now: datetime | None = None) -> Stats:
    """Fetch and aggregate unsung stats for ``login``.

    ``since`` is ``"year"`` (trailing 365 days, default) or ``"all"`` (lifetime).
    """
    if not token:
        raise ApiError("a GitHub token is required (set GITHUB_TOKEN)")
    now = now or datetime.now(timezone.utc)

    # First call establishes identity + createdAt (query the trailing year).
    first = _post(token, {"login": login, "from": _iso(now - timedelta(days=365)), "to": _iso(now)})
    created = datetime.fromisoformat(first["createdAt"].replace("Z", "+00:00"))
    real_login = first["login"]
    name = first.get("name")

    agg = {"reviews": {}, "prs": {}, "issues": {}, "per_repo": {}}
    _accumulate(first["contributionsCollection"], real_login, agg)

    if since == "all":
        # Re-walk full history year by year (the trailing year was already added
        # by the identity call, so skip the first window here).
        windows = list(_windows(created, "all", now))
        for frm, to in windows[1:]:
            data = _post(token, {"login": real_login, "from": _iso(frm), "to": _iso(to)})
            _accumulate(data["contributionsCollection"], real_login, agg)
        since_label = "all time"
    else:
        since_label = "the last year"

    top = sorted(agg["per_repo"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return Stats(
        login=real_login,
        name=name,
        reviews_given=sum(agg["reviews"].values()),
        prs_to_others=sum(agg["prs"].values()),
        issues_for_others=sum(agg["issues"].values()),
        projects_helped=len(agg["per_repo"]),
        top_helped=top,
        since_label=since_label,
    )
