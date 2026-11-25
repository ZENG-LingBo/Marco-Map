"""Build a plain page for each map, a list of them, a sitemap and robots.txt.

Search engines drop everything after # in an address, so to them viewer.html is one page,
whichever map it shows. These pages give each map its own address, maps/<id>/, with its title,
mapmaker, date and library, and for the reading editions every text and its translation, as
plain HTML that search engines can read. Each page opens its map in the viewer.

    python scripts/build_pages.py

Reads demo/data/catalogue.json (the entries that have "page"), their map files and
demo/data/collection.json. Writes demo/maps/, demo/img/previews/, demo/sitemap.xml and
demo/robots.txt. Run it again whenever one of those data files changes.

Reading editions get a preview image cut from their own tiles in demo/tiles/; delete a preview
to make it again. Collection maps show the thumbnail the front page already uses: their rights
were still being checked when this was written (see HIDDEN in build_collection.py).
"""
import html
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

SITE = "https://mappingtartary.com/"
DEMO = Path(__file__).resolve().parent.parent / "demo"
PREVIEWS = DEMO / "img" / "previews"
PREVIEW_MAX = 1600  # px, longest side
COLLECTION_PREFIX = "tartary-"  # the viewer's address for collection maps, as in js/viewer.js

# as in js/viewer.js; a map file's own "categories" overrides these
CATEGORY = {
    "cartouche": "Cartouche", "inscription": "Inscription", "toponym": "Place name",
    "diagram": "Diagram", "colophon": "Colophon", "illustration": "Illustration",
    "cardinal": "Cardinal point", "passage": "Passage", "numeral": "Number",
    "placename": "Towns, rivers and lakes", "graticule": "Degree numbers",
}
# Library names that the collection's catalogue abbreviates. Only names that are certain;
# the others are shown as the catalogue gives them.
SOURCE_NAMES = {
    "BL": "British Library", "BNF": "Bibliothèque nationale de France",
    "BNE": "Biblioteca Nacional de España", "NYPL": "New York Public Library",
    "Rumsey": "David Rumsey Map Collection", "Newberry": "Newberry Library", "ERARA": "e-rara",
    "wikimedia": "Wikimedia Commons", "Ruderman": "Barry Lawrence Ruderman Antique Maps",
    "Rudermann": "Barry Lawrence Ruderman Antique Maps",
}
FONTS = ("https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;"
         "0,8..60,600;1,8..60,400&family=Noto+Serif+TC:wght@400;600&family=IBM+Plex+Sans:wght@400;500&display=swap")

esc = html.escape


def year_of(text):
    """The year for schema.org's dateCreated, only when the date is a single, certain year."""
    m = re.fullmatch(r"(?:.*\D)?(\d{4})", text.strip())
    return m[1] if m and not re.search(r"\bc\.|–|-|\?", text) else None


def first_sentences(text, limit=160):
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if out and len(out) + len(s) + 1 > limit:
            break
        out = (out + " " + s).strip()
    return out if len(out) <= limit else out[:limit - 1].rsplit(" ", 1)[0] + "…"


def head(title, description, path, image, depth, jsonld, image_size=None):
    up = "../" * depth
    url = SITE + path
    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        '<meta property="og:site_name" content="Mapping Tartary">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:image" content="{esc(SITE + image)}">',
    ]
    if image_size:
        tags += [f'<meta property="og:image:width" content="{image_size[0]}">',
                 f'<meta property="og:image:height" content="{image_size[1]}">']
    tags += [
        f'<meta name="twitter:card" content="{"summary_large_image" if image_size and image_size[0] >= 800 else "summary"}">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link href="{FONTS}" rel="stylesheet">',
        f'<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">',
        f'<link rel="stylesheet" href="{up}css/demo.css">',
        '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/") + "</script>",
    ]
    return "<head>\n  " + "\n  ".join(tags) + "\n</head>"


def page(title, description, path, image, depth, jsonld, body, image_size=None):
    return ("<!doctype html>\n<html lang=\"en\">\n" + head(title, description, path, image, depth, jsonld, image_size)
            + "\n<body>\n<div class=\"page map-page\">\n" + body + "\n" + footer(depth) + "\n</div>\n</body>\n</html>\n")


def crumbs(depth, here=None):
    up = "../" * depth
    parts = [f'<a href="{up}">Mapping Tartary</a>']
    if here:
        parts.append(f'<a href="{up}maps/">All maps</a>')
    return '<nav class="crumbs">' + " › ".join(parts) + "</nav>"


