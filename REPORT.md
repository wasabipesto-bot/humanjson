# The human.json vouch graph — survey of 5 October 2026

All numbers come from `data/stats.json`, which `just analyze` regenerates. The interactive
graph is in `report/index.html`.

## How the data was collected

The crawler started from four seed sets, then followed every vouch until no new sites appeared:

| Seed set | Sites | What it is |
|---|---:|---|
| Notion snapshot (earlier today) | 1,630 | the 215 known files plus everything they vouch for |
| Research | 236 | Codeberg stargazers, watchers and commenters on the spec repo; GitHub code search; fediverse; web search |
| GitHub repos | 77 | declared `url` of every human.json found in a public GitHub repo |
| Blind sample | 6,958 | every blog listed by the IndieWeb webring, blogroll.org and indieblog.page |

In total 7,494 sites were probed, with deep links followed. A site counts as having a
human.json if its `<link rel="human-json">` resolves to a parseable file, or if one of the
fallback paths (`/human.json`, `/.well-known/human.json`, `/humans.json`) serves one. Mirrors and
aliases are merged, and a vouch for `example.com/blog/post` resolves to whichever file's
declared `url` is a prefix of it, as the spec says.

Version history comes from two independent sources: Wayback Machine captures of every file,
and the git history of the 80 files kept in public GitHub repos.

**Coverage caveat:** this is still a snowball sample from IndieWeb-adjacent seeds. The blind
sample shows how much it misses (see "How many are there?").

---

## 1. How many are there, and which are the largest?

**292 sites publish a working human.json file.** That's up from 215 in this morning's snapshot.
Between them they hold **2,431 vouches** for **1,602 distinct sites**, but **1,310 of those sites
(82%) publish no file of their own.** Most of the graph is people vouching *out* into the
non-participating web.

| | |
|---|---:|
| Median vouches per file | 4 |
| Mean vouches per file | 8.3 |
| Files with zero vouches | 22 |
| Files nobody else's file vouches for | 81 |

**Most vouches given:** sethmlarson.dev (101, auto-generated from an RSS subscription list),
jorgesanz.net (74), artlung.com (69), burgeonlab.com (68), brennan.day (67), rldane.space (66),
chrisburnell.com (58), joelchrono.xyz (56), neilzone.co.uk (50), firesphere.dev (44).

jorgesanz.net is the second-largest file, yet **no other file vouches for it.** Only blind
probing of the IndieWeb webring found it. Following vouches alone would never have surfaced it.

**Most vouched for** (in-degree): shkspr.mobi/blog and neilzone.co.uk (27 each), joelchrono.xyz (20),
robida.net, the spec author (18), ploum.net (16), sethmlarson.dev (15). PageRank gives the same
top two. By betweenness, neilzone.co.uk and rldane.space are the main bridges between clusters.

**Most vouched for without a file:** jamesg.blog and benjaminhollon.com (12 each), neatnik.net (11),
ohhelloana.blog (10), then pluralistic.net, kevquirk.com, zacharykai.net and 82mhz.net (6 each).
These are the obvious next adopters, or people who declined. Their status is unknown.

### How many are there really?

The blind sample estimates adoption among the blogs most likely to know about human.json:

| Directory | Reachable blogs | With human.json | Rate |
|---|---:|---:|---:|
| IndieWeb webring | 435 | 22 | 5.1% |
| blogroll.org | 1,210 | 46 | 3.8% |
| indieblog.page | 4,984 | 94 | 1.9% |
| **All (deduplicated by host)** | **5,593** | **107** | **1.9%** |

**About 1 in 5 of the files found by blind probing (21 of 107) are vouched for by nobody.** A
crawler that only follows vouches therefore undercounts by roughly 20% even inside the
IndieWeb. Outside that community, adoption is presumably close to zero. A plausible range for
total deployments today is 300–400, almost all of them in this one community.

## 2. Longest chains, largest circle of trust

Looking only at the 292 sites with files and the 645 vouches between them:

- **Largest circle of trust: 121 sites.** This is the largest strongly connected component:
  every member can reach every other by following vouches. Next is a separate group of 8, then
  several groups of 4.
