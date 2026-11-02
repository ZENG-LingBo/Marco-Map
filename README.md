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
- `review/` — review mode for specialists, behind a password (below): labels the model was least sure of come first; each opens at its place on the scan beside the machine reading, to accept, correct (text, number, box) or dispute with a comment. Buttons insert the marks of the transcription rules (titlo, raised letters, pre-reform letters, long s). Decisions are kept in the browser and exported as a corrections file

**Review workflow.**
1. A specialist opens `review/`, enters the reviewers' password, types their name, works through the queue and presses **Export**.
2. Their file goes into `corrections/<map id>/`.
3. `python scripts/apply_corrections.py demo/data/<map>.json corrections/<map id>/*.json` writes the decisions into the map file. The viewer then shows "Checked by …", "Corrected by …" or "Disputed by …" on each label, and "not yet checked" on the rest.
4. The corrections files are the record. Run the script again after rebuilding a map file. Any decision made against an older machine reading is skipped and listed, to be checked again.

For now nothing is stored on a server: the file goes back by e-mail. A shared database with e-mail login (Cloudflare Access, free for up to 50 users) can replace that step once the project's Cloudflare account exists (runbook §1).

**The password.**
- GitHub Pages can't check a password on the server, so the review page is published encrypted. `demo/review/index.html` holds only ciphertext: AES-256-GCM, with the key derived from the password by PBKDF2-SHA256 over 600,000 rounds.
- The browser decrypts it once the right password is entered, and remembers it for that tab only.
- The source is in `review-src/`, which `.gitignore` keeps out of this public repository; otherwise the tool could be read here. The encrypted page contains the full source, so it can be recovered by decrypting it with the password. After editing it, or to change the password, run `python scripts/build_review.py --password-file <file outside the repository>`.
- It is one shared password, not personal accounts. Anyone can download the ciphertext and guess offline, so keep the password long and random.
- The map data and tiles the tool opens are the public ones. Personal logins come with Cloudflare Access.

**Maps that aren't public.** `demo/private/` is in `.gitignore` and is never published. `scripts/build_remezov.py` builds the Remezov ethnographic map there, because its image rights are not cleared. The front page, the viewer and review mode list it only when the site runs on the computer that built it (`python -m http.server` in `demo/`), marked "on this computer only"; on the public site the request for `private/catalogue.json` fails and nothing is shown.

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
| Speed 1626 (`data/speed-1626.json`) | `demo/tiles/`, cut from the BnF copy (Ge D 22030) on Wikimedia Commons with `scripts/make_dzi.py` | the model's output as checked in the transcription test, built with `scripts/build_speed.py`; map labels pinned at their centres (boxes approximate), back-page paragraphs boxed from the column layout |
| French-Russian map of Siberia, 1675–85 (`data/frru-1680.json`) | `demo/tiles/`, the Newberry Library's scan (Ayer MS map 30, sheet 115; no copyright) after contrast adjustment; "As scanned" uses the TARTARY Project's tiles of the same image | read by four agents, one per quadrant, plus a second reading along the quadrant lines; merged by `scripts/build_frru.py`, which flags where the two readings differ. Notes and peoples pinned; 264 towns, rivers and lakes shown on demand |
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
