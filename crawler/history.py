"""Pull Wayback Machine history for every human.json file found by crawl.py.

For each file URL, list captures via the CDX API (collapsed on content
digest), download each distinct version raw (id_ mode), and store parsed
vouch lists so we can diff versions: when vouches were added, removed
(trust broken?), and how often files change.

Incremental: files never looked up go first, then the stalest; captures
already stored are not re-downloaded. CDX is slow (~10 s a query), so each
run has a budget (--max-files).

Usage: uv run history.py --db ../data/crawl.sqlite [--max-files N] [--recheck-days D]
"""

import argparse
import asyncio
import json
import sqlite3
import sys
import time

import httpx

from crawl import UA, lenient_json, norm

SCHEMA = """
create table if not exists wb_captures (
    hj_url text,
    timestamp text,
    digest text,
    statuscode text,
    parse text,
    declared_url text,
    vouch_targets text,             -- json list of normalised targets
    vouch_dates text,               -- json {target: vouched_at}
    primary key (hj_url, timestamp)
);
create table if not exists wb_status (hj_url text primary key, n_captures integer, error text, checked_at real);
"""


async def cdx(client, url):
    r = await client.get(
        "https://web.archive.org/cdx/search/cdx",
        params={"url": url, "output": "json", "fl": "timestamp,digest,statuscode", "collapse": "digest"},
    )
    r.raise_for_status()
    rows = r.json() if r.text.strip() else []
    return rows[1:] if rows else []


async def one(client, db, sem, hj_url):
    async with sem:
        err = None
        for attempt in range(4):
            try:
                caps = await cdx(client, hj_url)
                break
            except Exception as e:
                err = type(e).__name__
                await asyncio.sleep(5 * (attempt + 1))
        else:
            db.execute("insert or replace into wb_status values (?,?,?,?)", (hj_url, None, err, time.time()))
            return
        have = {r[0] for r in db.execute("select timestamp from wb_captures where hj_url=?", (hj_url,))}
        for ts, digest, status in caps:
            if status != "200" or ts in have:
                continue
            try:
                r = await client.get(f"https://web.archive.org/web/{ts}id_/{hj_url}")
                data, mode = lenient_json(r.content)
            except Exception:
                data, mode = None, "fetch-fail"
            targets, dates, declared = [], {}, None
            if isinstance(data, dict):
                declared = data.get("url")
                for v in data.get("vouches") or []:
                    if isinstance(v, dict) and (t := norm(v.get("url"))):
                        targets.append(t)
                        dates[t] = v.get("vouched_at") or v.get("vouched-at")
            db.execute(
                "insert or replace into wb_captures values (?,?,?,?,?,?,?,?)",
                (hj_url, ts, digest, status, mode, str(declared), json.dumps(targets), json.dumps(dates)),
            )
            await asyncio.sleep(0.5)
        n = db.execute("select count(*) from wb_captures where hj_url=?", (hj_url,)).fetchone()[0]
        db.execute("insert or replace into wb_status values (?,?,?,?)", (hj_url, n, None, time.time()))
        db.commit()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/crawl.sqlite")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-files", type=int, default=100_000)
    ap.add_argument("--recheck-days", type=float, default=28)
    a = ap.parse_args()
    db = sqlite3.connect(a.db, timeout=120)
    db.executescript(SCHEMA)
    if "checked_at" not in [r[1] for r in db.execute("pragma table_info(wb_status)")]:
        db.execute("alter table wb_status add column checked_at real")
    status = {r[0]: (r[1], r[2]) for r in db.execute("select hj_url, error, checked_at from wb_status")}
    stale = time.time() - a.recheck_days * 86400
    due = [u for (u,) in db.execute("select hj_url from files")
           if u not in status or status[u][0] is not None or (status[u][1] or 0) < stale]
    due.sort(key=lambda u: (u in status, (status.get(u) or (None, 0))[1] or 0))  # never-seen first, then stalest
    urls = due[: a.max_files]
    print(f"{len(due)} files due, looking up {len(urls)}", file=sys.stderr)
    sem = asyncio.Semaphore(a.concurrency)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": UA}) as client:
        tasks = [one(client, db, sem, u) for u in urls]
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % 25 == 0:
                print(f"  {i}/{len(urls)}", file=sys.stderr)
    db.commit()


if __name__ == "__main__":
    asyncio.run(main())
