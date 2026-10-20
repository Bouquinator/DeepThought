"""TOML reading (stdlib tomllib on 3.11+, vendored tomli on 3.10) and a small writer."""

try:
    import tomllib as _toml
except ModuleNotFoundError:  # Python 3.10
    from deepthought._vendor import tomli as _toml

TOMLDecodeError = _toml.TOMLDecodeError


def load_file(path):
    with open(path, "rb") as f:
        return _toml.load(f)


def loads(text):
    return _toml.loads(text)


def _scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_scalar(v)}" for k, v in value.items()) + " }"
    s = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def _key(k):
    k = str(k)
    if k and all(c.isalnum() or c in "-_" for c in k):
        return k
    return _scalar(k)


def dumps(data):
    """Serialise a dict of scalars / lists / one level of tables."""
    lines, tables = [], []
    for k, v in data.items():
        if isinstance(v, dict):
            tables.append((k, v))
        elif v is not None:
            lines.append(f"{_key(k)} = {_scalar(v)}")
    for name, table in tables:
        lines.append("")
        lines.append(f"[{_key(name)}]")
        for k, v in table.items():
            if v is not None:
                lines.append(f"{_key(k)} = {_scalar(v)}")
    return "\n".join(lines) + "\n"
