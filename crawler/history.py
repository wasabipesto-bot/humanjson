"""Pull Wayback Machine history for every human.json file found by crawl.py.

For each file URL, list captures via the CDX API (collapsed on content
digest), download each distinct version raw (id_ mode), and store parsed
vouch lists so we can diff versions: when vouches were added, removed
(trust broken?), and how often files change.

Usage: uv run crawler/history.py --db data/crawl.sqlite
"""

import argparse
import asyncio
import json
import sqlite3
import sys

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
create table if not exists wb_status (hj_url text primary key, n_captures integer, error text);
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
        for attempt in range(4):
            try:
                caps = await cdx(client, hj_url)
                break
            except Exception as e:
                err = type(e).__name__
                await asyncio.sleep(5 * (attempt + 1))
        else:
            db.execute("insert or replace into wb_status values (?,?,?)", (hj_url, None, err))
            return
        n = 0
        for ts, digest, status in caps:
            if status != "200":
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
            n += 1
            await asyncio.sleep(0.5)
        db.execute("insert or replace into wb_status values (?,?,?)", (hj_url, n, None))
        db.commit()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/crawl.sqlite")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    db = sqlite3.connect(a.db, timeout=120)
    db.executescript(SCHEMA)
    done = {r[0] for r in db.execute("select hj_url from wb_status where error is null")}
    urls = [r[0] for r in db.execute("select hj_url from files") if r[0] not in done]
    print(f"{len(urls)} files to look up", file=sys.stderr)
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
