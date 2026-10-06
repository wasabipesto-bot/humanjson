# The human.json vouch graph — survey of 5 October 2026

This is the first survey, frozen as of the 5 October 2026 crawl (`data/snapshots/2026-10-05/`).
The [live site](https://wasabipesto-bot.github.io/humanjson/) recomputes these numbers every week.

## How the data was collected

The crawler started from four seed sets, then followed every vouch until no new sites appeared:

| Seed set | Sites | What it is |
|---|---:|---|
| Notion snapshot (earlier today) | 1,630 | the 215 known files plus everything they vouch for |
| Research | 236 | Codeberg stargazers, watchers and commenters on the spec repo; GitHub code search; fediverse; web search |
| GitHub repos | 77 | declared `url` of every human.json found in a public GitHub repo |
| Blind sample | 6,958 | every blog listed by the IndieWeb webring, blogroll.org and indieblog.page |

In total 7,500 sites were probed. A site counts as having a human.json if its homepage's
`<link rel="human-json">` resolves to a parseable file, or if a fallback path
(`/human.json`, `/.well-known/human.json`, `/humans.json`) serves one. Mirrors and aliases are
merged, and a vouch for `example.com/blog/post` resolves to whichever file's declared `url` is
a prefix of it, as the spec says.

Version history comes from three sources:
- Wayback Machine captures of 186 of the files
- the complete git history of 80 files kept in public GitHub repos
- Wayback lookups for 1,282 vouched-for sites that have no file today

**Coverage caveat:** this is a snowball sample from IndieWeb-adjacent seeds. The blind
sample shows how much it misses (see "How many are there really?").

---

## 1. How many are there, and which are the largest?

**293 sites publish a discoverable human.json file**, up from 215 in this morning's snapshot.
At least 9 more sites have a file that this method can't see (see "How many are there
really?").

Between them the 293 files hold **2,431 vouches** for **1,603 distinct sites**, but **1,310 of
those sites (82%) publish no file of their own.** Most of the graph is people vouching *out*
into the non-participating web.

| | |
|---|---:|
| Median vouches per file | 4 |
| Mean vouches per file | 8.3 |
| Files with zero vouches | 23 |
| Files nobody else's file vouches for | 82 |

**Most vouches given:** sethmlarson.dev (101, auto-generated from an RSS subscription list),
jorgesanz.net (74), artlung.com (69), burgeonlab.com (68), brennan.day (67), rldane.space (66),
chrisburnell.com (58), joelchrono.xyz (56), neilzone.co.uk (50), firesphere.dev (44).

jorgesanz.net is the second-largest file, yet **no other file vouches for it.** Only blind
probing of directory-listed blogs found it.

**Most vouched for** (in-degree): shkspr.mobi/blog and neilzone.co.uk (27 each), joelchrono.xyz (20),
robida.net, the spec author (18), ploum.net (16), sethmlarson.dev (15). PageRank gives the same
top two. By betweenness, neilzone.co.uk and rldane.space are the main bridges between clusters.

**Most vouched for without a file:** jamesg.blog and benjaminhollon.com (12 each), neatnik.net (11),
ohhelloana.blog (10), then pluralistic.net, kevquirk.com, zacharykai.net and 82mhz.net (6 each).
Either these are the obvious next adopters or their owners declined; there's no way to tell
which.

### How many are there really?

Adoption among the blogs most likely to have heard of human.json:

| Directory | Reachable blogs | With human.json | Rate |
|---|---:|---:|---:|
| IndieWeb webring | 435 | 22 | 5.1% |
| blogroll.org | 1,210 | 46 | 3.8% |
| indieblog.page | 4,984 | 94 | 1.9% |
| **All (deduplicated by host)** | **5,593** | **107** | **1.9%** |

Three effects hide files from a crawler like this one:
- **No vouch path:** 21 of the 107 files found by blind probing (1 in 5) are vouched for by
  nobody. A crawler that only follows vouches undercounts by roughly 20% even inside the IndieWeb.
- **Not linked from the homepage:** 4 sites serve a working file that's linked only from
  another page (e.g. `/about`), or not linked at all.
- **robots.txt:** 5 sites publish a file but disallow all generic crawlers in robots.txt, so
  any robots-respecting verifier is shut out. 250 probed sites are blocked this way in total.

A plausible total today is **roughly 300–400 deployments, almost all of them in this one
community.** Outside it, adoption is presumably close to zero.

## 2. Longest chains, largest circle of trust

Looking only at the 293 sites with files and the 645 vouches between them:

- **Largest circle of trust: 121 sites.** This is the largest strongly connected component:
  every member can reach every other by following vouches. Next is a separate group of 8, then
  several groups of 4.
- **178 sites connect to the main cluster in at least one direction.** The other 115 are spread
  across 69 islands, mostly single sites whose vouches all point at sites without files.
- **Longest chain of trust: 11 hops.** That's the longest shortest path; 7 pairs tie at this
  distance. One of them:
  blog.edwardloveall.com → darthmall.net → benmyers.dev → shkspr.mobi/blog → neilzone.co.uk →
  shellsharks.com → evanhahn.com → robida.net → evilgeniuschronicles.org → jpreardon.com →
  denisdefreyne.com → janogonzalez.com.
  Inside the 121-site circle the average distance is 4.4 hops.
- **The 5-hop horizon:** the reference verifier stops after 5 hops. The median file reaches 64
  other files within 5 hops, and the best-placed (burgeonlab.com) reaches 131. **No site
  reaches half the network within 5 hops**, so "is this site trusted by someone I trust?"
  depends heavily on where you start.
- **Reciprocity: 57%** of vouches between file-holders are returned, making 185 mutual pairs.
  Returns are fast: 80 pairs are dated the same day and 135 within a week (median 1 day).
  Vouches mostly get *exchanged* rather than accumulating independently.
- **Largest group where everyone vouches for everyone: 4 sites.** Two groups tie, after
  excluding pairs on the same registrable domain. One is four personal sites that built up
  mutual vouches over time. The other is the same-day ring described under "Own questions".
  There are no tight cliques beyond that, just a loose core.

## 3. Has trust ever been broken?

**Rarely, and silently.** The format can't express distrust: there are no negative vouches and
no revocations. The only way to withdraw trust is to delete a vouch, so I diffed every
available version of every file:

| | Wayback captures (186 files) | Git history (80 files) |
|---|---:|---:|
| Vouches added in later versions | 431 | 215 |
| Removed: **withdrawn, target still online** | **9** | **1** |
| Removed: target site offline | 4 | 0 |
| Removed: moved to a new URL or domain | 3 | 2 |
| Removed: vouch for own site | 0 | 2 |
| Removed: same-day edit | 0 | 6 |

- **Ten genuine withdrawals by five people** (one person removed the same vouch from two of
  their files). One file dropped five live vouches between two captures, late March and early
  October. The other four people each dropped one vouch, somewhere between March and August.
- Each was checked against the archived and live files, and every withdrawn-from site is still
  online. The names are in `data/stats.json` → `history.withdrawn`; they're left out here
  because they're social signals about real people.
- **Additions outnumber removals of any kind about 24 to 1**, and genuine withdrawals by about
  65 to 1. Trust gets added steadily and is very rarely taken back.
- A withdrawal is visible only to someone who kept an older copy. Nothing in the protocol
  records it, so a verifier will never know the vouch existed.

## 4. Are the files being updated?

**Yes, by an active minority.** Measured two ways:

| Age as of 5 Oct | Newest dated vouch (269 files) | GitHub last commit (80 files) |
|---|---:|---:|
| ≤ 30 days | 38 | 12 |
| 31–90 days | 40 | 12 |
| 91–180 days | 63 | 16 |
| > 180 days | 128 | 40 |

- **About 29% gained a vouch in the last 90 days** (78 of 269 dated files). The GitHub-hosted
  subset matches: 24 of 80 had a commit in the last 90 days.
- **Nearly half are write-once:** 129 files have every vouch dated the same day.
- **New vouches are holding at about 200 a month** (Aug 215, Sep 211). That's down from the
  launch spike (March 1,090), but the rate hasn't decayed since June.
- **New files keep appearing:** 15 in July, 12 in August, 24 in September (dated by each file's
  earliest vouch).
- `Last-Modified` headers look fresher (94 under 30 days), but static-site rebuilds reset that
  header on every deploy, so it isn't evidence of editing.

Adoption by first-vouch month: 158 files in March 2026 (the spec launched on 8 March; the
peak was the week of 16 March), 36 in April, 26 in May, 4 in June, then 15 / 12 / 24 from July
to September. Thirty vouches are dated *before* March 2026. People backdate vouches to when
they started trusting someone, so `vouched_at` is a soft date.

## 5. Will 50% of today's files still exist, or be recently updated, in a year?

These are two different questions with very different answers.

**Still exist (file still served in October 2027): very likely yes, ~90%.**
- Observed loss so far is small. Of the 1,282 vouched-for sites without a file today, the
  Wayback Machine saw a human.json on 15. Re-checking those:
  - **3 files are gone** (404, link tag removed)
  - 1 site still links a file that now 404s
  - 2 sites were only temporarily down (see correction below)
  - 4 still serve the file but don't link it from the homepage
  - 5 are robots-blocked
  Add the other 4 sites in the live crawl that declare a broken file, and about **8 of
  roughly 310 known deployments (~2.5%) have broken or disappeared in seven months.**
  Annualised, that's around 4–5%.

  *Correction (6 October):* the first version of this report counted vhbelvadi.com as
  "file gone" and hisvirusness.com as "offline". Both were serving their files again in the
  next day's crawl, so they were outages during the first crawl, not removals. The weekly
  pipeline now carries a file forward through transient errors, for up to four weeks, so
  outages like these no longer register as churn.
- Blog mortality looks similar. Of the 1,310 sites people vouched for in the last seven
  months, 33 (2.5%) are already unreachable.
- Failing would take more than half of these files being deleted within a year. Nothing in
  the data points that way: there's no exodus, and additions outnumber removals 24 to 1.

**Recently updated (vouch list changed in the 90 days before October 2027): very unlikely,
~5–10%.**
- Only about 29% meet that bar *today*, seven months after launch, with a novelty wave
  still fresh.
- Activity is concentrated in a few dozen maintainers, and nearly half of all files have
  never been edited since they were created.

**Suggested resolution criteria if you write the market:**
- Freeze the list now (`data/snapshots/2026-10-05/`, 299 file URLs).
- In October 2027, count a file as "existing" if the same site still serves a parseable
  human.json at any path.
- Count it as "recently updated" if its vouch list (not merely `Last-Modified`) differs
  from a crawl 90 days earlier.
- Run `just crawl snapshot` quarterly so those comparisons exist.

## 6. Own questions

**Is the protocol being used as written?**
- 279 of 293 files claim version 0.1.1. Nine other version strings appear: "1", "1.0.0" and
  "1.1.0" (none of these versions exist), and "0.1.2", "0.1.4", "0.1.6". No file uses the draft
  0.2.0 `urls: []` format yet.
- 26 sites (9%) are discoverable *only* through a fallback path the spec doesn't define. The
  reference verifier can't find them.
- Only 115 (39%) send `Access-Control-Allow-Origin: *`, which browser-based verifiers need.
- 5 files are invalid JSON (trailing commas, missing commas between vouches), and 5 more sites
  link a file that 404s, can't be parsed, or is unreachable.
- 20 files vouch for their own site, which means nothing. 33 vouches have no date, and 13 use
  `vouched` instead of `vouched_at`.

**Does anyone game it?** Not maliciously, but the sybil shape described in spec issue #16
already exists, innocently:
- One closed ring of four unrelated-looking sites (different domains and topics, probably one
  webmaster's portfolio) all vouched for each other on the same day. **No site outside the ring
  vouches for any of them.** A verifier starting inside the ring would rate all four as
  trusted, and nothing in the protocol distinguishes a ring of friends from a ring of one person.
- 30 sites make 60 vouches for their own other properties (subdomains or same-owner domains),
  such as a personal site vouching for its blog, docs and recipe-book subdomains.
- 10 islands of 3+ sites are disconnected from the main graph; most are one person's own domains.

**Who participates?** 276 of 293 run their own domain. Only 9 are on github.io, 5 on Neocities
and one each on Cloudflare Pages, codeberg.page and tilde.club. None are on a bearblog.dev,
micro.blog, wordpress.com or substack.com subdomain, presumably because hosted platforms don't
let authors add a link tag without a plugin. The most common TLDs are .com (86), .net (28),
.org (27), .dev (19) and .uk (15). Country domains lean UK, German and French, consistent with
the March spread through UK and European tech blogs. Vouching skews mildly local: 8 of 40
vouches from .uk file-holders go to other .uk file-holders, about 4× their 5% share of files
(small numbers).

**Where did the 293 come from?** Counted by the seed list that reached each site first:
- 134 by following vouches
- 98 from the original snapshot
- 25 from the directory sample
- 17 from the research seeds
- 16 from GitHub code search
- 1 from re-probing removed vouch targets

21 sites are reachable through no vouch at all.

## Limitations

- **Sampling:** snowball sampling from one community. The 1.9% adoption rate applies to
  IndieWeb directory blogs, not to the web.
- **robots.txt:** 250 sites disallow generic crawlers, so they weren't probed. At least 5 of
  them publish a file.
- **Discovery:** the crawler reads only the homepage's link tag plus three fallback paths, so
  files linked from other pages are missed (at least 4 known cases).
- **Dates:** `vouched_at` is self-reported and sometimes backdated.
- **History coverage:** Wayback captures are uneven. 112 of 298 file URLs were never archived,
  and a vouch added and removed between captures is invisible. Git history is complete but
  covers only 80 files.
