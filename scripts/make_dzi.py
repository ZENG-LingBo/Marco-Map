"""Cut a scan into Deep Zoom (DZI) tiles that GitHub Pages can serve next to the demo.

    python scripts/make_dzi.py <scan.jpg> demo/tiles/<name>

writes demo/tiles/<name>.dzi and demo/tiles/<name>_files/<level>/<col>_<row>.jpg.
Used for the Ortelius scans: Internet Archive's IIIF server takes over a second per tile and
sometimes stalls, which is too slow to rely on in a lecture.
"""
import math
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TILE, OVERLAP, QUALITY = 254, 1, 82


def main(src, out):
    out = Path(out)
    files = out.parent / (out.name + "_files")
    img = Image.open(src).convert("RGB")
    width, height = img.size
    top = math.ceil(math.log2(max(width, height)))
    count = 0
    for level in range(top, -1, -1):
        w = math.ceil(width / 2 ** (top - level))
        h = math.ceil(height / 2 ** (top - level))
        if img.size != (w, h):
            img = img.resize((w, h), Image.LANCZOS)
        (files / str(level)).mkdir(parents=True, exist_ok=True)
        for col in range(math.ceil(w / TILE)):
            for row in range(math.ceil(h / TILE)):
                box = (max(0, col * TILE - OVERLAP), max(0, row * TILE - OVERLAP),
                       min(w, (col + 1) * TILE + OVERLAP), min(h, (row + 1) * TILE + OVERLAP))
                img.crop(box).save(files / str(level) / f"{col}_{row}.jpg", quality=QUALITY)
                count += 1
    out.with_suffix(".dzi").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="jpg" Overlap="{OVERLAP}" TileSize="{TILE}">\n'
        f'  <Size Width="{width}" Height="{height}"/>\n</Image>\n', encoding="utf-8")
    print(f"{src}: {width} x {height}, {top + 1} levels, {count} tiles -> {out}.dzi")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
