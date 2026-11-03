"""Build demo/data/speed-1626.json from the transcription test's output.

    python scripts/build_speed.py ../map-test/output
    python scripts/make_dzi.py ../map-test/sources/speed1626/bnf_1of2.jpg demo/tiles/speed-1626-map
    python scripts/make_dzi.py ../map-test/sources/speed1626/bnf_2of2.jpg demo/tiles/speed-1626-text

The texts are the model's output exactly as checked in map-test/results.md; this script only adds
labels, categories, the tour, and boxes on the scans (the BnF copy on Wikimedia Commons, map
6351 x 4962 px, text 6387 x 5030 px).

Map face: the model gave the centre of each text block, all checked by eye on the scan; the boxes
round those centres are a default size from the length of the text, marked "region_approx" (the
viewer shows a pin at the centre, review mode asks for the box to be redrawn).
Back of the sheet: one passage per numbered paragraph. The four columns are read 3, 4 (p. 39), 1, 2
(p. 40); a paragraph's box is the column holding most of it, from its first to its last line,
placed by spacing the column's lines evenly between its first and last printed line.
"""
import json
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "demo" / "data" / "speed-1626.json"
MAP_W, MAP_H = 6351, 4962

# id: (English label or None for the start of the text, category, tour stop)
MAP = {
    "T01": ("Title", "cartouche", True),
    "T02": ("Imprint: Speed, George Humble, 1626", "colophon", True),
    "T03": ("Engraver: Dirck Grijp", "colophon", False),
    "T04": ("Scale", "diagram", False),
    "T05": ("Town view: Astrakhan", "illustration", True),
    "T06": ("Town view: Samarkand", "illustration", False),
    "T07": ("Town view: Cambalu", "illustration", False),
    "T08": ("Town view: the house on Nova Zembla", "illustration", True),
    "T09": ("Costume: a Samoyed man", "illustration", True),
    "T10": ("Costume: Tartar gentlewoman", "illustration", False),
    "T11": ("Costume: a Tartar", "illustration", False),
    "T12": ("Costume: Tartar country woman", "illustration", False),
    "T13": ("Costume: Samoyed woman", "illustration", False),
    "T14": ("Costume: Tartar gentleman", "illustration", False),
    "T15": ("Costume: Tartar woman", "illustration", False),
    "T16": ("Costume: Tartar country man", "illustration", False),
    "T17": ("Nova Zembla and the Dutch voyages", "inscription", True),
    "T18": ("Martsin af Isle", "inscription", False),
    "T19": ("The White Sea", "inscription", False),
    "T20": ("Biatlaozara, the Muscovite treasure castle", "inscription", True),
    "T21": ("The Don, between Asia and Europe", "inscription", True),
    "T22": ("Astrakhan", "inscription", True),
    "T23": ("The Caspian Sea", "inscription", True),
    "T24": ("Pliny's people who live on the smell of meat", "inscription", True),
    "T25": ("Grustina, where Tartars and Russians trade", "inscription", True),
    "T26": ("The Kalmyks (a note in Latin)", "inscription", True),
    "T27": ("Niaren More, the still sea", "inscription", False),
    "T28": ("The island Tazata, after Pliny", "inscription", False),
    "T29": ("Annibi, after Carpini", "inscription", False),
    "T30": ("Voices in the desert of Lop", "inscription", True),
    "T31": ("Cara Kithay, Black Cathay", "inscription", True),
    "T32": ("The Stone Tower", "inscription", True),
    "T33": ("Ung, or Gog", "inscription", True),
    "T34": ("Sumongul, Mercator's Magog", "inscription", True),
    "T35": ("Tenduc, a Christian kingdom", "inscription", True),
    "T36": ("Mount Altai, burial place of the kings", "inscription", True),
    "T37": ("A castle against the Tartars", "inscription", False),
    "T38": ("Campion", "inscription", False),
    "T39": ("Asbestos: earth that will not burn", "inscription", True),
    "T40": ("The Great Wall", "inscription", True),
    "T41": ("Quinsay, the town of heaven", "inscription", True),
    "T42": ("The middle meridian", "inscription", False),
    "T43": ("Degrees round the border", "diagram", False),
}
# checked word for word against the full-resolution scan (map-test/results.md)
CHECKED_MAP = {"T17", "T30", "T39"}

