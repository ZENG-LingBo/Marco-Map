# Marco-Map

Historical Chinese maps online: the takeover plan, feature demos and cost estimate for Prof. Marco Caboara's map project at HKUST.

**Status (27 Sep 2026).** Alexia (TSANG Tze Nam) built the first site; its code, hosting and image tiles are still in her personal accounts and the repository invite is pending. Nothing here touches her code or storage yet. This repository holds the plan to take the project over, a working demonstration of the features Prof. Caboara asked for, and the one-year cost estimate.

## Read this first

| Document | For whom | What it answers |
|---|---|---|
| [docs/00-brief-for-prof-marco.md](docs/00-brief-for-prof-marco.md) | Prof. Caboara | why the project should be owned this way, what it costs and why, what he needs to decide |
| [docs/01-migration-runbook.md](docs/01-migration-runbook.md) | Ling Bo | step-by-step: project accounts, GitHub transfer, re-deploy, copying 200 GB of tiles to Cloudflare R2, backups |
| [docs/02-feature-exploration.md](docs/02-feature-exploration.md) | whoever builds on the demo | what the four reference sites really do, what the demo does, the data model, how to plug in Alexia's tiles, upgrade path |
| [docs/03-cost-estimate.md](docs/03-cost-estimate.md) | budget holder | four scenarios with arithmetic and sources; recommended ≈ US$80 in year one, ≈ US$60 after |
| [docs/04-email-drafts.md](docs/04-email-drafts.md) | Ling Bo | draft replies to Alexia (handover list) and to Prof. Caboara (cover note); nothing has been sent |

## The demo

`demo/` is plain HTML, CSS and JavaScript with one JSON file per map. It uses two maps that the Library of Congress already serves as zoomable IIIF images, so no tiles are hosted here.

- `index.html` — catalogue front page
- `viewer.html` — deep zoom · numbered annotations · reading panel with 原文 original / translation / commentary / source · front/back switch · guided tour · translated-label layer · deep links · author mode (`E`) to copy a region
- `story.html` — narrative mode: scrolling flies the map to each passage and turns the sheet over when needed

Run it locally (the pages fetch their data, so they need a web server):

```bash
cd demo && python3 -m http.server 8000
# open http://localhost:8000/
```

Publish it: enable **Settings → Pages → Source: GitHub Actions** once; `.github/workflows/pages.yml` then deploys `demo/` on every push to the default branch, at `https://zeng-lingbo.github.io/Marco-Map/`.

Transcriptions and translations in `demo/data/*.json` were read from the scans for this prototype and are marked illustrative; they must be checked before publication.

## Repository layout

```
docs/      the five documents above
demo/      the demonstration site
app/       (later) Alexia's application, imported with its history — see runbook §2
```

## Out of scope for this first pass

Touching Alexia's code or bucket (no access yet); sending any e-mail; creating the project accounts (needs Prof. Caboara's decisions); a backend for user-editable annotations (the feature doc names the free tools for that).
