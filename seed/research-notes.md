# human.json research notes (2026-10-05)

Goal: find NEW candidate sites beyond the known ~215 IndieWeb/UK-tech cluster.
236 candidate root URLs written to `research-seeds.txt`. All unverified — a
crawler should check each for `<link rel="human-json">` / a reachable
`human.json`. No posting/commenting/signup was done anywhere; everything here
came from read-only GET requests (curl, WebSearch, WebFetch, `gh` code/repo
search, Codeberg API).

## Source breakdown (approx. counts of distinct domains contributed)

- **GitHub code search** (`gh search code`), ~60 domains: queries used:
  - `rel="human-json"` (HTML head snippets) — found static-site repos
    (Jekyll/Hugo/Astro/11ty) with the link tag, e.g. `the-bootloader.io`,
    `ussjoin.com`, `sethmlarson.dev`, `joelchrono.xyz`, `eviefp.github.io`,
    `paddyroddy.github.io`, `takeonrules.com`, `blakerain.com`.
  - `human.json` filtered to `--filename human.json` — found the data files
    themselves, revealing sites not caught by the rel= search: `tommi.space`,
    `bootleg.technology`, `raniz.blog`, `thechels.uk`, `hanno-rein.de`
    (German astrophysicist), `luiscarlospando.com`, `jamestitcumb.com`,
    `dedigitaletuin.nl` (Dutch), `nicolasfriedli.ch` (Swiss/French),
    `tero.dev` (Finnish).
  - Plain `--filename human.json` with no other terms was almost entirely
    noise (ML/game-dev "human.json" data files unrelated to the protocol,
    e.g. crowd-human datasets, D&D race files, MakeHuman configs) — excluded
    from seeds.
  - `gh search repos human-json` turned up zero relevant hits — all results
    were unrelated "JSON for humans" formatting libraries. A notable *near*
    hit worth flagging: `DeckardHoliday/Fursona-Vouch-Network` and
    `flamiinngo/vouch` look like independent, unrelated "vouch" systems, not
    human.json implementations — did not include as seeds.
  - Found a Ruby Jekyll plugin generator: `aldur/aldur.blog` —
    `_plugins/human_json_generator.rb`; a Django implementation:
    `MartinPaulEve/blog` (`_human/human_json.py`) and a standalone package
    `timo/django-human-json` (see Codeberg/Forgejo mirror below); a Go
    package `anhgelus/go-human.json`; an Eleventy/Nunjucks template
    (`cxsquared/11tysite`, `teroyks/tero.dev`, `Raniz85/raniz.blog`).

- **Codeberg API — repo search**: only two repos named `human.json`: the
  canonical `robida/human.json` and a fork `berndpetrovitsch/human.json`
  (no distinct site found for the latter beyond the owner's profile, which
  has no website listed).