PARAGRAPHS = [
    "The Scythians, oldest of nations", "The Magogins", "The barbarous nations by the Maeotis",
    "“The workshop of mankind”", "Goths, Getae and a curse of tyranny", "The lost Ten Tribes",
    "What the Tartars look like", "Hordes and tents", "Religion", "Chinggis, their first king",
    "The limits of Tartary and its five provinces", "Tartaria minor: the Crimea", "Asiatica, or desert Tartary",
    "Tartaria antiqua, the land of Magog", "Zagathai: Samarkand and Bactria", "Cathay and the Great Khan",
]
# columns in reading order: first and last line of each in the diplomatic text (found from the
# column joins the model reported), the text's x range and the y of its first and last line
# (y of the first and last printed line measured on the scan; the page-40 running head is its own
# entry so that it does not stretch column 1)
COLUMNS = [
    ("col3, p. 39", "SCYTHARVM", 3302, 4822, 1347, 4595),
    ("col4, p. 39", "Doubtle", 4700, 6291, 1351, 4630),
    ("running head, p. 40", "40 THE DESCRIPTION", 332, 3117, 176, 176),
    ("col1, p. 40", "ſettled himſelfe", 332, 1673, 345, 4294),
    ("col2, p. 40", "their rich Metropolis", 1712, 3117, 335, 4258),
]


def incipit(text, n=46):
    text = text.replace("\n", " ")
    return text if len(text) <= n + 2 else text[:n].rsplit(" ", 1)[0] + " …"


