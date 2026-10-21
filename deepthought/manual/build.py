"""Build the web manual: one self-contained HTML file (no server, works offline).

The page shows docs/reference.md as man-style entries with search, plus the
other docs (protocol, writing suites, architecture) with their table of contents.
"""

import html
import json
import re
from pathlib import Path

from deepthought import __version__
from deepthought.cli import man
from deepthought.core import paths
from deepthought.manual.markdown import Renderer, slug

DOCS = paths.REPO_ROOT / "docs"
TEMPLATE = Path(__file__).with_name("page.html")
# (id, file) in tab order; the reference is rendered as entries, the others as pages
PAGES = [("reference", "reference.md"), ("protocol", "protocol.md"),
         ("writing-suites", "writing-suites.md"), ("architecture", "architecture.md")]
DOC_IDS = {f: i for i, f in PAGES}
# code spans that name an entry are cross-referenced when the name can't be an ordinary word
DISTINCTIVE = re.compile(r"^(DT_|dt_|t_dt|\[|\{|dt |@|--)")


def _link(url):
    """Relative links of the docs → routes of the page, or files of the repository."""
    if url.startswith(("http://", "https://", "mailto:")):
        return url
    path, _, anchor = url.partition("#")
    if not path:
        return f"#/{{doc}}/{anchor}"  # same page: completed by the caller
    name = Path(path).name
    if name == "reference.md":
        return "#/ref" + (f"/{anchor}" if anchor else "")
    if name in DOC_IDS and (DOCS / name).exists():
        return f"#/doc/{DOC_IDS[name]}" + (f"/{anchor}" if anchor else "")
    target = (DOCS / path).resolve()
    return target.as_uri() if target.exists() else url


def _plain(md):
    """Searchable text of some Markdown."""
    text = re.sub(r"```\w*", " ", md)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"[`*|#>]+|\s+", " ", text).strip()


def _page(doc_id, md, names):
    renderer = Renderer(link=lambda u: _link(u).replace("{doc}", f"doc/{doc_id}"),
                        code=lambda t: f"#/ref/{t}" if t in names and DISTINCTIVE.match(t) else None)
    body = renderer.render(md)
    title = next((t for lvl, t, _ in renderer.headings if lvl == 1), doc_id)
    toc = [{"level": lvl, "text": re.sub(r"`", "", t), "id": hid} for lvl, t, hid in renderer.headings if lvl in (2, 3)]
    return {"id": doc_id, "title": title, "html": body, "toc": toc,
            "search": [{"text": h["text"], "id": h["id"]} for h in toc]}


def _reference(names):
    raw = (DOCS / "reference.md").read_text(encoding="utf-8")
    titles = {re.sub(r"^\d+\.\s*", "", t.strip()): t.strip() for t in re.findall(r"^## (.+)$", raw, re.M)}
    intro_md = raw.split("**Sections**")[0]
    intro_md = re.sub(r"^# .*\n", "", intro_md, count=1)
    page_link = lambda u: _link(u).replace("{doc}", "ref")  # noqa: E731
    intro = Renderer(link=page_link, code=lambda t: None).render(intro_md)
    sections = []
    for title, entries in man.load():
        out = []
        for e in entries:
            md = e.text
            see = set()
            m = re.search(r"^See also:\s*(.+?)\.?\s*$", md, re.M)
            if m:
                listed = [s.strip().strip("`") for s in m.group(1).split(",") if s.strip()]
                see = set(listed)
                linked = ", ".join(f"`{s}`" for s in listed)
                md = md[:m.start()] + f"See also: {linked}." + md[m.end():]
            renderer = Renderer(link=page_link,
                                code=lambda t, see=see: f"#/ref/{t}" if t in names and t not in e.names
                                and (t in see or DISTINCTIVE.match(t)) else None)
            out.append({"names": e.names, "html": renderer.render(md), "text": _plain(md).lower()})
        raw_title = titles.get(title, title)
        sections.append({"title": title, "anchor": slug(raw_title), "entries": out})
    return {"intro": intro, "sections": sections}


def data(initial=""):
    sections = man.load()
    names = {n for _, es in sections for e in es for n in e.names}
    pages = [_page(doc_id, (DOCS / f).read_text(encoding="utf-8"), names)
             for doc_id, f in PAGES[1:] if (DOCS / f).exists()]
    return {"version": __version__, "initial": initial, "reference": _reference(names),
            "pages": pages}


def build(dest, initial="", theme=""):
    """Write the manual to `dest` (a folder). Returns the HTML file."""
    payload = data(initial)
    payload["theme"] = theme
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # nothing in the data may close the <script> element
    blob = blob.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__VERSION__", html.escape(__version__)).replace("/*__DATA__*/null", blob)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "index.html"
    out.write_text(page, encoding="utf-8")
    return out
