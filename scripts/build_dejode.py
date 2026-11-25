"""Build demo/data/dejode-1593.json, the reading edition of Cornelis de Jode's China regnum (1593).

    python scripts/build_dejode.py ../map-test

Map face: the HKUST copy, read from the collection's own image (map 94 on tiles.mappingtartary.com,
12,925 x 9,618 px, the same pixels as Marco's "De Jode 1593.jpg"). Three agents (Claude Opus 5.5)
read it blind on 25 Nov 2026, one vertical strip each, from the 6 x 5 grid of crops in
map-test/crops/dejode_map/ (prompts as for Hondius, map-test/prompts.md). Their files are merged
here with the Hondius helpers. Where the project team has its own reading of a text (the side
panels, from "5r.docx"; the notes on the map, from "Map05_Internal text boxes"), it is shown in the
commentary beside the machine reading.

Back: "China quae et Sina", printed over pp. 53 and 55 of the Speculum orbis terrae, shown from the
pages Prof. Caboara printed from the BnF copy on 25 Nov 2026 (139 ppi). The text is the project
team's transcription and translation, made by a scholar Prof. Caboara engaged; he said on 25 Nov
that no personal credit is needed. It is split into passages with a box on the printed column
(map-test/output/dejode_back_passages.json).
"""
import json
import sys
from pathlib import Path

from build_hondius import close, merge, norm, same_text, label as hondius_label  # noqa: E402

DEMO = Path(__file__).resolve().parent.parent / "demo"
OUT = DEMO / "data" / "dejode-1593.json"
MAP_W, MAP_H = 12925, 9618
MAP_TILES = "https://tiles.mappingtartary.com/005_HKUST-(G7820-1593-.J64)-view.dzi"
TEXT_W, TEXT_H = 2364, 1529
STRIPS = ("west", "middle", "east")

# By the start of the text: the title, the four roundel captions and the signature in the side
# panels, and the compass words. Everything else is a note (five words or more) or a name.
FIXED = {
    "chinaregn": ("cartouche", "Title"),  # engraved REGNVM
    "inchinaauem": ("cartouche", "The fishing bird (roundel, top left)"),
    "hectamexmendo": ("colophon", "Sources: Mendoza and Maffei"),
    "iniaponiaidol": ("cartouche", "The three-headed idol of Japan (roundel, bottom left)"),
    "collectorecornelio": ("colophon", "Compiled by Cornelis de Jode of Antwerp"),
    "chinensesinmari": ("cartouche", "Living on boats, and the ducks (roundel, top right)"),
    "inchinacurrus": ("cartouche", "The sailing wagon (roundel, bottom right)"),
    "septentrio": ("cardinal", "North"), "meridies": ("cardinal", "South"),
    "oriens": ("cardinal", "East"), "occidens": ("cardinal", "West"),
}

# The team's own readings, matched on a piece of the machine reading (normalised).
TEAM = [
    ("inchinaauem", "In China avem habent mira dexteritate hero suo pisces venantem. Hec tam ex Mendoza qua(m) Maffei scriptis desumpta sunt.",
     "Chinese has a bird that fish for his owner with great ability. This information comes both from Mendoza's and Maffei's books."),
    ("hectamexmendo", "In China avem habent mira dexteritate hero suo pisces venantem. Hec tam ex Mendoza qua(m) Maffei scriptis desumpta sunt.",
     "Chinese has a bird that fish for his owner with great ability. This information comes both from Mendoza's and Maffei's books."),
    ("iniaponiaidol", "In Iaponia idolu(m) colunt triceps: neq(ue) animarum immortalitate(m) prorsus ignorant.",
     "In Japan people worship a three headed idol, and they do not ignore at all the immortality of the soul."),
    ("collectorecornelio", "Collectore Cornelio de Iudeis Antverp.", "Summarized by Cornelis de Jode from Antwerp."),
    ("chinensesinmari", "Chinenses in mari negociantur, hic ta(m)quam domi suæ hærent: familia(m) habent hic ad quam alenda(m) nihil hic deest. Singuli iuxta navim sua(m) anatu(m) alunt copiam.",
     "Chinese trade by sea like if they were at home: they live with their family and have all what they need for nourishing it. Each one of them raises a lot of ducks by the side of his own boat."),
    ("inchinacurrus", "In China currus excogitantur quorum fabrica adeo rara est, ut extensis velis, solo spirante vento quoquo velint vehe(n)di agitentur.",
     "In China was invented a wagon whose structure is so unusual that, after loosening the sails, they can be driven in any direction with the sole energy of the blowing wind."),
    ("anteannos", None, "313 years ago The Tartars invaded the Kingdom of China, but after 93 years of cruel domination the Chinese expelled them, having secretly appointed their own king. To prevent a second invasion the King erected a wall in the North, which is in some parts up to 80 miles long, with the remaining parts been protected by mountains"),
    ("patanietmogori", None, "The Pathan and the Moghuls are Scythes or Massagetes [=two nomadic population of Classical times], their capital is Samarkhand"),
    ("reperiturmoscus", None, "Here one can find the very valuable musk deer"),
    ("hicmurus500", None, "This wall runs for 500 miles, 7 orgyai [7 times 1.85 m] large, 14 tall, built between mountains, which constitute most of the barrier"),
    ("chinensesdocent", None, "The Chinese teach Music, Astronomy, Arithmetic etc. They play the cithara, the lyre and the flute and other instruments."),
    ("1165", None, "In the year 1165 AD this island of Japan obeyed to just one king, now it is subdivided into 60 kingdoms."),
    ("bramasincol", None, "The inhabitants of Bramas or Bracmanos are almost all black, they have plenty of gold and silver, and great abundance of rubies."),
    ("bracman", None, "The inhabitants of Bramas or Bracmanos are almost all black, they have plenty of gold and silver, and great abundance of rubies."),
    ("temperat", None, "The people are temperate and live long, they do not eat meat, as commanded by their religion. There are academies all over the country, such is their devotion to study. They cremate corpses as prescribed by their religion, and only collect and preserve the ashes."),
]


