# 02 · Feature exploration: what the reference sites do, and what the demo does

**Audience:** Ling Bo, and anyone who will build on the demo. Open the demo from the [README](../README.md).

## 1. The four sites Prof. Caboara sent, as they actually work

The pages were fetched and read; what follows is what is in their HTML, not what their descriptions say.

### leventhalmap.org — *A Qing Dynasty Imperial Route Map* ("Map Chat", 2022)
Hand-written HTML by MacLean Collection interns. The six-metre accordion map is five PNG strips laid side by side inside a horizontally scrolling `<div id="world">`, and an SVG the same width sits on top:

```html
<svg id="svgMap" viewBox="0 0 7224.1 272">
  <path onclick="pointContent('old-summer-palace')" class="pointsvg" data-name="The Old Summer Palace" d="M53.1,142.1 …"/>
  …
</svg>
<div onclick="pointContent('old-summer-palace')" class="informationPoints" id="old-summer-palace">
  <div id="title-font">The Old Summer Palace<br>M. Iuwan Ming Yuan<br>C. Yuanmingyuan 圆明园</div>
  <hr> Although not a part of Qianlong's journey, the mapmakers included …
  <span class="close-icon">✕</span>
</div>
```
Each dot toggles a popup with a **trilingual heading (English / Manchu romanisation / Chinese)** and a short note. No zoom, no library, no data file: every annotation is hand-coded HTML. Thirty-two of 230 toponyms are annotated.

### leventhalmap.org — *Qing Dynasty Route* article
An essay page that links to the interactive above. Nothing interactive itself.

### leventhalmap.org — *Remapping the World in Japan* (2022)
Scrollytelling. Left column: narrative `<section>`s. Right column: fourteen pre-cropped detail JPEGs stacked on top of each other; an `IntersectionObserver` in `js/observer.js` toggles an `appear` class (opacity) on the image matching the section in view. Clicking an inline image opens a full-size modal. Bootstrap for layout, otherwise plain HTML. Every "zoom" is a separately exported crop.

### oculi-mundi.com — *Cao Junyi's 1644 world map* essay and tour
A Next.js site with content in the Sanity CMS. Essays embed detail crops from Sanity's image CDN. The collection page and the "tour" page embed **Micrio**, a commercial deep-zoom platform; the page data carries `hasMicrioMarkers`, `hasMicrioTours` and a `micrioTour` id, so markers and guided tours are authored in Micrio's dashboard. This is the "buy" version of what the Leventhal pages hand-build.

### What Prof. Caboara is therefore asking for
1. A map you can zoom into as far as the scan allows (Oculi Mundi).
2. Clickable places on the map that show the **original text, a translation and a commentary** (Leventhal).
3. A way to show **the back of the map** and other text that is not on the front (new).
4. A narrative or guided tour mode (both).

## 2. What the demo implements

| Feature | Page | Mechanism | Answers |
|---|---|---|---|
| Deep zoom on the library's IIIF tiles | viewer, story | OpenSeadragon 6.1 with an `info.json` tile source; nothing hosted by us | Oculi Mundi |
| Numbered pins + region outlines | viewer | OpenSeadragon overlays positioned from pixel rectangles in the JSON | Leventhal SVG dots |
| Reading panel: 原文 / Translation / Commentary / Source, vertical Chinese toggle | viewer | rendered from `annotations[].text` | Leventhal popups |
| Index with category filter, numbers matching pins | viewer | `annotations[].category` | new |
| Front / back (or left / right half) switch | viewer, story | `views[]`: each view has its own tile source; annotations point at a view; selecting an annotation on the other side switches the view first | new (verso text) |
| Guided tour: Prev / Next / Play | viewer | walks `annotations[]` in order, 7 s per stop | Oculi Mundi tours |
| Translated labels drawn on the map, opacity slider | viewer | a second overlay per annotation | new |
| Deep links `#map=…&view=…&a=…` and viewport `v=x,y,zoom` | viewer | `history.replaceState`; hash change opens the annotation | new |
| Author mode (`E`): drag a rectangle → region JSON on the clipboard | viewer | `OpenSeadragon.MouseTracker` on the canvas; converts viewport to image pixels | new |
| Narrative: scrolling flies the map, switches sides, highlights the region | story | `IntersectionObserver` on `<section>`s; sections generated from `story.sections` | Leventhal "Remapping" |
| Catalogue front page | index | rendered from `catalogue.json` | Oculi Mundi collection |

Two maps are included so that both cases are real: the **Ricci 1602** map (Chinese inscriptions; the two LoC halves act as switchable views) and **Miller Atlas folio 4** (a vellum sheet with a genuine recto and verso, Latin cartouches on both).

## 3. The data model (one JSON file per map)

