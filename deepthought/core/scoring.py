"""Moulinette-style grading.

grade = mandatory pass rate (0..100); bonus counts (up to +25) only when the
mandatory part is perfect. A failed build gives 0. Flags explain what an
evaluator or the moulinette would also object to.

Suite errors (problems in the test suite itself) are left out of the grade,
like skipped tests, and make the verdict "incomplete". When they leave a
category without any graded test, there is no grade (None).
"""

from deepthought.core.models import BUILD_ERROR, FAILED_STATUSES, PASS, SKIP, SUITE_ERROR


def _bucket():
    return {"passed": 0, "failed": 0, "skipped": 0, "suite_errors": 0, "total": 0}


def score_run(run):
    per_suite = {}
    for g in run.groups:
        s = per_suite.setdefault(g.suite, {"mandatory": _bucket(), "bonus": _bucket(), "extra": _bucket(),
                                           "build_failed": False})
        b = s[g.category if g.category in s else "mandatory"]
        if g.status == BUILD_ERROR and not g.tests:
            b["failed"] += 1
            b["total"] += 1
        if g.status == SUITE_ERROR and not g.tests:
            b["suite_errors"] += 1
        for t in g.tests.values():
            if t.status == SKIP:
                b["skipped"] += 1
                continue
            if t.status == SUITE_ERROR:
                b["suite_errors"] += 1
                continue
            b["total"] += 1
            if t.status == PASS:
                b["passed"] += 1
            elif t.status in FAILED_STATUSES:
                b["failed"] += 1
    stage_status = {st.id.split(":")[0]: st.status for st in run.stages}
    flags = []
    if any(st.status == "fail" and st.id.startswith("build") for st in run.stages):
        flags.append("build")
    for name in ("norminette", "forbidden", "relink", "rules", "files"):
        if stage_status.get(name) == "fail":
            flags.append(name)

    suites = {}
    total = {"mandatory": _bucket(), "bonus": _bucket(), "extra": _bucket()}
    for uid, s in per_suite.items():
        suites[uid] = _grade(s, flags)
        for cat in total:
            for k in total[cat]:
                total[cat][k] += s[cat][k]
    overall = _grade(total, flags)
    overall["suites"] = suites
    overall["flags"] = flags
    overall["suite_errors"] = sum(total[cat]["suite_errors"] for cat in ("mandatory", "bonus"))
    return overall


def _pct(b):
    return round(100.0 * b["passed"] / b["total"], 1) if b["total"] else None


def _grade(s, flags):
    m, b = s["mandatory"], s["bonus"]
    mp, bp = _pct(m), _pct(b)
    suite_errors = m["suite_errors"] + b["suite_errors"]
    if "build" in flags:
        grade = 0
    elif mp is None and m["suite_errors"]:
        grade = None  # every mandatory test hit a suite problem: nothing to grade
    elif mp is None:
        grade = 100 if (bp is None or bp == 100) else 0
    else:
        grade = int(mp) if mp < 100 else 100
    if grade == 100 and bp is not None:
        grade = 100 + int(25 * b["passed"] / b["total"])
    verdict = "ok" if grade is not None and grade >= 100 else "ko"
    if any(f in flags for f in ("norminette", "forbidden")):
        verdict = "ko"
    elif suite_errors and (grade is None or grade >= 100):
        verdict = "incomplete"  # nothing wrong found, but not everything could be tested
    return {"grade": grade, "verdict": verdict, "mandatory": dict(m, pct=mp), "bonus": dict(b, pct=bp),
            "extra": dict(s["extra"], pct=_pct(s["extra"]))}
