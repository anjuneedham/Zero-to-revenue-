"""Read-only opportunity sources. Each returns RawItems; nothing here spends money or writes outside."""

import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

from agents.scout import sanitize
from agents.scout.evaluate import RawItem
from integrations.web.fetch import fetch_json

_AMOUNT = re.compile(r"(?:\$\s?|USD\s?|USDC\s?)(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|(\d{1,3}(?:,\d{3})+|\d+)\s?(?:USD|USDC|USDT|DAI)\b", re.I)
_ASSET = re.compile(r"\b(USDC|USDT|DAI|ETH|BNB|USD)\b|\$", re.I)


def parse_amount(*texts: str):
    """Returns (amount, asset) as CLAIMED by the text; asset '' if unclear. Never verified."""
    for t in texts:
        m = _AMOUNT.search(t or "")
        if m:
            amount = float((m.group(1) or m.group(2)).replace(",", ""))
            a = _ASSET.search(m.group(0))
            asset = (a.group(1).upper() if a and a.group(1) else "USD")
            return amount, asset
    return None, ""


class GitHubBounties:
    """Open GitHub issues labelled 'bounty'. Public, unauthenticated (GITHUB_TOKEN raises the rate limit)."""
    name = "github-bounty-label"
    hosts = {"api.github.com"}

    def __init__(self, fetch=fetch_json, per_page: int = 30):
        self.fetch, self.per_page = fetch, per_page

    def items(self) -> list[RawItem]:
        q = quote("label:bounty state:open is:issue is:public")
        url = f"https://api.github.com/search/issues?q={q}&sort=created&order=desc&per_page={self.per_page}"
        headers = {"Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        data = self.fetch(url, self.hosts, headers)
        out, reputation = [], {}
        for it in (data.get("items") or []) if isinstance(data, dict) else []:
            if not isinstance(it, dict) or not it.get("html_url") or "pull_request" in it:
                continue
            labels = [sanitize.clean(l.get("name"), 80) for l in it.get("labels") or [] if isinstance(l, dict)]
            repo = str(it.get("repository_url", "")).removeprefix("https://api.github.com/repos/")
            owner = repo.split("/")[0] if "/" in repo else ""
            amount, asset = parse_amount(str(it.get("title", "")), *labels)
            if repo not in reputation:
                reputation[repo] = self._repo_vetted(repo, headers)
            out.append(RawItem(
                title=str(it.get("title", "")), source=self.name, source_url=str(it["html_url"]),
                body=str(it.get("body") or ""), organization=owner, category="development bounty",
                required_skills=[l for l in labels if l.lower() not in ("bounty", "help wanted")][:5],
                expected_payment=amount, payment_asset=asset, labels=labels, sponsor_verified=reputation[repo]))
        return out

    def _repo_vetted(self, repo: str, headers: dict):
        """True: established repo (>=50 stars, >=180 days old). False: young/unknown farm-like repo.
        None: could not check (rate limit, error) - never guessed."""
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo or ""):
            return None
        try:
            r = self.fetch(f"https://api.github.com/repos/{repo}", self.hosts, headers)
            created = datetime.fromisoformat(str(r["created_at"]).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - created).days
            return int(r.get("stargazers_count", 0)) >= 50 and age >= 180
        except Exception:
            return None


class SuperteamEarn:
    """Superteam Earn: vetted listings with stated reward, token, deadline, sponsor and submission count.
    Rewards are prize POOLS shared among winners, so the owner's share is unknown until results."""
    name = "superteam-earn"
    hosts = {"superteam.fun"}

    def __init__(self, fetch=fetch_json, take: int = 40):
        self.fetch, self.take = fetch, take

    def items(self) -> list[RawItem]:
        data = self.fetch(f"https://superteam.fun/api/listings?take={self.take}", self.hosts, {"Accept": "application/json"})
        out = []
        for x in data if isinstance(data, list) else []:
            if not isinstance(x, dict) or not x.get("slug") or x.get("status") != "OPEN" or x.get("isWinnersAnnounced"):
                continue
            sponsor = x.get("sponsor") if isinstance(x.get("sponsor"), dict) else {}
            amount = x.get("rewardAmount")
            subs = (x.get("_count") or {}).get("Submission") if isinstance(x.get("_count"), dict) else None
            caveats = []
            if amount:
                caveats.append("reward is a prize pool shared among winners; your share is unknown")
            if subs is not None:
                caveats.append(f"{subs} submission(s) so far")
            if x.get("agentAccess") not in (None, "HUMAN_ONLY"):
                caveats.append(f"AI-use policy: {x.get('agentAccess')}")
            out.append(RawItem(
                title=str(x.get("title", "")), source=self.name, source_url=f"https://superteam.fun/earn/listing/{x['slug']}",
                organization=str(sponsor.get("name") or "").strip(), category=str(x.get("type") or "bounty"),
                deadline=x.get("deadline"), expected_payment=float(amount) if isinstance(amount, (int, float)) else None,
                payment_asset=str(x.get("token") or ""), caveats=caveats,
                sponsor_verified=sponsor.get("isVerified") if isinstance(sponsor.get("isVerified"), bool) else None,
                human_only=x.get("agentAccess") == "HUMAN_ONLY"))
        return out


class FreelancerCom:
    """Freelancer.com public project-search API (no login). Fixed-price projects only; bid_count and
    bid_avg are a competition signal, not a difficulty signal, and are passed through as a caveat."""
    name = "freelancer-com"
    hosts = {"www.freelancer.com"}

    def __init__(self, fetch=fetch_json, limit: int = 50, min_budget: float = 500):
        self.fetch, self.limit, self.min_budget = fetch, limit, min_budget

    def items(self) -> list[RawItem]:
        url = (f"https://www.freelancer.com/api/projects/0.1/projects/active/?limit={self.limit}"
               "&compact=true&job_details=true&full_description=true&project_types[]=fixed")
        data = self.fetch(url, self.hosts, {"Accept": "application/json"})
        result = data.get("result") if isinstance(data, dict) else None
        out = []
        for p in (result.get("projects") if isinstance(result, dict) else None) or []:
            if not isinstance(p, dict) or not p.get("id") or p.get("type") != "fixed":
                continue
            budget = p.get("budget") if isinstance(p.get("budget"), dict) else {}
            hi = budget.get("maximum")
            if not isinstance(hi, (int, float)) or hi < self.min_budget:
                continue
            currency = (p.get("currency") or {}).get("code", "USD") if isinstance(p.get("currency"), dict) else "USD"
            jobs = [j.get("name") for j in (p.get("jobs") or []) if isinstance(j, dict) and j.get("name")]
            bids = p.get("bid_stats") if isinstance(p.get("bid_stats"), dict) else {}
            caveats = []
            if bids.get("bid_count") is not None:
                caveats.append(f"{bids['bid_count']} bid(s) already placed, average ${bids.get('bid_avg', 0):.0f}")
            caveats.append("budget is a client-set range; the awarded amount may be lower")
            out.append(RawItem(
                title=str(p.get("title", "")), source=self.name, source_url=f"https://www.freelancer.com/projects/{p['id']}",
                body=sanitize.clean(p.get("preview_description") or p.get("description") or "", 3000), category="freelance project",
                required_skills=jobs[:6], expected_payment=float(hi), payment_asset=str(currency), payment_method="Freelancer.com escrow",
                caveats=caveats))
        return out


DEFAULT_SOURCES = [SuperteamEarn, GitHubBounties, FreelancerCom]
