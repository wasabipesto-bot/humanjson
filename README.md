# humanjson

A live map of the [human.json](https://codeberg.org/robida/human.json) vouch network: who
publishes a file, who vouches for whom, how the trust graph is shaped, and whether it's
growing or decaying.

**Site:** https://wasabipesto-bot.github.io/humanjson/ (re-crawled weekly)
**First write-up:** [REPORT.md](REPORT.md), the survey of 5 October 2026.

## How it runs

Every Monday, `.github/workflows/weekly.yml` runs `just weekly`:

1. **load:** rebuild a scratch sqlite DB from `data/state/` (history carried between runs).
2. **seeds:** re-download the directory samples and the Codeberg participant list.
3. **crawl:** probe every seed and every site ever seen (`data/state/known-sites.txt`), then
   follow vouches until nothing new turns up.
4. **history:** extend version history, each step with a per-run budget so the job stays short:
   Wayback captures of files (up to 100 a week, each re-checked every 28 days), git history of
   files kept on GitHub, and Wayback lookups for vouched-for sites with no file (up to 200 a
   week, re-checked every 90 days).
5. **analyze:** resolve the graph, compute `data/stats.json`, build `report/index.html`.
6. **snapshot / save:** freeze the crawl into `data/snapshots/<date>/`, write state back, commit,
   deploy to Pages.

`.github/workflows/pages.yml` rebuilds the site from the newest snapshot, without crawling,
whenever analysis or crawler code changes. Locally, run `just rebuild` to do the same, or
`just weekly` for the full pipeline.

## Layout

```
seed/            starting points (static lists + the ones seeds.py refreshes)
crawler/
  crawl.py         BFS crawler -> data/crawl.sqlite
  seeds.py         refresh directory samples and Codeberg participants
  history.py       Wayback versions of every file
  git_history.py   commit history of human.json files in public GitHub repos
  churn_probe.py   did vouched-for sites without a file ever have one?
  state.py         load/save data/state <-> sqlite
  snapshot.py      freeze a crawl into data/snapshots/<date>/
analysis/
  build_graph.py   aliases/mirrors/prefix urls -> site graph (data/graph.json)
  stats.py         every number on the site (data/stats.json)
  report.py        report/index.html (layout precomputed; no JS dependencies)
data/
  state/           committed history (diffable JSON lines)
  snapshots/       one directory per crawl: every file body + every probe
```

## Crawler behaviour

Follows the spec's guidance for verifiers:
- **Politeness:** honours robots.txt, identifies itself in the User-Agent, sends one request
  at a time per host, caps bodies at 1 MB, and gives each request a hard 45 s deadline.
- **Discovery:** reads `<link rel="human-json">` on the page, then the HTTP `Link:` header,
  then tries `/human.json`, `/.well-known/human.json` and `/humans.json`. Those fallback paths
  aren't in the spec, but 9% of real deployments rely on them.
- **DNS:** resolves directly against public resolvers (1.1.1.1 / 9.9.9.9 / 8.8.8.8) instead of
  the system resolver. Thousands of lookups for dead blog domains can jam a local resolver.
- **Parsing:** lenient about trailing commas, missing commas between vouches, and
  `vouched-at` / `vouched` date keys, but records which files needed that. Also records
  0.2.0-style `urls: []`.
