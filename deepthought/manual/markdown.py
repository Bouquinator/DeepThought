"""A small Markdown → HTML converter for DeepThought's own docs (stdlib only).

Supports what docs/*.md use: ATX headings, paragraphs, fenced code (with a light
syntax highlighter), tables, nested lists and task lists, block quotes, rules,
and inline code, bold, italics and links. Everything is HTML-escaped.
"""

import html
import re

_FENCE = re.compile(r"^(\s*)```(\w*)\s*$")
_LIST = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?[\s|:-]+\|[\s|:-]*$")


def slug(text):
    """GitHub-style anchor of a heading."""
    text = re.sub(r"<[^>]+>", "", text).lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


class Renderer:
    """link(url) -> href rewrites relative links; code(text) -> href|None turns
    `code spans` into cross-references."""

    def __init__(self, link=None, code=None):
        self.link = link or (lambda url: url)
        self.code = code or (lambda text: None)
        self.headings = []  # [(level, text, id)]

    # ---------------------------------------------------------------- inline
    # code spans and links, whichever comes first; link text may contain code spans
    _INLINE = re.compile(r"(?P<ticks>`+)(?P<code>.+?)(?P=ticks)"
                         r"|\[(?P<text>(?:`[^`]*`|[^\[\]`])+)\]\((?P<url>[^)\s]+)\)")

    def inline(self, text, links=True):
        out, pos = [], 0
        for m in self._INLINE.finditer(text):
            if m.group("code") is None and not links:
                continue
            out.append(self._emphasis(text[pos:m.start()]))
            if m.group("code") is not None:
                code = m.group("code")
                out.append(self._code_span(code.strip() if len(m.group("ticks")) > 1 else code, xref=links))
            else:
                href = self.link(m.group("url"))
                ext = ' target="_blank" rel="noopener"' if href.startswith(("http://", "https://")) else ""
                out.append(f'<a href="{html.escape(href)}"{ext}>{self.inline(m.group("text"), links=False)}</a>')
            pos = m.end()
        out.append(self._emphasis(text[pos:]))
        return "".join(out)

    def _code_span(self, code, xref=True):
        href = self.code(code) if xref else None
        tag = f"<code>{html.escape(code)}</code>"
        return f'<a class="xref" href="{html.escape(href)}">{tag}</a>' if href else tag

    @staticmethod
    def _emphasis(text):
        text = html.escape(text, quote=False)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<em>\1</em>", text)
        return text

    # ---------------------------------------------------------------- blocks
    def render(self, md):
        lines = md.replace("\t", "    ").splitlines()
        return self._blocks(lines)

    def _blocks(self, lines):
        out, i, para = [], 0, []

        def flush():
            if para:
                out.append(f"<p>{self.inline(' '.join(l.strip() for l in para))}</p>")
                para.clear()

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            fence = _FENCE.match(line)
            if fence:
                flush()
                indent, lang = len(fence.group(1)), fence.group(2)
                j = i + 1
                body = []
                while j < len(lines) and not _FENCE.match(lines[j]):
                    body.append(lines[j][indent:] if lines[j][:indent].strip() == "" else lines[j])
                    j += 1
                out.append(code_block("\n".join(body), lang))
                i = j + 1
                continue
            if not stripped:
                flush()
                i += 1
                continue
            heading = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)
            if heading:
                flush()
                level, text = len(heading.group(1)), heading.group(2)
                hid = slug(text)
                self.headings.append((level, text, hid))
                out.append(f'<h{level} id="{html.escape(hid)}">{self.inline(text)}</h{level}>')
                i += 1
                continue
            if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
                flush()
                out.append("<hr>")
                i += 1
                continue
            if stripped.startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1].strip()):
                flush()
                j = i + 2
                rows = []
                while j < len(lines) and lines[j].strip().startswith("|"):
                    rows.append(lines[j])
                    j += 1
                out.append(self._table(line, rows))
                i = j
                continue
            if stripped.startswith(">"):
                flush()
                j = i
                quote = []
                while j < len(lines) and lines[j].strip().startswith(">"):
                    quote.append(re.sub(r"^\s*>\s?", "", lines[j]))
                    j += 1
                out.append(f"<blockquote>{self._blocks(quote)}</blockquote>")
                i = j
                continue
            if _LIST.match(line) and not para:
                j, html_list = self._list(lines, i)
                out.append(html_list)
                i = j
                continue
            para.append(line)
            i += 1
        flush()
        return "\n".join(out)

    def _list(self, lines, i):
        first = _LIST.match(lines[i])
        base = len(first.group(1))
        ordered = first.group(2)[0].isdigit()
        items = []
        while i < len(lines):
            m = _LIST.match(lines[i])
            if not m or len(m.group(1)) < base:
                if lines[i].strip() and m is None and len(lines[i]) - len(lines[i].lstrip()) > base and items:
                    items[-1].append(lines[i].strip())  # continuation line
                    i += 1
                    continue
                break
            if len(m.group(1)) > base:  # nested list
                j, sub = self._list(lines, i)
                items[-1].append(("html", sub))
                i = j
                continue
            items.append([m.group(3)])
            i += 1
        parts = []
        for item in items:
            text = " ".join(x for x in item if isinstance(x, str))
            nested = "".join(x[1] for x in item if isinstance(x, tuple))
            box = re.match(r"^\[([ xX])\]\s+(.*)$", text)
            if box:
                mark = "☑" if box.group(1).strip() else "☐"
                parts.append(f'<li class="task"><span class="box">{mark}</span> {self.inline(box.group(2))}{nested}</li>')
            else:
                parts.append(f"<li>{self.inline(text)}{nested}</li>")
        tag = "ol" if ordered else "ul"
        return i, f"<{tag}>{''.join(parts)}</{tag}>"

    def _table(self, header, rows):
        def cells(row):
            return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]

        head = "".join(f"<th>{self.inline(c)}</th>" for c in cells(header))
        body = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in cells(r)) + "</tr>" for r in rows)
        return f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


