"""Build demo/data/frru-1680.json, the French-Russian manuscript map, from the transcription test.

    python scripts/build_frru.py ../map-test/output
    python ../map-test/scripts/enhance_scan.py <Newberry TIFF> ../map-test/sources/frru/frru_enhanced.jpg
    python scripts/make_dzi.py ../map-test/sources/frru/frru_enhanced.jpg demo/tiles/frru-1680-map

Newberry Library, Ayer MS map 30, sheet 115: "Carte generale de la Siberie et de la Grande Tartarie",
1675-85, a French copy of a lost Russian map. Four agents read it by quadrant (map-test/prompts.md);
this merges their files, drops the few labels two of them reported on a shared edge, and joins the
sea name that runs along the top across two quadrants.

The texts are the model's output, unchanged. Text blocks (title, scale, notes, peoples and regions)
are pinned at their centres; the place names (towns, rivers, lakes) are pinned too but kept "quiet",
so the viewer shows them only when that category is chosen. Boxes are a default size round each
centre ("region_approx"). The map view is the scan after scripts/enhance_scan.py (CLAHE on
lightness); "As scanned" shows the Newberry image itself, from the TARTARY Project's tiles.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "demo" / "data" / "frru-1680.json"
W, H = 9061, 6772
# the TARTARY Project's tiles of the same scan, copied to project storage (scripts/mirror_tiles.py)
AS_SCANNED = "https://tiles.mappingtartary.com/991815158805867_ayer_ms_map_30_sheet_115-view.dzi"


def key(text):
    t = unicodedata.normalize("NFD", text.lower().replace("ſ", "s"))
    return re.sub(r"[^a-z0-9]", "", t)


def incipit(text, n=46):
    text = text.replace("\n", " ").replace(" | ", " ")
    return text if len(text) <= n + 2 else text[:n].rsplit(" ", 1)[0] + " …"


def box(centre, lines, maxlen, big=False):
    x, y = centre
    cw, lh = (90, 150) if big else (34, 60)
    w = min(2600, max(160, cw * maxlen))
    h = min(1200, lh * lines + 30)
    x0, y0 = max(0, int(x - w / 2)), max(0, int(y - h / 2))
    return {"x": x0, "y": y0, "w": min(int(w), W - x0), "h": min(int(h), H - y0)}


def part(q):
    return "the strips along the quadrant lines" if q == "seams" else f"quadrant {q}"


def block_category(b):
    o = b["original"]
    # letters actually read: the [illegible] and [?] markers are not part of the text
    letters = re.sub(r"[^A-Za-zÀ-ÿſ]", "", o.replace("[illegible]", "").replace("[?]", ""))
    if "CARTE GENERALE" in o.upper():
        return "cartouche", True
    if "Verstes" in o or "Echelle" in o:
        return "diagram", True
    if not letters and "[illegible]" not in o:
        return "graticule", False  # degrees in the border
    if (b.get("note") or "").lower().startswith("not part of the map") or "Ayer MS" in o:
        return None, False  # modern shelfmark
    if letters.isupper() and len(letters) > 3:
        return "toponym", True  # regions, peoples and seas in large letters
    if "[illegible]" in o and len(letters) < 4:
        return "inscription", False
    return "inscription", True


def main(test_output):
    test_output = Path(test_output)
    blocks, names = [], []
    for q in (1, 2, 3, 4, "seams"):
        d = json.loads((test_output / f"frru_map_q{q}.json" if q != "seams" else test_output / "frru_map_seams.json").read_text(encoding="utf-8"))
        for b in d["textblocks"]:
            b["q"], b["_block"] = q, True
            blocks.append(b)
        for n in d["placenames"]:
            n["q"], n["_block"] = q, False
            names.append(n)

    # The sea name runs along the whole top edge: quadrant 1 read "LA MER GLACIALLE ET DE SCYTHIE OV
    # BIEN D" and stopped at its edge, quadrant 2 read "OV BIEN DE TARTARIE". One label, centred on the
    # whole inscription (x about 190 to 7160, per the two agents' notes).
    west = next((b for b in blocks if "MER GLACIALLE" in b["original"]), None)
    east = next((b for b in blocks if b["original"].startswith("OV BIEN DE TARTARIE")), None)
    if west and east:
        west["original"] = west["original"].rsplit(" OV BIEN D", 1)[0] + " " + east["original"]
        west["expanded"] = west["expanded"].rsplit(" OU BIEN D", 1)[0] + " OU BIEN DE TARTARIE"
        west["translation_en"] = "The Icy Sea and [Sea] of Scythia, or else of Tartary [the Arctic Ocean]"
        west["centre"] = [3675, 400]
        west["crops"] = sorted(set(west.get("crops", []) + east.get("crops", [])))
        west["note"] = "Joined from two readings: quadrant 1 read the western part, quadrant 2 the eastern part (\"OV BIEN DE TARTARIE\")."
        blocks.remove(east)

    def text_of(it):
        return it.get("original") or it.get("name") or ""

    def clean(it):
        return key(text_of(it).replace("[illegible]", "").replace("[?]", "").replace("…", ""))

    def dist2(a, b):
        return (a["centre"][0] - b["centre"][0]) ** 2 + (a["centre"][1] - b["centre"][1]) ** 2

    def ratio(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

    # One label read twice: by two quadrants near their shared edge (sometimes spelt a little
    # differently), or as a name the agent also listed inside a longer note. The same letters within
    # 400 px, or one reading containing the other or nearly equal to it within 150 px. Keep the text
    # block first, then the more confident reading, then the longer one.
    conf = {"high": 0, "medium": 1, "low": 2}
    quad = [it for it in blocks + names if it["q"] != "seams"]
    quad.sort(key=lambda it: (0 if it["_block"] else 1, conf.get(it["confidence"], 1), -len(text_of(it))))
    kept = []
    for it in quad:
        k = clean(it)
        if not any((k == clean(o) and dist2(o, it) < 400 ** 2) or
                   (dist2(o, it) < 150 ** 2 and k and clean(o) and (k in clean(o) or clean(o) in k or ratio(k, clean(o)) >= 0.75))
                   for o in kept):
            kept.append(it)

    # The seam strips re-read the labels on the quadrant lines independently. Pair each strip reading
    # with its nearest quadrant reading; where they differ, the commentary says so (a reviewer should
    # look there). Strip readings cut by the strip edge ("[illegible]...", "...") are not compared.
    def legible(it):
        return bool(re.search(r"[A-Za-zſ]{3}", text_of(it).replace("[illegible]", "")))
    seam = [it for it in blocks + names if it["q"] == "seams" and legible(it)
            and "…" not in text_of(it) and "[illegible]" not in text_of(it)]
    best = {}
    for sr in seam:
        cands = [o for o in kept if dist2(o, sr) < 250 ** 2 and ratio(clean(o), clean(sr)) >= 0.5]
        if cands:
            o = min(cands, key=lambda o: dist2(o, sr))
            if id(o) not in best or dist2(o, sr) < best[id(o)][1]:
                best[id(o)] = (sr, dist2(o, sr), o)
    for sr, _, o in best.values():
        ks, ko = clean(sr), clean(o)
        if ks == ko:
            o["second"] = "A second, independent reading of this label agrees."
        elif not (ks in ko or ko in ks):  # one of the two saw only part of the label
            o["second"] = f"A second, independent reading gives “{text_of(sr).replace(' | ', ' / ')}”: worth checking on the scan."
    gaps = [sr for sr in seam if not any(dist2(o, sr) < 160 ** 2 or (dist2(o, sr) < 700 ** 2 and (
        clean(sr) in clean(o) or clean(o) in clean(sr) or ratio(clean(sr), clean(o)) > 0.6)) for o in kept)]
    print(f"{len(quad) - len(kept)} double readings merged; the strips add {len(gaps)}: " + "; ".join(text_of(g) for g in gaps))
    blocks = [it for it in kept + gaps if it["_block"]]
    names = [it for it in kept + gaps if not it["_block"]]

    annotations = []
    for i, b in enumerate(sorted(blocks, key=lambda b: (b["centre"][1] // 1200, b["centre"][0]))):
        cat, tour = block_category(b)
        if cat is None:
            continue
        lines = b["original"].split(" | ")
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        if b.get("second"):
            notes.append(b["second"])
        annotations.append({
            "id": f"b{i:03d}", "view": "map", "category": cat, "tour": tour, "confidence": b["confidence"],
            "label": {"fr": incipit(b["expanded"] or b["original"]), "en": incipit(b["translation_en"]) or "Illegible"},
            "region": box(b["centre"], len(lines), max(len(l) for l in lines), big=cat == "toponym"),
            "region_approx": True,
            "text": {
                "lang": "fr", "original": b["original"].replace(" | ", "\n"), "expanded": b["expanded"],
                "translation": b["translation_en"], "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on 2 Nov 2026 from crops {', '.join(b.get('crops') or [])} of the Newberry scan (after contrast adjustment), {part(b['q'])}."],
            },
        })
    for i, n in enumerate(sorted(names, key=lambda n: (n["centre"][1] // 1200, n["centre"][0]))):
        kind = n.get("kind") or "other"
        notes = [f"{kind.capitalize()}. The model's confidence in this reading: {n['confidence']}."]
        if n.get("note"):
            notes.append("Its note: " + n["note"])
        if n.get("second"):
            notes.append(n["second"])
        annotations.append({
            "id": f"n{i:03d}", "view": "map", "category": "placename", "tour": False, "confidence": n["confidence"],
            "label": {"fr": n["name"], "en": n.get("english") or n["name"]},
            "region": box(n["centre"], 1, len(n["name"])), "region_approx": True,
            "text": {
                "lang": "fr", "original": n["name"], "translation": n.get("english") or "",
                "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on 2 Nov 2026 from crops {', '.join(n.get('crops') or [])}, {part(n['q'])}."],
            },
        })

    agree = sum(1 for a in annotations if "agrees." in a["text"]["commentary"])
    differ = sum(1 for a in annotations if "worth checking" in a["text"]["commentary"])
    twice = agree + differ
    nb = sum(1 for a in annotations if a["category"] not in ("placename", "graticule"))
    nn = sum(1 for a in annotations if a["category"] == "placename")
    out = {
        "_comment": "Generated by scripts/build_frru.py from map-test/output (frru_map_q1-4). Texts are the model's output; boxes are approximate.",
        "id": "frru-1680",
        "title": {"fr": "Carte generale de la Siberie et de la Grande Tartarie",
                  "en": "General map of Siberia and Great Tartary"},
        "short": {"en": "French-Russian map of Siberia, 1675–85"},
        "creator": "Unknown French copyist, after a lost Russian map",
        "date": "c. 1675–1685",
        "quiet": ["placename", "graticule"],
        "categories": {"toponym": "Peoples, regions and seas", "inscription": "Note", "diagram": "Scale"},
        "notice": "Machine transcription and translation (Claude Opus 5.5, 2 Nov 2026), not yet reviewed by a specialist. [?] marks an uncertain reading, [illegible] what could not be read. Towns, rivers and lakes are listed under that category in the filter.",
        "catalogue": {
            "repository": "Newberry Library, Chicago: Ayer MS map 30, sheet 115 (Cartes Marines collection)",
            "reference": "Pen-and-ink and watercolour on cloth, 511 × 710 mm; cf. Postnikov",
            "digitised": "Newberry Library, 9,061 × 6,772 px; contrast adjusted for reading",
            "credit": "Newberry Library, Chicago (no copyright, Newberry open access)",
            "url": "https://collections.newberry.org/asset-management/2KXJ8ZSANZV_H",
        },
        "description": "\n".join([
            "A French manuscript copy of a lost Russian map of Siberia, probably compiled between 1675 and 1685, from the Cartes Marines collection of French colonial maps. Its full title promises “all the rivers, towns and streams, and the dwellings of the Tartars and Kalmyks”: the Russian names are written in French spelling, and tents mark the nomadic peoples, from the Yakuts and Tungus to the Kalmyks, Bashkirs and Mongols, down to the Great Wall and Peking.",
            f"Every text on it was read from the scan by an AI model, Claude Opus 5.5, working in four parts: {nb} titles, notes and names of peoples and regions, pinned on the map, and {nn} towns, rivers and lakes, shown when you choose them in the filter. No published transcription exists, so the readings are the model's, with its own confidence for each. The labels along the lines between the four parts were read a second time, independently: {agree} of {twice} agree letter for letter, and the {differ} that differ, almost all small river names, are flagged in their commentary as worth checking.",
            "The scan is faded, so the map view has its contrast adjusted to bring out pale ink; “As scanned” shows the Newberry image itself.",
        ]),
        "views": [
            {"id": "map", "label": {"en": "Map (contrast adjusted)"}, "tileSource": "tiles/frru-1680-map.dzi", "width": W, "height": H},
            {"id": "scan", "label": {"en": "As scanned"}, "tileSource": AS_SCANNED, "width": W, "height": H},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{nb} text blocks, {nn} place names -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
