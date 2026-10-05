# humanjson

A survey of the [human.json](https://codeberg.org/robida/human.json) vouch network: who
publishes a file, who vouches for whom, how the trust graph is shaped, and whether
it's alive. Findings are in [REPORT.md](REPORT.md); the interactive explorer is
`report/index.html`.

## Layout

```
seed/        starting points
  human-json-deployments-2026-10-05.csv   first survey (215 files), from Notion
  human-json-crawl.py                     the crawler that produced it (superseded)
  seeds-2026-10-05-csv.txt                every site in / vouched for by that CSV
  research-seeds.txt, research-notes.md   new candidates from Codeberg, GitHub, fediverse, web
  sample-*.txt                            blind sample: IndieWeb webring, blogroll.org, indieblog.page
crawler/
  crawl.py      BFS crawler -> data/crawl.sqlite (resumable)
  history.py    Wayback Machine versions of every file -> wb_captures table
  snapshot.py   freeze a crawl into data/snapshots/<date>/ (committed, diffable)
analysis/
  build_graph.py  resolve aliases/mirrors/prefix urls into a site graph -> data/graph.json
  stats.py        every number in REPORT.md -> data/stats.json
  report.py       report/index.html (layout precomputed, no JS dependencies)
```

`just all` runs crawl → history → analyze → snapshot.

## Crawler behaviour

- Discovery order: `<link rel="human-json">` in the page, HTTP `Link:` header, then
  `/human.json`, `/.well-known/human.json` and `/humans.json`. The fallbacks aren't in the spec,
  but about 7% of real deployments rely on them.
- Honours robots.txt, sends one request at a time per host, identifies itself in the
  User-Agent, caps bodies at 1 MB and gives each request a hard 45 s deadline.
- Resolves DNS directly against public resolvers (1.1.1.1 / 9.9.9.9 / 8.8.8.8). On
  2026-10-05 the system resolver (Tailscale MagicDNS → DoH upstream) jammed for the whole
  host under thousands of lookups for dead blog domains.
- Accepts trailing commas and `vouched-at`; records 0.2.0-style `urls: []`.

## Consent

These files are public and meant to be fetched by verifiers. Publishing an aggregate is a
different matter, though: spec issue #63 (opened 2026-10-05) asks for an opt-in `policy`
field before anyone republishes the network. Nothing from this repo has been published.
