# The map site: a short brief for Prof. Caboara

*Written for a reader who does not want the technical detail. The technical versions are the other documents in this folder.*

## What the site will do

A visitor opens a map and can zoom into it as far as the scan allows. Numbered markers sit on the places we have written about. Clicking one opens a reading panel beside the map with the **original inscription**, its **translation**, and our **commentary**, with the source underneath. A button turns the sheet over to show the **back of the map** and whatever is written there. A "play" button walks the visitor through the markers in order, and a separate narrative page tells a story that moves the map as you scroll, in the manner of the Leventhal "Map Chat" pages you sent, but with the whole map staying zoomable underneath.

There is a working demonstration of all of this, using two maps that the Library of Congress serves online: Ricci's 1602 world map, and a 1519 Portuguese atlas sheet that has text on both sides. The link is in the covering e-mail.

## Part A. How the project will be owned, and why

**Where things are today.** The first version of the site lives in Alexia's personal accounts: her code account (GitHub), her hosting account (Vercel) and her storage account (Amazon). That is normal for a first prototype, but it is like keeping the lab notebook at a student's flat. When a student graduates, the notebook goes with them, or the password is lost.

**What we propose.** Move everything into accounts that belong to the *project*, not to a person:

- one project e-mail address (ideally an HKUST one; otherwise a mailbox you own) that is the owner of every account;
- one "organisation" on GitHub, where the code lives, with you and Ling Bo as owners and future students added as members;
- one hosting account (Cloudflare) that holds the web address, the website itself and the map images, again with named members;
- one shared password safe (Bitwarden) that you own, where every credential lives. Nothing is ever sent around by e-mail.

**Why this is worth doing now.**
- *Handover becomes trivial.* Bringing in the next student means adding one name in three places. Removing them is the same. No migration, no lost passwords.
- *Fewer moving parts.* Two services (GitHub for code, Cloudflare for everything else) instead of four. One bill a year, one place to look when something breaks.
- *The free accounts we use today are personal ones.* Their terms are "one user, non-commercial", and the free storage allowance is far below the 200 gigabytes of map images the project already has.
- *The originals are kept safe.* Alexia's original scans go to an offline archive drive that Ling Bo keeps, and a second copy of everything goes to a cheap backup service. Three copies in three places.

## Part B. What it costs, and why

Plain words for the three things one pays for: a **domain name** is the address people type; **storage** is the shelf the map images sit on; **hosting** is the reading room that serves the pages. Prices were checked on 27 September 2026 and assume 144 maps, about 200 gigabytes of images (we also checked 300).

| Option | About per year | What you get | Trade-off |
|---|---|---|---|
| **Recommended: serviceable and convenient** | **US$80 in the first year, then about US$60** (US$115 / US$90 at 300 GB) | own web address, site hosting, all 144 maps stored with unlimited viewing, a backup copy, all owned by the project, and free tools so your team can edit texts through a web form rather than code | someone on the team (Ling Bo, then a successor) keeps it running; expected effort is small |
| **Cheapest possible** | **US$35 to 50** | the same site on a free address (`something.pages.dev`), no backup | looks temporary, and no second copy of the images |
| **Buy a commercial product** (Micrio, the platform behind Oculi Mundi) | **about US$2,400** (€2,220) | a polished editor with vendor support, hosting included | the presentation belongs to the vendor; the front/back and bilingual reading panel from the demo would have to be re-created within their features; the cheaper €960 tier stops at 100 images, fewer than our 144 maps; discounts for academic institutions exist on request |

**Why not simply keep everything free as it is now?** Because "free" today means personal accounts under one student's name, with a rule of one user and non-commercial use, and a storage allowance the project has already outgrown. Keeping Amazon and Vercel properly would cost about the same as the recommended option (about US$80 a year) while leaving the ownership problem unsolved.

**Why the recommended option is cheap.** The map images are the only real cost, and the storage we recommend (Cloudflare R2) does not charge for people viewing them, which is where costs usually surprise projects like this. Everything else fits in the free tiers that these companies offer to small teams.

If the lab would rather spend money than staff time, the commercial option is a legitimate choice; the demo lets you compare what each route looks like before deciding.

## What we need from you

1. **A web address.** Suggestions: something short with "maps" and the project's name; `.com` or `.org` costs about US$10 a year. Or ask HKUST for a `something.ust.hk` name, which is free but tied to university rules.
2. **Who owns the project e-mail and the card.** Ideally you, with Ling Bo as administrator.
3. **Build or buy.** Continue with the free viewer in the demo (recommended), or purchase Micrio.

## What happens next

- Weeks 1–2: set up the project accounts; receive the code and images from Alexia; copy the images to the new storage (this happens computer-to-computer, not through anyone's laptop).
- Weeks 3–4: move the existing site into the project's accounts under the new address; first maps with annotations added using the demo's features.
- From week 5: the team adds annotations map by map through the web form; the narrative pages are written as essays are ready.

Nothing in the plan is irreversible. The images stay in a standard format that any viewer can read, and the texts live in plain files that can be moved anywhere.
