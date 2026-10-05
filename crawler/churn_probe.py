"""Did sites that have no human.json today ever have one?

For every vouched-for site without a live file, ask the Wayback Machine CDX
API whether it ever archived a human.json under that host. A hit means the
file existed and was removed (or moved somewhere our probe can't see):
the closest thing we have to an abandonment rate.

Writes data/churn_probe.json (not sqlite, so it can run beside the history job).
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

from crawl import UA

ROOT = Path(__file__).resolve().parent.parent


async def check(client, sem, host, out):
    async with sem:
        for attempt in range(4):
            try:
                r = await client.get("https://web.archive.org/cdx/search/cdx", params={
                    "url": host, "matchType": "host", "output": "json", "collapse": "urlkey",
                    "filter": ["original:.*human\\.json.*", "statuscode:200"], "fl": "original,timestamp",
                    "limit": "50"})
                r.raise_for_status()
                rows = r.json() if r.text.strip() else []
                out[host] = rows[1:] if rows else []
                return
            except Exception as e:
                await asyncio.sleep(10 * (attempt + 1))
        out[host] = None


async def main():
    g = json.loads((ROOT / "data/graph.json").read_text())
    hosts = sorted({n["id"].split("/")[0] for n in g["nodes"] if not n["has_file"]})
    path = ROOT / "data/churn_probe.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    todo = [h for h in hosts if out.get(h) is None]
    print(f"{len(todo)} hosts to check", file=sys.stderr)
    sem = asyncio.Semaphore(3)
    async with httpx.AsyncClient(timeout=60, headers={"User-Agent": UA}) as client:
        tasks = [asyncio.create_task(check(client, sem, h, out)) for h in todo]
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % 50 == 0:
                path.write_text(json.dumps(out, indent=0))
                print(f"  {i}/{len(todo)}, hits so far {sum(1 for v in out.values() if v)}", file=sys.stderr)
    path.write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    asyncio.run(main())
