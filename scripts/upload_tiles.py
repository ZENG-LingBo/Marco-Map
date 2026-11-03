"""Upload the mirrored tiles (scripts/mirror_tiles.py) to a Cloudflare R2 bucket.

    python scripts/upload_tiles.py <mirror dir> <bucket> [--concurrency 100] [--chunk 5000]

Uses Wrangler's `r2 bulk put` (from this repository's node_modules, signed in as for `npm run deploy`)
in batches. Keys are the paths under <mirror dir>, as in the S3 bucket. Tiles are sent as image/jpeg
and the .dzi descriptors as application/xml, all with a one-year immutable Cache-Control, since a
tile never changes. A batch that finishes is recorded in <mirror dir>/_uploaded.txt, so a stopped run
carries on from the next batch; delete that file to send everything again.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRANGLER = ROOT / "node_modules" / "wrangler" / "bin" / "wrangler.js"
CACHE = "public, max-age=31536000, immutable"
TYPES = {".jpg": "image/jpeg", ".dzi": "application/xml"}


def main(argv):
    mirror, bucket = Path(argv[0]).resolve(), argv[1]
    concurrency = argv[argv.index("--concurrency") + 1] if "--concurrency" in argv else "100"
    chunk = int(argv[argv.index("--chunk") + 1]) if "--chunk" in argv else 5000
    done_file = mirror / "_uploaded.txt"
    done = set(done_file.read_text(encoding="utf-8").split()) if done_file.exists() else set()
    batches = []
    for suffix, content_type in TYPES.items():
        files = sorted(f for f in mirror.rglob("*" + suffix) if not f.name.startswith("_"))
        for i in range(0, len(files), chunk):
            batches.append((f"{suffix[1:]}-{i // chunk:04d}", content_type, files[i:i + chunk]))
    total = sum(len(b[2]) for b in batches)
    print(f"{total} files in {len(batches)} batches to {bucket}", flush=True)
    sent = 0
    for name, content_type, files in batches:
        sent += len(files)
        if name in done:
            continue
        listing = mirror / f"_batch-{name}.json"
        listing.write_text(json.dumps([{"key": f.relative_to(mirror).as_posix(), "file": str(f)} for f in files]), encoding="utf-8")
        result = subprocess.run(
            ["node", str(WRANGLER), "r2", "bulk", "put", bucket, "--filename", str(listing), "--remote", "--force",
             "--content-type", content_type, "--cache-control", CACHE, "--concurrency", concurrency],
            cwd=ROOT, capture_output=True, text=True)
        listing.unlink()
        finished = re.search(r"Uploaded 100% \(([\d,]+) out of ([\d,]+)\)", result.stdout)  # Wrangler prints 5,000
        if result.returncode != 0 or not finished or {int(n.replace(",", "")) for n in finished.groups()} != {len(files)}:
            print(f"batch {name} failed (exit {result.returncode}):\n{result.stdout[-1500:]}\n{result.stderr[-1500:]}")
            return 1
        with done_file.open("a", encoding="utf-8") as f:
            f.write(name + "\n")
        print(f"{name} done: {sent}/{total}", flush=True)
    print("all batches uploaded")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
