seeds := "seed/seeds-2026-10-05-csv.txt seed/research-seeds.txt seed/sample-webring.txt seed/sample-blogroll.txt seed/sample-indieblog.txt seed/github-seeds.txt"

# Crawl (resumable; delete data/crawl.sqlite for a fresh run)
crawl:
    uv run crawler/crawl.py {{seeds}} --db data/crawl.sqlite

# Pull Wayback Machine history for every discovered file
history:
    cd crawler && uv run history.py --db ../data/crawl.sqlite
    cd crawler && uv run git_history.py --db ../data/crawl.sqlite

# Resolve graph, compute stats, build report/index.html
analyze:
    uv run analysis/build_graph.py
    uv run analysis/stats.py > /dev/null
    uv run analysis/report.py

# Freeze the current crawl into data/snapshots/<today>/
snapshot:
    uv run crawler/snapshot.py

all: crawl history analyze snapshot
