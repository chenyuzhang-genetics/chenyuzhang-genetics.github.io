"""Rebuild the publication list in index.html from publications.bib.
Usage: python3 tools/build_pubs.py"""
import re, html, urllib.parse, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
bib = (ROOT / "publications.bib").read_text(encoding="utf-8")
JOURNAL_FIX = {"plant physiology and biochemistry": "Plant Physiology and Biochemistry",
               "horticulture research": "Horticulture Research",
               "journal of experimental botany": "Journal of Experimental Botany"}
ME = {"zhang, chenyu", "zhang, chen-yu"}

def fields(entry):
    return {k.lower(): v.strip() for k, v in re.findall(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", entry)}

def short(name):
    if name.strip().lower() == "others":
        return None
    last, _, given = name.partition(",")
    inits = "".join(p[0].upper() for p in re.split(r"[\s\-]+", given.strip()) if p)
    return f"{last.strip()} {inits}".strip()

def title_html(t):
    t = t.replace("\\_", " ").replace("{", "").replace("}", "")
    t = html.escape(t)
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
    q = urllib.parse.quote_plus(p["title"].replace("\\_", " "))
    href = f"https://doi.org/{p['doi']}" if p["doi"] else f"https://scholar.google.com/scholar?q={q}"
    doi_txt = f' · <a class="doi" href="https://doi.org/{p["doi"]}">doi:{html.escape(p["doi"])}</a>' if p["doi"] else ""
    chip = '<span class="chip">First author</span>' if p["first"] else ""
    out.append(f'        <li class="pub"><div class="yr">{yr}</div><div>'
               f'<a class="t" href="{href}">{p["html_title"]}</a>{chip}'
               f'<div class="meta">{p["authors"]}{"" if p["authors"].endswith(".") else "."} <i>{p["journal"]}</i> {p["loc"]}{doi_txt}</div></div></li>')
summary = f'        <li class="pub-count">{len(pubs)} journal articles · {n_first} as first author</li>'
block = "\n".join([summary] + out)

idx = ROOT / "index.html"
page = idx.read_text(encoding="utf-8")
page = re.sub(r'(<ul class="pubs" id="pub-list">\n).*?(\n      </ul>)', lambda m: m.group(1) + block + m.group(2), page, flags=re.S)
idx.write_text(page, encoding="utf-8")
print(f"{len(pubs)} publications, {n_first} first-author")