def footer(depth):
    up = "../" * depth
    return (f'<footer class="footer"><a href="{up}">Mapping Tartary</a> · <a href="{up}maps/">All maps</a> · '
            "HKUST · <a href=\"https://github.com/ZENG-LingBo/Marco-Map\">source and documentation on GitHub</a></footer>")


def website():
    return {"@type": "WebSite", "name": "Mapping Tartary", "url": SITE}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


# ---------- preview images ----------

def preview_from_dzi(dzi, out):
    """Stitch the smallest pyramid level at least PREVIEW_MAX wide or high, then scale it down."""
    root = ET.parse(dzi).getroot()
    ns = {"d": root.tag[1:].split("}")[0]} if root.tag.startswith("{") else {}
    size = root.find("d:Size", ns) if ns else root.find("Size")
    W, H = int(size.get("Width")), int(size.get("Height"))
    ts, overlap, fmt = int(root.get("TileSize")), int(root.get("Overlap")), root.get("Format")
    top = math.ceil(math.log2(max(W, H)))
    level = top
    while level > 0 and max(math.ceil(W / 2 ** (top - level + 1)), math.ceil(H / 2 ** (top - level + 1))) >= PREVIEW_MAX:
        level -= 1
    w, h = math.ceil(W / 2 ** (top - level)), math.ceil(H / 2 ** (top - level))
    canvas = Image.new("RGB", (w, h))
    folder = dzi.with_name(dzi.stem + "_files") / str(level)
    for c in range(math.ceil(w / ts)):
        for r in range(math.ceil(h / ts)):
            with Image.open(folder / f"{c}_{r}.{fmt}") as tile:
                canvas.paste(tile.convert("RGB"), (c * ts - (overlap if c else 0), r * ts - (overlap if r else 0)))
    canvas.thumbnail((PREVIEW_MAX, PREVIEW_MAX), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=80, optimize=True, progressive=True)


def preview(map_data):
    view = next(v for v in map_data["views"] if v["id"] == "map")
    out = PREVIEWS / f"{map_data['id']}.jpg"
    if not out.exists():
        preview_from_dzi(DEMO / view["tileSource"], out)
    with Image.open(out) as im:
        return f"img/previews/{out.name}", im.size


# ---------- reading editions ----------

def text_block(a, map_data):
    t = a["text"]
    lang = t.get("lang", "en")
    original = t.get("expanded") or t["original"]
    original_html = "<br>".join(esc(line) for line in original.split("\n"))
    label = a["label"].get("en") or next(iter(a["label"].values()))
    cats = {**CATEGORY, **(map_data.get("categories") or {})}
    viewer = f"../../viewer.html#map={map_data['id']}&amp;a={esc(a['id'])}"
    out = [f'<li id="{esc(a["id"])}">',
           f'<h3>{esc(label)} <span class="cat">{esc(cats.get(a["category"], a["category"]))}</span></h3>',
           f'<p class="original" lang="{esc(lang)}">{original_html}</p>']
    if t.get("translation") and t["translation"].strip() != original.strip():
        out.append(f'<p class="translation">{esc(t["translation"])}</p>')
    out.append(f'<a class="show" href="{viewer}">Show on the map</a></li>')
    return "\n".join(out)


