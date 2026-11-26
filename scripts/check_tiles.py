"""Check that every tile of every mirrored map is there and whole, on disk and (optionally) online.

    python scripts/check_tiles.py <mirror dir> [--base https://tiles.mappingtartary.com] [--origin https://mappingtartary.com]

The expected tiles come from the .dzi descriptors in <mirror dir>. On disk, a tile must start with the
JPEG start marker and end with the end marker. With --base, each tile is also requested from that host
(HEAD, with an Origin header like a browser's): it must answer 200 with the length of the file on disk,
Access-Control-Allow-Origin, and a long immutable Cache-Control. Problems go to <mirror dir>/_check.tsv.
"""
import http.client
import math
import sys
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_tiles import tile_keys  # noqa: E402


def expected(mirror):
    for dzi in sorted(mirror.rglob("*.dzi")):
        root = ET.fromstring(dzi.read_bytes())
        ns = root.tag.split("}")[0] + "}"
        size = root.find(ns + "Size")
        key = dzi.relative_to(mirror).as_posix()
        yield key
        yield from tile_keys(key, int(size.get("Width")), int(size.get("Height")), int(root.get("TileSize")))


class Online(threading.local):
    conn = None

    def head(self, host, key, origin):
        path = "/" + urllib.parse.quote(key, safe="/;,()")
        for _ in range(3):
            try:
                if self.conn is None:
                    self.conn = http.client.HTTPSConnection(host, timeout=30)
                self.conn.request("HEAD", path, headers={"Origin": origin, "User-Agent": "MappingTartary-check/1.0"})
                r = self.conn.getresponse()
                r.read()
                return r.status, {k.lower(): v for k, v in r.getheaders()}
            except (OSError, http.client.HTTPException):
                if self.conn is not None:
                    self.conn.close()
                self.conn = None
        return None, {}


def main(argv):
    mirror = Path(argv[0]).resolve()
    base = argv[argv.index("--base") + 1] if "--base" in argv else None
    origin = argv[argv.index("--origin") + 1] if "--origin" in argv else "https://mappingtartary.com"
    keys = list(expected(mirror))
    print(f"{len(keys)} files expected", flush=True)
    online, lock, out = Online(), threading.Lock(), open(mirror / "_check.tsv", "w", encoding="utf-8")
    stats = {"bad": 0}

    def check(key):
        path, problem = mirror / key, None
        if not path.is_file():
            problem = "missing"
        else:
            data = path.read_bytes()
            if key.endswith(".jpg") and (data[:2] != b"\xff\xd8" or data[-2:] != b"\xff\xd9"):
                problem = "not a whole jpeg"
            elif base:
                status, headers = online.head(urllib.parse.urlsplit(base).netloc, key, origin)
                if status != 200:
                    problem = f"online status {status}"
                elif headers.get("content-length") != str(len(data)):
                    problem = f"online length {headers.get('content-length')} != {len(data)}"
                elif headers.get("access-control-allow-origin") not in ("*", origin):
                    problem = f"no CORS header ({headers.get('access-control-allow-origin')})"
                elif "immutable" not in headers.get("cache-control", ""):
                    problem = f"cache-control {headers.get('cache-control')}"
        if problem:
            with lock:
                stats["bad"] += 1
                out.write(f"{problem}\t{key}\n")
                out.flush()

    with ThreadPoolExecutor(32 if base else 8) as pool:
        for i, _ in enumerate(pool.map(check, keys), 1):
            if i % 20000 == 0:
                print(f"{i}/{len(keys)}  problems {stats['bad']}", flush=True)
    print(f"checked {len(keys)} files{' online and on disk' if base else ' on disk'}: {stats['bad']} problems")
    return 1 if stats["bad"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
