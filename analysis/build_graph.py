"""Resolve crawl.sqlite into a site-level vouch graph.

Nodes are *sites* (one per distinct human.json file, keyed by its declared
url) plus *bare targets* (vouched-for sites with no file). A vouch target
resolves to a file-owning site if it was probed and led to that file, or if
the file's declared url is a prefix of it (the spec treats `url` as a prefix).

Writes data/graph.json, consumed by stats.py and the report.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crawler"))
from crawl import norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MULTI_TENANT = {"github.com", "codeberg.org", "gitlab.com", "sr.ht", "git.sr.ht", "medium.com", "substack.com",
                "bsky.app", "youtube.com", "twitch.tv", "patreon.com", "ko-fi.com", "itch.io", "tumblr.com",
                "linktr.ee", "instagram.com", "twitter.com", "x.com", "mastodon.social", "dev.to", "lobste.rs",
                "news.ycombinator.com", "web.archive.org", "neocities.org", "soundcloud.com", "bandcamp.com"}


def main(db_path=ROOT / "data/crawl.sqlite", out=ROOT / "data/graph.json"):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    files = {r["hj_url"]: dict(r) for r in db.execute("select * from files")}
    for f in files.values():
        f.pop("body")

    # Owner key per file: declared url if it normalises, otherwise the probed site
    probed_to_file = defaultdict(set)
    for r in db.execute("select site, hj_url from probes where status='ok'"):
        probed_to_file[r["hj_url"]].add(r["site"])

    owner = {}
    for hj, f in files.items():
        d = f["declared_url"]
        if d and d.startswith("["):  # 0.2.0 style urls: []
            try:
                d = json.loads(d)[0]
            except Exception:
                d = None
        k = norm(d) if d else None
        if not k:
            k = min(probed_to_file.get(hj) or {norm(hj.rsplit("/", 1)[0])}, key=len)
        owner[hj] = k

    # Duplicate files (mirrors on several domains, or same file at two paths)
    # collapse onto one site key; keep the copy with most vouches.
    by_key = defaultdict(list)
    for hj, k in owner.items():
        by_key[k].append(hj)
    canonical = {}
    for k, hjs in by_key.items():
        best = max(hjs, key=lambda h: (files[h]["n_vouches"] or 0, -len(h)))
        canonical[k] = best
    # Same content at different declared keys? (e.g. jneidel.com/.de both declaring themselves)
    by_sha = defaultdict(list)
    for k, hj in canonical.items():
        by_sha[files[hj]["sha256"]].append(k)

    alias = {}  # any key -> site key
    for k, hj in canonical.items():
        alias[k] = k
    for hj, sites in probed_to_file.items():
        k = owner.get(hj)
        for s in sites:
            alias.setdefault(s, k)
    for shas in by_sha.values():
        if len(shas) > 1:
            primary = min(shas, key=len)
            for k in shas:
                alias[k] = primary
    for a in alias:
        while alias[alias[a]] != alias[a]:
            alias[a] = alias[alias[a]]
    file_sites = {alias[k] for k in canonical}

    def resolve(t):
        if t in alias:
            return alias[t]
        # declared url acts as a prefix: longest owning prefix wins
        parts = t.split("/")
        for i in range(len(parts) - 1, 0, -1):
            p = "/".join(parts[:i])
            if p in alias:
                return alias[p]
        # Bare target: collapse deep links to the site (host, or host/~user, host/@user,
        # or the first path segment on hosts that serve many people)
        if len(parts) > 1 and (parts[1][:1] in ("~", "@") or parts[0] in MULTI_TENANT):
            return "/".join(parts[:2])
        return parts[0]

    probe_status = {r["site"]: r["status"] for r in db.execute("select site, status from probes")}
    probe_source = {r["site"]: r["source"] for r in db.execute("select site, source from probes")}

    nodes = {}
    for k in file_sites:
        hj = canonical[k]
        f = files[hj]
        nodes[k] = {
            "id": k, "has_file": True, "hj_url": hj, "version": f["version"], "parse": f["parse"],
            "cors": f["cors"], "content_type": f["content_type"], "last_modified": f["last_modified"],
            "n_vouches_raw": f["n_vouches"], "extra_keys": json.loads(f["extra_keys"] or "[]"),
            "aliases": sorted(a for a, v in alias.items() if v == k and a != k),
            "source": probe_source.get(k),
        }

    edges = {}
    for r in db.execute("select hj_url, idx, target_raw, target, vouched_at, extra from vouches"):
        if r["hj_url"] not in owner:
            continue
        src = alias[owner[r["hj_url"]]]
        if canonical.get(owner[r["hj_url"]]) != r["hj_url"] and owner[r["hj_url"]] in canonical:
            continue  # non-canonical duplicate file
        if not r["target"]:
            continue
        dst = resolve(r["target"])
        if dst == src:
            nodes[src]["self_vouch"] = True
            continue
        e = edges.setdefault((src, dst), {"source": src, "target": dst, "vouched_at": r["vouched_at"],
                                           "target_raw": r["target_raw"]})
        if r["extra"]:
            e["extra"] = json.loads(r["extra"])
        if dst not in nodes:
            nodes[dst] = {"id": dst, "has_file": False, "probe_status": probe_status.get(r["target"])}

    g = {"nodes": list(nodes.values()), "edges": list(edges.values())}
    out.write_text(json.dumps(g, indent=1))
    print(f"{sum(n['has_file'] for n in nodes.values())} sites with files, "
          f"{sum(not n['has_file'] for n in nodes.values())} bare targets, {len(edges)} edges", file=sys.stderr)


if __name__ == "__main__":
    main()