def approx_box(block):
    x, y = block["position"]["x"], block["position"]["y"]
    lines = block["original"].split(" | ")
    w = min(1500, max(140, 21 * max(len(l) for l in lines)))
    h = min(900, 46 * len(lines) + 24)
    x0, y0 = max(0, x - w // 2), max(0, y - h // 2)
    return {"x": x0, "y": y0, "w": min(w, MAP_W - x0), "h": min(h, MAP_H - y0)}


def split_paragraphs(text, sep):
    cuts, at = [0], 0
    for k in range(2, 17):
        at = text.index(sep.format(k), at)
        cuts.append(at)
        at += 3
    cuts.append(len(text))
    return [text[a:b].strip(" |") for a, b in zip(cuts, cuts[1:])]


def main(test_output):
    test_output = Path(test_output)
    face = json.loads((test_output / "speed_map.json").read_text(encoding="utf-8"))
    back = json.loads((test_output / "speed_verso.json").read_text(encoding="utf-8"))
    blocks = {b["id"]: b for b in face["textblocks"]}
    assert set(blocks) == set(MAP), set(blocks) ^ set(MAP)

    annotations = []
    for bid, (label, cat, tour) in MAP.items():
        b = blocks[bid]
        notes = [f"The model's confidence in this reading: {b['confidence']}."]
        if b.get("note"):
            notes.append("Its note: " + b["note"])
        if bid in CHECKED_MAP:
            notes.append("Checked word for word against the scan on 29 Oct 2026: it matches, including the engraver's slips, which the model kept and flagged.")
        annotations.append({
            "id": bid.lower(), "view": "map", "category": cat, "tour": tour, "confidence": b["confidence"],
            "label": {"en": label},
            "region": approx_box(b), "region_approx": True,
            "text": {
                "lang": "la" if b.get("language") == "Latin" else "en",
                "original": b["original"].replace(" | ", "\n"),
                "expanded": b["expanded"],
                "translation": b["translation_en"],
                "commentary": "\n".join(notes),
                "source": [f"Read by Claude Opus 5.5 on 29 Oct 2026 from the BnF copy (Wikimedia Commons, sheet 1 of 2), crops {', '.join(b['crops'])}."],
            },
        })

    lines = back["original"].split(" | ")
    starts = [next(i for i, l in enumerate(lines) if l.startswith(c[1])) for c in COLUMNS] + [len(lines)]

    def place(i):  # (column index, y) of line i
        c = max(k for k in range(len(COLUMNS)) if starts[k] <= i)
        first, last = starts[c], starts[c + 1] - 1
        y0, y1 = COLUMNS[c][4], COLUMNS[c][5]
        return c, y0 + (i - first) * (y1 - y0) / max(1, last - first)

    para_line = [0] + [next(i for i, l in enumerate(lines) if l.startswith(f"({k}) ")) for k in range(2, 17)] + [len(lines)]
    originals = split_paragraphs(back["original"], " | ({}) ")
    expanded = split_paragraphs(back["expanded"], "({}) ")
    english = split_paragraphs(back["translation_en"], "({}) ")
    uncertain = back.get("uncertain") or []
    for k in range(16):
        span = range(para_line[k], para_line[k + 1])
        by_col = {}
        for i in span:
            c, y = place(i)
            by_col.setdefault(c, []).append(y)
        c = max(by_col, key=lambda c: len(by_col[c]))
        ys = by_col[c]
        name, _, x0, x1, *_ = COLUMNS[c]
        notes = []
        flagged = [u["text"] for u in uncertain if re.search(rf"para \({k + 1}\)", u.get("where", ""))]
        if flagged:
            notes.append("Marked uncertain or illegible here by the model: " + "; ".join(flagged) + ".")
        if len(by_col) > 1:
            notes.append(f"The paragraph runs on into the next column; the box shows the part in {name}.")
        annotations.append({
            "id": f"text-{k + 1}", "view": "text", "category": "passage", "tour": True, "confidence": "high",
            "label": {"en": PARAGRAPHS[k]},
            "region": {"x": x0, "y": int(min(ys) - 30), "w": x1 - x0, "h": int(max(ys) - min(ys) + 90)},
            "text": {
                "lang": "en",
                "original": originals[k].replace(" | ", "\n"),
                "expanded": expanded[k],
                "translation": english[k],
                "commentary": "\n".join(notes),
                "source": ["Read by Claude Opus 5.5 on 29 Oct 2026 from the BnF copy (Wikimedia Commons, sheet 2 of 2), column by column in reading order."],
            },
        })

    out = {
        "_comment": "Generated by scripts/build_speed.py from map-test/output. Texts are the model's output as checked; map boxes are approximate.",
        "id": "speed-1626",
        "title": {"en": "A Newe Mape of Tartary"},
        "short": {"en": "Speed, Tartary, 1626"},
        "creator": "John Speed (1552–1629); engraved by Dirck Grijp",
        "date": "London: George Humble, 1626",
        "notice": "Machine transcription (Claude Opus 5.5, 29 Oct 2026), not yet reviewed by a specialist. The text is English: “Modern spelling” gives the same words in today's spelling. [?] marks an uncertain reading, [illegible] text hidden by stains.",
        "catalogue": {
            "repository": "Bibliothèque nationale de France, Ge D 22030, via Wikimedia Commons",
            "reference": "From Speed's world atlas, A Prospect of the Most Famous Parts of the World",
            "extent": "Map on one side, the description of Tartary on the other (pp. 39–40)",
            "digitised": "Map 6,351 × 4,962 px, text 6,387 × 5,030 px",
            "credit": "Bibliothèque nationale de France (gallica.bnf.fr), via Wikimedia Commons",
            "url": "https://commons.wikimedia.org/wiki/File:A_newe_mape_of_Tartary_-_augmented_by_John_Speed..._;_Gryp_sculp._-_btv1b53061592x_(1_of_2).jpg",
        },
        "description": "\n".join([
            "John Speed's map of Tartary, dated 1626 on the plate and sold by George Humble in London. Four town views run along the top (Astrakhan, Samarkand, Cambalu and the house the Dutch built on Nova Zembla), eight costume figures stand down the sides, and 26 notes on the map range from the Dutch voyages to the Great Wall, Pliny's people who live on smells, and asbestos.",
            "Every text on it was read from the scan by an AI model, Claude Opus 5.5, as engraved and in modern spelling. Three of the longest notes were checked word for word against the scan and match, including the engraver's own slips, which the model kept and flagged. The model also read 411 smaller place names; they are not pinned yet.",
            "Turn the sheet over for Speed's “Description of the Kingdome of Tartary” (pp. 39–40), 3,236 words in 16 paragraphs. Twenty lines checked against the scan had no errors; a brown stain hides a few words in paragraphs 3 and 8.",
        ]),
        "views": [
            {"id": "map", "label": {"en": "Map"}, "tileSource": "tiles/speed-1626-map.dzi", "width": MAP_W, "height": MAP_H},
            {"id": "text", "label": {"en": "Back: description of Tartary"}, "tileSource": "tiles/speed-1626-text.dzi", "width": 6387, "height": 5030},
        ],
        "annotations": annotations,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(annotations)} annotations -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
