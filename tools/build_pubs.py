"""Rebuild the publication list in index.html from publications.bib.
Usage: python3 tools/build_pubs.py"""
import re, html, urllib.parse, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
bib = (ROOT / "publications.bib").read_text(encoding="utf-8")
JOURNAL_FIX = {"plant physiology": "Plant Physiology",
               "international journal of molecular sciences": "International Journal of Molecular Sciences",
               "plant physiology and biochemistry": "Plant Physiology and Biochemistry",
               "horticulture research": "Horticulture Research",
               "journal of experimental botany": "Journal of Experimental Botany"}
ME = {"zhang, chenyu", "zhang, chen-yu"}

ACCENTS = {"v": {"s": "š", "c": "č", "z": "ž", "S": "Š", "C": "Č", "Z": "Ž"},
           "'": {"e": "é", "a": "á", "o": "ó"}, '"': {"o": "ö", "u": "ü", "a": "ä"}}

def delatex(s):
    s = re.sub(r"\\([v'\"])\{?(\w)\}?", lambda m: ACCENTS.get(m.group(1), {}).get(m.group(2), m.group(2)), s)
    return s.replace("\\_", " ").replace("{", "").replace("}", "")

def fields(entry):
    out, i = {}, 0
    for m in re.finditer(r"(\w+)\s*=\s*\{", entry):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth and j < len(entry):
            depth += {"{": 1, "}": -1}.get(entry[j], 0); j += 1
        out[m.group(1).lower()] = delatex(entry[m.end():j - 1].strip()); i = j
    return out

def short(name):
    if name.strip().lower() == "others":
        return None
    last, _, given = name.partition(",")
    inits = "".join(p if p.isupper() and len(p) > 1 else p[0].upper() for p in re.split(r"[\s\-]+", given.strip()) if p)
    return f"{last.strip()} {inits}".strip()

def title_html(t):
    t = html.escape(t.rstrip("."))
    return re.sub(r"(Camellia sinensis)", r"<i>\1</i>", t, flags=re.I)

pubs = []
for entry in re.split(r"\n(?=@)", bib.strip()):
    f = fields(entry)
    if "title" not in f:
        continue
    raw = [a.strip() for a in f["author"].split(" and ")]
    authors, first = [], raw[0].lower() in ME
    for a in raw:
        s = short(a)
        if s is None:
            authors.append("et al.")
        elif a.lower() in ME:
            authors.append(f"<b>{html.escape(s)}</b>")
        else:
            authors.append(html.escape(s))
    j = f.get("journal", "")
    j = JOURNAL_FIX.get(j.lower(), j)
    loc = f.get("volume", "")
    if f.get("number"): loc += f"({f['number']})"
    if f.get("pages"): loc += f": {f['pages'].replace('--', '–')}"
    pubs.append(dict(year=int(f["year"]), title=f["title"], first=first,
                     html_title=title_html(f["title"]), authors=", ".join(authors),
                     journal=html.escape(j), loc=html.escape(loc), doi=f.get("doi", "")))

pubs.sort(key=lambda p: (-p["year"], not p["first"], p["title"]))
n_first = sum(p["first"] for p in pubs)
out, last_year = [], None
for p in pubs:
    yr = str(p["year"]) if p["year"] != last_year else ""
    last_year = p["year"]
    q = urllib.parse.quote_plus(p["title"])
    href = f"https://doi.org/{p['doi']}" if p["doi"] else f"https://scholar.google.com/scholar?q={q}"
    doi_txt = f' · <a class="doi" href="https://doi.org/{p["doi"]}">doi:{html.escape(p["doi"])}</a>' if p["doi"] else ""
    chip = '<span class="chip">First author</span>' if p["first"] else ""
    out.append(f'        <li class="pub"><div class="yr">{yr}</div><div>'
               f'<a class="t" href="{href}">{p["html_title"]}</a>{chip}'
               f'<div class="meta">{p["authors"]}{"" if p["authors"].endswith(".") else "."} {f"<i>{p['journal']}</i> " if p["journal"] else ""}{p["loc"]}{doi_txt}</div></div></li>')
summary = f'        <li class="pub-count">{len(pubs)} journal articles · {n_first} as first author</li>'
block = "\n".join([summary] + out)

idx = ROOT / "index.html"
page = idx.read_text(encoding="utf-8")
page = re.sub(r'(<ul class="pubs" id="pub-list">\n).*?(\n      </ul>)', lambda m: m.group(1) + block + m.group(2), page, flags=re.S)
idx.write_text(page, encoding="utf-8")
print(f"{len(pubs)} publications, {n_first} first-author")