# Places where the team's English departs from the Latin (found while aligning the passages, 25 Nov 2026).
ENGLISH_NOTES = {
    "b02": "The team's English has “in less than two hundred years” where the Latin says “ante cc annos”, 200 years ago.",
    "b03": "The team's English leaves out “chinam radicem” (china root) from the list of products.",
    "b07": "The team's English has “different from” French and German ways where the Latin says “non absimilis”, not unlike.",
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


def team_for(b):
    n = norm(b["original"])
    return next(((la, en) for key, la, en in TEAM if key in n), None)


def box(b):
    x0, y0, x1, y1 = b["box"]
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


def main(test):
    test = Path(test)
    blocks, places = [], []
    for s in STRIPS:
        d = json.loads((test / "output" / f"dejode_map_{s}.json").read_text(encoding="utf-8"))
        blocks += d["textblocks"]
        places += d["placenames"]
    seams = test / "output" / "dejode_map_seams.json"
    if seams.exists():
        seam_data = json.loads(seams.read_text(encoding="utf-8"))
        places += seam_data.get("placenames", [])
        for s in seam_data["textblocks"]:
            blocks = [b for b in blocks if not any(norm(b["original"]).startswith(norm(r)) for r in s["replaces"])]
            blocks.append(dict(s, note=s["note"] + " Read across the seam between two readers' strips."))
    blocks = merge(blocks, "original", 500)
    # one or two letters with no name the readers could attach them to ("M" by Mongul, "an" above Focchieu)
    blocks = [b for b in blocks if len(norm(b["original"])) > 2]
    places = merge(places, "name", 250)
    places = [p for p in places if not any(close(p["centre"], b["centre"], 250) and same_text(p["name"], b["original"]) for b in blocks)]

    order = {"cartouche": 0, "colophon": 1, "inscription": 2, "cardinal": 4, "toponym": 3}
    blocks.sort(key=lambda b: (order[category(b)], b["centre"][0] // 3000, b["centre"][1]))
    annotations = []
    team_used = 0
    for k, b in enumerate(blocks):
        cat = category(b)
        f = fixed(b)
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        t = team_for(b)
        if t:
            team_used += 1
            if t[0]:
                notes.append("The project team's transcription: " + t[0])
            notes.append("The project team's translation: " + t[1])
        annotations.append({
            "id": f"m{k + 1:03d}", "view": "map", "category": cat, "tour": cat not in ("toponym", "cardinal"),
            "confidence": b["confidence"], "label": {"en": f[1] if f else hondius_label(b, cat)}, "region": box(b),
            "text": {
                "lang": "la", "original": b["original"].replace(" | ", "\n"), "expanded": b["expanded"],
                "translation": b["translation_en"], "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on 25 Nov 2026 from the HKUST copy, crops {', '.join(b['crops'])}."],
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
                "source": [f"Read by Claude Opus 5.5 on 25 Nov 2026 from the HKUST copy, crops {', '.join(p['crops'])}."],
            },
        })

    back = json.loads((test / "output" / "dejode_back_passages.json").read_text(encoding="utf-8"))
    differ = back.get("differences") or []
    t = back["title"]
    x0, y0, x1, y1 = t["box"]
    passages = [{
        "id": "b00", "view": "text", "category": "passage", "tour": True, "confidence": "high",
        "label": {"en": "p. 53: Title"}, "region": {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
        "text": {"lang": "la", "original": "CHINA QVAE ET SINA.", "translation": t["english"], "commentary": "",
                 "source": ["Transcription and translation by the TARTARY Project team."]},
    }]
    for p in back["passages"]:
        x0, y0, x1, y1 = p["box"]
        notes = [d for d in differ if d.get("passage") == p["id"]]
        comm = []
        if notes:
            comm.append("Where the printed page seems to differ from the team's transcription: " + "; ".join(
                f"the print has “{d['print']}” for “{d['team']}”" + ("" if d.get("certain") else " (uncertain at this resolution)") for d in notes) + ".")
        if p["id"] in ENGLISH_NOTES:
            comm.append(ENGLISH_NOTES[p["id"]])
        if p.get("note"):
            comm.append(p["note"])
        passages.append({
            "id": p["id"], "view": "text", "category": "passage", "tour": True, "confidence": "high",
            "label": {"en": f"p. {p['page']}: {p['heading_en']}"},
            "region": {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)},
            "text": {
                "lang": "la", "original": p["latin"], "translation": p["english"], "commentary": "\n".join(comm),
                "source": ["Transcription and translation by the TARTARY Project team (a scholar engaged by Prof. Caboara), not a machine reading. Boxes placed on the BnF pages by Claude Opus 5.5."],
            },
        })
    annotations = [a for a in annotations if a["category"] != "placename"] + passages + [a for a in annotations if a["category"] == "placename"]

    n_blocks, n_places = len(blocks), len(places)
    out = {
        "_comment": "Generated by scripts/build_dejode.py from map-test/output. Map texts are the model's output (readers' boxes; place names are pins); the back is the project team's text.",
        "id": "dejode-1593",
        "title": {"la": "China regnum", "en": "The Kingdom of China"},
        "short": {"en": "De Jode, China, 1593"},
        "creator": "Cornelis de Jode (1568–1600)",
        "date": "Antwerp, 1593 (Speculum orbis terrae)",
        "notice": "The texts on the map are a machine transcription (Claude Opus 5.5, 25 Nov 2026), not yet reviewed by a specialist; where the project team has its own reading, the commentary gives it. The text on the back is the team's transcription and translation. [?] marks an uncertain reading.",
        "catalogue": {
            "repository": "Map: HKUST Library. Text pages: Bibliothèque nationale de France",
            "reference": "From the second edition of the Speculum orbis terrae, published by Gerard de Jode's widow and son Cornelis (Antwerp, 1593); this map appears in no other edition",
            "extent": "Map, and the description “China quae et Sina” printed on pp. 53 and 55",
            "digitised": f"Map {MAP_W:,} × {MAP_H:,} px (HKUST); text pages printed from the BnF's scan (Gallica)",
            "credit": "Map: HKUST Library · Text pages: Source gallica.bnf.fr / BnF",
        },
        "description": "\n".join([
            "Cornelis de Jode's map of China, Tartary and Japan, signed by Cornelis and published in 1593 in the second edition of his father Gerard's atlas, the Speculum orbis terrae; it appears in no other edition. A round map sits in a decorated frame, with four roundels from Jesuit reports: a fishing bird, Chinese families living on boats with their ducks, a three-headed idol, and the Chinese sailing wagon.",
            f"An AI model, Claude Opus 5.5, read the map from the HKUST copy without any reference text: {n_blocks} texts, notes and names, which can be read in the panel and the tour, and {n_places} place names, shown under “Towns, rivers and lakes” in the filter. For {team_used} of the texts the commentary also gives the project team's own reading.",
            "Turn the sheet over for the atlas's description “China quae et Sina” (pp. 53 and 55), in the project team's transcription and translation, shown on the pages of the BnF copy.",
        ]),
        "quiet": ["placename"],
        "categories": {"toponym": "Peoples, regions and seas", "inscription": "Note", "cardinal": "Compass word", "colophon": "Signature and sources"},
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": MAP_TILES, "width": MAP_W, "height": MAP_H},
            {"id": "text", "label": {"en": "Text: pp. 53 and 55"}, "tileSource": "tiles/dejode-1593-text.dzi", "width": TEXT_W, "height": TEXT_H},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{n_blocks} text blocks ({team_used} with the team's reading), {n_places} place names, {len(passages)} passages -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
