"""Build demo/data/blaeu-tartaria.json, the reading edition of Willem Janszoon Blaeu's
Tartaria sive Magni Chami Imperium.

    python scripts/build_blaeu.py ../map-test

Map face: the David Rumsey Map Collection copy, as in the collection (map 100 on
tiles.mappingtartary.com, 8,964 x 6,705 px). Two agents (Claude Opus 5.5) read it blind on
26 Nov 2026, one half each, from the 5 x 4 grid of crops in map-test/crops/blaeu_map/, and a
third read strips across the line between the halves (blaeu_map_seams.json).

Back: the description "TARTARIA" (two pages), from the Biblioteca Nacional de España copy that
Prof. Caboara sent as a PDF on 26 Nov 2026, turned upright and set side by side
(map-test/sources/blaeu1636/bne_tartaria_pp1-2.png). Read blind by one agent the same day and
split into passages at the printed margin notes (map-test/scripts/passages_blaeu.py). The
reading was then compared word by word with Prof. Caboara's own transcription, made from another
copy (Vienna, ÖAW); most differences were checked on the scan, and where checked the scan
agreed with this reading.
"""
import json
import sys
from pathlib import Path

from build_hondius import close, merge, norm, same_text, label as hondius_label  # noqa: E402
from build_ortelius_russia import apply_seams  # noqa: E402

DEMO = Path(__file__).resolve().parent.parent / "demo"
ID = "blaeu-tartaria"
OUT = DEMO / "data" / f"{ID}.json"
MAP_W, MAP_H = 8964, 6705
MAP_TILES = "https://tiles.mappingtartary.com/108521142.1-view.dzi"
TEXT_W, TEXT_H = 3388, 2782
SIDES = ("west", "east")
DATE = "26 Nov 2026"

FIXED = {
    "tartariasive": ("cartouche", "Title, carried by the camel"),
    "20406080": ("diagram", "Scale: common German miles"),
}

# Notes where another copy reads differently from this print (from the project's transcription of
# the Vienna copy, ÖAW AC09051019). Slips in that transcription are not listed on the page.
OTHER_COPY = {
    "b03": "A transcription of another copy (Vienna) reads “Temur Cutlu”.",
    "b05": "A transcription of another copy (Vienna) reads “Religionem suam assiduo conatu propagant”; this print has no “assiduo”.",
    "b17": "The first numeral is unclear in this scan: it is the same sign as the first of “LXXIII” on p. 1, so both are read as L. A transcription of another copy (Vienna) reads “LX”.",
}
# Readings in the passages changed after a closer look at the scan (26 Nov 2026).
PASSAGE_FIXES = {
    "b17": [("longitudine IX circiter", "longitudine LX[?] circiter"), ("about IX German miles", "about LX[?] [sixty] German miles")],
}


UNRESOLVED = ("simmav", "mmav")  # "SI | MMAV⸗ | RE⸗ | MAIER": large capitals among the mountains, grouping and sense not understood


def fixed(b):
    n = norm(b["original"])
    for k, v in FIXED.items():
        if n.startswith(k):
            return v
    return None


def category(b):
    f = fixed(b)
    if f:
        return f[0]
    if norm(b["original"]).startswith(UNRESOLVED):
        return "toponym"
    return "inscription" if len(b["expanded"].split()) >= 4 else "toponym"


def box(b):
    x0, y0, x1, y1 = b["box"]
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