# -------------------------------------------------------------------- code
_KEYWORDS = {
    "c": r"\b(?:int|char|void|size_t|ssize_t|long|unsigned|const|static|struct|typedef|return|if|else|while|for|do|"
         r"break|continue|sizeof|NULL|double|float|bool|off_t|pid_t)\b",
    "python": r"\b(?:def|class|import|from|return|if|elif|else|for|while|in|not|and|or|with|as|try|except|raise|"
              r"None|True|False|lambda|pass)\b",
    "sh": r"\b(?:if|then|else|elif|fi|for|in|do|done|case|esac|while|exit|export|set|shift)\b",
    "toml": r"\b(?:true|false)\b",
    "json": r"\b(?:true|false|null)\b",
}
_ALIASES = {"h": "c", "py": "python", "bash": "sh", "shell": "sh", "zsh": "sh", "console": "sh"}


def _token_re(lang):
    comment = {"c": r"//[^\n]*|/\*.*?\*/", "python": r"#[^\n]*", "sh": r"(?<![\w$])#[^\n]*",
               "toml": r"#[^\n]*"}.get(lang)
    parts = []
    if comment:
        parts.append(f"(?P<com>{comment})")
    parts.append(r'(?P<str>"(?:\\.|[^"\\\n])*"' + (r"|'(?:\\.|[^'\\\n])*'" if lang != "c" else r"|'(?:\\.|[^'\\\n])'") + ")")
    if lang == "c":
        parts.append(r"(?P<mac>\bDT_[A-Z0-9_]+\b|^\s*#\s*\w+)")
        parts.append(r"(?P<fn>\b(?:dt|ft)_\w+(?=\())")
    if lang == "toml":
        parts.append(r"(?P<sec>^\s*\[\[?[^\]\n]+\]\]?)")
        parts.append(r"(?P<key>^\s*[\w.\"-]+(?=\s*=))")
    if lang == "json":
        parts.append(r'(?P<key>"[^"\n]*"(?=\s*:))')
    if lang in _KEYWORDS:
        parts.append(f"(?P<kw>{_KEYWORDS[lang]})")
    parts.append(r"(?P<num>\b\d+(?:\.\d+)?\b)")
    order = ["com", "key", "sec", "str", "mac", "fn", "kw", "num"]
    parts.sort(key=lambda p: order.index(re.match(r"\(\?P<(\w+)>", p).group(1)))
    return re.compile("|".join(parts), re.M | re.S)


def code_block(code, lang=""):
    lang = _ALIASES.get(lang.lower(), lang.lower())
    if lang not in _KEYWORDS:
        body = html.escape(code)
    else:
        out, pos = [], 0
        for m in _token_re(lang).finditer(code):
            out.append(html.escape(code[pos:m.start()]))
            out.append(f'<span class="t-{m.lastgroup}">{html.escape(m.group(0))}</span>')
            pos = m.end()
        out.append(html.escape(code[pos:]))
        body = "".join(out)
    label = f'<span class="lang">{html.escape(lang)}</span>' if lang else ""
    return f'<div class="code">{label}<button class="copy" title="Copy">copy</button><pre><code>{body}</code></pre></div>'
