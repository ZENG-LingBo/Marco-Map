"""Copy the collection's deep-zoom tiles out of Alexia's S3 bucket into a folder on this computer.

    python scripts/mirror_tiles.py <out dir> [--dry-run] [--only <key prefix> ...] [--threads 16]

The bucket cannot be listed, so the tiles are worked out from each map's .dzi descriptor (tile
size, overlap, width and height), the same way a viewer asks for them. The maps come from
demo/data/collection.json and the "As scanned" layer of demo/data/frru-1680.json.

Files are written under the bucket's own keys (<key>.dzi and <key>_files/<level>/<col>_<row>.jpg),
so a later move to project storage only changes the host in the URL. Nothing is overwritten: a tile
already on disk is skipped, so an interrupted run carries on where it stopped. Every tile is
checked (HTTP 200, the length the server announced, a JPEG header). Anything else is written to
<out dir>/_problems.tsv; nothing is retried forever.

The bucket is in Alexia's AWS account and the traffic is billed to her (a few GB, inside the free
allowance). Be gentle with --threads.
"""
import http.client
import json
import math
import sys
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEMO = Path(__file__).resolve().parent.parent / "demo"
HOST = "tartary-deepzoom-bucket.s3.ap-northeast-1.amazonaws.com"
AGENT = "MappingTartary-mirror/1.0"
BAD_CHARS = set('<>:"\\|?*')


def dzi_keys():
    """Bucket keys (decoded) of every .dzi the site uses, in order, without duplicates."""
    urls = [m["dzi"] for m in json.loads((DEMO / "data" / "collection.json").read_text(encoding="utf-8"))["maps"]]
    frru = json.loads((DEMO / "data" / "frru-1680.json").read_text(encoding="utf-8"))
    for view in frru.get("views", []):
        if HOST in view.get("tileSource", ""):
            urls.append(view["tileSource"])
    keys = []
    for url in urls:
        parts = urllib.parse.urlsplit(url)
        assert parts.netloc == HOST, url
        key = urllib.parse.unquote(parts.path.lstrip("/"))
        assert key.endswith(".dzi") and not (BAD_CHARS & set(key)), key
        if key not in keys:
            keys.append(key)
    return keys


class Client(threading.local):
    """One keep-alive connection per thread."""
    conn = None

    def get(self, key):
        path = "/" + urllib.parse.quote(key, safe="/;,()")
        for attempt in range(3):
            try:
                if self.conn is None:
                    self.conn = http.client.HTTPSConnection(HOST, timeout=30)
                self.conn.request("GET", path, headers={"User-Agent": AGENT})
                r = self.conn.getresponse()
                body = r.read()
                announced = r.getheader("Content-Length")
                if r.status == 200 and announced is not None and int(announced) != len(body):
                    raise http.client.IncompleteRead(body)
                return r.status, body
            except (OSError, http.client.HTTPException):
                if self.conn is not None:
                    self.conn.close()
                self.conn = None
        return None, b""


def tile_keys(key, width, height, size):
    stem = key[: -len(".dzi")] + "_files"
    top = math.ceil(math.log2(max(width, height)))
    for level in range(top + 1):
        scale = 2 ** (top - level)
        cols = math.ceil(math.ceil(width / scale) / size)
        rows = math.ceil(math.ceil(height / scale) / size)
        for col in range(cols):
            for row in range(rows):
                yield f"{stem}/{level}/{col}_{row}.jpg"


def main(argv):
    out = Path(argv[0])
    dry = "--dry-run" in argv
    threads = int(argv[argv.index("--threads") + 1]) if "--threads" in argv else 16
    only = argv[argv.index("--only") + 1:] if "--only" in argv else None
    only = [a for a in only if not a.startswith("--")] if only else None
    out.mkdir(parents=True, exist_ok=True)
    client = Client()
    lock = threading.Lock()
    problems = open(out / "_problems.tsv", "a", encoding="utf-8")
    stats = {"done": 0, "skipped": 0, "bad": 0, "bytes": 0}

    def fetch(key):
        dest = out / key
        if dest.exists() and dest.stat().st_size > 0:
            with lock:
                stats["skipped"] += 1
            return
        status, body = client.get(key)
        if status == 200 and (key.endswith(".dzi") or body[:2] == b"\xff\xd8"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(body)
            tmp.replace(dest)
            with lock:
                stats["done"] += 1
                stats["bytes"] += len(body)
        else:
            with lock:
                stats["bad"] += 1
                problems.write(f"{status}\t{len(body)}\t{key}\n")
                problems.flush()

    keys = dzi_keys()
    plan = []
    for key in keys:
        status, body = client.get(key)
        if status != 200:
            print(f"cannot read descriptor {key}: {status}")
            return 1
        root = ET.fromstring(body)
        ns = root.tag.split("}")[0] + "}"
        size = root.find(ns + "Size")
        assert root.get("Format") == "jpg", key
        descriptor = out / key
        descriptor.parent.mkdir(parents=True, exist_ok=True)
        if not descriptor.exists():
            descriptor.write_bytes(body)
        tiles = list(tile_keys(key, int(size.get("Width")), int(size.get("Height")), int(root.get("TileSize"))))
        plan.append((key, tiles))
    total = sum(len(t) for _, t in plan)
    print(f"{len(plan)} maps, {total} tiles expected")
    (out / "_plan.json").write_text(json.dumps([{"dzi": k, "tiles": len(t)} for k, t in plan], indent=1), encoding="utf-8")
    if dry:
        return 0
    wanted = [t for k, tiles in plan for t in tiles if only is None or any(k.startswith(o) for o in only)]
    with ThreadPoolExecutor(threads) as pool:
        for i, _ in enumerate(pool.map(fetch, wanted), 1):
            if i % 2000 == 0:
                print(f"{i}/{len(wanted)}  new {stats['done']}  already there {stats['skipped']}  problems {stats['bad']}  {stats['bytes'] / 1e6:.0f} MB", flush=True)
    print(f"finished: new {stats['done']}, already there {stats['skipped']}, problems {stats['bad']}, {stats['bytes'] / 1e6:.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
