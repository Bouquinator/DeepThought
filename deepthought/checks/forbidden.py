"""Forbidden functions: external symbols used by the student's code (nm)."""

import platform
import re
from pathlib import Path

from deepthought.core import proc

# symbols the toolchain inserts by itself
TOOLCHAIN = {
    "__stack_chk_fail", "__stack_chk_guard", "dyld_stub_binder", "__chkstk_darwin",
    "_GLOBAL_OFFSET_TABLE_", "__gmon_start__", "__cxa_finalize", "__libc_start_main",
    "_ITM_deregisterTMCloneTable", "_ITM_registerTMCloneTable", "__error", "__errno_location",
    "__stdoutp", "__stderrp", "__stdinp", "_DYNAMIC", "__dso_handle", "_mh_execute_header",
    "__assert_rtn", "__assert_fail", "__memcpy_chk", "__memset_chk", "__strcpy_chk",
    "__strlcpy_chk", "__strlcat_chk", "__memmove_chk",
}
# runtime hooks inserted by -fsanitize=… builds
SANITIZER_PREFIXES = ("__asan_", "__ubsan_", "__sanitizer_", "__lsan_", "__tsan_", "__msan_")
# functions a compiler may emit for struct copies / zero-initialisation
COMPILER_EMITTED = {"memset", "memcpy", "memmove", "bzero", "__bzero"}


def _normalise(sym):
    if platform.system() == "Darwin" and sym.startswith("_"):
        sym = sym[1:]
    return sym.split("@")[0]


def symbols(paths, nm="nm"):
    defined, undefined = set(), set()
    for p in paths:
        res = proc.run([nm, "-g", str(p)], timeout=60)
        for line in res.stdout.decode(errors="replace").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in ("U", "w", "v"):
                undefined.add(_normalise(parts[1]))
            elif len(parts) == 3 and parts[1] not in ("U",):
                defined.add(_normalise(parts[2]))
    return defined, undefined


def check(ctx, suite, stage):
    cfg = suite.forbidden
    allowed = set(cfg.get("allowed", []))
    targets = [ctx.ws.src / ctx.x(a, suite) for a in cfg.get("artifacts", suite.build.get("artifacts", []))]
    if cfg.get("sources"):
        # compile the given sources to objects ourselves (projects without a Makefile)
        objdir = ctx.ws.out / "_forbidden" / suite.uid
        objdir.mkdir(parents=True, exist_ok=True)
        targets = []
        for src in cfg["sources"]:
            for f in sorted(ctx.ws.src.glob(ctx.x(src, suite))):
                obj = objdir / (f.stem + ".o")
                cmd = [ctx.config["cc"], "-c", str(f), "-o", str(obj), *[a for d in
                       {str(p.parent) for p in ctx.ws.src.rglob("*.h")} for a in ("-I", d)],
                       *[str(ctx.x(c, suite)) for c in cfg.get("cflags", [])]]
                res = proc.run(cmd, cwd=str(ctx.ws.src), timeout=60)
                if res.ok:
                    targets.append(obj)
                else:
                    stage.log += f"$ compile {f.name}: failed\n{res.text()}\n"
    targets = [t for t in targets if Path(t).exists()]
    if not targets:
        stage.status = "skip"
        stage.message = "nothing to inspect (no artifact was built)"
        return
    if not proc.which("nm"):
        stage.status = "skip"
        stage.message = "`nm` is not available"
        return
    defined, undefined = symbols(targets)
    external = sorted(s for s in undefined - defined if s and s not in TOOLCHAIN
                      and not s.startswith(SANITIZER_PREFIXES))
    bad = [s for s in external if s not in allowed and s not in COMPILER_EMITTED
           and not any(re.fullmatch(p, s) for p in cfg.get("allowed_regex", []))]
    emitted = [s for s in external if s in COMPILER_EMITTED and s not in allowed]
    stage.items = [{"label": s, "ok": s not in bad and s not in emitted,
                    "note": "compiler-emitted?" if s in emitted else ""} for s in external]
    stage.log += "allowed: " + (", ".join(sorted(allowed)) or "(none)") + "\nexternal symbols used: " + (", ".join(external) or "(none)")
    if bad:
        stage.status = "fail"
        stage.message = f"forbidden: {', '.join(bad)}"
    elif emitted:
        stage.status = "warn"
        stage.message = f"{', '.join(emitted)} referenced (often inserted by the compiler for struct copies / zero-init)"
    else:
        stage.status = "pass"
        stage.message = "only allowed functions: " + (", ".join(external) or "none")
