"""Export the current crawl to data/snapshots/<date>/ as plain, diffable files.

files.jsonl.gz  one line per human.json file: url, headers we care about, raw body
probes.tsv.gz   every site probed and what happened

Snapshots are what future re-crawls are compared against (churn, updates,
withdrawn vouches), so they are committed; the sqlite working DB is not.
"""

import argparse
import gzip
import json
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data/crawl.sqlite"))
    ap.add_argument("--date", default=date.today().isoformat())
    a = ap.parse_args()
    out = ROOT / "data/snapshots" / a.date
    out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    with gzip.open(out / "files.jsonl.gz", "wt") as f:
        for r in db.execute("select * from files order by hj_url"):
            d = dict(r)
            d["body"] = d["body"].decode("utf-8", "replace")
            f.write(json.dumps(d, sort_keys=True) + "\n")
    with gzip.open(out / "probes.tsv.gz", "wt") as f:
        cols = ["site", "probed_at", "depth", "status", "final_url", "hj_url", "via", "link_header", "source"]
        f.write("\t".join(cols) + "\n")
        for r in db.execute(f"select {','.join(cols)} from probes order by site"):
            f.write("\t".join("" if v is None else str(v).replace("\t", " ") for v in r) + "\n")
    print(f"snapshot written to {out}")


if __name__ == "__main__":
    main()
