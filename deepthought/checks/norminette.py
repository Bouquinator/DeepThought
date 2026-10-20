"""42's norminette, when installed."""

import re

from deepthought.core import proc

LINE_RE = re.compile(r"^(?P<file>.+?): (?P<state>OK!|Error!)")
ERR_RE = re.compile(r"^\s*Error:\s*(?P<code>\S+)\s*\(line:\s*(?P<line>\d+),\s*col:\s*(?P<col>\d+)\):\s*(?P<msg>.*)")


def check(ctx, suite, stage):
    if not ctx.options.get("norminette", ctx.config["norminette"]):
        stage.status = "skip"
        stage.message = "disabled in settings"
        return
    exe = proc.which("norminette")
    if not exe:
        stage.status = "skip"
        stage.message = "norminette is not installed"
        stage.hint = "python3 -m pip install --user norminette"
        return
    cfg = suite.norminette
    targets = [str(ctx.ws.src / ctx.x(p, suite)) for p in cfg.get("paths", [])] or [str(ctx.ws.src)]
    with ctx.slots:
        res = proc.run([exe, *targets], cwd=str(ctx.ws.src), timeout=120, tracker=ctx.tracker)
    stage.ms = res.ms
    out = res.text().replace(str(ctx.ws.src) + "/", "")
    stage.log = out
    current = None
    bad_files = 0
    for line in out.splitlines():
        m = LINE_RE.match(line)
        if m:
            current = m.group("file")
            if m.group("state") == "Error!":
                bad_files += 1
            continue
        m = ERR_RE.match(line)
        if m and current:
            stage.items.append({"file": current, "line": int(m.group("line")), "col": int(m.group("col")),
                                "code": m.group("code"), "msg": m.group("msg")})
    if bad_files or (res.code != 0 and not stage.items and "Error" in out):
        stage.status = "fail"
        stage.message = f"{len(stage.items)} error(s) in {bad_files} file(s): the moulinette would give 0"
    else:
        stage.status = "pass"
        stage.message = "norm OK"
