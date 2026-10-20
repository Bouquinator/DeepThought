"""Placeholder expansion for suite.toml strings: {project}, {suite}, {matrix.X}…"""

import re
import shlex

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][\w.]*)\}")


def expand(value, ctx):
    """Replace known {placeholders}; unknown ones are left untouched."""
    if isinstance(value, list):
        return [expand(v, ctx) for v in value]
    if not isinstance(value, str):
        return value

    def sub(m):
        key = m.group(1)
        if key in ctx:
            return str(ctx[key])
        return m.group(0)

    return _PLACEHOLDER.sub(sub, value)


def as_argv(value, ctx):
    """A command given as a string (shell-split) or a list, expanded."""
    if isinstance(value, str):
        return [expand(p, ctx) for p in shlex.split(value)]
    return [str(expand(p, ctx)) for p in value]


def quote_cmd(argv):
    return " ".join(shlex.quote(str(a)) for a in argv)