```jsonc
{
  "id": "ricci-1602",
  "title": { "zh": "坤輿萬國全圖", "en": "Complete Map of the Myriad Countries of the World" },
  "catalogue": { "repository": "…", "reference": "…", "extent": "…", "credit": "…", "url": "…" },
  "description": "…",
  "views": [
    { "id": "right", "label": { "zh": "右半", "en": "Right half" }, "tileSource": "https://…/info.json", "width": 22499, "height": 20335 },
    { "id": "left",  "label": { "zh": "左半", "en": "Left half" },  "tileSource": "https://…/info.json", "width": 22678, "height": 20538 }
  ],
  "annotations": [
    { "id": "title", "view": "right", "category": "cartouche",
      "label": { "zh": "坤輿萬國全圖", "en": "Title" },
      "region": { "x": 20480, "y": 300, "w": 1880, "h": 1120 },        // image pixels
      "text": { "lang": "zh", "original": "…", "translation": "…", "commentary": "…", "source": ["…"] } }
  ],
  "story": { "title": {…}, "byline": "…", "sections": [ { "annotation": "title", "heading": {…}, "body": ["…"] } ] }
}
```
Pixel rectangles are what OpenSeadragon, IIIF (`/x,y,w,h/`) and Annotorious all use, so this file can be exported as **W3C Web Annotation** (`SpecificResource` + `FragmentSelector` `xywh=`) without touching the content. A real verso is simply a third entry in `views`.

## 4. Plugging in Alexia's tiles

Only the `tileSource` per view changes. OpenSeadragon reads all of these:

| Her tile layout | `tileSource` value |
|---|---|
| IIIF (any level, static or server) | `"https://tiles.example/maps/ricci/info.json"` |
| Deep Zoom (`.dzi` + `_files/`) | `"https://tiles.example/maps/ricci.dzi"` |
| XYZ / "google" layout (`z/x/y.jpg`) | a custom tile source: `{ "height": H, "width": W, "tileSize": 256, "minLevel": 0, "maxLevel": Z, "getTileUrl": function (z, x, y) { return base + z + "/" + x + "/" + y + ".jpg"; } }` — ten lines in `viewer.js` once the layout is known |
| Zoomify (`TileGroup0/…`) | `{ "type": "zoomifytileservice", "width": W, "height": H, "tilesUrl": "https://…/" }` |
| One large JPEG (no tiles) | `{ "type": "image", "url": "https://…/map.jpg" }` |

The bucket needs CORS for `GET`/`HEAD` (see runbook §5). If her app is Leaflet-based with georeferenced XYZ tiles, keep Leaflet for those maps and OpenSeadragon for scans; both read the same annotation JSON.

## 5. Upgrade path

1. **Editing without code — Sveltia CMS** (free, MIT). A form UI over the JSON files in the repo; the professor logs in with GitHub; every save is a commit. Its official Cloudflare Workers authenticator deploys with one click. Sanity is the hosted alternative (free tier: 20 seats, 100 GB assets).
2. **Drawing regions in the browser — Annotorious for OpenSeadragon** (`@annotorious/openseadragon` 3.9). Replaces the demo's author mode with rectangles and polygons, and imports/exports W3C Web Annotation JSON.
3. **IIIF Presentation manifests.** Once the tiles are IIIF, a manifest per map lets Mirador, Universal Viewer and any library aggregator open the same maps and annotations.
4. **Essays and exhibitions.** Exhibit.so (free, St Andrews) and Storiiies (free, Cogapp) build scroll stories from IIIF manifests without code; useful for outreach pages beside the viewer.
5. **Commercial route.** Micrio (see cost estimate §3D) if the lab prefers a vendor editor and support.
6. Not recommended: Zoomify (the company has ceased operations; the domain now belongs to an unrelated firm).

## 6. Known limits of the demo

- Transcriptions and translations were read from the scans for this prototype and are marked illustrative; scholarly checking is needed before publication.
- The Miller Atlas shows a real verso; for the Ricci map the two LoC halves stand in for "sides" because no verso scan exists.
- Author mode copies a region to the clipboard; it does not save into the file (that is what Sveltia CMS or Annotorious add).
- No search, no georeferencing, no multi-language UI beyond zh/en labels.
- On phones the control bar wraps to several rows; a compact mobile header is a small follow-up.
- Pages must be served over HTTP (the data is fetched); open the folder with `python3 -m http.server` or via GitHub Pages.

## 7. Files

```
demo/index.html          catalogue front page (reads data/catalogue.json)
demo/viewer.html + js/viewer.js   the viewer
demo/story.html  + js/story.js    narrative mode
demo/css/demo.css        one stylesheet, design tokens at the top
demo/data/catalogue.json list of maps
demo/data/ricci-1602.json, demo/data/miller-1519.json   content
```
Libraries: OpenSeadragon 6.1.1 (cdnjs, BSD). Fonts: Source Serif 4, Noto Serif TC, IBM Plex Sans (Google Fonts). No build step.
