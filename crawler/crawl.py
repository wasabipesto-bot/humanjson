"""Breadth-first crawler for the human.json vouch network.

Starts from a list of seed sites, discovers each site's human.json file
(<link rel="human-json">, HTTP Link header, then well-known fallbacks),
records every file verbatim plus its parsed vouches, and follows vouch
targets until the frontier is empty.

Polite by default: robots.txt is honoured, one request at a time per host,
descriptive User-Agent, 1 MB body cap.

Usage: uv run crawler/crawl.py SEEDS.txt [SEEDS2.txt ...] --db data/crawl.sqlite
"""

import argparse
import asyncio
import hashlib
import json
import re
import socket
import sqlite3
import sys
import time
import urllib.parse
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

import dns.exception
import dns.resolver
import httpx

UA = "humanjson-survey/0.3 (+https://github.com/wasabipesto-bot/humanjson; maps the human.json vouch graph; honours robots.txt)"
MAX_BODY = 1_000_000
FALLBACK_PATHS = ["/human.json", "/.well-known/human.json", "/humans.json"]

SCHEMA = """
create table if not exists probes (
    site text primary key,          -- normalised site key we probed
    probed_at real,
    depth integer,
    status text,                    -- ok | no-human-json | robots | err:...
    final_url text,
    hj_url text,
    via text,                       -- link | link-header | fallback
    link_header integer,
    source text                     -- seed file or 'vouch'
);
create table if not exists files (
    hj_url text primary key,
    fetched_at real,
    http_status integer,
    content_type text,
    cors text,
    last_modified text,
    etag text,
    sha256 text,
    parse text,                     -- strict | lenient | fail
    version text,
    declared_url text,
    n_vouches integer,
    extra_keys text,
    body blob
);
create table if not exists vouches (
    hj_url text,
    idx integer,
    target_raw text,
    target text,                    -- normalised site key
    vouched_at text,
    extra text,
    primary key (hj_url, idx)
);
"""


# --- DNS -----------------------------------------------------------------------
# Resolve directly against public resolvers instead of the system resolver. On the
# crawl host the system path is Tailscale MagicDNS -> DoH upstream, and thousands of
# lookups for dead blog domains jammed it for the whole machine (2026-10-05).
_resolver = dns.resolver.Resolver(configure=False)
_resolver.nameservers = ["1.1.1.1", "9.9.9.9", "8.8.8.8"]
_resolver.lifetime = 6
_dns_cache: dict[str, list] = {}
_orig_getaddrinfo = socket.getaddrinfo


def _getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if not isinstance(host, str) or host in ("localhost",) or re.fullmatch(r"[\d.]+|[\da-fA-F:]+", host):
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    if host not in _dns_cache:
        addrs = []
        for rdtype, fam in (("A", socket.AF_INET), ("AAAA", socket.AF_INET6)):
            try:
                addrs += [(fam, a.to_text()) for a in _resolver.resolve(host, rdtype)]
            except (dns.exception.DNSException, OSError):
                pass
        _dns_cache[host] = addrs
    addrs = [(f, a) for f, a in _dns_cache[host] if family in (0, f)]
    if not addrs:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
    # Prefer IPv4, matching what most clients try first
    addrs.sort(key=lambda fa: fa[0] != socket.AF_INET)
    st = type or socket.SOCK_STREAM
    return [(f, st, proto or 6, "", (a, port) if f == socket.AF_INET else (a, port, 0, 0)) for f, a in addrs]


socket.getaddrinfo = _getaddrinfo


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.in_head_done = False

    def handle_starttag(self, tag, attrs):
        if tag not in ("link", "a"):
            return
        d = dict(attrs)
        rel = (d.get("rel") or "").lower().split()
        if "human-json" in rel and d.get("href"):
            # Prefer <link>; <a rel> is non-normative but seen in the wild
            self.hrefs.append((0 if tag == "link" else 1, d["href"]))


def idna_host(host: str) -> str:
    try:
        host.encode("ascii")
        return host
    except UnicodeEncodeError:
        return host.encode("idna").decode("ascii")