- **Codeberg API — issues/comments on `robida/human.json`** (~40 domains):
  paginated `/issues?state=all` and `/issues/comments`. Commenters' profile
  `website` fields gave a solid list of real adopters outside the известный
  cluster: `khinsen.net` (Konrad Hinsen, scientist), `nfnitloop.com`,
  `brassnet.biz`, `tzovar.as` (gedankenstuecke), `cog.dog` (Alan Levine,
  well-known edtech blogger), `kytta.dev`, `tante.cc` (Tante, German tech
  writer), `jak2k.eu`, `dominikschwind.com` (lostfocus.de), `beesbuzz.biz`
  (fluffy-critter), `danq.me`, `fireye.coffee`, `dbuho.me`, `nicolalosito.it`,
  `ntteloos.nl`, `ploum.net` (well-known Belgian blogger), `shinmera.com`
  (Lisp developer), `burgeonlab.com`, `stritzke.me`.
  - **Notable open issue (2026-10-05, #63, kensanata/Alex Schroeder)**:
    proposes a `policy` field (`syndicate`, `feed`) for consent to be
    aggregated into a "planet" (blog aggregator); motivated by wanting to
    crawl the human.json network to build a feed planet but being
    uncomfortable about lack of opt-in. Relevant if we build a crawler/
    aggregator — may want to respect a similar policy field if one appears.
  - **Issue #62/#61/#60 (MartinEve = Martin Paul Eve)**: raises concerns
    about (a) centralizing discovery on top of the decentralized model,
    (b) what the "distance" trust metric (1st/2nd/3rd-hop vouches) is
    actually supposed to mean, (c) the protocol being a high-value signal
    to AI trainers for filtering out synthetic data from training sets —
    an unresolved philosophical objection, not a technical one.

- **Codeberg API — stargazers/watchers on `robida/human.json`** (by far the
  biggest single source, ~140 distinct domains): paginated
  `/stargazers?page=N` (6 pages of real data, 255 stars total) and
  `/subscribers`. Starring the repo doesn't *prove* someone has adopted
  human.json, but cross-referencing against who also commented/is an issue
  participant, and general plausibility (personal blog domains, not orgs),
  makes this a very high-yield, mostly non-IndieWeb-cluster list spanning
  many countries: Germany (`alexohneander.de`, `moellus.de`, `marcgoertz.de`,
  `georg.avistats.de`, `www.ytvwld.de`), Poland (`michal.sapka.pl`,
  `pbielecki.com`), Finland (`miska.tammenpaa.com`, `jslazak.com` is actually
  Polish), Sweden (`kekos.se`, `markuseliasson.se`, `voxelmanip.se`),
  Netherlands (`ntteloos.nl`, `martijn-staal.nl`), Uzbekistan
  (`abduaziz.ziyodov.uz`), Spain (`estebansaiz.com`, `www.socardomingo.com`),
  Italy (`nicolalosito.it`), Czechia (`jan.vlnas.cz`), Denmark (fediverse
  account only), France (`tgm.happyngreen.fr`), Canada (`taffer.ca`,
  `matthewbird.ca`), many personal/neocities/itch.io sites
  (`bpavuk.neocities.org`, `umaruru.neocities.org`, `artlung.neocities.org`,
  `raktapadma.neocities.org`, `lime360.nekoweb.org`,
  `kahvinkaunistama.itch.io`). This list is explicitly "unverified — just
  starred the repo" and should be treated as lower-confidence than the
  issue/comment list, but it is the best lead for genuinely new,
  non-cluster sites and worth crawling first.
  - Forks of the repo (not necessarily sites, but people who forked the
    *spec* repo, suggesting an implementation attempt): `egonw/human.json`
    (Egon Willighagen, Dutch academic — profile linked to
    `social.edu.nl/@egonw`), `mkljczk/cat.json` (a themed variant? check
    manually — named `cat.json` not `human.json`, possibly a joke/parody
    fork, low confidence), `dennis_str/human.json` → `stritzke.me` (already
    listed above).

- **Web search (WebSearch)**: multi-language queries (German, French,
  Japanese, Spanish) mostly returned the already-famous English-language
  writeups (nedbatchelder, evanhahn, foosel, joelchrono, cogdogblog,
  hamatti.org, neilzone.co.uk, dazfuller.uk) plus two genuinely new
  non-English finds:
  - **French**: `anthonypena.fr/2026/05/12/humanjson-ou-comment-creer-un-reseau-de-contenu-certifie-humain/` —
    a French-language explainer blog post, describes the trust-graph color
    coding (green/yellow/orange/gray/blue by hop distance). Author's own
    site is a plausible human.json adopter.
  - **German**: `source.rdctd.de/timo/django-human-json` — a Forgejo-hosted
    (self-hosted git, NOT Codeberg/GitHub) Django app implementing the
    protocol server-side, with a wiki. This is a THIRD independent
    implementation surface (besides the canonical JS repo and the Ruby/
    Python plugins found via GitHub) and suggests other Forgejo/self-hosted
    instances are worth searching if time allows — we did not get to a
    broader Forgejo-instance sweep.
  - Japanese and Spanish-language native blog posts about human.json were
    NOT found — all results in those languages redirected back to English
    sources or were irrelevant (dictionary/JSON-formatting libraries).
  - **Opt-out / abandonment finding**: `gordonmclean.co.uk/2026/05/05/no-human-json-for-me/`
    — explicitly argues against adopting human.json (believes it's a
    technical non-solution to a social problem, skeptical AI will always be
    detectable via "tells" like em-dashes). References an anonymous blog
    "Hakkerblog" that also wrote about human.json (irony: anonymous author
    writing about human verification) — `hakkerblog.com` added to seeds as
    unverified. Comments on the post include Beto Dealmeida (human.json's
    creator) clarifying the protocol works more like a "curated blogroll"
    than a strict verification system — useful framing if asked about the
    protocol's actual guarantees.

- **HN Algolia** (`hn.algolia.com/api/v1/search?query=human.json`): found the
  known cluster of write-up submissions (evanhahn, sethmlarson, shkspr.mobi,
  codeyarns, jsbarretto, nedbatchelder) — nothing new beyond what WebSearch
  also surfaced. Tried to recursively walk the main submission's comment
  tree (id 47298655) for additional linked sites but the thread returned no
  comments via the Algolia `items` endpoint (likely too new / comments not
  yet indexed, or endpoint limitation) — worth re-trying later if more
  thoroughness is wanted.

- **Fediverse hashtag timelines** (`#humanjson` / `#human-json` on
  mastodon.social): returned ~30 posts, mostly reposts/boosts of the same
  handful of blog links already captured above, but surfaced ~25 distinct
  **author profile URLs** as candidates (listed in seeds without the
  `@handle` path, e.g. `functional.cafe`, `troet.cafe`, `fediscience.org`,
  `pony.social` were excluded from the final seed file since a Mastodon
  instance root is not a personal site — the specific profile pages are
  listed below for manual follow-up instead of polluting the crawl list):
  `functional.cafe/@marcosh`, `mastodon.design/@timotheegoguely`,
  `mamot.fr/@ploum` (same ploum.net found independently — corroborates),
  `polymaths.social/@rl_dane`, `social.golemwire.com/golemwire`,
  `troet.cafe/@tyrandus` (corroborates `tyrandus.dev` from stargazers),
  `soc.zom.bi/@linuro`, `chaos.social/@defnull`,
  `indieweb.social/@thefoggiest`, `mstdn.social/@dazfuller` (corroborates
  known dazfuller.uk writeup), `bayes.club/@georgrueppel`,
  `social.rossabaker.com/@ross` (corroborates rossabaker.com), `aus.social/@claudinec`,
  `infosec.exchange/@aiyion`, `mementomori.social/@oranki`, `mas.to/@vavakado`,
  `fediscience.org/@Guillawme` (corroborates gaullier.org), `oslo.town/@matt`,
  `fosstodon.org/@slott56`, `pony.social/@axxuy` (corroborates axoga.to).
  Tried `#human_json` — zero results (tag not used).
  - Two notable fediverse-only posts worth a human read (not blogs, but
    discussion of the protocol in languages/communities outside the usual
    cluster): `lostfocus.de/2026/03/26/dancer-json/` (German, a parody
    "dancer.json"?) and the `rbfirehose.com` / `evilgeniuschronicles.org`
    podcast-note posts (English, long-running indie podcaster commentary).

- **Codeberg stargazer fork `mkljczk/cat.json`**: named differently from the
  spec (`cat.json` not `human.json`) — flagged as possibly a joke/parody
  variant rather than a genuine implementation; did not add the owner's
  site as a seed, noted here for awareness only.

- **Not reachable / not useful**:
  - lobste.rs search API (`/search.json`) rejected the query parameters
    (400 "Unpermitted query or form parameter") — lobste.rs's public search
    may need different params or is gated; did not find a working endpoint
    in the time available.
  - Bluesky public search endpoint
    (`public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`) returned an empty/
    unparseable response — likely requires auth or a different host for
    unauthenticated access; not pursued further (task says read-only, no
    sign-ups, so did not attempt to authenticate).
  - Wayback CDX `url=human.json` search was not run — given the very high
    yield from Codeberg stargazers/comments already, and time constraints,
    this was deprioritized. Worth trying for a future pass:
    `http://web.archive.org/cdx/search/cdx?url=human.json&matchType=domain&output=json`
    probably still too broad (matches all `*/human.json` paths including
    unrelated ML datasets), would need filtering by content (presence of
    `"vouches"` key) after fetching candidates.

## Summary counts
- GitHub code search (rel= + filename queries, deduped, relevant only): ~60
- Codeberg issues/comments commenter websites: ~40
- Codeberg stargazers + watchers + forks: ~140 (dominant source)
- Web search / blog writeups (non-English + opt-out post): ~8
- Fediverse post authors (profile URLs, listed separately, not in seed file): ~25
- Total unique root URLs written to research-seeds.txt: 236

## Caveats
- None of these are verified to actually publish a valid human.json; this
  is a candidate list for a crawler to check (per task instructions).
- Overlap with the known ~215-site cluster was not checked against an
  existing list (none was provided) — some entries here may already be
  known. Dedup against the existing 215 should happen downstream.
- All data gathered via read-only HTTP GET (curl/WebFetch/WebSearch/gh
  search). No account actions, no posting, no comments, no sign-ups.
