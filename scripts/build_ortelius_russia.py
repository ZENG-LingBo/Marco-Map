"""Build demo/data/ortelius-1570-russia.json, the reading edition of Ortelius's map of Russia,
after Anthony Jenkinson (Theatrum orbis terrarum, 1570; van den Broecke Ort 162).

    python scripts/build_ortelius_russia.py ../map-test

Map face: the David Rumsey Map Collection copy, as in the collection (map 169 on
tiles.mappingtartary.com, 10,259 x 7,106 px; map-test/scripts/stitch_dzi.py puts it together).
Two agents (Claude Opus 5.5) read it blind on 26 Nov 2026, one half each, from the 5 x 4 grid of
crops in map-test/crops/ortelius_russia_map/ (map-test/scripts/make_crops_istanbul.py). Their files
are merged here with the Hondius helpers. Afterwards the reading was compared with Marcel van den
Broecke's lists for Ort 162 (map-test/scripts/compare_ortelius_russia_vdb.py); his text is a
reference only and is not published.

Back: p. 104 of the 1595 Latin Theatrum, Biblioteca Nacional de España copy, from the PDF
Prof. Caboara sent on 26 Nov 2026. Read blind by one agent the same day and split into passages
by subject (map-test/scripts/passages_ortelius_russia.py).
"""
import difflib
import json
import sys
from pathlib import Path

from build_hondius import close, merge, norm, same_text, label as hondius_label  # noqa: E402

DEMO = Path(__file__).resolve().parent.parent / "demo"
ID = "ortelius-1570-russia"
OUT = DEMO / "data" / f"{ID}.json"
MAP_W, MAP_H = 10259, 7106
MAP_TILES = "https://tiles.mappingtartary.com/1570-Ortelius-Jenskinson_Rumsey_Muscovy-view.dzi"
TEXT_W, TEXT_H = 1675, 2527
SIDES = ("west", "east")
DATE = "26 Nov 2026"

# By the start of the text (normalised): the cartouches, the captions and notes, the scale and the
# privilege. Everything else is a note (four words or more) or a name.
FIXED = {
    "rvssiaemosco": ("cartouche", "Title, with Jenkinson's dedication"),
    "ioannesbasil": ("cartouche", "Ivan IV, emperor of Russia"),
    "zlatababa": ("inscription", "Zlata Baba, the golden old woman"),
    "horumregionum": ("inscription", "Worshippers of the sun and a red cloth"),
    "haecsaxa": ("inscription", "The horde turned to stone"),
    "hecsaxa": ("inscription", "The horde turned to stone"),
    "kirgessigens": ("inscription", "The Kirghiz: their rite and burial in trees"),
    "kirgissigens": ("inscription", "The Kirghiz: their rite and burial in trees"),
    "shamarcandia": ("inscription", "Samarkand and Tamerlane"),
    "cascara": ("inscription", "Kashgar, on the road to Cathay"),
    "amangusla": ("inscription", "From Mangyshlak to Bukhara"),
    "corasanpar": ("inscription", "Lesser Khorasan, taken in 1558"),
    "haecparslitu": ("inscription", "This part of Lithuania is under Russia"),
    "hecparslitu": ("inscription", "This part of Lithuania is under Russia"),
    "scala": ("diagram", "Scale of Russian, English and Spanish miles"),
    "cumpriuilegio": ("colophon", "Privilege"),
    "cumprivilegio": ("colophon", "Privilege"),
    "septentrio": ("cardinal", "North"), "meridies": ("cardinal", "South"),
    "oriens": ("cardinal", "East"), "occidens": ("cardinal", "West"),
}

# Notes on single texts, from the comparison with van den Broecke's lists (filled in after review).
NOTES = {}

# Readings corrected after checking a difference from van den Broecke on the scan (26 Nov 2026).
CORRECTIONS = {
    "cascara": [("entem verſus", "entem Verſus")],  # capital V on the plate
}