- **178 sites connect to the main cluster in at least one direction.** The other 114 are
  scattered across 68 islands, mostly single sites whose vouches all point at sites without files.
- **Longest chain of trust: 11 hops.** That is the longest shortest path; there's no shorter
  route between the two ends:
  blog.edwardloveall.com → darthmall.net → benmyers.dev → shkspr.mobi/blog → neilzone.co.uk →
  shellsharks.com → evanhahn.com → robida.net → evilgeniuschronicles.org → jpreardon.com →
  denisdefreyne.com → janogonzalez.com.
  Inside the 121-site circle, the average distance is 4.4 hops and the maximum is 11.
- **The 5-hop horizon:** the reference verifier stops after 5 hops. From the median file you can
  reach 67 other files within 5 hops. The best-placed site (burgeonlab.com) reaches 131. **No
  site can reach half the network within 5 hops**, so in practice "is this site trusted by
  someone I trust?" depends heavily on which file you start from.
- **Reciprocity: 57%** of vouches between file-holders are returned, making 185 mutual pairs.
  Returns are fast: 80 of the 185 pairs are dated the same day and 135 within a week (median
  1 day). Vouches mostly get *exchanged* rather than accumulating independently.
- **Largest group where everyone vouches for everyone: 4 sites.** Two groups tie, after
  excluding pairs on the same registrable domain. One is four personal sites that built up
  mutual vouches over time. The other is the same-day ring described under "Own questions"
  below. Beyond that the network is sparse: no tight cliques,
  just a loose core.

## 3. Has trust ever been broken?

**Rarely, and quietly.** No file contains a negative or revocation statement; the format has no
way to express one. The only way to withdraw trust is to delete the vouch, so I diffed every
available version of every file:

- **GitHub history** (80 files): 37 changed after their first commit. Across all versions,
  vouches were added 275 times and removed 19 times.
- Most removals are clean-up: same-day edits (6), a site removing its vouch for itself (2), and
  vouches moved to someone's new domain (3).
- **8 genuine withdrawals by 3 sites:** a site still online dropped from a vouch list months
  after being added. One file dropped 6 vouches at once between late March and October. One
  dropped a single vouch between June and August. One dropped a single vouch in August. All
  were confirmed against the archived and live files; details are in `data/stats.json` →
  `history.withdrawn`.

<!-- WAYBACK -->

A withdrawal is invisible to anyone who didn't keep the old file. Nothing in the protocol
records it.

## 4. Are the files being updated?

**Yes, by a minority that's still active.** Measured three ways:

| Age as of 5 Oct | Newest dated vouch | GitHub last commit |
|---|---:|---:|
| ≤ 30 days | 38 | 12 |
| 31–90 days | 40 | 12 |
| 91–180 days | 63 | 16 |
| > 180 days | 128 | 40 |

- **About 29% of files have gained a vouch in the last 90 days** (78 of 269 dated). The same
  share holds for the GitHub-hosted subset (24 of 80 committed in the last 90 days).
- **Nearly half are write-once:** 129 files have every vouch dated the same day.
- **New vouches are still steady at about 200 a month** (Aug 215, Sep 211). That's down from
  the March launch spike (1,090), but it hasn't faded since June.
- **New files are still appearing:** 14 in July, 13 in August, 25 in September (dated by
  earliest vouch).
- `Last-Modified` headers look fresher (94 under 30 days), but static-site rebuilds reset that
  header on every deploy, so it isn't evidence of editing.

Adoption by first-vouch month: 153 files in March 2026 (the spec launched on 8 March; the peak
was the week of 16 March, when it spread through the IndieWeb), 34 in April, 24 in May, 5 in
June, then 14 / 13 / 25 / 3 (July to early October). Thirty vouches are dated before March 2026.
People backdate vouches to when they started trusting someone, so `vouched_at` is a soft date.

## 5. Will 50% of today's files still exist, or be recently updated, in a year?

This splits into two questions with very different answers.

**Still exist (file still served in October 2027): very likely yes, ~85–90%.**
- The file is a static asset on a personal site, so it survives as long as the site does. The
  1,310 sites people vouched for in the last seven months make a useful proxy for blog
  mortality: 33 of them (2.5%) are already unreachable (DNS failure, broken TLS, timeouts).
