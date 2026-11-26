"""Build demo/data/hondius-1606.json, the reading edition of Hondius's Tartaria (1606).

    python scripts/build_hondius.py ../map-test

Map face: the HKUST copy, read from the collection's own tiles (map 95 on tiles.mappingtartary.com,
12,455 x 11,585 px), which map-test/sources/hondius1606/map_hkust_full.jpg stitches together.
Four agents (Claude Opus 5.5) read it blind on 25 Nov 2026, one quarter each, from the 8 x 6 grid
of crops in map-test/crops/hondius_map/ (prompts in map-test/prompts.md). Their files are merged
here: an item reported by two readers at a seam is kept once (same letters, centres close).
Text blocks keep the reader's box round the text; place names get a pin only.

Back: pages 333-334 of the 1606 Latin Mercator-Hondius atlas, Utrecht University Library copy,
as printed by Prof. Caboara on 25 Nov 2026 (map-test/sources/hondius1606/utrecht-1, -3, turned
upright and set side by side). The text is the blind reading of 25 Nov 2026 of the same pages in
another copy (map-test/output/mercator_verso_p311/p312.json), which matches the Utrecht pages line
for line; it is split into passages at the printed margin notes (hondius_back_passages.json).
A passage's box spans its lines, placed by spacing each page's body lines evenly between the
first and last printed line.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

DEMO = Path(__file__).resolve().parent.parent / "demo"
OUT = DEMO / "data" / "hondius-1606.json"
MAP_W, MAP_H = 12455, 11585
MAP_TILES = "https://tiles.mappingtartary.com/b787114-HKUST-view.dzi"
TEXT_W, TEXT_H = 5916, 3828
PAGE2_X = 2958  # page 334 sits to the right of page 333 in the text image

# Body text column and line placement on each page (pixels of the upright Utrecht pages).
PAGES = {
    # top of the first body line, and the pitch from it to the top of the last (measured ink bands:
    # p. 333 lines 5 and 64 at y 557 and 3094; p. 334 lines 2 and 59 at y 274 and 2738)
    333: {"x0": 470, "x1": 2320, "first": 5, "top": 557, "pitch": (3094 - 557) / 59},
    334: {"x0": 680 + PAGE2_X, "x1": 2420 + PAGE2_X, "first": 2, "top": 274, "pitch": (2738 - 274) / 57},
}
TITLE_BOX = {"x": 560, "y": 230, "w": 1700, "h": 315}  # TARTARIA / SIVE / Magni Chami imperium
QUADRANTS = ("nw", "ne", "sw", "se")


def norm(s):
    for a, b in (("ſ", "s"), ("æ", "ae"), ("Æ", "AE"), ("œ", "oe"), ("Œ", "OE"), ("ß", "ss")):  # NFKD keeps these as letters of their own
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def close(a, b, d):
    return abs(a[0] - b[0]) < d and abs(a[1] - b[1]) < d


def same_text(a, b):
    na, nb = norm(a), norm(b)
    return bool(na and nb) and (na == nb or (min(len(na), len(nb)) >= 6 and (na in nb or nb in na)))


def merge(items, key, dist):
    kept = []
    for it in items:
        dup = next((k for k in kept if close(k["centre"], it["centre"], dist) and same_text(k[key], it[key])), None)
        if dup is None:
            kept.append(it)
        elif len(norm(it[key])) > len(norm(dup[key])):  # keep the fuller reading of a label cut at a seam
            kept[kept.index(dup)] = it
    return kept


# The cartouches and the scale, by the start of their text; everything else is a note (five words
# or more) or a name of a people, region or sea. Readers' notes can't decide this: a region name
# beside a cartouche gets "cartouche" in its note too.
FIXED = {
    "tartaria": ("cartouche", "Title"),
    "iodocushondius": ("cartouche", "Hondius greets the reader"),
    "inhactartariae": ("cartouche", "Address to the reader"),
    "milliariagermanica": ("diagram", "Scale: common German miles"),
}


def fixed(b):
    n = norm(b["original"])
    for k, v in FIXED.items():
        if n == k if k == "tartaria" else n.startswith(k):
            return v
    return None


def category(b):
    f = fixed(b)
    if f:
        return f[0]
    return "inscription" if len(b["expanded"].split()) >= 5 else "toponym"


def label(b, cat):
    f = fixed(b)
    if f:
        return f[1]
    t = (b.get("label") or b["translation_en"]).strip().rstrip(".")
    t = re.sub(r"\s*\[[^\]]*\]", "", t)
    if len(t) <= 48:
        return t
    cut = re.split(r"(?<=[,;:.])\s", t[:60])[0].rstrip(",;:.")
    return (cut if len(cut) >= 20 else t[:46].rsplit(" ", 1)[0]) + "…"


def box(b):
    x0, y0, x1, y1 = b["box"]
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


def main(test):
    test = Path(test)
    blocks, places = [], []
    for q in QUADRANTS:
        d = json.loads((test / "output" / f"hondius_map_{q}.json").read_text(encoding="utf-8"))
        for b in d["textblocks"]:
            b["_q"] = q
            blocks.append(b)
        for p in d["placenames"]:
            p["_q"] = q
            places.append(p)
    # texts cut at the quarter seams, read whole from crops across the seam (hondius_map_seams.json)
    seams = json.loads((test / "output" / "hondius_map_seams.json").read_text(encoding="utf-8"))["textblocks"]
    for s in seams:
        blocks = [b for b in blocks if not any(norm(b["original"]).startswith(norm(r)) for r in s["replaces"])]
        blocks.append(dict(s, _q="seam", note=s["note"] + " Read across the seam between two readers' quarters."))
    blocks = merge(blocks, "original", 500)
    places = merge(places, "name", 250)
    # a place name that is also a text block (a large name filed by one reader as a block) is kept once
    places = [p for p in places if not any(close(p["centre"], b["centre"], 250) and same_text(p["name"], b["original"]) for b in blocks)]

    annotations = []
    blocks.sort(key=lambda b: (b["centre"][0] // 2500, b["centre"][1]))
    order = {"cartouche": 0, "inscription": 1, "diagram": 2, "toponym": 3}
    for k, b in enumerate(sorted(blocks, key=lambda b: order[category(b)])):
        cat = category(b)
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        annotations.append({
            "id": f"m{k + 1:03d}", "view": "map", "category": cat, "tour": cat != "toponym",
            "confidence": b["confidence"], "label": {"en": label(b, cat)}, "region": box(b),
            "text": {
                "lang": "la", "original": b["original"].replace(" | ", "\n"), "expanded": b["expanded"],
                "translation": b["translation_en"], "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on 25 Nov 2026 from the HKUST copy, crops {', '.join(b['crops'])}."],
            },
        })
    for k, p in enumerate(sorted(places, key=lambda p: (p["centre"][0], p["centre"][1]))):
        x, y = p["centre"]
        w, h = max(120, 28 * len(p["name"])), 70
        eng = p.get("english")
        annotations.append({
            "id": f"p{k + 1:03d}", "view": "map", "category": "placename", "tour": False,
            "confidence": p["confidence"], "label": {"la": p["name"], "en": eng or p["name"]},
            "region": {"x": int(x - w / 2), "y": int(y - h / 2), "w": w, "h": h}, "region_approx": True,
            "text": {
                "lang": "la", "original": p["name"], "expanded": p["name"].replace("ſ", "s"),
                "translation": eng or p["name"],
                "commentary": f"{p.get('kind', 'name').capitalize()}. The model's confidence in this reading: {p['confidence']}." + (" Its note: " + p["note"] if p.get("note") else ""),
                "source": [f"Read by Claude Opus 5.5 on 25 Nov 2026 from the HKUST copy, crops {', '.join(p['crops'])}."],
            },
        })

    back = json.loads((test / "output" / "hondius_back_passages.json").read_text(encoding="utf-8"))
    for p in back["passages"]:
        pg = PAGES[p["page"]]
        if p["heading"] == "Title":
            region = TITLE_BOX
        else:
            top = pg["top"] + (p["first_line"] - pg["first"]) * pg["pitch"]
            bottom = pg["top"] + (p["last_line"] - pg["first"] + 1) * pg["pitch"]
            region = {"x": pg["x0"] - 20, "y": int(top - 6), "w": pg["x1"] - pg["x0"] + 40, "h": int(bottom - top + 12)}
        heading = p["heading"] or ""
        lab = p["heading_en"] if p["heading"] else "Continued from p. 333"
        annotations.append({
            "id": p["id"], "view": "text", "category": "passage", "tour": True, "confidence": "high",
            "label": {"la": heading.replace(" | ", " ").replace("- ", "") if heading else "", "en": f"p. {p['page']}: {lab}"},
            "region": region,
            "text": {
                "lang": "la", "original": p["original"].replace(" | ", "\n"), "expanded": p["expanded"],
                "translation": p["translation_en"],
                "commentary": "\n".join(x for x in [
                    f"Margin note: {heading.replace(' | ', ' ')}" if heading and heading != "Title" else "",
                    p.get("note") or ""] if x),
                "source": ["Read blind by Claude Opus 5.5 on 25 Nov 2026 from another copy of the same printing (pp. 333–334, line for line the same as the Utrecht pages shown here), and compared with the project team's transcription: each difference was checked on the scan by the AI, not yet by a person."],
            },
        })
    for a in annotations:
        if not a["label"].get("la"):
            a["label"].pop("la", None)
    # place names last, so the texts and passages get the low numbers in the panel and the index
    annotations = [a for a in annotations if a["category"] != "placename"] + [a for a in annotations if a["category"] == "placename"]

    n_blocks, n_places = len(blocks), len(places)
    out = {
        "_comment": "Generated by scripts/build_hondius.py from map-test/output. Texts are the model's output; text-block boxes are the readers' own, place names are pins.",
        "id": "hondius-1606",
        "title": {"la": "Tartaria", "en": "Tartary"},
        "short": {"en": "Hondius, Tartary, 1606"},
        "creator": "Jodocus Hondius (1563–1612)",
        "date": "Amsterdam, 1606 (Mercator–Hondius Atlas, Latin edition)",
        "notice": "Machine transcription (Claude Opus 5.5, 25 Nov 2026), not yet reviewed by a specialist. [?] marks an uncertain reading. The text on the back was compared with the project team's transcription (each difference checked on the scan by the AI); the texts on the map have not been checked yet.",
        "catalogue": {
            "repository": "Map: HKUST Library. Text pages: Utrecht University Library",
            "reference": "From the first Latin edition of the Mercator–Hondius Atlas sive cosmographicae meditationes (Amsterdam, 1606)",
            "extent": "Map, and the atlas text on Tartary, pp. 333–334",
            "digitised": f"Map {MAP_W:,} × {MAP_H:,} px (HKUST); text pages printed from Utrecht University Library's scan",
            "credit": "Map: HKUST Library · Text pages: Utrecht University Library",
        },
        "description": "\n".join([
            "Jodocus Hondius's map of Tartary, from the first Latin edition of the Mercator–Hondius Atlas (Amsterdam, 1606). It stretches from Muscovy and the Caspian to Korea and the strait of Anian, with two costume figures, an address to the reader, and notes on Gog and Magog, the tombs of the khans, Christian Tenduc, the Great Wall and asbestos.",
            f"An AI model, Claude Opus 5.5, read the map from the HKUST copy without any reference text: {n_blocks} texts and notes, which can be read in the panel and the tour, and {n_places} place names, shown under “Towns, rivers and lakes” in the filter.",
            "Turn the sheet over for the atlas's description of Tartary (pp. 333–334), shown from the Utrecht University Library copy, in passages that follow its printed margin notes. The reading was compared with the project team's transcription, and every difference was checked on the scan by the AI, not yet by a person.",
        ]),
        "quiet": ["placename"],
        "categories": {"toponym": "Peoples, regions and seas", "inscription": "Note", "diagram": "Scale"},
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": MAP_TILES, "width": MAP_W, "height": MAP_H},
            {"id": "text", "label": {"en": "Text: pp. 333–334"}, "tileSource": "tiles/hondius-1606-text.dzi", "width": TEXT_W, "height": TEXT_H},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{n_blocks} text blocks, {n_places} place names, {len(back['passages'])} passages -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
