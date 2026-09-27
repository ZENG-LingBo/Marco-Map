# 03 · Cost estimate: one year, from nothing

**Audience:** Ling Bo and Prof. Caboara's budget holder. Plain-language version in [00-brief-for-prof-marco.md](00-brief-for-prof-marco.md).
**Prices:** list prices read on 27 Sep 2026 from the vendors' own pricing pages (links in §6). Two rows could not be fetched directly (Namecheap and Hetzner block automated access) and cite price aggregators; they are marked ‡. Currency: US$ unless stated; Micrio prices in €.

## 1. Assumptions

| Item | Value | Why |
|---|---|---|
| Maps | 144 | Alexia's figure |
| Tiles stored | **200 GB** (300 GB sensitivity column) | Ling Bo's estimate, "not larger than 300 GB" |
| Average tile | ~40 KB | typical 256 px JPEG at quality 85 |
| Tile count | ~5 million | 200 GB ÷ 40 KB |
| Traffic | 100–200 GB/month, ≈2.5–5 million tile requests/month | a research site with a few thousand visitors/month; each visit pulls a few hundred tiles |
| Team | 2–3 people who must all be able to log in | handover requirement |

## 2. The four scenarios

| Scenario | Year 1 at 200 GB | Year 1 at 300 GB | Following years | Handover | Who can edit content without code |
|---|---|---|---|---|---|
| **A. Recommended: serviceable and convenient** (Cloudflare Pages + R2 + domain + B2 backup) | **≈ $80** | ≈ $115 | ≈ $61 / ≈ $88 | one org, one account, one vault | yes, with Sveltia CMS ($0) |
| **B. Lowest cost, all maps** (`*.pages.dev`, R2, no domain, no backup) | ≈ $52 | ≈ $79 | ≈ $34 / ≈ $52 | same accounts, no domain | same |
| **C. Keep AWS + Vercel as today** (S3 + CloudFront + Vercel Hobby + domain) | ≈ $78 | ≈ $106 | ≈ $78 / ≈ $106 | single-user Hobby, AWS IAM to manage | no (nothing built in) |
| **D. Buy a commercial viewer** (Micrio Premium + Image Tours + domain) | **≈ €2,220 + $10** (≈ $2,400) | same | same | vendor dashboard, 4 users | yes, vendor editor |

"Zero cost" strictly ($0): scenario B on the R2 free tier holds 10 GB, i.e. about 7 of the 144 maps. Fine for a pilot, not for the collection, so it is not a scenario here.

## 3. Arithmetic

### A. Recommended (Cloudflare-centred)

| Line | 200 GB | 300 GB | Basis |
|---|---|---|---|
| Domain `.com` at Cloudflare Registrar | $10.46 | $10.46 | at-cost; `.org` $8.50 first year then $11.20; `.hk` is not offered by Cloudflare, Dynadot $12.24 then $19.12; an HKUST `*.ust.hk` name from ITSO is $0 |
| Cloudflare Pages (site) | $0 | $0 | Free plan: 500 builds/month, 20,000 files per site, unlimited static requests, custom domains, account members |
| R2 storage | (200−10) × $0.015 × 12 = **$34.20** | (300−10) × $0.015 × 12 = **$52.20** | first 10 GB-month free |
| R2 reads (Class B) | $0 | $0 | 5M/month reads < 10M free |
| R2 egress | $0 | $0 | R2 charges no egress |
| R2 one-off migration writes (Class A) | (5M − 1M) × $4.50/M = **$18** | (7.5M − 1M) × $4.50/M = $29 | one-off, year 1 only; 1M/month free |
| Backblaze B2 backup | 0.2 TB × $6.95 × 12 = **$16.68** | 0.3 TB × $6.95 × 12 = $25.02 | first 10 GB free; egress to Cloudflare free |
| GitHub organisation, Bitwarden organisation, Sveltia CMS | $0 | $0 | free tiers cover this team |
| **Year 1** | **≈ $79** | **≈ $117** | |
| **Year 2+** (no migration writes) | **≈ $61** | **≈ $88** | |

Optional add-on: **Vercel Pro** at $20/seat/month if the app must keep Next.js server features and the team wants shared ownership: +$240/year for one seat (+$480 for two). Cloudflare Pages Functions/Workers are the $0–$60/year alternative if a little server-side code is needed.

### B. Lowest cost with all maps
Scenario A minus the domain and the backup: R2 storage $34.20 (200 GB) or $52.20 (300 GB) per year, plus the one-off $18 migration writes. The site lives at `<project>.pages.dev`; tiles must still be served through a custom hostname because `r2.dev` is rate-limited and "for development", which in practice means buying the $10 domain anyway. Not recommended for a site meant to last.

### C. Keep AWS + Vercel

| Line | 200 GB | 300 GB | Basis |
|---|---|---|---|
| S3 Standard storage | 200 × $0.023 × 12 = $55.20 | 300 × $0.023 × 12 = $82.80 | us-east-1 list price |
| S3 GET requests | ≈ 2.5M/month × $0.0004/1k × 12 = $12 | same | assumes CloudFront serves half the tiles from cache |
| CloudFront | $0 | $0 | 1 TB/month and 10M requests/month always free; beyond that $0.085–0.12/GB |
| S3 → internet egress | $0 with CloudFront | | without CloudFront: (200−100) × $0.09 × 12 = $108/year |
| Vercel Hobby | $0 | $0 | single user, non-commercial only |
| Domain | $10.46 | $10.46 | |
| **Year** | **≈ $78** | **≈ $106** | |

