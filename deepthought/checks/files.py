"""[files] required = ["libft.h", "Makefile"]: files that must exist in the project."""


def check(ctx, suite, stage):
    required = suite.files.get("required", [])
    stage.items = [{"label": f, "ok": any(ctx.ws.src.glob(ctx.x(f, suite)))} for f in required]
    missing = [i["label"] for i in stage.items if not i["ok"]]
    stage.status = "fail" if missing else "pass"
    stage.message = f"missing: {', '.join(missing)}" if missing else f"{len(required)} required file(s) present"
