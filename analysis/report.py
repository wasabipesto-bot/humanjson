"""Build report/index.html: a self-contained explorer for the vouch graph + stats.

Layout is computed here (networkx ForceAtlas2) so the page needs no libraries.
"""

import json
import math
from datetime import date, timedelta
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent


def compress(p):
    """Beyond the 95th-percentile radius, distance grows logarithmically, so one far-off
    cluster doesn't shrink the core to a corner of the canvas."""
    cx = sorted(x for x, _ in p.values())[len(p) // 2]
    cy = sorted(y for _, y in p.values())[len(p) // 2]
    radii = sorted(math.hypot(x - cx, y - cy) for x, y in p.values())
    r95 = radii[int(len(radii) * 0.95)] or 1.0
    out = {}
    for k, (x, y) in p.items():
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        f = (r95 + r95 * 0.25 * math.log1p((r - r95) / r95)) / r if r > r95 else 1.0
        out[k] = (dx * f, dy * f)  # centred on the median
    return out


def layout(g):
    """ForceAtlas2 for the main component; everything else packed on rings around it.

    Every node is included, leaves too, so each file's vouches are visible. Components
    that share no vouch with the main network (a site plus targets nobody else vouches
    for, or a file with no vouches at all) get their own compact layout and sit on rings
    hugging the core, rather than drifting off or being parked in a separate row.
    """
    H = nx.Graph()
    H.add_nodes_from(n["id"] for n in g["nodes"])
    H.add_edges_from((e["source"], e["target"]) for e in g["edges"])
    comps = sorted(nx.connected_components(H), key=lambda c: (-len(c), min(c)))
    main = H.subgraph(comps[0])
    p = nx.forceatlas2_layout(main, max_iter=1000, scaling_ratio=4.0, gravity=1.0,
                              distributed_action=True, seed=7)
    assert all(math.isfinite(c) for v in p.values() for c in v), "layout produced non-finite positions"
    pos = compress({k: (float(x), float(y)) for k, (x, y) in p.items()})
    R = max(math.hypot(x, y) for x, y in pos.values())
    unit = R / 40  # radius of a one-node component
    ring_r, angle = R * 1.12, 0.0
    for c in comps[1:]:
        sub = H.subgraph(c)
        radius = unit * math.sqrt(len(c))
        local = nx.spring_layout(sub, seed=7, scale=radius * 0.8) if len(c) > 1 else {next(iter(c)): (0.0, 0.0)}
        step = 2 * (radius + unit) / ring_r  # arc taken by this component
        if angle + step > 2 * math.pi:  # ring full: start another, further out
            ring_r += 2 * (radius + unit) + unit * 4
            angle = 0.0
        a = angle + step / 2
        cx, cy = ring_r * math.cos(a), ring_r * math.sin(a)
        for k, (x, y) in local.items():
            pos[k] = (cx + float(x), cy + float(y))
        angle += step
    xs = [x for x, _ in pos.values()]
    ys = [y for _, y in pos.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    return {k: ((x - min(xs)) / span, (y - min(ys)) / span) for k, (x, y) in pos.items()}


def main():
    g = json.loads((ROOT / "data/graph.json").read_text())
    S = json.loads((ROOT / "data/stats.json").read_text())
    pos = layout(g)
    crawl_date = date.fromisoformat(S["crawl_date"])
    indeg, outdeg = {}, {}
    for e in g["edges"]:
        outdeg[e["source"]] = outdeg.get(e["source"], 0) + 1
        indeg[e["target"]] = indeg.get(e["target"], 0) + 1
    nodes = [
        {"id": n["id"], "f": int(n["has_file"]), "x": round(pos[n["id"]][0], 4), "y": round(pos[n["id"]][1], 4),
         "i": indeg.get(n["id"], 0), "o": outdeg.get(n["id"], 0)}
        for n in g["nodes"]
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
            if date(2026, 1, 1) <= dd <= crawl_date:
                first[e["source"]] = min(first.get(e["source"], dd), dd)
    for d in first.values():
        wk = d - timedelta(days=d.weekday())
        weekly[wk.isoformat()] = weekly.get(wk.isoformat(), 0) + 1
    start = date(2026, 3, 2)
    weeks = []
    w = start
    while w <= crawl_date:
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
