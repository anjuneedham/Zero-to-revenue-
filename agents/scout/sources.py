"""Read-only opportunity sources. Each returns RawItems; nothing here spends money or writes outside."""

import os
import re
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
        out = []
        for it in (data.get("items") or []) if isinstance(data, dict) else []:
            if not isinstance(it, dict) or not it.get("html_url") or "pull_request" in it:
                continue
            labels = [sanitize.clean(l.get("name"), 80) for l in it.get("labels") or [] if isinstance(l, dict)]
            repo = str(it.get("repository_url", "")).removeprefix("https://api.github.com/repos/")
            owner = repo.split("/")[0] if "/" in repo else ""
            amount, asset = parse_amount(str(it.get("title", "")), *labels)
            out.append(RawItem(
                title=str(it.get("title", "")), source=self.name, source_url=str(it["html_url"]),
                body=str(it.get("body") or ""), organization=owner, category="development bounty",
                required_skills=[l for l in labels if l.lower() not in ("bounty", "help wanted")][:5],
                expected_payment=amount, payment_asset=asset, labels=labels))
        return out


DEFAULT_SOURCES = [GitHubBounties]
