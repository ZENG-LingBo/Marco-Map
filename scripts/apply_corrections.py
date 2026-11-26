"""Merge specialists' corrections files (exported from demo/review.html) into a map file.

    python scripts/apply_corrections.py demo/data/ortelius-1570.json corrections/ortelius-1570/*.json
    python scripts/apply_corrections.py MAP.json FILE.json ... -o OUT.json   (default: rewrite MAP.json)

The corrections files are the record of the review; the map file is rebuilt from the transcription
test by build_*.py, so run this again after every rebuild.

- accepted: the label gets review = {status, by, at, comment}; its text stays.
- corrected / added: the reviewer's text, number and box replace the machine's; the machine reading
  is kept under review.machine.
- disputed: the text stays as it is; the reviewer's proposed text, if any, goes to review.proposed.
Each item carries the machine reading it was checked against. If the map file's reading has changed
since (a rebuild with new output), the item is skipped and reported: check it again in review mode.
When several files decide the same label, the latest decision wins, and differing decisions are listed.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

FORMAT = "marco-map-corrections/1"


def incipit(text, n=46):
    text = re.sub(r"^\s*\d+[.,]?\s*", "", text.replace("\n", " ")).strip()
    return text if len(text) <= n + 2 else text[:n].rsplit(" ", 1)[0] + " …"


def norm(s):
    return str(s or "").replace("\r\n", "\n").strip()


def same_reading(item, a):
    m, t = item.get("machine") or {}, a.get("text") or {}
    return norm(m.get("original")) == norm(t.get("original")) and norm(m.get("translation")) == norm(t.get("translation"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("map")
    ap.add_argument("corrections", nargs="+")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    map_path = Path(args.map)
    data = json.loads(map_path.read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in data["annotations"]}

    decisions, sources = {}, []
    for f in args.corrections:
        c = json.loads(Path(f).read_text(encoding="utf-8"))
        if c.get("format") != FORMAT:
            sys.exit(f"{f}: not a Marco-Map corrections file")
        if c.get("map") != data["id"]:
            sys.exit(f"{f}: corrections for {c.get('map')}, not {data['id']}")
        sources.append(Path(f).name)
        for aid, item in c["items"].items():
            if not item.get("status"):
                continue  # undone in review mode
            prev = decisions.get(aid)
            if prev and prev["status"] != item["status"] and prev["by"] != item["by"]:
                print(f"  {aid}: {prev['by']} {prev['status']}, {item['by']} {item['status']} -> keeping the later one")
            if not prev or item["at"] > prev["at"]:
                decisions[aid] = item

    counts, skipped = {}, []
    for aid, item in sorted(decisions.items()):
        status = item["status"]
        if item.get("added"):
            if aid in by_id:
                a = by_id[aid]
            else:
                a = json.loads(json.dumps(item["added"]))
                data["annotations"].append(a)
                by_id[aid] = a
        elif aid not in by_id:
            skipped.append(f"{aid}: no such label in the map file")
            continue
        else:
            a = by_id[aid]
            if not same_reading(item, a):
                skipped.append(f"{aid}: the machine reading changed after it was checked")
                continue
        review = {"status": status, "by": item["by"], "at": item["at"]}
        if item.get("comment"):
            review["comment"] = item["comment"]
        fields = item.get("fields")
        if status in ("corrected", "added") and (fields or item.get("region")):
            t = a.setdefault("text", {})
            if not item.get("added"):
                review["machine"] = {"original": t.get("original", ""), "expanded": t.get("expanded", ""),
                                     "translation": t.get("translation", ""), "number": a.get("number"),
                                     "region": a.get("region")}
            if fields:
                for k in ("original", "expanded", "translation"):
                    t[k] = fields.get(k, t.get(k, ""))
                if "number" in fields and (fields["number"] or a.get("number") is not None):
                    a["number"] = fields["number"] or None
                lang = t.get("lang", "la")
                label = a.setdefault("label", {})
                if t.get("expanded"):
                    label[lang] = incipit(t["expanded"])
                # Russian maps take their English label from the translation; Latin maps have a written one
                if lang == "ru" or item.get("added"):
                    label["en"] = incipit(t.get("translation", "")) or label.get("en", "")
            if item.get("region"):
                a["region"] = item["region"]
                a.pop("region_approx", None)
        elif status == "disputed" and fields:
            review["proposed"] = {k: fields.get(k) for k in ("number", "original", "expanded", "translation")}
            if item.get("region"):
                review["proposed"]["region"] = item["region"]
        a["review"] = review
        counts[status] = counts.get(status, 0) + 1

    data["reviewed"] = {"applied": date.today().isoformat(), "files": sources}
    out = Path(args.out) if args.out else map_path
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) +
          f"; {len(data['annotations']) - sum(counts.values())} labels not yet checked")
    for s in skipped:
        print("  skipped " + s)


if __name__ == "__main__":
    main()