def norm(u: str) -> str | None:
    """Site key: scheme-less, lowercase punycode host without www., path without trailing slash."""
    if not isinstance(u, str):
        return None
    u = u.strip()
    if not re.match(r"^https?://", u, re.I):
        if re.match(r"^[\w.-]+\.[a-z]{2,}(/|$)", u, re.I):
            u = "https://" + u
        else:
            return None
    try:
        p = urllib.parse.urlsplit(u)
    except ValueError:
        return None
    if not p.hostname:
        return None
    host = idna_host(p.hostname.lower().rstrip("."))
    if host.startswith("www."):
        host = host[4:]
    if p.port and p.port not in (80, 443):
        host += f":{p.port}"
    path = re.sub(r"/(index\.html?)?$", "", p.path)
    return host + path


def site_url(key: str) -> str:
    return "https://" + key + ("/" if "/" not in key else "")


def lenient_json(raw: bytes):
    text = raw.decode("utf-8-sig", "replace")
    try:
        return json.loads(text), "strict"
    except json.JSONDecodeError:
        pass
    fixed = re.sub(r",(\s*[}\]])", r"\1", text)  # trailing commas
    fixed = re.sub(r"}(\s*){", r"},\1{", fixed)  # missing comma between vouch objects
    fixed = re.sub(r"^\s*//.*$", "", fixed, flags=re.M)  # line comments
    try:
        return json.loads(fixed), "lenient"
    except json.JSONDecodeError:
        return None, "fail"


DATE_KEYS = ("vouched_at", "vouched-at", "vouchedAt", "vouched", "vouchd_at", "date")


def store_vouches(db, hj_url, vouches) -> list[str]:
    db.execute("delete from vouches where hj_url=?", (hj_url,))
    targets = []
    for i, v in enumerate(vouches):
        if isinstance(v, str):
            v = {"url": v}
        if not isinstance(v, dict):
            continue
        raw = v.get("url")
        when = next((v[k] for k in DATE_KEYS if v.get(k)), None)
        extra = {k: x for k, x in v.items() if k != "url" and k not in DATE_KEYS}
        t = norm(raw) if isinstance(raw, str) else None
        db.execute(
            "insert or replace into vouches values (?,?,?,?,?,?)",
            (hj_url, i, raw if isinstance(raw, str) else json.dumps(raw), t,
             str(when) if when is not None else None, json.dumps(extra) if extra else None),
        )
        if t:
            targets.append(t)
    return targets


def reparse(db):
    """Re-derive parse mode and vouch rows from stored bodies (after parser changes)."""
    for hj_url, body in db.execute("select hj_url, body from files").fetchall():
        data, mode = lenient_json(body)
        vouches = (data or {}).get("vouches") or []
        db.execute("update files set parse=?, n_vouches=? where hj_url=?",
                   (mode, len(vouches) if isinstance(vouches, list) else 0, hj_url))
        store_vouches(db, hj_url, vouches if isinstance(vouches, list) else [])
    db.commit()


