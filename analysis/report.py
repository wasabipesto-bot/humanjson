"""Build report/index.html: a self-contained explorer for the vouch graph + stats.

Layout is computed here (networkx spring layout) so the page needs no libraries.
"""

import json
import math
from datetime import date, timedelta
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent


def layout(g):
    G = nx.DiGraph()
    for n in g["nodes"]:
        G.add_node(n["id"])
    for e in g["edges"]:
        G.add_edge(e["source"], e["target"])
    indeg = dict(G.in_degree())
    # Keep every site with a file, plus bare targets vouched for by 2+ sites;
    # single-vouch bare targets are leaves that only add hairballs.
    keep = {n["id"] for n in g["nodes"] if n["has_file"] or indeg[n["id"]] >= 2}
    H = G.subgraph(keep).to_undirected()
    pos = {}
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    main = H.subgraph(comps[0])
    p = nx.forceatlas2_layout(main, max_iter=1000, scaling_ratio=12.0, gravity=0.5, linlog=False, distributed_action=True, seed=7) \
        if hasattr(nx, "forceatlas2_layout") else nx.spring_layout(main, k=1.6 / math.sqrt(len(main)), iterations=300, seed=7)
    xs = [v[0] for v in p.values()]
    ys = [v[1] for v in p.values()]
    span = float(max(max(xs) - min(xs), max(ys) - min(ys))) or 1.0
    for k, (x, y) in p.items():
        pos[k] = (float(x - min(xs)) / span, float(y - min(ys)) / span)
    # Small components & isolates: a tidy grid under the main component
    col, maxy = 0, max(v[1] for v in pos.values())
    for c in comps[1:]:
        for i, k in enumerate(sorted(c)):
            pos[k] = (0.02 + (col % 40) * 0.024 + i * 0.006, maxy + 0.06 + (col // 40) * 0.03)
        col += 1
    return pos, keep


def main():
    g = json.loads((ROOT / "data/graph.json").read_text())
    S = json.loads((ROOT / "data/stats.json").read_text())
    pos, keep = layout(g)
    indeg, outdeg = {}, {}
    for e in g["edges"]:
        outdeg[e["source"]] = outdeg.get(e["source"], 0) + 1
        indeg[e["target"]] = indeg.get(e["target"], 0) + 1
    nodes = [
        {"id": n["id"], "f": int(n["has_file"]), "x": round(pos[n["id"]][0], 4), "y": round(pos[n["id"]][1], 4),
         "i": indeg.get(n["id"], 0), "o": outdeg.get(n["id"], 0)}
        for n in g["nodes"] if n["id"] in keep
    ]
    idx = {n["id"]: i for i, n in enumerate(nodes)}
    edges = [[idx[e["source"]], idx[e["target"]]] for e in g["edges"] if e["source"] in idx and e["target"] in idx]

    # weekly adoption (first evidence of a file) — recomputed from stats' monthly isn't fine enough
    weekly = {}
    first = {}
    for e in g["edges"]:
        d = e.get("vouched_at") or ""
        if len(d) >= 10 and d[:4].isdigit():
            try:
                dd = date.fromisoformat(d[:10])
            except ValueError:
                continue
            if date(2026, 1, 1) <= dd <= date(2026, 10, 5):
                first[e["source"]] = min(first.get(e["source"], dd), dd)
    for d in first.values():
        wk = d - timedelta(days=d.weekday())
        weekly[wk.isoformat()] = weekly.get(wk.isoformat(), 0) + 1
    start = date(2026, 3, 2)
    weeks = []
    w = start
    while w <= date(2026, 10, 5):
        weeks.append([w.isoformat(), weekly.get(w.isoformat(), 0)])
        w += timedelta(days=7)
    early = sum(v for k, v in weekly.items() if k < start.isoformat())

    data = {"nodes": nodes, "edges": edges, "stats": S, "weeks": weeks, "early": early}
    html = (ROOT / "analysis/report_template.html").read_text().replace(
        "/*DATA*/null", json.dumps(data, separators=(",", ":")))
    out = ROOT / "report/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"wrote {out} ({len(html) // 1024} KB, {len(nodes)} nodes, {len(edges)} edges)")


if __name__ == "__main__":
    main()