BACK_NOTES = {
    "b08": "The last two works named, Oderborn's life of Basilides [Ivan IV] and Chytraeus's Chronicle of Saxony, are not in the 1570 text: they were added in the Latin editions of 1592 and 1595 (van den Broecke, Ort 162).",
}


def fixed(b):
    n = norm(b["original"])
    for k, v in FIXED.items():
        if n == k if v[0] == "cardinal" else n.startswith(k):
            return v
    return None


def category(b):
    f = fixed(b)
    if f:
        return f[0]
    return "inscription" if len(b["expanded"].split()) >= 4 else "toponym"


def box(b):
    x0, y0, x1, y1 = b["box"]
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


def _inside(c, bx, pad):
    return bx[0] - pad <= c[0] <= bx[2] + pad and bx[1] - pad <= c[1] <= bx[3] + pad


def _overlaps(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return min(len(na), len(nb)) >= 3
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.6


def apply_seams(path, blocks, places):
    """A third reader read strips centred on the line between the two halves, whole. Its reading of
    a text replaces the halves' readings of the same text (a piece of it, or the same letters) that
    lie inside or near its box; a name it reports replaces the same name nearby."""
    if not path.exists():
        return blocks, places
    seam = json.loads(path.read_text(encoding="utf-8"))
    # a reading cut off at the edge of the seam strip ("[…]") is less than the halves already have
    for s in [s for s in seam.get("textblocks", []) if "[…]" not in s["original"]]:
        blocks = [b for b in blocks if not (_inside(b["centre"], s["box"], 300) and _overlaps(b["original"], s["original"]))]
        places = [p for p in places if not (_inside(p["centre"], s["box"], 150) and _overlaps(p["name"], s["original"]))]
        blocks.append(dict(s, note=((s.get("note") or "") + " Read whole from strips across the line between the two readers' halves.").strip()))
    for s in [s for s in seam.get("placenames", []) if "[…]" not in s["name"]]:
        places = [p for p in places if not (close(p["centre"], s["centre"], 400) and _overlaps(p["name"], s["name"]))]
        places.append(s)
    return blocks, places


# Names engraved in giant, widely spaced capitals, which the two readers saw in pieces (normalised
# letters of each piece -> the whole name). Checked on the scan on 26 Nov 2026; the same names are in
# van den Broecke's list (S:A:MOYEDA, T:ARTARI., PER:SIA.).
GIANTS = [
    (["sa", "moyeda"], "S⸗ A⸗ | MOYEDA", "SAMOYEDA", "Samoyeda [the land of the Samoyeds]"),
    (["artari"], "T⸗ | ARTARI.", "TARTARI.", "The Tartars"),
    (["per", "sia"], "PER⸗ | SIA.", "PERSIA.", "Persia"),
]
EXTRA_BOX = {"artari": (3250, 3588)}  # the T, at x 3280, lies west of what the east reader boxed
DROP = ["russica80", "rußica80"]  # a row of the scale cut at the readers' line; the whole scale is read once


def join_giants(blocks):
    for parts, original, expanded, english in GIANTS:
        found = [next((b for b in blocks if norm(b["original"]) == p), None) for p in parts]
        if not all(found):
            print("giant name not joined:", original)
            continue
        x0 = min(b["box"][0] for b in found); y0 = min(b["box"][1] for b in found)
        x1 = max(b["box"][2] for b in found); y1 = max(b["box"][3] for b in found)
        for p in parts:
            if p in EXTRA_BOX:
                x0, y0 = min(x0, EXTRA_BOX[p][0]), min(y0, EXTRA_BOX[p][1])
        blocks = [b for b in blocks if not any(b is f for f in found)]
        conf = "medium" if any(b["confidence"] != "high" for b in found) else "high"
        blocks.append({"original": original, "expanded": expanded, "translation_en": english, "confidence": conf,
                       "crops": sorted({c for b in found for c in b["crops"]}), "box": [x0, y0, x1, y1],
                       "centre": [(x0 + x1) // 2, (y0 + y1) // 2],
                       "note": "Giant spaced capitals across the map, read in pieces by the two readers and joined here."})
    return [b for b in blocks if not any(norm(b["original"]).startswith(d) for d in DROP)]


def main(test):
    test = Path(test)
    blocks, places = [], []
    for s in SIDES:
        d = json.loads((test / "output" / f"ortelius_russia_map_{s}.json").read_text(encoding="utf-8"))
        blocks += d["textblocks"]
        places += d["placenames"]
    blocks, places = apply_seams(test / "output" / "ortelius_russia_map_seams.json", blocks, places)
    for b in blocks:
        for key, fixes in CORRECTIONS.items():
            if norm(b["original"]).startswith(key):
                for old, new in fixes:
                    assert old in b["original"], (key, old)
                    b["original"] = b["original"].replace(old, new)
    blocks = join_giants(blocks)
    blocks = merge(blocks, "original", 500)
    blocks = [b for b in blocks if len(norm(b["original"])) > 2]
    places = merge(places, "name", 250)
    places = [p for p in places if not any(close(p["centre"], b["centre"], 250) and same_text(p["name"], b["original"]) for b in blocks)]

    order = {"cartouche": 0, "inscription": 1, "diagram": 2, "colophon": 3, "toponym": 4, "cardinal": 5}
    blocks.sort(key=lambda b: (order[category(b)], b["centre"][0] // 2500, b["centre"][1]))
    annotations = []
    for k, b in enumerate(blocks):
        cat = category(b)
        f = fixed(b)
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        key = next((k2 for k2 in NOTES if norm(b["original"]).startswith(k2)), None)
        if key:
            notes.append(NOTES[key])
        annotations.append({
            "id": f"m{k + 1:03d}", "view": "map", "category": cat, "tour": cat not in ("toponym", "cardinal"),
            "confidence": b["confidence"], "label": {"en": f[1] if f else hondius_label(b, cat)}, "region": box(b),
            "text": {
                "lang": "la", "original": b["original"].replace(" | ", "\n"), "expanded": b["expanded"],
                "translation": b["translation_en"], "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on {DATE} from the David Rumsey Map Collection copy, crops {', '.join(b['crops'])}."],
            },
        })
    for p in sorted(places, key=lambda p: (p["centre"][0], p["centre"][1])):
        x, y = p["centre"]
        w, h = max(120, 28 * len(p["name"])), 70
        eng = p.get("english")
        annotations.append({
            "id": f"p{len(annotations) + 1:03d}", "view": "map", "category": "placename", "tour": False,
            "confidence": p["confidence"], "label": {"la": p["name"], "en": eng or p["name"]},
            "region": {"x": int(x - w / 2), "y": int(y - h / 2), "w": w, "h": h}, "region_approx": True,
            "text": {
                "lang": "la", "original": p["name"], "expanded": p["name"].replace("ſ", "s"), "translation": eng or p["name"],
                "commentary": f"{p.get('kind', 'name').capitalize()}. The model's confidence in this reading: {p['confidence']}." + (" Its note: " + p["note"] if p.get("note") else ""),
                "source": [f"Read by Claude Opus 5.5 on {DATE} from the David Rumsey Map Collection copy, crops {', '.join(p['crops'])}."],
            },
        })

    back = json.loads((test / "output" / "ortelius_russia_back_passages.json").read_text(encoding="utf-8"))
    passages = []
    for p in back["passages"]:
        x0, y0, x1, y1 = p["box"]
        comm = [BACK_NOTES[p["id"]]] if p["id"] in BACK_NOTES else []
        passages.append({
            "id": p["id"], "view": "text", "category": "passage", "tour": True, "confidence": "high",
            "label": {"en": f"p. 104: {p['heading_en']}"},
            "region": {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
            "text": {
                "lang": "la", "original": p["original"].replace(" | ", "\n"), "expanded": p["expanded"],
                "translation": p["translation_en"], "commentary": "\n".join(comm),
                "source": [f"Read blind by Claude Opus 5.5 on {DATE} from the BNE copy of the 1595 Latin Theatrum, p. 104; the translation was then compared with Marcel van den Broecke's English (orteliusmaps.com, Ort 162)."],
            },
        })
    annotations = [a for a in annotations if a["category"] != "placename"] + passages + [a for a in annotations if a["category"] == "placename"]

    n_blocks, n_places = len(blocks), len(places)
    out = {
        "_comment": f"Generated by scripts/build_ortelius_russia.py from map-test/output. Texts are the model's output (readers' boxes; place names are pins).",
        "id": ID,
        "title": {"la": "Russiae, Moscoviae et Tartariae descriptio", "en": "Russia, Muscovy and Tartary"},
        "short": {"en": "Ortelius, Russia, 1570"},
        "creator": "Abraham Ortelius (1527–1598), after Anthony Jenkinson (1529–1611)",
        "date": "Antwerp, 1570 (Theatrum orbis terrarum)",
        "notice": f"Machine transcription and translation (Claude Opus 5.5, {DATE}), not yet reviewed by a specialist. [?] marks an uncertain reading. The texts were compared afterwards with Marcel van den Broecke's published edition (Ort 162).",
        "catalogue": {
            "repository": "Map: David Rumsey Map Collection. Text page: Biblioteca Nacional de España",
            "reference": "Abraham Ortelius, Theatrum orbis terrarum (Antwerp, 1570), after Anthony Jenkinson's map of 1562; van den Broecke Ort 162. Text page from the Latin edition of 1595",
            "extent": "Map, and the description of Russia printed on the back (p. 104 in the 1595 edition)",
            "digitised": f"Map {MAP_W:,} × {MAP_H:,} px (David Rumsey Map Collection); text page from the BNE's scan (Biblioteca Digital Hispánica)",
            "credit": "Map: David Rumsey Map Collection, David Rumsey Map Center, Stanford Libraries (CC BY-NC-SA) · Text page: Biblioteca Nacional de España (CC BY)",
        },
        "description": "\n".join([
            "Anthony Jenkinson's map of Russia, Muscovy and Tartary, first printed in London in 1562 and engraved for Abraham Ortelius's Theatrum orbis terrarum (Antwerp, 1570). Jenkinson travelled for the Muscovy Company to Moscow, down the Volga and across the Caspian to Bukhara (1558–1559). The map shows Ivan IV enthroned, and notes on the peoples he met or heard of: the golden idol Zlata Baba, sun-worshippers, a horde turned to stone, the Kirghiz who hang their dead in trees, Samarkand and the tomb of Tamerlane, and the road to Cathay.",
            f"An AI model, Claude Opus 5.5, read the map from the David Rumsey Map Collection copy without any reference text: {n_blocks} texts, notes and names, which can be read in the panel and the tour, and {n_places} place names, shown under “Towns, rivers and lakes” in the filter.",
            "Turn the sheet over for Ortelius's description of Russia, read by the same model from the Biblioteca Nacional de España copy of the 1595 Latin edition (p. 104); it is the 1570 text with two later additions to the reading list.",
        ]),
        "quiet": ["placename"],
        "categories": {"toponym": "Peoples, regions and seas", "inscription": "Note", "diagram": "Scale", "colophon": "Privilege", "cardinal": "Compass word"},
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": MAP_TILES, "width": MAP_W, "height": MAP_H},
            {"id": "text", "label": {"en": "Text: p. 104 (1595)"}, "tileSource": f"tiles/{ID}-text.dzi", "width": TEXT_W, "height": TEXT_H},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{n_blocks} text blocks, {n_places} place names, {len(passages)} passages -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