class Crawler:
    def __init__(self, db: sqlite3.Connection, concurrency: int, max_probes: int):
        self.db = db
        self.probe_sem = asyncio.Semaphore(concurrency)
        self.sem = asyncio.Semaphore(concurrency * 2)
        self.host_locks: dict[str, asyncio.Lock] = {}
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.robots_locks: dict[str, asyncio.Lock] = {}
        self.max_probes = max_probes
        self.ssl = httpx.create_ssl_context()

    def new_client(self):
        # One small client per probed site: a single shared pool across thousands of
        # hosts makes httpcore's per-request connection scan quadratic.
        return httpx.AsyncClient(
            follow_redirects=True,
            verify=self.ssl,
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"},
        )

    async def get(self, client, url: str):
        host = urllib.parse.urlsplit(url).hostname or ""
        lock = self.host_locks.setdefault(host, asyncio.Lock())
        async with self.sem, lock:
            # Hard deadline: some servers trickle bytes forever under a per-read timeout
            return await asyncio.wait_for(self._get(client, url), timeout=45)

    async def _get(self, client, url: str):
        async with client.stream("GET", url) as r:
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_BODY:
                    break
            return r, bytes(buf)

    async def allowed(self, client, url: str) -> bool:
        p = urllib.parse.urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        lock = self.robots_locks.setdefault(origin, asyncio.Lock())
        async with lock:
            if origin not in self.robots:
                # RFC 9309: 2xx -> parse; 4xx ("unavailable", incl. 401/403) -> no restrictions;
                # 5xx or no response ("unreachable") -> assume complete disallow.
                rp = urllib.robotparser.RobotFileParser()
                rp.unreachable = None
                try:
                    r, body = await self.get(client, origin + "/robots.txt")
                    if r.status_code >= 500:
                        rp.disallow_all, rp.unreachable = True, f"robots-http{r.status_code}"
                    elif r.status_code >= 400:
                        rp.allow_all = True
                    else:
                        rp.parse(body.decode("utf-8", "replace").splitlines())
                except Exception as e:
                    rp.disallow_all, rp.unreachable = True, "robots-" + type(e).__name__
                self.robots[origin] = rp
        return self.robots[origin].can_fetch(UA, url)

    def blocked_status(self, url: str) -> str:
        """Why allowed() said no: a real robots.txt disallow, or robots.txt was unreachable."""
        p = urllib.parse.urlsplit(url)
        why = getattr(self.robots.get(f"{p.scheme}://{p.netloc}"), "unreachable", None)
        return f"err:{why}" if why else "robots"

    async def fetch_file(self, client, hj_url: str):
        if not await self.allowed(client, hj_url):
            return None, "robots"
        r, body = await self.get(client, hj_url)
        if r.status_code != 200:
            return None, f"http{r.status_code}"
        data, mode = lenient_json(body)
        if not isinstance(data, dict) or not ("url" in data or "urls" in data or "vouches" in data):
            return None, "not-human-json"
        return (str(r.url), r, body, data, mode), None

    async def probe(self, key: str):
        # Concurrency is bounded per probe (not per request) so idle keep-alive
        # connections can't pile up across thousands of queued sites.
        async with self.probe_sem, self.new_client() as client:
            return await self._probe(client, key)

    async def _probe(self, client, key: str):
        res = {"site": key, "probed_at": time.time()}
        url = site_url(key)
        try:
            if not await self.allowed(client, url):
                res["status"] = self.blocked_status(url)
                if not res["status"].startswith("err:robots-") or not url.startswith("https://"):
                    return res, None
                # robots.txt unreachable over https: fall through to the plain-http retry below
                url = "http://" + url[len("https://"):]
                if not await self.allowed(client, url):
                    res["status"] = self.blocked_status(url)
                    return res, None
            try:
                r, body = await self.get(client, url)
            except httpx.ConnectError:
                # Plenty of personal sites have broken TLS but still serve plain HTTP
                if not url.startswith("https://"):
                    raise
                url = "http://" + url[len("https://"):]
                if not await self.allowed(client, url):
                    res["status"] = self.blocked_status(url)
                    return res, None
                r, body = await self.get(client, url)
            res["final_url"] = str(r.url)
            lh = r.headers.get("link", "")
            res["link_header"] = int("human-json" in lh)
            cands = []
            if "html" in r.headers.get("content-type", "") or body[:200].lstrip().startswith(b"<"):
                p = LinkParser()
                try:
                    p.feed(body.decode("utf-8", "replace"))
                except Exception:
                    pass
                cands += [("link", urllib.parse.urljoin(str(r.url), h)) for _, h in sorted(p.hrefs)]
            if res["link_header"]:
                m = re.search(r"<([^>]+)>[^,]*rel=\"?[^,\"]*human-json", lh)
                if m:
                    cands.append(("link-header", urllib.parse.urljoin(str(r.url), m.group(1))))
            cands += [("fallback", urllib.parse.urljoin(str(r.url), f)) for f in FALLBACK_PATHS]
            seen, last_err = set(), None
            for via, hj in cands:
                if hj in seen:
                    continue
                seen.add(hj)
                try:
                    got, err = await self.fetch_file(client, hj)
                except Exception as e:
                    got, err = None, "err:" + type(e).__name__
                if got:
                    res.update(status="ok", hj_url=got[0], via=via)
                    return res, got
                if via != "fallback":
                    last_err = f"declared-but-{err}"
            res["status"] = last_err or "no-human-json"
        except Exception as e:
            res["status"] = "err:" + type(e).__name__ + ":" + str(e)[:80]
        return res, None

    def store(self, res, got, depth, source):
        targets = []
        self.db.execute(
            "insert or replace into probes values (?,?,?,?,?,?,?,?,?)",
            (res["site"], res["probed_at"], depth, res.get("status"), res.get("final_url"),
             res.get("hj_url"), res.get("via"), res.get("link_header"), source),
        )
        if got:
            hj_url, r, body, data, mode = got
            vouches = data.get("vouches") or []
            if not isinstance(vouches, list):
                vouches = []
            declared = data.get("url") if "url" in data else json.dumps(data.get("urls"))
            self.db.execute(
                "insert or replace into files values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (hj_url, time.time(), r.status_code, r.headers.get("content-type"),
                 r.headers.get("access-control-allow-origin"), r.headers.get("last-modified"),
                 r.headers.get("etag"), hashlib.sha256(body).hexdigest(), mode,
                 str(data.get("version")), declared if isinstance(declared, str) else json.dumps(declared),
                 len(vouches), json.dumps([k for k in data if k not in ("version", "url", "urls", "vouches")]),
                 body),
            )
            targets = store_vouches(self.db, hj_url, vouches)
        return targets

    async def run(self, seeds: list[tuple[str, str]]):
        # getaddrinfo runs in the default executor; 8 threads starve on slow/dead DNS
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(128))
        done = {row[0] for row in self.db.execute("select site from probes")}
        # Re-expand vouches from any files already stored (resumable)
        frontier = {}
        for key, src in seeds:
            if key not in done:
                frontier.setdefault(key, src)
        for (t,) in self.db.execute("select distinct target from vouches where target is not null"):
            if t not in done:
                frontier.setdefault(t, "vouch")
        depth = 0
        while frontier and len(done) < self.max_probes:
            batch = list(frontier.items())[: self.max_probes - len(done)]
            frontier = {}
            t0, n_ok = time.time(), 0

            async def one(key, src):
                res, got = await self.probe(key)
                return key, src, res, got

            tasks = [asyncio.create_task(one(k, s)) for k, s in batch]
            for i, fut in enumerate(asyncio.as_completed(tasks), 1):
                key, src, res, got = await fut
                done.add(key)
                n_ok += res.get("status") == "ok"
                for t in self.store(res, got, depth, src):
                    if t not in done:
                        frontier.setdefault(t, "vouch")
                if i % 100 == 0:
                    self.db.commit()
                    print(f"  depth {depth}: {i}/{len(batch)} probed, {n_ok} ok", file=sys.stderr)
            self.db.commit()
            print(f"depth {depth}: probed {len(batch)} in {time.time() - t0:.0f}s, ok {n_ok}, "
                  f"next frontier {len(frontier)}", file=sys.stderr)
            depth += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seeds", nargs="+")
    ap.add_argument("--db", default="data/crawl.sqlite")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--max-probes", type=int, default=50_000)
    ap.add_argument("--reparse", action="store_true", help="rebuild vouches from stored bodies, then exit")
    a = ap.parse_args()
    db = sqlite3.connect(a.db, timeout=120)
    db.executescript(SCHEMA)
    if a.reparse:
        reparse(db)
        return
    seeds = []
    for f in a.seeds:
        for line in open(f):
            line = line.split("#")[0].strip()
            if line and (k := norm(line)):
                seeds.append((k, f.rsplit("/", 1)[-1]))
    print(f"{len(seeds)} seeds", file=sys.stderr)
    asyncio.run(Crawler(db, a.concurrency, a.max_probes).run(seeds))


if __name__ == "__main__":
    main()
