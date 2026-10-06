"""Did sites that have no human.json today ever have one?

For every vouched-for site without a live file, ask the Wayback Machine CDX
API whether it ever archived a human.json under that host. A hit means the
file existed and was removed (or moved somewhere our probe can't see):
the closest thing we have to an abandonment rate.

Writes data/state/churn.json ({host: {checked, rows}}) and churn_recheck.json.
Incremental: never-checked hosts first, re-checked after --recheck-days; --max-hosts
caps a run, since each CDX query takes ~10 s.
"""

import argparse
import asyncio
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

import httpx

from crawl import UA, lenient_json

ROOT = Path(__file__).resolve().parent.parent


async def check(client, sem, host, out):
    async with sem:
        for attempt in range(4):
            try:
                r = await client.get("https://web.archive.org/cdx/search/cdx", params={
                    "url": host, "matchType": "host", "output": "json", "collapse": "urlkey",
                    "filter": ["original:.*/humans?\\.json$", "statuscode:200"], "fl": "original,timestamp",
                    "limit": "50"})
                r.raise_for_status()
                rows = r.json() if r.text.strip() else []
                out[host] = {"checked": time.time(), "rows": rows[1:] if rows else []}
                return
            except Exception:
                await asyncio.sleep(10 * (attempt + 1))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hosts", type=int, default=100_000)
    ap.add_argument("--recheck-days", type=float, default=90)
    a = ap.parse_args()
    g = json.loads((ROOT / "data/graph.json").read_text())
    # Most informative first: hosts robots.txt kept us out of, then the most vouched-for
    status = dict(sqlite3.connect(ROOT / "data/crawl.sqlite").execute("select site, status from probes"))
    indeg = {}
    for e in g["edges"]:
        indeg[e["target"]] = indeg.get(e["target"], 0) + 1
    bare = [n["id"] for n in g["nodes"] if not n["has_file"]]
    bare.sort(key=lambda k: (status.get(k) != "robots", -indeg.get(k, 0), k))
    hosts = list(dict.fromkeys(k.split("/")[0] for k in bare))
    path = ROOT / "data/state/churn.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    stale = time.time() - a.recheck_days * 86400
    due = [h for h in hosts if h not in out or out[h]["checked"] < stale]
    due.sort(key=lambda h: h in out)  # never-checked first, keeping priority order within each group
    todo = due[: a.max_hosts]
    print(f"{len(due)} hosts due, checking {len(todo)}", file=sys.stderr)
    sem = asyncio.Semaphore(3)
    async with httpx.AsyncClient(timeout=60, headers={"User-Agent": UA}) as client:
        tasks = [asyncio.create_task(check(client, sem, h, out)) for h in todo]
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}, hits so far {sum(1 for v in out.values() if v['rows'])}", file=sys.stderr)
    path.write_text(json.dumps(dict(sorted(out.items())), indent=0) + "\n")

    # Re-fetch every archived file URL as it is today (robots.txt permitting). A 200 +
    # parseable JSON means the file is still there and only homepage discovery missed it.
    file_re = re.compile(r"/humans?\.json$")
    recheck, robots = {}, {}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": UA}) as client:
        for host, v in out.items():
            for orig, _ in v["rows"]:
                if not file_re.search(orig.split("?")[0]) or orig in recheck:
                    continue
                try:
                    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(orig))
                    if origin not in robots:
                        rp = urllib.robotparser.RobotFileParser()
                        rr = await client.get(origin + "/robots.txt")
                        if rr.status_code == 200:
                            rp.parse(rr.text.splitlines())
                        else:
                            rp.allow_all = rr.status_code >= 400 and rr.status_code not in (401, 403)
                            rp.disallow_all = not rp.allow_all
                        robots[origin] = rp
                    if not robots[origin].can_fetch(UA, orig):
                        recheck[orig] = {"status": None, "robots": True}
                        continue
                    r = await client.get(orig)
                    data, mode = lenient_json(r.content) if r.status_code == 200 else (None, None)
                    recheck[orig] = {"status": r.status_code, "parses": isinstance(data, dict)}
                except Exception as e:
                    recheck[orig] = {"status": None, "error": type(e).__name__}
    (ROOT / "data/state/churn_recheck.json").write_text(json.dumps(dict(sorted(recheck.items())), indent=1) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
