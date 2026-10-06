"""Carry last week's file forward for sites that failed transiently this crawl.

A timeout or an unreachable robots.txt says nothing about whether a site still has
its human.json, but dropping the file would make the site vanish from the graph and
show up as churn. So if this crawl got an error (status err:*) for a site that had a
file in the previous snapshot, the previous file is re-used and the probe is marked
`ok-carried`. A file is carried for at most --max-days since it was last actually
fetched; after that the site drops out like any other.

Usage: uv run crawler/carry.py [--max-days 28]
"""

import argparse
import gzip
import json
import time

from crawl import store_vouches, lenient_json
from state import ROOT, connect


def previous_snapshot(today):
    snaps = sorted(p.parent for p in (ROOT / "data/snapshots").glob("*/files.jsonl.gz") if p.parent.name < today)
    return snaps[-1] if snaps else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-days", type=float, default=28)
    a = ap.parse_args()
    today = time.strftime("%Y-%m-%d", time.gmtime())
    snap = previous_snapshot(today)
    if not snap:
        print("no previous snapshot; nothing to carry")
        return
    prev_files = {}
    with gzip.open(snap / "files.jsonl.gz", "rt") as f:
        for line in f:
            d = json.loads(line)
            prev_files[d["hj_url"]] = d
    prev_ok = {}
    with gzip.open(snap / "probes.tsv.gz", "rt") as f:
        cols = f.readline().rstrip("\n").split("\t")
        for line in f:
            r = dict(zip(cols, line.rstrip("\n").split("\t")))
            if r["status"].startswith("ok") and r["hj_url"] in prev_files:
                prev_ok[r["site"]] = r["hj_url"]
    db = connect()
    cutoff = time.time() - a.max_days * 86400
    carried = 0
    for site, status in db.execute("select site, status from probes").fetchall():
        hj = prev_ok.get(site)
        if not hj or not status.startswith("err:"):
            continue
        d = prev_files[hj]
        if d["fetched_at"] < cutoff:
            continue  # failing for too long: let it go
        if not db.execute("select 1 from files where hj_url=?", (hj,)).fetchone():
            body = d["body"].encode()
            db.execute("insert into files values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (hj, d["fetched_at"], d["http_status"], d["content_type"], d["cors"], d["last_modified"],
                        d["etag"], d["sha256"], d["parse"], d["version"], d["declared_url"], d["n_vouches"],
                        d["extra_keys"], body))
            data, _ = lenient_json(body)
            vouches = (data or {}).get("vouches") or []
            store_vouches(db, hj, vouches if isinstance(vouches, list) else [])
        # keep the error that triggered the carry, so persistent failures are visible
        db.execute("update probes set status='ok-carried', hj_url=?, via=? where site=?", (hj, "carried:" + status, site))
        carried += 1
    db.commit()
    print(f"carried {carried} files forward from {snap.name}")


if __name__ == "__main__":
    main()