def reading_page(entry):
    d = json.loads((DEMO / entry["file"]).read_text(encoding="utf-8"))
    mid = d["id"]
    path = f"maps/{mid}/"
    assert entry["page"] == path, (entry["page"], path)
    en = d["title"]["en"]
    orig_lang = next((l for l in ("la", "fr", "ru", "zh") if l in d["title"]), None)
    image, size = preview(d)
    english = all(a["text"].get("lang") == "en" for a in d["annotations"])
    what = "transcription" if english else "transcription and translation"
    title = f"{en} ({d['short']['en'].replace(', Tartary', '')}): {what} · Mapping Tartary"
    description = first_sentences(d["description"])
    quiet = set(d.get("quiet") or [])
    on_map = [a for a in d["annotations"] if a["view"] == "map" and a["category"] not in quiet]
    on_back = [a for a in d["annotations"] if a["view"] != "map"]
    places = [a for a in d["annotations"] if a["category"] == "placename"]
    back_label = next((v["label"]["en"] for v in d["views"] if v["id"] != "map" and v["id"] != "scan"), None)
    cat = d["catalogue"]

    jsonld = {"@context": "https://schema.org", "@type": "Map", "name": en, "url": SITE + path,
              "image": SITE + image, "description": d["description"], "isAccessibleForFree": True,
              "isPartOf": website()}
    if orig_lang:
        jsonld["alternateName"] = d["title"][orig_lang]
    if year_of(entry["date"]):
        jsonld["dateCreated"] = year_of(entry["date"])

    viewer = f"../../viewer.html#map={mid}"
    body = [crumbs(2, True), '<header class="masthead">', '<div class="kicker">Reading edition</div>', f"<h1>{esc(en)}</h1>"]
    if orig_lang:
        body.append(f'<p class="orig" lang="{orig_lang}">{esc(d["title"][orig_lang])}</p>')
    body += [f'<p class="meta">{esc(d["creator"])} · {esc(d["date"])}</p>', "</header>",
             f'<figure class="preview"><a href="{viewer}"><img src="../../{image}" width="{size[0]}" height="{size[1]}" '
             f'alt="{esc(en)}, {esc(d["creator"])}, {esc(d["date"])}"></a>'
             f'<figcaption>{esc(cat.get("credit", cat["repository"]))}</figcaption></figure>',
             f'<p class="links"><a class="btn primary" href="{viewer}">Explore the map in deep zoom</a></p>',
             f'<p class="notice">{esc(d["notice"])}</p>',
             '<h2 class="section-title">About this map</h2>', f"<p>{esc(d['description'])}</p>",
             '<dl class="facts">']
    for key, name in (("repository", "Copy"), ("reference", "Reference"), ("extent", "Extent"), ("digitised", "Image")):
        if cat.get(key):
            body.append(f"<dt>{name}</dt><dd>{esc(cat[key])}</dd>")
    if cat.get("url"):
        body.append(f'<dt>Source</dt><dd><a href="{esc(cat["url"])}">{esc(cat["url"])}</a></dd>')
    body.append("</dl>")
    body += [f'<h2 class="section-title">Texts on the map · {len(on_map)}</h2>', '<ol class="texts">']
    body += [text_block(a, d) for a in on_map]
    body.append("</ol>")
    if on_back:
        body += [f'<h2 class="section-title">{esc(back_label or "On the back")} · {len(on_back)}</h2>', '<ol class="texts">']
        body += [text_block(a, d) for a in on_back]
        body.append("</ol>")
    if places:
        body += [f'<h2 class="section-title">{esc(CATEGORY["placename"])} · {len(places)}</h2>',
                 '<table class="feature-table places"><thead><tr><th>On the map</th><th>Reading</th></tr></thead><tbody>']
        for a in places:
            t = a["text"]
            body.append(f'<tr id="{esc(a["id"])}"><td lang="{esc(t.get("lang", "en"))}">{esc(t.get("expanded") or t["original"]).replace(chr(10), " ")}</td>'
                        f'<td>{esc(t.get("translation", ""))}</td></tr>')
        body.append("</tbody></table>")
    return path, page(title, description, path, image, 2, jsonld, "\n".join(body), size)


# ---------- the collection ----------

def sources_text(m):
    return ", ".join(SOURCE_NAMES.get(s, s) for s in m["sources"])


def collection_title(m):
    return m["title"] or "Untitled map"


def names(people):
    return " and ".join([", ".join(people[:-1]), people[-1]]) if len(people) > 1 else "".join(people)


