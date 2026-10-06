"""Move crawl state between the working sqlite DB and committed, diffable files.

The sqlite DB is a scratch artefact (gitignored, rebuilt every CI run). What
has to survive between runs lives in data/state/ as sorted JSON lines:

  wayback.jsonl     Wayback captures of human.json files (+ when each file was last looked up)
  git.jsonl         versions of human.json files kept in public GitHub repos
  git_files.json    which repo/path pairs to follow, so history survives a failed code search
  churn.json        Wayback lookups for vouched-for sites that have no live file
  known-sites.txt   every site that ever had a file or received a vouch (crawl seed, only grows)

  uv run crawler/state.py load [--snapshot]   rebuild data/crawl.sqlite from state (+ latest snapshot)
  uv run crawler/state.py save                write state back out of data/crawl.sqlite
"""

import argparse
import gzip
import json
import sqlite3
from pathlib import Path

from crawl import SCHEMA, reparse
from git_history import SCHEMA as GIT_SCHEMA
from history import SCHEMA as WB_SCHEMA

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data/state"
DB = ROOT / "data/crawl.sqlite"


def connect(fresh=False):
    if fresh:
        for p in (DB, DB.with_name(DB.name + "-journal")):
            p.unlink(missing_ok=True)
    db = sqlite3.connect(DB, timeout=120)
    db.executescript(SCHEMA + WB_SCHEMA + GIT_SCHEMA)
    return db


def rows(db, sql):
    cur = db.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur]


def write_jsonl(path, items):
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in items))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def latest_snapshot():
    snaps = sorted((ROOT / "data/snapshots").glob("*/files.jsonl.gz"))
    return snaps[-1].parent if snaps else None


def load(with_snapshot):
    db = connect(fresh=True)
    for r in read_jsonl(STATE / "wayback.jsonl"):
        if r["kind"] == "status":
            db.execute("insert or replace into wb_status values (?,?,?,?)",
                       (r["hj_url"], r["n_captures"], r["error"], r.get("checked_at")))
        else:
            db.execute("insert or replace into wb_captures values (?,?,?,?,?,?,?,?)",
                       (r["hj_url"], r["timestamp"], r["digest"], r["statuscode"], r["parse"],
                        r["declared_url"], r["vouch_targets"], r["vouch_dates"]))
    for r in read_jsonl(STATE / "git.jsonl"):
        db.execute("insert or replace into gh_versions values (?,?,?,?,?,?,?,?)",
                   (r["repo"], r["path"], r["sha"], r["committed_at"], r["parse"], r["declared_url"],
                    r["vouch_targets"], r["vouch_dates"]))
    if with_snapshot and (snap := latest_snapshot()):
        # Re-create the crawl tables from the newest snapshot, so the site can be
        # rebuilt without crawling (e.g. after a change to the analysis code).
        with gzip.open(snap / "files.jsonl.gz", "rt") as f:
            for line in f:
                d = json.loads(line)
                db.execute("insert or replace into files values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (d["hj_url"], d["fetched_at"], d["http_status"], d["content_type"], d["cors"],
                            d["last_modified"], d["etag"], d["sha256"], d["parse"], d["version"],
                            d["declared_url"], d["n_vouches"], d["extra_keys"], d["body"].encode()))
        with gzip.open(snap / "probes.tsv.gz", "rt") as f:
            cols = f.readline().rstrip("\n").split("\t")
            for line in f:
                v = [x or None for x in line.rstrip("\n").split("\t")]
                db.execute(f"insert or replace into probes ({','.join(cols)}) values ({','.join('?' * len(cols))})", v)
        reparse(db)
        print(f"loaded snapshot {snap.name}")
    db.commit()
    print(f"state loaded into {DB}")


def save():
    db = connect()
    STATE.mkdir(parents=True, exist_ok=True)
    wb = [{"kind": "status", **r} for r in rows(db, "select * from wb_status order by hj_url")]
    wb += [{"kind": "capture", **r} for r in rows(db, "select * from wb_captures order by hj_url, timestamp")]
    write_jsonl(STATE / "wayback.jsonl", wb)
    write_jsonl(STATE / "git.jsonl", rows(db, "select * from gh_versions order by repo, path, committed_at, sha"))
    # Known sites only grow: anything that ever had a file or got a vouch is re-probed every run
    known_path = STATE / "known-sites.txt"
    known = set(known_path.read_text().split()) if known_path.exists() else set()
    known |= {r[0] for r in db.execute("select site from probes where status like 'ok%'")}
    known |= {r[0] for r in db.execute("select distinct target from vouches where target is not null")}
    known_path.write_text("\n".join(sorted(known)) + "\n")
    print(f"state saved: {len(wb)} wayback rows, {len(known)} known sites")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["load", "save"])
    ap.add_argument("--snapshot", action="store_true", help="also load the newest snapshot (no-crawl rebuilds)")
    a = ap.parse_args()
    load(a.snapshot) if a.cmd == "load" else save()
