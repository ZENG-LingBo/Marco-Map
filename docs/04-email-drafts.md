# 04 · Draft e-mails

Drafts for Ling Bo to edit and send. Nothing has been sent. Square brackets mark things to fill in.

---

## 1. To Alexia (TSANG Tze Nam) — handover

**Subject:** Map site handover: what I need from you, and what happens to the images

Hi Alexia,

Thanks again for building the first version of the site, and for agreeing to the repository invite.

Prof. Caboara wants the project set up so that it can be handed on easily in future, so I am moving it into accounts owned by the project rather than by any of us. That changes a couple of things about the handover, so here is the full list in one place.

**1. The code.** Instead of inviting me as a collaborator, could you transfer the repository? GitHub: *Settings → Danger zone → Transfer ownership*, to the organisation **[hkust-marco-map]** (I will create it and send you the exact name). Transferring keeps the history, issues and settings, and GitHub redirects the old links. If you would rather keep your copy, a collaborator invite is fine and I will mirror it instead.

**2. Deployment details.** Could you send me the list of environment variables (names and values), the build command and root directory from the Vercel project, and any custom domain you set up (and who holds its DNS)? Please put anything secret into the shared password vault I will invite you to (Bitwarden), not into e-mail.

**3. The tiles in S3.** To answer your question: yes, by "the database" I meant the tiles in S3. Because it is around 200 GB, the fastest and safest way is a direct copy from your bucket to the project's new storage (Cloudflare R2), computer to computer, so nothing has to pass through a laptop or my NAS. For that I only need:
- the bucket name and region, and the folder layout / tile format (DZI, XYZ tiles, IIIF, or something else);
- a **read-only** IAM key for that bucket (policy: `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation`), again via the vault.

One thing to know in advance: AWS bills the bucket owner for data leaving S3 above 100 GB in a month. For 200 GB that is about US$9 if done in one go, or nothing if we split the copy across two months; the project will reimburse you either way, and AWS also waives it on request when a customer moves off. I will run the copy on a date that suits you.

**4. The originals.** The original scans (TIFF/PNG), your tiling script and its settings, and the metadata spreadsheet (titles, dates, repositories, credits) are the things that are not in S3. For those the NAS account I set up for you is the right place: [drive.lbzeng.com], folder *Marco-Map/originals*. I have changed the password since it went out by e-mail; the new one is in the vault. The account is upload-only and I will close it once the files are in.

**5. Afterwards.** Once I confirm the copy (I will compare file counts and sizes on both sides), please keep your copies for 30 days and then delete them, so we know where the single source is.

Happy to go through any of this on a call, or when we next meet. And if you have opinions on the new features Prof. Caboara asked for (annotations with the original text and translation, showing the back of a map, guided tours), I would like to hear them: there is a working demo at [link].

Best,
Ling Bo

---

## 2. To Prof. Caboara — cover note

**Subject:** Map site: demo, plan and costs for your decision

Dear Prof. Caboara,

Following our discussion and the sites you sent me (the Leventhal "Map Chat" pages and Oculi Mundi), I have put together three things:

1. **A working demonstration** of the features we discussed: zoom into the scan, numbered markers that open the original inscription beside its translation and our commentary, a button that turns the sheet over to show the back, a guided tour, and a narrative page that moves the map as you scroll. It uses two maps that the Library of Congress serves online, Ricci's 1602 world map and a 1519 Portuguese atlas sheet with text on both sides: [demo link].

2. **A short brief** (two pages, no technical detail) on how the project should be owned so that it can be handed over easily in future, and what it will cost for a year: [link to docs/00-brief-for-prof-marco.md].

3. The detailed plan for taking over Alexia's site and images, and the cost estimate with sources, for anyone who wants the detail.

The short version: the recommended setup costs about **US$80 in the first year and about US$60 a year after that**, with everything owned by the project rather than by a student. There is also a commercial route (Micrio, the platform behind Oculi Mundi) at roughly **US$2,400 a year**, which buys a vendor-supported editor; the brief compares the two.

I need three decisions from you when convenient:
- a **web address** for the site (a `.org` or `.com` costs about US$10 a year; an HKUST `something.ust.hk` name is free but bound by university rules);
- **who holds the project e-mail and the payment card** (my suggestion: you, with me as administrator);
- **build or buy**: continue with the free viewer in the demo, or purchase Micrio.

I would be glad to walk you through the demo in person; twenty minutes is enough.

With best regards,
Ling Bo
