# 01 · Migration runbook: taking the site over, properly

**Audience:** Ling Bo (technical). The plain-language version for Prof. Caboara is [00-brief-for-prof-marco.md](00-brief-for-prof-marco.md).
**Status:** written before access to Alexia's repository. Steps marked ☐ are to be executed once the GitHub invite and bucket details arrive; nothing here has been run yet.

## 0. What we are moving

| Asset | Where it is today | Where it goes |
|---|---|---|
| Web app code | Alexia's personal GitHub repo (Vercel-deployed) | `Marco-Map` under a project-owned GitHub organisation |
| Map tiles, 144 maps, ~200 GB (plan for 300 GB) | Alexia's personal AWS S3 bucket (free tier) | Cloudflare R2 bucket in the project's Cloudflare account, served from `tiles.<domain>` |
| Deployment | Alexia's Vercel Hobby project | Cloudflare Pages (static) or Vercel Pro team (if the app needs server features) |
| Original scans, metadata sheet, tiling script | Alexia's machine / unknown | Offline archive (Ling Bo's NAS) **and** a cloud backup |

Facts verified on 27 Sep 2026 against the vendors' own documentation are marked *(verified)*; each has a link in §8.

## 1. Ownership first: set up a project identity (do this before moving anything)

The point Prof. Caboara made is the right one: the site must be easy to hand over. Everything below is owned by a **project**, not by a person, so that handing over means adding a name, not migrating.

1. ☐ **Project e-mail.** Ask HKUST ITSO for a departmental/project alias (they issue `*.ust.hk` names and mailboxes to research projects); if that is slow, create a plain mailbox that Prof. Caboara owns. This address owns every account below. Recovery phone: Prof. Caboara's.
2. ☐ **Password manager.** Bitwarden free *organisation* (2 users free; Teams ≈ US$4/user/month if more are needed later). Prof. Caboara is owner; Ling Bo is admin. Every credential created below goes in the shared collection. Nothing is ever sent by e-mail.
3. ☐ **GitHub organisation** (free; unlimited members on public repos *(verified)*), e.g. `hkust-marco-map`. Owners: Prof. Caboara and Ling Bo. `Marco-Map` is transferred into it (see §2).
4. ☐ **Cloudflare account** under the project e-mail. Free plan supports invited members with roles *(verified)*, Registrar works on the Free plan *(verified)*, and R2 custom domains do not need a paid plan *(verified)*. Add Prof. Caboara as Super Administrator and Ling Bo as Administrator. This one account holds: the domain, DNS, Pages (the site) and R2 (the tiles).
5. ☐ **AWS**: only if the project keeps AWS at all. If so, an AWS Organisation with IAM Identity Center (both free *(verified)*) rather than a personal root account.

Result: **two services** (GitHub, Cloudflare) instead of four (GitHub, Vercel, AWS, a registrar), one login each, one bill (Cloudflare), one vault.

## 2. Code: GitHub transfer, not fork or mirror

| Method | Keeps issues, PRs, webhooks, secrets | Redirects old URL | When to use |
|---|---|---|---|
| **Transfer** (repo Settings → Danger zone → Transfer) | yes | yes | default |
| Fork | no | no, stays "forked from" | only if Alexia must keep ownership |
| `git clone --bare` + `git push --mirror` | no (commits, branches, tags only) | no | fallback if she cannot transfer |

Constraint *(verified)*: the receiving account/organisation must not already own a repo with the same name, and the invite must be accepted within one day.

1. ☐ Alexia transfers her repo to the organisation **under its current name**.
2. ☐ Ling Bo merges it into `Marco-Map` (this repo) so that history, docs and demo live together, then archives the transferred copy:
   ```bash
   git clone git@github.com:hkust-marco-map/Marco-Map.git && cd Marco-Map
   git remote add alexia git@github.com:hkust-marco-map/<her-repo-name>.git
   git fetch alexia
   # put the app under app/ without losing history
   git merge --allow-unrelated-histories -s ours --no-commit alexia/main
   git read-tree --prefix=app/ -u alexia/main
   git commit -m "Import map viewer app from Alexia's repository under app/"
   ```
   If her repo is literally called `Marco-Map`, rename this one for a day, accept the transfer, then merge the other way round.
3. ☐ Fallback if she keeps ownership:
   ```bash
   git clone --bare https://github.com/<alexia>/<repo>.git && cd <repo>.git
   git lfs fetch --all            # only if the repo uses LFS
   git push --mirror git@github.com:hkust-marco-map/<repo>.git
   git lfs push --all git@github.com:hkust-marco-map/<repo>.git
   ```

