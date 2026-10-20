"""suite.toml loading and validation.

A suite is a directory containing `suite.toml`. See docs/writing-suites.md
for the full reference; this module is the source of truth for what is
accepted.
"""

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

from deepthought import PROTOCOL, __version__
from deepthought.core import toml

RUNNERS = ("c-unit", "python-unit", "exec", "script")
CHECKS = ("rules", "relink", "norminette", "forbidden", "files")
SUITE_KEYS = {"suite", "detect", "build", "forbidden", "norminette", "files", "defaults", "group", "fetch"}
PLATFORMS = ("darwin", "linux")
PLATFORM_KEYS = {"sources", "include", "link", "cflags", "ldflags", "env"}
GROUP_KEYS = {
    "name", "description", "category", "runner", "when", "before", "sources", "include",
    "link", "cflags", "ldflags", "matrix", "fixtures", "timeout", "leaks", "cases",
    "command", "tests", "env", "split", *PLATFORMS,
}


class ManifestError(Exception):
    def __init__(self, path, errors):
        self.path = Path(path)
        self.errors = errors if isinstance(errors, list) else [errors]
        super().__init__(f"{path}: " + "; ".join(self.errors))


@dataclass
class Group:
    name: str
    runner: str
    category: str = "mandatory"
    description: str = ""
    when: dict = field(default_factory=dict)
    before: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    include: list = field(default_factory=list)
    link: list = field(default_factory=list)
    cflags: list = field(default_factory=list)
    ldflags: list = field(default_factory=list)
    matrix: dict = field(default_factory=dict)
    fixtures: str = "fixtures"
    timeout: float = None
    leaks: bool = None
    cases: str = ""
    command: object = None
    tests: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    split: bool = False
    platform: dict = field(default_factory=dict)  # {"darwin": {...}, "linux": {...}}
    index: int = 0

    def get(self, key):
        """A list/dict setting plus the current platform's additions."""
        import platform as _platform

        base = getattr(self, key)
        extra = self.platform.get(_platform.system().lower(), {}).get(key)
        if extra is None:
            return base
        if isinstance(base, dict):
            return {**base, **extra}
        return list(base) + (extra if isinstance(extra, list) else [extra])

    @property
    def slug(self):
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-") or f"group{self.index}"

    def variants(self):
        """Matrix expansion: [{}] without a matrix, else one dict per combination."""
        if not self.matrix:
            return [{}]
        keys = list(self.matrix)
        values = [v if isinstance(v, list) else [v] for v in self.matrix.values()]
        return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


@dataclass
class Suite:
    id: str
    name: str
    path: Path
    project: str
    version: str = "0.0.0"
    engine: str = ""
    authors: list = field(default_factory=list)
    description: str = ""
    homepage: str = ""
    detect: dict = field(default_factory=dict)
    build: dict = field(default_factory=dict)
    forbidden: dict = field(default_factory=dict)
    norminette: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    groups: list = field(default_factory=list)
    fetch: list = field(default_factory=list)  # [{"name", "git", "ref", "into", "path"}]
    source: str = "builtin"
    origin: str = ""
    uid: str = ""
    compatible: bool = True
    warnings: list = field(default_factory=list)

    @property
    def checks(self):
        return list(self.build.get("checks", []))

    def to_dict(self):
        return {
            "uid": self.uid or self.id,
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "project": self.project,
            "authors": self.authors,
            "description": self.description,
            "homepage": self.homepage,
            "path": str(self.path),
            "source": self.source,
            "origin": self.origin,
            "compatible": self.compatible,
            "warnings": self.warnings,
            "checks": self.checks,
            "groups": [
                {"name": g.name, "category": g.category, "runner": g.runner,
                 "description": g.description, "variants": len(g.variants())}
                for g in self.groups
            ],
        }


def _version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def engine_compatible(spec, version=__version__):
    """Tiny range check: '>=0.1', '<2', '>=0.1,<1.0', '' (any)."""
    if not spec:
        return True
    current = _version_tuple(version)
    for part in spec.split(","):
        part = part.strip()
        m = re.match(r"(>=|<=|==|>|<)?\s*([\d.]+)$", part)
        if not m:
            return False
        op, ver = m.group(1) or ">=", _version_tuple(m.group(2))
        ok = {
            ">=": current >= ver, "<=": current <= ver, "==": current == ver,
            ">": current > ver, "<": current < ver,
        }[op]
        if not ok:
            return False
    return True


def _list(value, name, errors, where):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        errors.append(f"{where}: '{name}' must be a string or a list")
        return []
    return value