def main(test):
    test = Path(test)
    blocks, places = [], []
    for s in SIDES:
        d = json.loads((test / "output" / f"blaeu_map_{s}.json").read_text(encoding="utf-8"))
        blocks += d["textblocks"]
        places += d["placenames"]
    blocks, places = apply_seams(test / "output" / "blaeu_map_seams.json", blocks, places)
    blocks = merge(blocks, "original", 500)
    blocks = [b for b in blocks if len(norm(b["original"])) > 2]
    places = merge(places, "name", 250)
    places = [p for p in places if not any(close(p["centre"], b["centre"], 40 if p.get("kind") == "town" else 250)
                                           and same_text(p["name"], b["original"]) for b in blocks)]

    order = {"cartouche": 0, "inscription": 1, "diagram": 2, "toponym": 3}
    blocks.sort(key=lambda b: (order[category(b)], b["centre"][0] // 2500, b["centre"][1]))
    annotations = []
    for k, b in enumerate(blocks):
        cat = category(b)
        f = fixed(b)
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        annotations.append({
            "id": f"m{k + 1:03d}", "view": "map", "category": cat, "tour": cat != "toponym",
            "confidence": b["confidence"], "label": {"en": f[1] if f else ("Large capitals, not yet understood" if norm(b["original"]).startswith(UNRESOLVED) else hondius_label(b, cat))}, "region": box(b),
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

    back = json.loads((test / "output" / "blaeu_back_passages.json").read_text(encoding="utf-8"))
    passages = []
    for p in back["passages"]:
        x0, y0, x1, y1 = p["box"]
        comm = []
        if p.get("heading"):
            comm.append(f"Margin note: {p['heading']}")
        if p["id"] in OTHER_COPY:
            comm.append(OTHER_COPY[p["id"]])
        for old_t, new_t in PASSAGE_FIXES.get(p["id"], []):
            hit = False
            for k in ("original", "expanded", "translation_en"):
                if old_t in p[k]:
                    p[k] = p[k].replace(old_t, new_t)
                    hit = True
            assert hit, (p["id"], old_t)
        passages.append({
            "id": p["id"], "view": "text", "category": "passage", "tour": True, "confidence": "high",
            "label": {"la": p["heading"] or "", "en": f"p. {p['page']}: {p['heading_en']}"},
            "region": {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
            "text": {
                "lang": "la", "original": p["original"].replace(" | ", "\n"), "expanded": p["expanded"],
                "translation": p["translation_en"], "commentary": "\n".join(comm),
                "source": [f"Read blind by Claude Opus 5.5 on {DATE} from the BNE pages shown here, then compared word by word with the project's transcription of another copy (Vienna); most differences were checked on this scan by the AI, not yet by a person."],
            },
        })
    for a in passages:
        if not a["label"].get("la"):
            a["label"].pop("la", None)
    annotations = [a for a in annotations if a["category"] != "placename"] + passages + [a for a in annotations if a["category"] == "placename"]

    n_blocks, n_places = len(blocks), len(places)
    out = {
        "_comment": "Generated by scripts/build_blaeu.py from map-test/output. Texts are the model's output (readers' boxes; place names are pins).",
        "id": ID,
        "title": {"la": "Tartaria sive Magni Chami Imperium", "en": "Tartary, or the Empire of the Great Khan"},
        "short": {"en": "Blaeu, Tartary, 1630s"},
        "creator": "Willem Janszoon Blaeu (1571–1638)",
        "date": "Amsterdam, 1630s (Blaeu's atlas)",
        "notice": f"Machine transcription and translation (Claude Opus 5.5, {DATE}), not yet reviewed by a specialist. [?] marks an uncertain reading. The text on the back was compared with the project's transcription of another copy; the texts on the map have not been checked yet.",
        "catalogue": {
            "repository": "Map: David Rumsey Map Collection. Text pages: Biblioteca Nacional de España",
            "reference": "From Willem Janszoon Blaeu's Latin atlas (Amsterdam). The map copy is catalogued as 1634; the text pages come from a later Latin edition in the BNE, catalogued as 1646",
            "extent": "Map, and the description “Tartaria” printed on the back (two pages)",
            "digitised": f"Map {MAP_W:,} × {MAP_H:,} px (David Rumsey Map Collection); text pages from the BNE's scan (Biblioteca Digital Hispánica)",
            "credit": "Map: David Rumsey Map Collection, David Rumsey Map Center, Stanford Libraries (CC BY-NC-SA) · Text pages: Biblioteca Nacional de España (CC BY)",
        },
        "description": "\n".join([
            "Willem Janszoon Blaeu's map of Tartary, from his Latin atlas of the 1630s. It runs from Muscovy and the Caspian to the China Sea, with a camel carrying the title, and notes on Gog and Magog, the Christian kingdom of Tenduc in Marco Polo's day, the tombs of the Tartar kings on Mount Alchai, Cambalu, the rhubarb of Tangut, the illusions of the desert of Lop and the Great Wall.",
            f"An AI model, Claude Opus 5.5, read the map from the David Rumsey Map Collection copy without any reference text: {n_blocks} texts, notes and names, which can be read in the panel and the tour, and {n_places} place names, shown under “Towns, rivers and lakes” in the filter.",
            "Turn the sheet over for the atlas's description of Tartary, read by the same model from the Biblioteca Nacional de España copy, in passages that follow its printed margin notes. It was compared with the project's transcription of another copy.",
        ]),
        "quiet": ["placename"],
        "categories": {"toponym": "Peoples, regions and seas", "inscription": "Note", "diagram": "Scale"},
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": MAP_TILES, "width": MAP_W, "height": MAP_H},
            {"id": "text", "label": {"en": "Text: two pages"}, "tileSource": f"tiles/{ID}-text.dzi", "width": TEXT_W, "height": TEXT_H},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{n_blocks} text blocks, {n_places} place names, {len(passages)} passages -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
