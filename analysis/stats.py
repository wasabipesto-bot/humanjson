"""Statistics over data/graph.json (+ crawl.sqlite for history and the blind sample).

Writes data/stats.json and prints a readable summary. Each section answers
one of the project questions; see REPORT.md for the narrative.
"""

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crawler"))
from crawl import norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 5)


SECOND_LEVEL = {"co.uk", "org.uk", "me.uk", "ac.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp", "com.br", "co.za"}


def regdom(k):
    h = k.split("/")[0].split(":")[0]
    parts = h.split(".")
    n = 3 if ".".join(parts[-2:]) in SECOND_LEVEL else 2
    return ".".join(parts[-n:])


def parse_date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if not m:
        return None
    try:
        d = date(*map(int, m.groups()))
    except ValueError:
        return None
    return d if date(2000, 1, 1) <= d <= TODAY else None


def main():
    g = json.loads((ROOT / "data/graph.json").read_text())
    db = sqlite3.connect(ROOT / "data/crawl.sqlite")
    nodes = {n["id"]: n for n in g["nodes"]}
    sites = {k for k, n in nodes.items() if n["has_file"]}
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    for e in g["edges"]:
        G.add_edge(e["source"], e["target"], vouched_at=e["vouched_at"])
    F = G.subgraph(sites).copy()  # file-to-file trust graph
    S = {}

    # ---- 1. How many, and largest -------------------------------------------------
    outdeg = sorted(((G.out_degree(k), k) for k in sites), reverse=True)
    indeg_all = sorted(((G.in_degree(k), k, nodes[k]["has_file"]) for k in G), reverse=True)
    S["counts"] = {
        "sites_with_file": len(sites),
        "bare_targets": len(nodes) - len(sites),
        "edges": G.number_of_edges(),
        "edges_between_files": F.number_of_edges(),
        "files_with_zero_vouches": sum(1 for k in sites if G.out_degree(k) == 0),
        "median_out_degree": sorted(d for d, _ in outdeg)[len(outdeg) // 2],
        "mean_out_degree": round(sum(d for d, _ in outdeg) / len(outdeg), 1),
    }
    S["top_out"] = [{"site": k, "vouches": d} for d, k in outdeg[:20]]
    S["top_in"] = [{"site": k, "vouched_by": d, "has_file": f} for d, k, f in indeg_all[:25]]
    S["top_in_without_file"] = [{"site": k, "vouched_by": d} for d, k, f in indeg_all if not f][:15]
    S["unvouched_sites"] = sum(1 for k in sites if F.in_degree(k) == 0)

    # ---- 2. Chains and circles of trust ---------------------------------------------
    sccs = sorted(nx.strongly_connected_components(F), key=len, reverse=True)
    core = F.subgraph(sccs[0])
    wccs = sorted(nx.weakly_connected_components(F), key=len, reverse=True)
    mutual = nx.Graph((u, v) for u, v in F.edges if F.has_edge(v, u))
    # Cliques of *independent* sites: drop pairs on the same registrable domain
    mutual_ind = nx.Graph((u, v) for u, v in mutual.edges if regdom(u) != regdom(v))
    cliques = sorted(nx.find_cliques(mutual_ind), key=len, reverse=True) if mutual_ind.number_of_edges() else []
    # Longest shortest path (the longest chain of trust you'd actually have to follow)
    longest = (0, None, None)
    reach5 = {}
    for s in sites:
        lengths = nx.single_source_shortest_path_length(F, s)
        far = max(lengths.items(), key=lambda kv: kv[1])
        if far[1] > longest[0]:
            longest = (far[1], s, far[0])
        reach5[s] = sum(1 for d in lengths.values() if 0 < d <= 5)
    chain = nx.shortest_path(F, longest[1], longest[2]) if longest[1] else []
    S["trust"] = {
        "largest_scc": len(sccs[0]),
        "scc_sizes_top5": [len(c) for c in sccs[:5]],
        "n_singleton_scc": sum(1 for c in sccs if len(c) == 1),
        "largest_wcc": len(wccs[0]),
        "n_wcc": len(wccs),
        "wcc_sizes_top5": [len(c) for c in wccs[:5]],
        "core_diameter": nx.diameter(core) if len(core) > 1 else 0,
        "core_avg_shortest_path": round(nx.average_shortest_path_length(core), 2) if len(core) > 1 else 0,
        "longest_shortest_chain": longest[0],
        "longest_chain": chain,
        "mutual_pairs": mutual.number_of_edges(),
        "reciprocity": round(nx.overall_reciprocity(F), 3),
        "largest_mutual_clique": len(cliques[0]) if cliques else 0,
        "largest_mutual_cliques": [sorted(c) for c in cliques if len(c) == len(cliques[0])],
        "median_reach_within_5_hops": sorted(reach5.values())[len(reach5) // 2],
        "max_reach_within_5_hops": max(reach5.items(), key=lambda kv: kv[1]),
        "share_reaching_half_within_5": round(sum(v >= len(sites) / 2 for v in reach5.values()) / len(sites), 3),
    }
    # Groups cut off from the main component
    S["islands"] = [sorted(c) for c in wccs[1:] if len(c) >= 3]
    same = [(u, v) for u, v in G.edges if regdom(u) == regdom(v)]
    S["same_owner"] = {
        "edges_same_registrable_domain": len(same),
        "sites_doing_it": len({u for u, _ in same}),
        "examples": sorted(f"{u} -> {v}" for u, v in same)[:30],
    }
    # Same-day rings: 3+ independent sites that all vouch for each other, all on one date
    S["same_day_rings"] = []
    for c in nx.find_cliques(mutual_ind):
        if len(c) >= 3:
            dates = {F.edges[u, v]["vouched_at"] for u in c for v in c if u != v}
            inbound = {u for v in c for u in F.predecessors(v)} - set(c)
            if len(dates) == 1:
                S["same_day_rings"].append({"sites": sorted(c), "date": dates.pop(),
                                            "outside_vouchers": sorted(inbound)})
    pr = nx.pagerank(F)
    S["pagerank_top"] = [{"site": k, "pr": round(v, 4)} for k, v in sorted(pr.items(), key=lambda kv: -kv[1])[:15]]
    bc = nx.betweenness_centrality(F)
    S["betweenness_top"] = [{"site": k, "bc": round(v, 4)} for k, v in sorted(bc.items(), key=lambda kv: -kv[1])[:10]]

    # ---- 3. Timeline: when did people vouch / adopt --------------------------------
    first_seen = {}
    per_site_dates = defaultdict(list)
    for e in g["edges"]:
        d = parse_date(e["vouched_at"])
        if d:
            per_site_dates[e["source"]].append(d)
    wb_first = {}
    wb_rows = list(db.execute("select hj_url, min(timestamp), count(*) from wb_captures group by hj_url")) \
        if db.execute("select name from sqlite_master where name='wb_captures'").fetchone() else []
    hj_to_site = {n["hj_url"]: k for k, n in nodes.items() if n["has_file"]}
    for hj, ts, _ in wb_rows:
        if hj in hj_to_site:
            wb_first[hj_to_site[hj]] = datetime.strptime(ts[:8], "%Y%m%d").date()
    for k in sites:
        cands = [min(per_site_dates[k])] if per_site_dates.get(k) else []
        if k in wb_first:
            cands.append(wb_first[k])
        if cands:
            first_seen[k] = min(cands)
    months = Counter(d.strftime("%Y-%m") for d in first_seen.values())
    S["adoption_by_month"] = dict(sorted(months.items()))
    S["adoption_undated"] = len(sites) - len(first_seen)
    vouch_months = Counter(parse_date(e["vouched_at"]).strftime("%Y-%m")
                           for e in g["edges"] if parse_date(e["vouched_at"]))
    S["vouches_by_month"] = dict(sorted(vouch_months.items()))
    S["vouches_undated"] = sum(1 for e in g["edges"] if not parse_date(e["vouched_at"]))
    pre_spec = [k for k, d in first_seen.items() if d < date(2026, 3, 1)]
    S["pre_spec_dates"] = len(pre_spec)

    # ---- 4. Are they being updated? -------------------------------------------------
    last_vouch = {k: max(v) for k, v in per_site_dates.items()}
    last_mod = {}
    for k in sites:
        lm = nodes[k].get("last_modified")
        if lm:
            try:
                last_mod[k] = parsedate_to_datetime(lm).date()
            except Exception:
                pass
    # "last activity" = newest of newest vouch date and Last-Modified (LM can be deploy time, so report both)
    def bucket(d):
        age = (TODAY - d).days
        return "≤30d" if age <= 30 else "31–90d" if age <= 90 else "91–180d" if age <= 180 else ">180d"
    order = ["≤30d", "31–90d", "91–180d", ">180d"]
    S["freshness"] = {
        "newest_vouch_age": {b: sum(1 for d in last_vouch.values() if bucket(d) == b) for b in order},
        "newest_vouch_undated": len(sites) - len(last_vouch),
        "last_modified_age": {b: sum(1 for d in last_mod.values() if bucket(d) == b) for b in order},
        "last_modified_missing": len(sites) - len(last_mod),
        "single_date_files": sum(1 for k, v in per_site_dates.items() if len(set(v)) == 1 and len(v) > 1),
        "active_since_june": sum(1 for d in last_vouch.values() if d >= date(2026, 6, 1)),
    }
    # Did the file grow after its first day? (vouches dated later than the site's first vouch)
    grew = sum(1 for k, v in per_site_dates.items() if len(set(v)) > 1)
    S["freshness"]["files_with_vouches_on_multiple_dates"] = grew

    # ---- 5. Trust broken? (vouches removed between versions of a file) -------------
    # Two independent version sources, diffed separately (never across sources):
    #  - Wayback captures of the live file, followed by today's crawl
    #  - git history of files kept in public GitHub repos
    def iso(ts):
        return ts if "-" in ts else f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"

    seqs = {}  # (source, file) -> [(iso date, owner site, set of targets)]
    for hj, ts, targets, parse in db.execute(
            "select hj_url, timestamp, vouch_targets, parse from wb_captures order by hj_url, timestamp") if wb_rows else []:
        if parse in ("strict", "lenient") and hj in hj_to_site:
            seqs.setdefault(("wayback", hj), []).append((iso(ts), hj_to_site[hj], set(json.loads(targets))))
    cur = defaultdict(set)
    for hj, t in db.execute("select hj_url, target from vouches where target is not null"):
        cur[hj].add(t)
    for key in [k for k in seqs if k[0] == "wayback"]:
        seqs[key].append((TODAY.isoformat(), hj_to_site[key[1]], cur.get(key[1], set())))
    has_gh = db.execute("select name from sqlite_master where name='gh_versions'").fetchone()
    for repo, path, when, parse, declared, targets in db.execute(
            "select repo, path, committed_at, parse, declared_url, vouch_targets from gh_versions "
            "order by committed_at") if has_gh else []:
        if parse in ("strict", "lenient"):
            owner = norm(declared) or f"github.com/{repo}"
            seqs.setdefault(("git", f"{repo}/{path}"), []).append((when[:10], owner, set(json.loads(targets))))

    def classify(owner, gone, t0, t1, added):
        if regdom(gone) == regdom(owner):
            return "own site"
        name = regdom(gone).split(".")[0]
        if any(regdom(a) == regdom(gone) or regdom(a).split(".")[0] == name for a in added):
            return "url changed"
        if t0 == t1:
            return "same-day edit"
        return "withdrawn"

    removed, added_later = [], 0
    for (src, f), versions in seqs.items():
        for (t0, owner, a), (t1, _, b) in zip(versions, versions[1:]):
            added = b - a
            added_later += len(added)
            for gone in sorted(a - b):
                removed.append({"site": owner, "removed": gone, "between": [t0, t1], "source": src,
                                "kind": classify(owner, gone, t0, t1, added)})
    git_files = {f: v for (src, f), v in seqs.items() if src == "git"}
    last_commit = [max(t for t, _, _ in v) for v in git_files.values()]
    S["history"] = {
        "files_with_archive": len(wb_rows),
        "files_with_git_history": len(git_files),
        "git_files_changed_after_first_commit": sum(1 for v in git_files.values() if len({frozenset(x[2]) for x in v}) > 1),
        "git_commits_median": sorted(len(v) for v in git_files.values())[len(git_files) // 2] if git_files else 0,
        "git_last_commit_age": {b: sum(1 for t in last_commit if bucket(date.fromisoformat(t)) == b) for b in order},
        "vouches_removed": len(removed),
        "removed_by_kind": dict(Counter(r["kind"] for r in removed)),
        "withdrawn": [r for r in removed if r["kind"] == "withdrawn"],
        "removals": removed,
        "vouches_added_in_later_versions": added_later,
    }
    # Files that the archive saw but are now gone
    gone_files = [hj for hj, *_ in wb_rows if hj not in hj_to_site]
    S["history"]["archived_files_now_missing"] = gone_files

    # ---- 6. Dead / broken links in the graph ----------------------------------------
    status = dict(db.execute("select site, status from probes"))
    bare = [k for k, n in nodes.items() if not n["has_file"]]
    bare_status = Counter()
    for k in bare:
        s = status.get(k) or "unprobed"
        bare_status["dns-fail" if "address" in s or "not known" in s else
                    "tls" if "SSL" in s else "timeout" if "Timeout" in s else
                    s.split(":")[0] if s.startswith("err") else s] += 1
    S["bare_target_status"] = dict(bare_status.most_common())
    declared_broken = [k for k, s in status.items() if s and s.startswith("declared-but")]
    S["declared_but_broken"] = declared_broken

    # ---- 7. Spec compliance / hygiene ----------------------------------------------
    S["compliance"] = {
        "versions": dict(Counter(nodes[k]["version"] for k in sites).most_common()),
        "lenient_parse": [k for k in sites if nodes[k]["parse"] == "lenient"],
        "cors_star": sum(1 for k in sites if nodes[k]["cors"] == "*"),
        "content_type": dict(Counter((nodes[k]["content_type"] or "none").split(";")[0].strip()
                                     for k in sites).most_common()),
        "discovery_via": dict(db.execute(
            "select via, count(*) from (select distinct hj_url, via from probes where status='ok') group by via")),
        "self_vouch": sum(1 for k in sites if nodes[k].get("self_vouch")),
        "extra_top_level_keys": dict(Counter(x for k in sites for x in nodes[k]["extra_keys"]).most_common()),
        "vouch_extra_keys": dict(Counter(x for e in g["edges"] for x in (e.get("extra") or {})).most_common()),
        "undated_vouches": S["vouches_undated"],
    }

    # ---- 8. Where do they live? ----------------------------------------------------
    def tld(k):
        h = k.split("/")[0].split(":")[0]
        return h.rsplit(".", 1)[-1]
    def platform(k):
        h = k.split("/")[0]
        for p in ("github.io", "codeberg.page", "neocities.org", "bearblog.dev", "netlify.app", "pages.dev",
                  "srht.site", "nekoweb.org", "omg.lol", "micro.blog", "wordpress.com", "substack.com",
                  "tilde.", "blogspot."):
            if p in h:
                return p
        return "own domain"
    S["tlds"] = dict(Counter(tld(k) for k in sites).most_common(20))
    S["platforms"] = dict(Counter(platform(k) for k in sites).most_common())

    # ---- 9. Blind sample adoption rate ---------------------------------------------
    S["sample"] = {}
    all_reach, all_hits = set(), set()
    for name in ("sample-webring", "sample-blogroll", "sample-indieblog"):
        keys = {norm(l) for l in open(ROOT / f"seed/{name}.txt") if l.strip()} - {None}
        # Unit = host: directories often list a blog's feed URL alongside its homepage
        by_host = defaultdict(list)
        for k in keys:
            by_host[k.split("/")[0]].append(status.get(k) or "")
        reachable = [h for h, sts in by_host.items()
                     if any(x in ("ok", "no-human-json") or x.startswith("declared") for x in sts)]
        hits = [h for h, sts in by_host.items() if "ok" in sts]
        S["sample"][name] = {"listed_hosts": len(by_host), "reachable": len(reachable),
                             "with_human_json": len(hits),
                             "rate": round(len(hits) / len(reachable), 4) if reachable else None,
                             "robots_blocked": sum(1 for sts in by_host.values() if all(x == "robots" for x in sts)),
                             "hits": sorted(hits)}
        all_reach.update(reachable)
        all_hits.update(hits)
    S["sample_combined"] = {"reachable_hosts": len(all_reach), "with_human_json": len(all_hits),
                            "rate": round(len(all_hits) / len(all_reach), 4)}
    # Found by blind probing, and no file in the graph vouches for them
    S["sample_only_sites"] = sorted(k for k in sites if (nodes[k].get("source") or "").startswith("sample")
                                    and G.in_degree(k) == 0)

    # ---- 10. Who found what (discovery provenance) --------------------------------
    S["provenance"] = dict(Counter(nodes[k].get("source") or "alias-only" for k in sites).most_common())

    (ROOT / "data/stats.json").write_text(json.dumps(S, indent=1, default=str))
    summary = {k: v for k, v in S.items() if k not in ("history",)}
    summary["history"] = {k: v for k, v in S["history"].items() if k != "removals"}
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