- Observed decay of the files themselves is low: 5 sites declare a human.json link that now
  404s, won't parse, or is unreachable. <!-- CHURN -->
- For it to fail, more than half would have to delete the file or lose their site within a
  year. That would take a deliberate exodus, which is not in evidence.

**Recently updated (changed in the 90 days before October 2027): very unlikely, ~5–10%.**
- Only about 29% meet that bar *today*, seven months after launch. Activity is concentrated in
  a few dozen maintainers; nearly half of all files have never been touched since creation.
- Most of the momentum lives in files that are auto-generated from feed subscriptions or
  vouch YAML, and those keep changing even when nobody touches them by hand.

Suggested resolution criteria if you write the market: fix the list now (`data/snapshots/2026-10-05/`),
and in October 2027 count a file as "existing" if the same site still serves a parseable
human.json from any discovery path. Count it as "recently updated" if its vouch list
(not merely `Last-Modified`) differs from a crawl 90 days earlier. Run `just crawl snapshot`
quarterly so that comparison exists.

## 6. Own questions

**Is the protocol being used as written?**
- 278 of 292 files claim version 0.1.1. Nine other version strings appear: "1", "1.0.0" and
  "1.1.0" (none of these versions exist), and "0.1.2", "0.1.4", "0.1.6". No file uses the
  draft 0.2.0 `urls: []` format yet.
- 26 sites (9%) are discoverable *only* through a fallback path the spec doesn't define. The
  reference verifier can't find them.
- Only 115 (39%) send `Access-Control-Allow-Origin: *`, which browser-based verifiers need.
- 5 files are invalid JSON (trailing commas, missing commas between vouches). 5 more sites link
  a file that 404s, can't be parsed, or is unreachable.
- 20 files vouch for their own site, which means nothing. 33 vouches carry no date, and 13 use
  a `vouched` key instead of `vouched_at`.

**Does anyone game it?** Not maliciously, but the sybil shape described in spec issue #16 is
already here innocently:
- One closed ring of four unrelated-looking sites (different domains and topics, probably one
  webmaster's portfolio) all vouched for each other on the same day. **No site outside the ring
  vouches for any of them.** A verifier that starts inside the ring would rate all four as
  trusted, and nothing in the protocol can tell a ring of friends from a ring of one person.
- 30 sites vouch for their own other properties: 60 vouches between subdomains or same-owner
  domains, such as a personal site vouching for its blog, docs and recipe-book subdomains.
- 10 islands of 3+ sites are disconnected from the main graph. Most are a person's own domains.

**Who are the participants?** 276 of 292 run their own domain. Only 9 are on github.io, 5 on
Neocities and 1 on Cloudflare Pages. None are on a bearblog.dev, micro.blog, wordpress.com or
substack.com subdomain; hosted platforms don't let authors add a link tag, or they would need
a plugin. The most common TLDs are .com (86), .net (28), .org (27), .dev (19), .uk (15). Country
domains lean UK, German and French, consistent with the March spread through the UK and
European tech-blogging scene. Vouching skews mildly local: 8 of the 40 vouches from .uk file-holders go to other .uk
file-holders, about 4× what their 5% share of files would predict (small numbers).

**Where did the 292 come from?** By the seed list that reached each site first: 134 were found
by following vouches, 98 were in the original snapshot, 17 came from the research seeds
(Codeberg/GitHub/fediverse), 16 from GitHub code search and 25 from the directory sample. 21
sites are unreachable through any vouch, whatever seed found them.

## Limitations

- Snowball sampling from one community. The 1.9% adoption rate applies to IndieWeb directory
  blogs, not to the web.
- 250 sites disallow generic crawlers in robots.txt; they weren't probed, and some may have files.
- `vouched_at` is self-reported and sometimes backdated.
- Wayback coverage is uneven: most files have 0–2 captures, so a withdrawal between captures
  of an unarchived file is invisible. Git history is complete but covers only 80 files.
- Publishing this aggregate (as opposed to keeping it locally) runs into the consent question
  in spec issue #63. Nothing has been published.
