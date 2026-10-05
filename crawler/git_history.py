"""Version history of human.json files kept in public GitHub repos.

GitHub code search finds the files; for each, list every commit touching the
path and parse the file at each commit. Unlike Wayback captures this is the
complete edit history, so it shows exactly when vouches were added and removed.

Also writes seed/github-seeds.txt (each file's declared url) so the live crawl
can cover sites that nothing else led to.

Usage: uv run crawler/git_history.py --db data/crawl.sqlite   (needs `gh` logged in)
"""

import argparse
import json
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from crawl import lenient_json, norm

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ['"vouched_at"', '"vouches"', '"vouched_at" "version"']
SCHEMA = """
create table if not exists gh_versions (
    repo text, path text, sha text, committed_at text, parse text,
    declared_url text, vouch_targets text, vouch_dates text,
    primary key (repo, path, sha)
);
"""


def gh(*args):
    for attempt in range(3):
        p = subprocess.run(["gh", *args], capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout
        if "rate limit" in p.stderr.lower():
            time.sleep(60)
            continue
        raise RuntimeError(p.stderr.strip()[:200])
    raise RuntimeError("rate limited")


def find_files():
    found = set()
    for q in QUERIES:
        out = gh("search", "code", "--filename", "human.json", q, "--limit", "200", "--json", "repository,path")
        for x in json.loads(out):
            found.add((x["repository"]["nameWithOwner"], x["path"]))
        time.sleep(7)  # code search: 10 req/min
    return sorted(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data/crawl.sqlite"))
    a = ap.parse_args()
    db = sqlite3.connect(a.db, timeout=120)
    db.executescript(SCHEMA)
    files = find_files()
    print(f"{len(files)} files in {len({r for r, _ in files})} repos", file=sys.stderr)
    seeds = set()
    for repo, path in files:
        try:
            commits = json.loads(gh("api", "--paginate", f"repos/{repo}/commits?path={urllib.parse.quote(path)}&per_page=100"))
        except Exception as e:
            print(f"  {repo}/{path}: {e}", file=sys.stderr)
            continue
        for c in commits:
            sha = c["sha"]
            when = c["commit"]["committer"]["date"]
            try:
                raw = gh("api", f"repos/{repo}/contents/{urllib.parse.quote(path)}?ref={sha}",
                         "-H", "Accept: application/vnd.github.raw")
            except Exception:
                continue  # file deleted in this commit
            data, mode = lenient_json(raw.encode())
            targets, dates, declared = [], {}, None
            if isinstance(data, dict):
                declared = data.get("url")
                if isinstance(declared, str) and norm(declared):
                    seeds.add(declared)
                for v in data.get("vouches") or []:
                    if isinstance(v, dict) and (t := norm(v.get("url"))):
                        targets.append(t)
                        dates[t] = v.get("vouched_at") or v.get("vouched-at")
            db.execute("insert or replace into gh_versions values (?,?,?,?,?,?,?,?)",
                       (repo, path, sha, when, mode, str(declared), json.dumps(targets), json.dumps(dates)))
        db.commit()
        print(f"  {repo}/{path}: {len(commits)} commits", file=sys.stderr)
    (ROOT / "seed/github-seeds.txt").write_text("\n".join(sorted(seeds)) + "\n")


if __name__ == "__main__":
    main()