## 3. Deployment: re-import, do not "transfer" the Vercel project

*(verified)* Vercel project transfer requires being a member of the receiving team; Hobby accounts have no team, so Hobby→Hobby transfer is not possible without a temporary Pro upgrade. Vercel staff recommend "transfer the repository and redeploy". Also *(verified)*: Hobby is single-user and for non-commercial use only; a paid RA maintaining the site arguably counts as commercial.

Decision tree:

- ☐ **If the app is static-exportable** (Next.js `output: 'export'`, or plain HTML like the demo): deploy on **Cloudflare Pages** from the organisation repo. Free, multi-member, custom domain from the same account. This is the recommended path.
- ☐ **If it needs server features** (API routes, ISR, server actions): **Vercel Pro team** (US$20/seat/month) under the project e-mail, import the repo, re-enter environment variables, build command and root directory.
- ☐ Either way: Alexia removes the custom domain (if any) from her project; the project adds it on its side. Environment variables never transfer automatically — get the list from her (§7).

## 4. Tiles: cloud-to-cloud copy into R2

Size matters here: 200 GB (300 GB worst case) should not pass through a laptop or a home uplink.

**Recommended: S3 → Cloudflare R2**, zero egress forever *(verified)*.

1. ☐ Alexia creates a read-only IAM user on her bucket:
   ```json
   {"Version":"2012-10-17","Statement":[{"Effect":"Allow",
     "Action":["s3:GetObject","s3:ListBucket","s3:GetBucketLocation"],
     "Resource":["arn:aws:s3:::<her-bucket>","arn:aws:s3:::<her-bucket>/*"]}]}
   ```
   and sends the key **through the password manager**, not e-mail.
2. ☐ In the project Cloudflare account: R2 → create bucket `marco-tiles` (location hint APAC) → *Data migration → Super Slurper* → source S3, paste bucket, region and key. Free; only R2 Class A writes are billed and 1M/month are free *(verified)*.
   Alternative with `rclone` (same result, more control):
   ```ini
   # ~/.config/rclone/rclone.conf
   [s3aws]
   type = s3
   provider = AWS
   access_key_id = …
   secret_access_key = …
   region = <her-region>

   [r2]
   type = s3
   provider = Cloudflare
   endpoint = https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   access_key_id = …
   secret_access_key = …
   acl = private
   ```
   ```bash
   rclone sync s3aws:<her-bucket> r2:marco-tiles --transfers 64 --checkers 64 --fast-list --s3-no-check-bucket -P
   rclone size s3aws:<her-bucket>; rclone size r2:marco-tiles     # counts and bytes must match
   ```
3. **Who pays for the move:** AWS bills the *bucket owner's* account for internet egress above the 100 GB/month free allowance *(verified)*: about US$9 for 200 GB in one month, about US$0 if split over two months, and AWS waives exit egress entirely on request through a support ticket. Tell Alexia this in advance and offer to reimburse.
4. **The NAS (drive.lbzeng.com).** Keep it, for the right job: it is the **offline archive** for the original scans (TIFF/PNG), the tiling script and a one-off export, i.e. the things that are not in S3. Do **not** route the 200 GB of tiles through it (slow over a home uplink, and a file-system copy loses `Content-Type` and `Cache-Control` metadata), and never serve the public site from it. Housekeeping: create the account as upload-only with an expiry, send the credentials by a channel other than e-mail (the thread already contains them; change that password now), and disable the account when the upload is done.
5. Alternative if R2 is rejected: S3 → S3 into a project AWS account with a cross-account bucket policy, `aws s3 sync --dryrun` first, then `aws s3 ls --recursive --summarize` on both sides. New buckets default to *Bucket owner enforced*, so no ACL flags are needed *(verified)*.

## 5. After the copy: make the tiles servable

1. ☐ CORS on the bucket (same JSON works for R2 and S3):
   ```json
   [{"AllowedOrigins":["https://<domain>","https://<project>.pages.dev","http://localhost:8000"],
     "AllowedMethods":["GET","HEAD"],"AllowedHeaders":["*"],
     "ExposeHeaders":["ETag","Content-Length","Accept-Ranges","Content-Range"],"MaxAgeSeconds":3600}]
   ```
   ```bash
   npx wrangler r2 bucket cors set marco-tiles --file cors.json
   ```