Same money as A but worse on the things that matter here: a single-user Hobby account, an AWS root account to guard, two more vendors, and a bill that jumps if traffic ever exceeds the free tier. Adding Vercel Pro for team ownership makes it ≈ $318.

### D. Commercial viewer (Micrio) — "buy instead of build"

| Line | Per year | Notes |
|---|---|---|
| Micrio SHOW Standard | €960 | ≤ 100 images, 1 dashboard user, hosting and bandwidth included. **144 maps exceed the 100-image cap**, so Standard does not fit |
| Micrio SHOW Premium | €1,980 | ≤ 25,000 images, 4 dashboard users, galleries, custom UI |
| TELL: Image Tours add-on | €240 | markers, hotspots and guided tours edited in the dashboard, no code |
| Domain | $10 | |
| **Total** | **≈ €2,220 + $10 ≈ US$2,400** | "special discounts for cultural institutions, non-profits or individuals" on request; not published |

What the money buys: a polished no-code editor for markers and tours, IIIF import, vendor support, and no hosting to run. What it does not buy: ownership of the viewer (content is exportable, the presentation is not), and the front/back and bilingual reading-panel behaviours in the demo would have to be re-created within Micrio's feature set. The demo in this repository plus **Sveltia CMS** (free, form-based editing of the annotation files through GitHub login) gives the team the same "edit without code" outcome at $0.

Middle options: **Sanity** hosted CMS, free tier (20 seats, 10k documents, 100 GB assets), Growth $15/seat/month if it is ever needed; **Omeka.net** Silver $75/year (5 GB, for the essays and catalogue, not the tiles).

## 4. Extras that may come up later

| Need | Option | Cost per year |
|---|---|---|
| A real IIIF image server (dynamic crops, no pre-tiling) | Hetzner CX23 VPS ‡ €5.49/month + €0.50 IPv4; DigitalOcean $4–6/month; Oracle Cloud Always-Free ARM | ≈ €72 / $48–72 / $0 |
| User-editable annotations with a database | Supabase Free (500 MB) or Cloudflare D1 Free (5 GB) | $0 |
| Second seat in the password manager beyond two | Bitwarden Teams | ≈ $48 |
| Maps a library already serves over IIIF (like both maps in the demo) | link, do not host | $0 |
| More storage later | R2 is $0.18 per GB per year; B2 $0.083 | linear |

## 5. Recommendation

Go with **A**. It costs the same as keeping AWS, is owned by the project rather than a person, has zero egress risk, and leaves the whole yearly bill under US$120 even at 300 GB. Keep **D** in reserve as the "buy" option if, after seeing the demo, Prof. Caboara prefers a vendor-supported editor and the lab would rather spend ≈ US$2,400 a year than staff time.

## 6. Sources

Domains: [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) · [Cloudflare TLD prices](https://cfdomainpricing.com/) · [Porkbun .com](https://porkbun.com/tld/com) · [Porkbun .org](https://porkbun.com/tld/org) · [Dynadot .hk](https://www.dynadot.com/domain/hk) · [Namecheap via aggregator ‡](https://tldprice.org/registrar/namecheap) · [HKUST ITSO domain names](https://itso.hkust.edu.hk/services/workplace-services/getting-connected-with-wired-connection/request-domain-name)
Hosting: [Vercel pricing](https://vercel.com/pricing) · [Vercel Hobby](https://vercel.com/docs/plans/hobby) · [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) · [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/) · [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) · [Netlify credit pricing](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/)
Storage: [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/) · [R2 public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/) · [AWS S3 pricing](https://aws.amazon.com/s3/pricing/) · [AWS Free Tier](https://aws.amazon.com/free/) · [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/) · [Backblaze B2 pricing](https://www.backblaze.com/cloud-storage/pricing) · [Hetzner Object Storage](https://www.hetzner.com/storage/object-storage/) · [DigitalOcean Spaces](https://www.digitalocean.com/pricing/spaces-object-storage)
Compute: [Hetzner price adjustment ‡](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) · [DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets) · [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
Editing and data: [Micrio pricing](https://micr.io/pricing) · [Sanity pricing](https://www.sanity.io/pricing) · [Sveltia CMS](https://github.com/sveltia/sveltia-cms) · [Sveltia CMS authenticator (Cloudflare Workers)](https://github.com/sveltia/sveltia-cms-auth) · [Omeka.net plans](https://www.omeka.net/signup) · [Supabase pricing](https://supabase.com/pricing) · [Cloudflare D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) · [Bitwarden plans](https://bitwarden.com/pricing/business/)
Ownership: [GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) · [Cloudflare account members](https://developers.cloudflare.com/fundamentals/manage-members/manage/) · [AWS Organizations pricing](https://docs.aws.amazon.com/organizations/latest/userguide/pricing.html)