def load_suite(path):
    """Load and validate <path>/suite.toml. Raises ManifestError."""
    path = Path(path).resolve()
    manifest = path / "suite.toml" if path.is_dir() else path
    root = manifest.parent
    if not manifest.exists():
        raise ManifestError(manifest, "suite.toml not found")
    try:
        data = toml.load_file(manifest)
    except toml.TOMLDecodeError as e:
        raise ManifestError(manifest, f"invalid TOML: {e}")

    errors, warnings = [], []
    for key in data:
        if key not in SUITE_KEYS:
            warnings.append(f"unknown top-level key '{key}' (ignored)")

    meta = data.get("suite")
    if not isinstance(meta, dict):
        raise ManifestError(manifest, "missing [suite] table")
    for req in ("id", "name", "project"):
        if not meta.get(req):
            errors.append(f"[suite] '{req}' is required")
    sid = str(meta.get("id", ""))
    if sid and not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", sid):
        errors.append(f"[suite] id '{sid}' may only contain letters, digits, '.', '_' and '-'")

    build = data.get("build", {}) or {}
    for check in _list(build.get("checks"), "checks", errors, "[build]"):
        if check not in CHECKS:
            errors.append(f"[build] unknown check '{check}' (known: {', '.join(CHECKS)})")

    defaults = data.get("defaults", {}) or {}
    groups = []
    raw_groups = data.get("group", [])
    if not isinstance(raw_groups, list) or not raw_groups:
        errors.append("at least one [[group]] is required")
        raw_groups = []
    seen = set()
    for i, g in enumerate(raw_groups):
        where = f"[[group]] #{i + 1}"
        if not isinstance(g, dict):
            errors.append(f"{where}: must be a table")
            continue
        for key in g:
            if key not in GROUP_KEYS:
                warnings.append(f"{where}: unknown key '{key}' (ignored)")
        name = g.get("name")
        if not name:
            errors.append(f"{where}: 'name' is required")
            name = f"group {i + 1}"
        where = f"[[group]] '{name}'"
        runner = g.get("runner", "c-unit")
        if runner not in RUNNERS:
            errors.append(f"{where}: unknown runner '{runner}' (known: {', '.join(RUNNERS)})")
        group = Group(
            name=name,
            runner=runner,
            index=i,
            category=g.get("category", "mandatory"),
            description=g.get("description", ""),
            when=g.get("when", {}) or {},
            before=_list(g.get("before"), "before", errors, where),
            sources=_list(g.get("sources"), "sources", errors, where),
            include=_list(g.get("include"), "include", errors, where),
            link=_list(g.get("link"), "link", errors, where),
            cflags=_list(g.get("cflags"), "cflags", errors, where),
            ldflags=_list(g.get("ldflags"), "ldflags", errors, where),
            matrix=g.get("matrix", {}) or {},
            fixtures=g.get("fixtures", defaults.get("fixtures", "fixtures")),
            timeout=g.get("timeout", defaults.get("timeout")),
            leaks=g.get("leaks", defaults.get("leaks")),
            cases=g.get("cases", ""),
            command=g.get("command"),
            tests=_list(g.get("tests"), "tests", errors, where),
            env=g.get("env", {}) or {},
            split=bool(g.get("split", False)),
            platform={p: g[p] for p in PLATFORMS if isinstance(g.get(p), dict)},
        )
        for plat, table in group.platform.items():
            for key in table:
                if key not in PLATFORM_KEYS:
                    errors.append(f"{where}: [{plat}] only accepts {', '.join(sorted(PLATFORM_KEYS))} (got '{key}')")
        if group.slug in seen:
            errors.append(f"{where}: duplicate group name")
        seen.add(group.slug)
        if group.category not in ("mandatory", "bonus", "extra"):
            errors.append(f"{where}: category must be mandatory, bonus or extra")
        if runner == "c-unit" and not group.sources:
            errors.append(f"{where}: c-unit groups need 'sources'")
        if runner == "exec" and not group.cases:
            errors.append(f"{where}: exec groups need 'cases' (a TOML file of [[case]])")
        if runner == "exec" and group.cases and not (root / group.cases).exists():
            errors.append(f"{where}: cases file '{group.cases}' not found")
        if runner == "script" and not group.command:
            errors.append(f"{where}: script groups need 'command'")
        if runner == "python-unit" and not group.tests:
            errors.append(f"{where}: python-unit groups need 'tests' (globs of test files)")
        if not isinstance(group.matrix, dict):
            errors.append(f"{where}: 'matrix' must be a table of lists")
        groups.append(group)

    fetches = []
    raw_fetch = data.get("fetch", [])
    if not isinstance(raw_fetch, list):
        errors.append("[[fetch]] must be an array of tables")
        raw_fetch = []
    for i, f in enumerate(raw_fetch):
        where = f"[[fetch]] #{i + 1}"
        if not isinstance(f, dict) or not f.get("git"):
            errors.append(f"{where}: 'git' (repository URL) is required")
            continue
        name = f.get("name") or f"dep{i + 1}"
        into = f.get("into") or name
        dest = (root / into).resolve()
        # a dependency may be shared by sibling suites, but never escape their parent folder
        if not str(dest).startswith(str(root.parent.resolve())):
            errors.append(f"{where}: 'into' must stay inside the suite folder or its parent")
            continue
        if not re.match(r"^[A-Za-z0-9_-]+$", name):
            errors.append(f"{where}: 'name' may only contain letters, digits, '_' and '-'")
        fetches.append({"name": name, "git": f["git"], "ref": str(f.get("ref", "")), "path": str(dest)})

    if errors:
        raise ManifestError(manifest, errors)

    suite = Suite(
        id=sid,
        name=meta["name"],
        path=root,
        project=meta["project"],
        version=str(meta.get("version", "0.0.0")),
        engine=meta.get("engine", ""),
        authors=meta.get("authors", []),
        description=meta.get("description", ""),
        homepage=meta.get("homepage", ""),
        detect=data.get("detect", {}) or {},
        build=build,
        forbidden=data.get("forbidden", {}) or {},
        norminette=data.get("norminette", {}) or {},
        files=data.get("files", {}) or {},
        defaults=defaults,
        groups=groups,
        fetch=fetches,
        warnings=warnings,
    )
    suite.uid = suite.id
    suite.compatible = engine_compatible(suite.engine)
    if not suite.compatible:
        suite.warnings.append(
            f"needs engine {suite.engine}, this is {__version__} (protocol {PROTOCOL}): run `./dt update`"
        )
    return suite