def collection_page(m, prev, nxt, total):
    mid = COLLECTION_PREFIX + str(m["n"])
    path = f"maps/{mid}/"
    name = collection_title(m)
    who = ", ".join(m["authors"])
    title = f"{name} ({who + ', ' if who else ''}{m['year']}) · Mapping Tartary"
    by = names(m["authors"])
    description = (f"{name}, {'a map by ' + by + ', ' if by else ''}{m['year']}, in deep zoom: one of {total} European "
                   "maps of Tartary in the TARTARY Project collection at HKUST.")
    image = m["thumb"]
    with Image.open(DEMO / image) as im:
        size = im.size
    jsonld = {"@context": "https://schema.org", "@type": "Map", "name": name, "url": SITE + path, "image": SITE + image,
              "isAccessibleForFree": True, "isPartOf": website()}
    if m["authors"]:
        jsonld["creator"] = [{"@type": "Person", "name": a} for a in m["authors"]]
    if year_of(m["year"]):
        jsonld["dateCreated"] = year_of(m["year"])
    viewer = f"../../viewer.html#map={mid}"
    body = [crumbs(2, True), '<header class="masthead">', f'<div class="kicker">The collection · {esc(m["year"])}</div>',
            f"<h1>{esc(name)}</h1>",
            f'<p class="meta">{esc(who) + " · " if who else ""}{esc(m["year"])}'
            f'{" · " + esc(sources_text(m)) if m["sources"] else ""}</p>', "</header>",
            f'<figure class="preview small"><a href="{viewer}"><img src="../../{image}" width="{size[0]}" height="{size[1]}" '
            f'alt="{esc(name)}{", " + esc(who) if who else ""}, {esc(m["year"])}"></a></figure>',
            f'<p class="links"><a class="btn primary" href="{viewer}">Explore the map in deep zoom</a></p>',
            f"<p>{esc(name)}{', by ' + esc(by) if by else ''}, {esc(m['year'])}."
            f"{' Image: ' + esc(sources_text(m)) + '.' if m['sources'] else ''} "
            f"One of the {total} maps of Tartary in the TARTARY Project's collection at HKUST, catalogued on "
            '<a href="https://tartary.vercel.app">tartary.vercel.app</a>. Its texts have not been transcribed yet.</p>',
            '<nav class="prevnext">']
    if prev:
        body.append(f'<a href="../{COLLECTION_PREFIX}{prev["n"]}/">‹ {esc(prev["year"])}: {esc(collection_title(prev))}</a>')
    if nxt:
        body.append(f'<a class="next" href="../{COLLECTION_PREFIX}{nxt["n"]}/">{esc(nxt["year"])}: {esc(collection_title(nxt))} ›</a>')
    body.append("</nav>")
    return path, page(title, description, path, image, 2, jsonld, "\n".join(body), size)


def index_page(readings, coll):
    total = len(coll["maps"])
    path = "maps/"
    title = "All maps of Tartary · Mapping Tartary"
    description = (f"Every map on Mapping Tartary: reading editions of {', '.join(r['short']['en'] for r in readings)}, "
                   f"and {total} European maps of Tartary from {coll['maps'][0]['year']} to {coll['maps'][-1]['year']}.")
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "All maps", "url": SITE + path,
              "isPartOf": website()}
    body = [crumbs(1), '<header class="masthead">', '<div class="kicker">Mapping Tartary</div>', "<h1>All maps</h1>",
            '<p class="lede">Each map has a page of its own, with its mapmaker, date and library. '
            "The reading editions also give every text on the map and its translation.</p>", "</header>",
            '<h2 class="section-title">Reading editions</h2>', '<ul class="map-list">']
    for r in readings:
        body.append(f'<li><a href="{r["id"]}/">{esc(r["title"]["en"])}</a> <span class="meta">{esc(r["creator"])} · {esc(r["date"])}</span></li>')
    body += ["</ul>", f'<h2 class="section-title">The collection · {total} maps, by year</h2>', '<ul class="map-list">']
    for m in coll["maps"]:
        who = f' <span class="meta">{esc(", ".join(m["authors"]))}</span>' if m["authors"] else ""
        body.append(f'<li><span class="year">{esc(m["year"])}</span> <a href="{COLLECTION_PREFIX}{m["n"]}/">{esc(collection_title(m))}</a>{who}</li>')
    body.append("</ul>")
    return path, page(title, description, path, "img/previews/ortelius-1570.jpg", 1, jsonld, "\n".join(body))


def main():
    catalogue = json.loads((DEMO / "data" / "catalogue.json").read_text(encoding="utf-8"))
    coll = json.loads((DEMO / "data" / "collection.json").read_text(encoding="utf-8"))
    readings = [m for m in catalogue["maps"] if m.get("page")]
    pages = []
    for entry in readings:
        pages.append(reading_page(entry))
    maps = coll["maps"]
    for i, m in enumerate(maps):
        pages.append(collection_page(m, maps[i - 1] if i else None, maps[i + 1] if i + 1 < len(maps) else None, len(maps)))
    pages.insert(0, index_page(readings, coll))

    for p, text in pages:
        write(DEMO / p / "index.html", text)
    built = {(DEMO / p).resolve() for p, _ in pages}
    for old in (DEMO / "maps").iterdir():  # the page of a map no longer listed
        if old.is_dir() and old.resolve() not in built and (old / "index.html").exists():
            (old / "index.html").unlink()
            if not any(old.iterdir()):
                old.rmdir()

    urls = [SITE] + [SITE + p for p, _ in pages]
    write(DEMO / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(DEMO / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")
    print(f"{len(pages)} pages ({len(readings)} reading editions, {len(maps)} collection maps, 1 list), "
          f"sitemap with {len(urls)} addresses")


if __name__ == "__main__":
    main()
