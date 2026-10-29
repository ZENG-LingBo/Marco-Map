"""Build demo/data/ortelius-1570.json from the transcription test's output.

    python scripts/build_ortelius.py ../map-test/output

The texts (diplomatic transcription, expanded Latin, English) are the model's output exactly
as scored in map-test/results.md; nothing here corrects them. This script only adds what the
viewer needs: a label, a category, a region on the scan and the tour order.

Regions are rectangles in pixels of Internet Archive's full-size images (4334 x 3354 map,
3317 x 5092 text page). The viewer shows the same images from tiles in demo/tiles, cut with
scripts/make_dzi.py, because Internet Archive's IIIF server is too slow to rely on in a talk. The model gave the centre of each text; the boxes around those
centres were drawn by eye on the scan and are approximate. Refine one with author mode (E).
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "demo" / "data" / "ortelius-1570.json"

# Map face, in tour order (west to east, then the labels that are not tour stops).
# id: (English label, category, (x, y, w, h), tour stop)
MAP = {
    "title_cartouche": ("Title", "cartouche", (2960, 580, 460, 460), True),
    "cartouche_bottom_left": ("What the map shows", "cartouche", (540, 2480, 545, 325), True),
    "hic_magnus_prouentus": ("Sweet flag by the Volga", "inscription", (685, 975, 250, 60), True),
    "mar_de_bachu": ("The Caspian Sea", "toponym", (485, 1275, 255, 175), False),
    "hic_rubini": ("Rubies", "inscription", (490, 1600, 110, 75), True),
    "samarchand": ("Samarkand", "inscription", (920, 1685, 150, 65), True),
    "turchestan": ("Turchestan and the Ten Tribes", "inscription", (895, 1340, 435, 120), True),
    "tartaria": ("Tartaria", "inscription", (925, 1115, 790, 155), True),
    "magnus_cham": ("The Great Khan", "inscription", (1340, 1660, 370, 145), True),
    "mons_althay": ("Mount Althay, burial place of the khans", "inscription", (1685, 1680, 360, 120), True),
    "tabor": ("Tabor, and a king who came to France", "inscription", (1560, 1350, 395, 235), True),
    "danorum_horda": ("Horde of the Danites", "inscription", (1785, 505, 245, 125), True),
    "nepthalitarum_horda": ("Horde of the Naphtalites", "inscription", (1840, 645, 525, 300), True),
    "insula_falconum": ("Island of falcons", "inscription", (1980, 990, 140, 75), True),
    "oceanus_scythicus": ("The Scythian Ocean", "inscription", (2050, 1150, 665, 160), True),
    "arsareth": ("Arsareth, where the Ten Tribes went", "inscription", (2150, 1620, 410, 130), True),
    "argon": ("Argon and Prester John", "inscription", (2150, 1770, 410, 185), True),
    "tangut": ("Tangut and printing", "inscription", (1550, 1985, 255, 85), True),
    "rhabarbarum": ("Rhubarb", "inscription", (1600, 2155, 135, 80), True),
    "cambalu": ("Cambalu (Beijing)", "inscription", (1785, 2115, 145, 85), True),
    "pons_marmoreus": ("A marble bridge", "inscription", (1955, 2165, 135, 65), True),
    "his_montibus_eruuntur": ("Stones burned for fuel", "inscription", (1820, 2610, 180, 125), True),
    "quinsai": ("Quinsai (Hangzhou)", "inscription", (2475, 1955, 150, 60), True),
    "japan_insula": ("Japan", "inscription", (3040, 2640, 345, 185), True),
    "meaco": ("Meaco (Kyoto)", "inscription", (3115, 2375, 110, 100), True),
    "minas_de_plata": ("Silver mines", "toponym", (3105, 2280, 100, 55), False),
    "americae_pars": ("Part of America", "toponym", (3150, 1310, 790, 345), True),
    "esdras_reference": ("4 Esdras 13", "inscription", (2435, 1565, 75, 55), False),
    "bargu": ("Bargu, a marshy region", "toponym", (1775, 1095, 135, 85), False),
    "imaus_mons": ("Mount Imaus", "toponym", (500, 1890, 640, 430), False),
    "solitudines_vastae": ("Vast wildernesses", "toponym", (1200, 1985, 275, 205), False),
    "volga_label": ("River Volga", "toponym", (640, 880, 55, 120), False),
    "tauris_label": ("Tauris (Tabriz)", "toponym", (380, 1495, 75, 55), False),
    "tabin_label": ("Cape Tabin", "toponym", (2390, 1495, 210, 40), False),
    "meon_label": ("River Meon", "toponym", (1712, 2775, 60, 145), False),
    "brior_label": ("River Brior", "toponym", (1420, 2800, 75, 195), False),
    "septentrio": ("North", "cardinal", (1930, 310, 420, 65), False),
    "occidens": ("West", "cardinal", (295, 1560, 65, 350), False),
    "oriens": ("East", "cardinal", (3905, 1515, 80, 235), False),
    "privilege": ("Privilege", "colophon", (345, 2930, 200, 45), False),
}

# Why some published readings were corrected before scoring (map-test/scripts/adjudicate.py).
PUBLISHED_ERRORS = {
    "arsareth": "the plate reads “4 Esd. Cap. 13” and “Tartarorum”, where the published text has “v.13” and “Tartatorum”",
    "danorum_horda": "the plate has “.i.” (id est, ‘that is’) where the published text has “1.”, and “Schyticum prom:” is a separate label",
    "magnus_cham": "the plate reads “lingua … Imperatorem”, where the published text has “linga … Imperator”",
}
# What the scoring showed about the model's own misses (map-test/results.md).
MISSES = {
    "nepthalitarum_horda": "This note runs across the binding fold of the bound atlas, so letters are hidden in every line. The model marked them [illegible] instead of guessing, and still misread a few letters beside the fold (“Enthalitas” for Euthalitas, “udcant” for vocant). A flat scan of a loose sheet would not have this problem.",
    "cambalu": "The model missed the word “Cataię”, engraved a little to the right beside the town symbol, so “Cambalu, metropolis of Cathay” became “Cambalu, the metropolis”.",
}

# Back of the sheet: passages split where a sentence starts, with the lines they cover.
# (marker in the original, marker in the English, English label, (x, y, w, h))
TEXT = [
    ("TARTARIA", "TARTARIA or", "Heading", (380, 530, 1580, 400)),
    ("QVI Tartaros", "Whoever would describe", "What Tartary is", (60, 1055, 2230, 1025)),
    ("In hordas", "They are divided into hordas", "Hordes, looks and food", (60, 1990, 2230, 940)),
    ("Et quoniam", "And since they wander", "Steering by the Pole Star", (60, 2830, 2230, 735)),
    ("Tartaros, eorum", "The Tartars, and their customs", "Further reading", (60, 3478, 2230, 1060)),
]
TEXT_NOTES = {
    "What Tartary is": "“Iaxartem (hodie Chesel)” is one of the readings by which orteliusmaps.com tells the three 1570 Latin issues apart; it places this copy in issue B.",
    "Further reading": "The last lines, “gligenda” above a centred “libro. 18. cap. 30.”, are the other mark of the 1570 Latin issue B, of which 100 copies were printed. The page number, 47, closes the page.",
}


def split(text, markers):
    cuts = [text.index(m) for m in markers] + [len(text)]
    return [text[a:b].strip(" |") for a, b in zip(cuts, cuts[1:])]


def incipit(text, n=46):
    return text if len(text) <= n + 2 else text[:n].rsplit(" ", 1)[0] + " …"


def lines(diplomatic):
    return diplomatic.replace(" | ", "\n")


def pct(x):
    return f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"


def map_commentary(block, row):
    parts = [f"The model's confidence in this reading: {block['confidence']}."]
    if block.get("note"):
        parts.append("Its note: " + block["note"])
    if row is None:
        parts.append("This text is not among the 21 in the published edition, so there was nothing to score it against.")
    else:
        if row["cer_norm"] == 0:
            parts.append("It matches the published Latin letter for letter, once spelling conventions (long s, u/v, i/j, abbreviation marks) are set aside.")
        else:
            parts.append(f"Against the published Latin, {pct(row['cer_norm'])} of characters differ once spelling conventions (long s, u/v, i/j, abbreviation marks) are set aside.")
        if block["id"] in PUBLISHED_ERRORS:
            parts.append(f"Part of that is an error in the published text, checked on the scan: {PUBLISHED_ERRORS[block['id']]}. Against the corrected text, {pct(row['cer_norm_adjudicated'])} differ.")
    if block["id"] in MISSES:
        parts.append(MISSES[block["id"]])
    return "\n".join(parts)


def main(out_dir):
    out_dir = Path(out_dir)
    face = json.loads((out_dir / "ortelius_map.json").read_text(encoding="utf-8"))
    back = json.loads((out_dir / "ortelius_verso.json").read_text(encoding="utf-8"))
    scores = json.loads((out_dir / "scores.json").read_text(encoding="utf-8"))
    rows = {r["agent_id"]: r for r in scores["ortelius_map_textblocks"]["rows"]}
    blocks = {b["id"]: b for b in face["textblocks"]}
    assert set(blocks) == set(MAP), set(blocks) ^ set(MAP)

    annotations = []
    for bid, (label, cat, (x, y, w, h), tour) in MAP.items():
        b = blocks[bid]
        cx, cy = map(int, re.search(r"\((\d+),\s*(\d+)\)", b["position"]).groups())
        assert x <= cx <= x + w and y <= cy <= y + h, f"{bid}: centre ({cx}, {cy}) outside its box"
        annotations.append({
            "id": bid.replace("_", "-"),
            "view": "map",
            "category": cat,
            "tour": tour,
            "label": {"la": incipit(b["expanded"]), "en": label},
            "region": {"x": x, "y": y, "w": w, "h": h},
            "text": {
                "lang": "la",
                "original": lines(b["original"]),
                "expanded": b["expanded"],
                "translation": b["translation_en"],
                "commentary": map_commentary(b, rows.get(bid)),
                "source": [
                    f"Read by Claude Opus 5.5 on 29 Oct 2026 from Internet Archive's scan of the Boston Public Library copy (image 207), crops {', '.join(b['crops'])}.",
                    "Published edition compared with: Marcel van den Broecke, orteliusmaps.com, Ort 163.",
                ],
            },
        })

    originals = split(back["original"], [t[0] for t in TEXT])
    expanded = split(back["expanded"], [t[0] for t in TEXT])
    english = split(back["translation_en"], [t[1] for t in TEXT])
    for i, ((_, _, label, (x, y, w, h)), o, e, t) in enumerate(zip(TEXT, originals, expanded, english), 1):
        notes = ["The model left no word on this page marked uncertain. Internet Archive's own OCR disagrees with this reading in 72 places; in every one, the scan supports this reading."]
        if label in TEXT_NOTES:
            notes.append(TEXT_NOTES[label])
        annotations.append({
            "id": f"text-{i}",
            "view": "text",
            "category": "passage",
            "tour": True,
            "label": {"la": incipit(e), "en": label},
            "region": {"x": x, "y": y, "w": w, "h": h},
            "text": {
                "lang": "la",
                "original": lines(o),
                "expanded": e,
                "translation": t,
                "commentary": "\n".join(notes),
                "source": [
                    "Read by Claude Opus 5.5 on 29 Oct 2026 from Internet Archive's scan of the Boston Public Library copy (image 205, p. 47), in five strips.",
                    "English of the 1570 text for comparison: orteliusmaps.com, Ort text 163.",
                ],
            },
        })

    m = scores["ortelius_map_textblocks"]
    out = {
        "_comment": "Generated by scripts/build_ortelius.py from map-test/output. Texts are the model's output as scored; regions are approximate.",
        "id": "ortelius-1570",
        "title": {"la": "Tartariae sive Magni Chami regni typus", "en": "Map of Tartary, or of the Kingdom of the Great Khan"},
        "short": {"en": "Ortelius, Tartary, 1570"},
        "creator": "Abraham Ortelius (1527–1598)",
        "date": "Antwerp, 1570",
        "notice": "Machine transcription and translation (Claude Opus 5.5, 29 Oct 2026), not yet reviewed by a specialist. [?] marks an uncertain reading, [illegible] letters the model could not see.",
        "catalogue": {
            "repository": "Boston Public Library, via Internet Archive",
            "reference": "Theatrum orbis terrarum (Antwerp: Coppenius Diesth, 1570); van den Broecke Ort 163",
            "extent": "Map on a double page, with its description printed on the back (p. 47)",
            "digitised": "Internet Archive, images 205 and 207: map 4,334 × 3,354 px, text page 3,317 × 5,092 px",
            "credit": "Boston Public Library, digitised by Internet Archive",
            "url": "https://archive.org/details/theatrumorbister00orte",
        },
        "description": "\n".join([
            "Abraham Ortelius's map of Tartary, from the first edition of his atlas, the Theatrum orbis terrarum (Antwerp, 1570). It runs from the Volga to Japan and the edge of America, and its 40 engraved texts cite Marco Polo, Pliny and Hayton the Armenian. Several place the lost Ten Tribes of Israel in northern Asia.",
            f"Each numbered pin opens one of those texts: the Latin as engraved, the abbreviations written out, and an English translation. All of it was read from the scan by an AI model, Claude Opus 5.5, then compared with Marcel van den Broecke's published edition at orteliusmaps.com. Overall, {pct(m['cer_norm_weighted_adjudicated_all'])} of characters differ once the published text's own errors are corrected, and {pct(m['cer_norm_weighted_adjudicated_excl_gutter'])} leaving out the one note hidden in the binding fold. The model also read 371 smaller place names; they are not pinned yet because their positions were not recorded.",
            "Turn the sheet over for Ortelius's description of Tartary, printed on the back. This is the Boston Public Library copy, of the 1570 Latin issue B. HKUST's own copy of the map is in the collection without annotations.",
        ]),
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": "tiles/ortelius-1570-map.dzi", "width": 4334, "height": 3354},
            {"id": "text", "label": {"en": "Back: description of Tartary"}, "tileSource": "tiles/ortelius-1570-text.dzi", "width": 3317, "height": 5092},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(annotations)} annotations -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
