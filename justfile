seeds := "seed/seeds-2026-10-05-csv.txt seed/research-seeds.txt seed/codeberg-seeds.txt seed/github-seeds.txt seed/removed-targets.txt seed/sample-webring.txt seed/sample-blogroll.txt seed/sample-indieblog.txt data/state/known-sites.txt"

# Full weekly pipeline (what CI runs): fresh crawl on top of committed state, then site + snapshot
weekly: load seeds crawl history analyze snapshot save

# Rebuild the site from committed state + newest snapshot, no crawling (for code/design changes)
rebuild:
    cd crawler && uv run state.py load --snapshot
    just analyze

# Rebuild data/crawl.sqlite from data/state (history only; crawl tables start empty)
load:
    cd crawler && uv run state.py load

# Refresh directory samples and Codeberg seeds
seeds:
    uv run crawler/seeds.py

# Crawl every seed and follow vouches until nothing new turns up
crawl:
    uv run crawler/crawl.py {{seeds}} --db data/crawl.sqlite

# Version history, budgeted: Wayback captures, GitHub commits, Wayback lookups for sites without a file
history:
    cd crawler && uv run history.py --db ../data/crawl.sqlite --max-files 100
    cd crawler && uv run git_history.py --db ../data/crawl.sqlite
    uv run analysis/build_graph.py
    cd crawler && uv run churn_probe.py --max-hosts 200

# Resolve graph, compute stats, build report/index.html
analyze:
    uv run analysis/build_graph.py
    uv run analysis/stats.py > /dev/null
    uv run analysis/report.py

# Freeze this crawl into data/snapshots/<today>/
snapshot:
    uv run crawler/snapshot.py

# Write history and known sites back to data/state/
save:
    cd crawler && uv run state.py save
