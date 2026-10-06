"""Refresh the seed lists that can change between runs.

  directories  re-download the blind-sample directories (IndieWeb webring, blogroll.org,
               indieblog.page) into seed/sample-*.txt
  codeberg     websites of everyone who starred, watched, forked or commented on the spec
               repo, merged into seed/codeberg-seeds.txt (only grows)

A failed download leaves the previous list in place, so one flaky source never
shrinks the crawl.

Usage: uv run crawler/seeds.py [directories] [codeberg]
"""

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import httpx

from crawl import UA

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "seed"
SPEC_REPO = "robida/human.json"


def write(path, items, minimum):
    items = sorted(set(items))
    if len(items) < minimum:
        print(f"  {path.name}: only {len(items)} entries, keeping previous list", file=sys.stderr)
        return
    path.write_text("\n".join(items) + "\n")
    print(f"  {path.name}: {len(items)} entries", file=sys.stderr)


def links(html, skip):
    out = set()
    for u in re.findall(r'href="(https?://[^"]+)"', html):
        p = urllib.parse.urlsplit(u)
        h = p.hostname or ""
        if h and not any(x in h for x in skip):
            out.add(f"https://{h}")
    return out


def directories(client):
    try:
        feeds = client.get("https://indieblog.page/export").json()
        write(SEED / "sample-indieblog.txt",
              [e["homepage"] for e in feeds if e.get("homepage") and not e.get("errors")], 1000)
    except Exception as e:
        print(f"  indieblog.page failed: {e}", file=sys.stderr)
    try:
        # httpx rejects the emoji domain (🕸💍.ws) even in punycode; urllib doesn't mind
        req = urllib.request.Request("https://xn--sr8hvo.ws/directory", headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        write(SEED / "sample-webring.txt", links(html, ["xn--sr8hvo.ws", "github.com", "indieweb.org"]), 100)
    except Exception as e:
        print(f"  webring failed: {e}", file=sys.stderr)
    try:
        html = client.get("https://blogroll.org/").text
        write(SEED / "sample-blogroll.txt",
              links(html, ["blogroll.org", "twitter", "facebook", "wordpress.org", "gravatar"]), 300)
    except Exception as e:
        print(f"  blogroll.org failed: {e}", file=sys.stderr)


def paged(client, url):
    page = 1
    while True:
        r = client.get(url, params={"page": page, "limit": 50})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            return
        yield from batch
        page += 1


def codeberg(client):
    api = "https://codeberg.org/api/v1"
    users = set()
    try:
        for kind in ("stargazers", "subscribers"):
            users |= {u["login"] for u in paged(client, f"{api}/repos/{SPEC_REPO}/{kind}")}
        users |= {f["owner"]["login"] for f in paged(client, f"{api}/repos/{SPEC_REPO}/forks")}
        for issue in paged(client, f"{api}/repos/{SPEC_REPO}/issues?state=all&type=issues"):
            users.add(issue["user"]["login"])
        users |= {c["user"]["login"] for c in paged(client, f"{api}/repos/{SPEC_REPO}/issues/comments")}
    except Exception as e:
        print(f"  codeberg listing failed part-way: {e}", file=sys.stderr)
    path = SEED / "codeberg-seeds.txt"
    sites = set(path.read_text().split()) if path.exists() else set()
    for login in sorted(users):
        try:
            site = (client.get(f"{api}/users/{login}").json().get("website") or "").strip()
        except Exception:
            continue
        if site.startswith(("http://", "https://")):
            sites.add(site)
        elif site and "." in site and " " not in site:
            sites.add("https://" + site)
    write(path, sites, 0)


if __name__ == "__main__":
    which = sys.argv[1:] or ["directories", "codeberg"]
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": UA}) as client:
        if "directories" in which:
            directories(client)
        if "codeberg" in which:
            codeberg(client)
