"""`dt man`: the reference manual (docs/reference.md) as man pages.

Every `### heading` of the reference is an entry. Its names are the heading's
`code spans`, or the heading split on " · " when it has none.
"""

import re
import shutil
import textwrap

from deepthought.cli.reporter_plain import c
from deepthought.core import paths

REFERENCE = paths.REPO_ROOT / "docs" / "reference.md"


class Entry:
    def __init__(self, heading, section):
        self.heading = heading
        self.section = section
        names = re.findall(r"`([^`]+)`", heading) or heading.split(" · ")
        self.names = [n.strip() for n in names if n.strip()]
        self.lines = []

    @property
    def text(self):
        return "\n".join(self.lines).strip("\n")


def load(path=REFERENCE):
    """[(section title, [Entry])] in the order of the document."""
    sections, entry, fence = [], None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            sections.append((re.sub(r"^\d+\.\s*", "", line[3:].strip()), []))
            entry = None
            continue
        if not fence and line.startswith("### ") and sections:
            entry = Entry(line[4:].strip(), sections[-1][0])
            sections[-1][1].append(entry)
            continue
        if not fence and line.strip() == "---":
            entry = None
            continue
        if entry is not None:
            entry.lines.append(line)
    return [(title, entries) for title, entries in sections if entries]


def find(sections, topic, search_text=False):
    """Entries for `topic`: exact name matches first, else names containing it."""
    entries = [e for _, es in sections for e in es]
    t = topic.lower().strip()
    if search_text:
        return [e for e in entries if t in e.text.lower() or any(t in n.lower() for n in e.names)]
    for same in (lambda n: n == topic.strip(), lambda n: n.lower() == t):  # DT_CHECK_STR before dt_check_str
        exact = [e for e in entries if any(same(n) for n in e.names)]
        if exact:
            return exact
    return [e for e in entries if any(t in n.lower() for n in e.names)]


def _inline(text):
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: c(m.group(1), "bold"), text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"\1", text)
    text = re.sub(r"`([^`]+)`", lambda m: c(m.group(1), "cyan"), text)
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _cells(line):
    # split on | but not on \| (escaped pipes inside cells)
    return [x.strip().replace("\\|", "|") for x in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _table(rows, width):
    """Aligned columns, the last one wrapped; one block per row when even that doesn't fit."""
    header, body = rows[0], rows[1:]
    plain = lambda s: len(_ANSI.sub("", s))  # noqa: E731
    pad = lambda s, n: s + " " * (n - plain(s))  # noqa: E731
    cols = [max(plain(r[i]) if i < len(r) else 0 for r in rows) for i in range(len(header))]
    lead = 2 + sum(cols[:-1]) + 3 * (len(cols) - 1)
    if lead <= width * 0.55:
        out = []
        for i, r in enumerate([header] + body):
            r = [c(_ANSI.sub("", x), "dim") for x in r] if i == 0 else r
            r = r + [""] * (len(cols) - len(r))
            head = "  " + "".join(pad(x, n) + "   " for x, n in zip(r[:-1], cols))
            last = textwrap.wrap(r[-1], max(20, width - lead), break_long_words=False) or [""]
            out.append((head + last[0]).rstrip())
            out.extend(" " * lead + more for more in last[1:])
        return out
    out = []
    for r in body:
        out.append("  " + c(_ANSI.sub("", r[0]), "bold") if r else "")
        for name, value in zip(header[1:], r[1:]):
            if _ANSI.sub("", value).strip():
                out.extend(textwrap.wrap(f"{c(_ANSI.sub('', name), 'dim')}  {value}", width - 6, initial_indent="      ",
                                         subsequent_indent="        ", break_long_words=False))
    return out


def render(entry):
    width = min(shutil.get_terminal_size((100, 20)).columns, 100)
    out = [c(" · ".join(entry.names), "bold") + c(f"    ({entry.section})", "dim"), ""]
    fence = False
    table = []
    for line in entry.text.splitlines() + [""]:
        if table and not line.startswith("|"):
            out.extend(_table(table, width))
            table = []
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            out.append("    " + c(line, "cyan"))
        elif line.startswith("|"):
            if not re.match(r"^\|[\s|:-]+\|$", line):
                table.append([_inline(x) for x in _cells(line)])
        elif line.strip():
            stripped = line.strip()
            indent = "  " + " " * (len(line) - len(line.lstrip()))
            hang = indent + ("  " if re.match(r"^(- |\d+\. )", stripped) else "")
            # colour first so a wrap never splits a `code span` (escape codes stick to their word)
            out.extend(textwrap.wrap(_inline(stripped), width - len(hang), initial_indent=indent,
                                     subsequent_indent=hang, break_long_words=False))
        else:
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def listing(sections):
    width = min(shutil.get_terminal_size((100, 20)).columns, 100)
    out = [c("DeepThought reference", "bold") + "  —  ./dt man TOPIC  ·  ./dt man -k WORD", ""]
    for title, entries in sections:
        out.append(c(title, "bold"))
        names = ", ".join(n for e in entries for n in e.names)
        out.extend(textwrap.wrap(names, width - 4, initial_indent="    ", subsequent_indent="    "))
        out.append("")
    return "\n".join(out)


def main(topic, search_text=False):
    if not REFERENCE.exists():
        print(c(f"the reference manual is missing: {REFERENCE}", "red"))
        return 1
    sections = load()
    if not topic:
        print(listing(sections))
        return 0
    found = find(sections, topic, search_text)
    if not found:
        print(c(f"no entry for '{topic}'", "yellow") + "  (./dt man lists every entry, ./dt man -k WORD searches the text)")
        return 1
    if len(found) == 1 or (not search_text and all(any(n.lower() == topic.lower() for n in e.names) for e in found)):
        print("\n".join(render(e) for e in found))
        return 0
    print(c(f"{len(found)} entries match '{topic}':", "bold"))
    for e in found:
        print(f"  {c(' · '.join(e.names), 'cyan')}" + c(f"  ({e.section})", "dim"))
    print(c("\n./dt man NAME shows one of them", "dim"))
    return 0


def open_web(topic="", open_browser=True):
    """Build the web manual into the cache folder and open it in the browser."""
    import webbrowser
    from urllib.parse import quote

    from deepthought.core.config import Config
    from deepthought.manual.build import build

    config = Config()
    if not REFERENCE.exists():
        print(c(f"the reference manual is missing: {REFERENCE}", "red"))
        return 1
    initial = f"#/ref/{quote(topic, safe='')}" if topic else ""
    page = build(paths.cache_dir(config["cache_dir"]) / "manual", initial=initial, theme=config["theme"])
    url = page.as_uri()
    print(c("📖 DeepThought manual", "bold") + "  " + c(url + (initial if topic else ""), "cyan"))
    if open_browser and not webbrowser.open(url):
        print(c("   could not open a browser: open the link above yourself", "yellow"))
    elif open_browser:
        print(c("   opened in your browser · ./dt man TOPIC prints one entry here", "dim"))
    return 0