2. ☐ Custom domain `tiles.<domain>` on the bucket (R2 → Settings → Custom domains). The `r2.dev` URL is rate-limited and for development only *(verified)*.
3. ☐ Immutable caching: tiles never change, so set `Cache-Control: public, max-age=31536000, immutable` (rclone: `--header-upload "Cache-Control: public, max-age=31536000, immutable"` during the sync, or a Cloudflare cache rule on `tiles.<domain>`).
4. ☐ Point the app's tile base URL at `https://tiles.<domain>/…` and check one map end-to-end.
5. ☐ Cut-over: deploy on the new host under the temporary `*.pages.dev` URL → test → move the domain → ask Alexia to keep her copies for 30 days → confirm object counts again → she deletes.

## 6. Second copy and future re-tiling

- ☐ Backup of scans + tiles to **Backblaze B2** (≈US$17/year for 200 GB; egress to Cloudflare is free): `rclone sync r2:marco-tiles b2:marco-tiles-backup --fast-list -P`. The NAS is the third, offline copy.
- Re-tiling from a source TIFF, when a map is re-scanned or a new one arrives (libvips, free):
  ```bash
  vips dzsave scan.tif out --layout dz --tile-size 256 --overlap 1 --suffix .jpg[Q=85]   # Deep Zoom (DZI)
  vips dzsave scan.tif out --layout iiif3 --tile-size 512 --id https://tiles.<domain>/maps  # static IIIF
  vips dzsave scan.tif out --layout google                                                   # XYZ
  ```
  All three are plain files; OpenSeadragon (used in the demo) reads each of them. PMTiles or Cloud-Optimised GeoTIFF are single-file alternatives for later.

## 7. What to ask Alexia for (once Prof. Caboara has confirmed the project accounts)

1. Repository transfer to the organisation (or a collaborator invite as fallback).
2. The list of environment variables (names and values, per environment), the build command, root directory, and any custom domain plus who holds its DNS.
3. S3 bucket name, region, folder layout and tile format (DZI / XYZ / IIIF / other), and a read-only IAM key delivered through the password manager.
4. The original source scans, the tiling script and its parameters (to the NAS).
5. The metadata spreadsheet (titles, dates, repositories, credits, licences).
6. Any Vercel integrations, analytics or cron jobs; agreement to keep her copies 30 days after cut-over, then delete.

## 8. Sources

- GitHub: [Transferring a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository) · [Duplicating a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository) · [GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)
- Vercel: [Transferring projects](https://vercel.com/docs/projects/transferring-projects) · [Hobby plan](https://vercel.com/docs/plans/hobby) · [Fair use guidelines](https://vercel.com/docs/limits/fair-use-guidelines) · [Vercel staff on Hobby→Hobby transfer](https://community.vercel.com/t/transferring-a-project-to-another-user/1213)
- AWS: [Cross-account bucket access walkthrough](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-walkthroughs-managing-access-example2.html) · [Object Ownership](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html) · [aws s3 sync](https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html) · [S3 pricing](https://aws.amazon.com/s3/pricing/) · [S3 CORS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html) · [AWS Organizations pricing](https://docs.aws.amazon.com/organizations/latest/userguide/pricing.html)
- Cloudflare: [R2 Super Slurper](https://developers.cloudflare.com/r2/data-migration/super-slurper/) · [R2 pricing](https://developers.cloudflare.com/r2/pricing/) · [R2 with rclone](https://developers.cloudflare.com/r2/examples/rclone/) · [R2 CORS](https://developers.cloudflare.com/r2/buckets/cors/) · [R2 public buckets and custom domains](https://developers.cloudflare.com/r2/buckets/public-buckets/) · [Manage account members](https://developers.cloudflare.com/fundamentals/manage-members/manage/) · [Registrar](https://developers.cloudflare.com/registrar/)
- Tools: [rclone S3 backend](https://rclone.org/s3/) · [vips dzsave](https://www.libvips.org/API/current/method.Image.dzsave.html) · [IIIF static tiles](https://training.iiif.io/iiif-online-workshop/day-two/image-servers/static-tiles.html) · [PMTiles](https://docs.protomaps.com/pmtiles/) · [Backblaze B2 pricing](https://www.backblaze.com/cloud-storage/pricing)
- HKUST: [ITSO domain name request](https://itso.hkust.edu.hk/services/workplace-services/getting-connected-with-wired-connection/request-domain-name)
