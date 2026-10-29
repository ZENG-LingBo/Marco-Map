# Marco-Map

Historical Chinese maps online: the takeover plan, feature demos and cost estimate for Prof. Marco Caboara's map project at HKUST.

**Status (27 Sep 2026).** Alexia (TSANG Tze Nam) built the first site; its code, hosting and image tiles are still in her personal accounts and the repository invite is pending. Nothing here touches her code or storage yet. This repository holds the plan to take the project over, a working demonstration of the features Prof. Caboara asked for, and the one-year cost estimate.

**Update (29 Oct 2026).** For Prof. Caboara's IMCoS lecture in Tokyo on 9 Nov, the demo became a site of its own, "Mapping Tartary", which the project controls; Alexia's site (https://tartary.vercel.app) stays in her personal accounts. The front page lists all 144 maps of her catalogue, opened in this viewer from her image tiles. It also has a first reading edition: Ortelius's *Tartaria* of 1570, with all 40 texts on the map and the description on the back read, expanded and translated by Claude Opus 5.5 and scored against the published edition.

## Read this first

| Document | For whom | What it answers |
|---|---|---|
| [docs/00-brief-for-prof-marco.md](docs/00-brief-for-prof-marco.md) | Prof. Caboara | why the project should be owned this way, what it costs and why, what he needs to decide |
| [docs/01-migration-runbook.md](docs/01-migration-runbook.md) | Ling Bo | step-by-step: project accounts, GitHub transfer, re-deploy, copying 200 GB of tiles to Cloudflare R2, backups |
| [docs/02-feature-exploration.md](docs/02-feature-exploration.md) | whoever builds on the demo | what the four reference sites really do, what the demo does, the data model, how to plug in Alexia's tiles, upgrade path |
| [docs/03-cost-estimate.md](docs/03-cost-estimate.md) | budget holder | four scenarios with arithmetic and sources; recommended ≈ US$80 in year one, ≈ US$60 after |

## The demo

`demo/` is plain HTML, CSS and JavaScript with one JSON file per annotated map, no build step.

- `index.html` — front page: the annotated maps, then the 144-map collection with search
- `viewer.html` — deep zoom · numbered annotations · reading panel with 原文 original / translation / commentary / source · front/back switch · guided tour · translated-label layer · deep links · author mode (`E`) to copy a region
- `story.html` — narrative mode: scrolling flies the map to each passage and turns the sheet over when needed

Run it locally (the pages fetch their data, so they need a web server):

```bash
cd demo && python3 -m http.server 8000
# open http://localhost:8000/
```

Publish it: enable **Settings → Pages → Source: GitHub Actions** once; `.github/workflows/pages.yml` then deploys `demo/` on every push to the default branch, at `https://zeng-lingbo.github.io/Marco-Map/`.

What is where:

| Map | Images | Texts |
|---|---|---|
| Ortelius 1570 (`data/ortelius-1570.json`) | `demo/tiles/`, cut from Internet Archive's scan of the Boston Public Library copy with `scripts/make_dzi.py` (Internet Archive's own IIIF server took over a second per tile and sometimes stalled) | the model's output as scored in the transcription test, built with `scripts/build_ortelius.py`; boxes around each text drawn by eye, approximate |
| The collection, 144 maps (`data/collection.json`) | deep zoom from Alexia's S3 bucket `tartary-deepzoom-bucket`; thumbnails copied into `demo/img/thumbs/` | none yet; titles, mapmakers and sources as in her catalogue, from a snapshot of her site's API (`scripts/build_collection.py`) |
| Ricci 1602, Miller Atlas 1519 | Library of Congress IIIF | illustrative, written for the September prototype; must be checked before publication |

**The collection's deep zoom depends on Alexia's S3 bucket**, and every map opened here is billed to her AWS account as download traffic. Agree this with her; the lasting fix is the copy into project storage (runbook §4–5). To leave maps out (for example ones not yet cleared for publication), list their ids in `HIDDEN` in `scripts/build_collection.py` and run it again.

## Repository layout

```
docs/      the documents above
demo/      the demonstration site
scripts/   build the demo's data and tiles (not published)
app/       (later) Alexia's application, imported with its history — see runbook §2
```

## Out of scope for this first pass

Touching Alexia's code or bucket (no access yet); e-mails to Alexia and Prof. Caboara (drafted outside the repository); creating the project accounts (needs Prof. Caboara's decisions); a backend for user-editable annotations (the feature doc names the free tools for that).
