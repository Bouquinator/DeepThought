"""Streaming terminal reporter (also the CI reporter: plain text, exit code)."""

import os
import re
import sys
import threading
from xml.sax.saxutils import escape as xml_escape

from deepthought.core.models import FAILED_STATUSES, PASS, SKIP

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
CODES = {"red": 31, "green": 32, "yellow": 33, "blue": 34, "magenta": 35, "cyan": 36, "dim": 2, "bold": 1}


def c(text, *styles):
    if not USE_COLOR or not styles:
        return str(text)
    return "".join(f"\x1b[{CODES[s]}m" for s in styles) + str(text) + "\x1b[0m"


ICONS = {
    "pass": ("✓", "green"), "fail": ("✗", "red"), "crash": ("💥", "red"), "timeout": ("⏱", "magenta"),
    "leak": ("💧", "yellow"), "error": ("!", "red"), "build_error": ("⚒", "red"), "skip": ("–", "dim"),
    "warn": ("!", "yellow"), "pending": ("·", "dim"), "running": ("…", "cyan"),
}


def icon(status):
    ch, color = ICONS.get(status, ("?", "dim"))
    return c(ch, color)


def visible(s, limit=400):
    """Make invisible characters visible: \\n, \\t, \\0, trailing spaces, bytes."""
    if s is None:
        return c("(none)", "dim")
    out = []
    for ch in s[:limit]:
        o = ord(ch)
        if ch == "\n":
            out.append(c("\\n", "dim"))
        elif ch == "\t":
            out.append(c("\\t", "dim"))
        elif o == 0:
            out.append(c("\\0", "dim"))
        elif o < 0x20 or 0x7f <= o <= 0xff:
            out.append(c(f"\\x{o:02x}", "dim"))
        else:
            out.append(ch)
    text = "".join(out)
    stripped = s.rstrip(" ")
    if len(stripped) != len(s) and len(s) <= limit:
        text = text[: len(text) - (len(s) - len(stripped))] + c("·" * (len(s) - len(stripped)), "yellow")
    if len(s) > limit:
        text += c(f"… (+{len(s) - limit} chars)", "dim")
    return text


class PlainReporter:
    def __init__(self, verbose=False, quiet=False, stream=sys.stdout):
        self.verbose = verbose
        self.quiet = quiet
        self.out = stream
        self.done_tests = 0
        self.total_tests = 0
        self.printed_groups = set()
        self.lock = threading.Lock()
        self.progress_shown = False

    def _print(self, text=""):
        self._clear_progress()
        print(text, file=self.out, flush=True)

    def _clear_progress(self):
        if self.progress_shown:
            self.out.write("\r\x1b[2K")
            self.progress_shown = False

    def _progress(self):
        if not USE_COLOR or self.quiet or not self.total_tests:
            return
        width = 30
        fill = int(width * self.done_tests / self.total_tests)
        bar = c("█" * fill, "cyan") + c("░" * (width - fill), "dim")
        self.out.write(f"\r\x1b[2K  {bar} {self.done_tests}/{self.total_tests} tests")
        self.out.flush()
        self.progress_shown = True

    def __call__(self, ev):
        with self.lock:
            t = ev["type"]
            if t == "snapshot" and ev["run"]["status"] == "pending":
                run = ev["run"]
                self._print(c("DeepThought", "bold", "cyan") + c(f"  ·  {run['project']['name']}", "bold")
                            + c(f"  ({run['project']['kind']})  {run['project']['path']}", "dim"))
                for s in run["suites"]:
                    self._print(c(f"  suite {s['name']} v{s['version']} [{s['source']}]", "dim"))
                self._print()
            elif t == "stage" and ev["stage"]["status"] not in ("pending", "running"):
                st = ev["stage"]
                if st["id"] == "workspace" and not self.verbose:
                    return
                line = f"  {icon(st['status'])} {st['name']:<22} {c(st['message'], 'dim')}"
                if st.get("hint"):
                    line += c(f"  → {st['hint']}", "yellow")
                self._print(line)
                if st["status"] == "fail" and st["id"].startswith("build") and not self.quiet:
                    self._print(c("\n".join("      " + l for l in st["log"].splitlines()[-25:]), "dim"))
                if st["id"] == "norminette" and st["items"] and self.verbose:
                    for it in st["items"][:30]:
                        self._print(c(f"      {it['file']}:{it['line']}:{it['col']} {it['code']} {it['msg']}", "dim"))
            elif t == "tests":
                self.total_tests += sum(1 for x in ev["tests"] if not x["carried"])
                self._progress()
            elif t == "test" and ev["test"]["status"] not in ("pending", "running"):
                self.done_tests += 1
                if self.verbose:
                    tst = ev["test"]
                    self._print(f"    {icon(tst['status'])} {tst['id']:<40} {c(tst['desc'], 'dim')}")
                self._progress()
            elif t == "group":
                g = ev["group"]
                if g["status"] in ("pending", "running") or g["gid"] in self.printed_groups:
                    return
                self.printed_groups.add(g["gid"])
                self._group_line(g)

    def _group_line(self, g, tests=None):
        msg = g.get("message", "")
        self._print(f"  {icon(g['status'])} {c(g['name'], 'bold')} {c('[' + g['category'] + ']', 'dim')}"
                    + (f"  {c(msg, 'dim')}" if msg else ""))
        if g["status"] == "build_error" and not self.quiet:
            if g.get("build_cmd"):
                self._print(c(f"      $ {g['build_cmd'][:300]}", "dim"))
            for line in (g.get("build_log") or "").splitlines()[-20:]:
                self._print(c(f"      {line}", "red"))

    def summary(self, run):
        self._clear_progress()
        self._print()
        failed = [(g, t) for g in run["groups"] for t in g["tests"] if t["status"] in FAILED_STATUSES]
        if failed and not self.quiet:
            self._print(c(f"─── {len(failed)} failing test(s) " + "─" * 40, "bold"))
            for g, t in failed[:60]:
                self._failure(g, t)
            if len(failed) > 60:
                self._print(c(f"  … and {len(failed) - 60} more (open the web UI: ./dt)", "dim"))
        self._totals(run)

    def _failure(self, g, t):
        self._print()
        tag = {"crash": t.get("signal") or "CRASH", "timeout": "TIMEOUT", "leak": "LEAK",
               "build_error": "BUILD ERROR", "error": "ERROR"}.get(t["status"], "FAIL")
        flag = c("  REGRESSION", "magenta", "bold") if t.get("regression") else ""
        self._print(f"  {icon(t['status'])} {c(tag, 'red', 'bold')} {c(g['name'], 'dim')} › {c(t['id'], 'bold')}{flag}")
        if t["desc"]:
            self._print(c(f"    {t['desc']}", "dim"))
        if t.get("reason"):
            self._print(c(f"    {t['reason'].splitlines()[0]}", "yellow"))
        for a in t["asserts"][:5]:
            where = f" ({os.path.basename(a['file'])}:{a['line']})" if a.get("file") else ""
            self._print(f"    {c('›', 'red')} {a['msg']}{c(where, 'dim')}")
            self._print(f"      expected: {visible(a.get('expected'))}")
            self._print(f"      actual:   {visible(a.get('actual'))}")
        if len(t["asserts"]) > 5:
            self._print(c(f"      … {len(t['asserts']) - 5} more failed check(s)", "dim"))
        if t.get("leaks"):
            self._print(c(f"    leaked {t['leaks']['bytes']} byte(s) in {t['leaks']['count']} allocation(s)", "yellow"))
        if t["status"] in ("build_error", "crash", "error") and t.get("output"):
            lines = [l for l in t["output"].splitlines() if l.strip()]
            if t["status"] == "build_error":
                lines = [l for l in lines if re.search(r"error|undefined|referenced", l, re.I)] or lines
            for l in lines[:8]:
                self._print(c(f"      │ {l[:200]}", "dim"))
        for log in t.get("logs", [])[:3]:
            self._print(c(f"    · {log}", "dim"))
        if t.get("repro"):
            self._print(c(f"    repro: {t['repro']}", "dim"))

    def _totals(self, run):
        score = run.get("score") or {}
        counts = {}
        for g in run["groups"]:
            for t in g["tests"]:
                counts[t["status"]] = counts.get(t["status"], 0) + 1
        parts = []
        for status in ("pass", "fail", "crash", "timeout", "leak", "error", "skip"):
            if counts.get(status):
                parts.append(f"{icon(status)} {counts[status]} {status}")
        self._print(c("─" * 60, "dim"))
        self._print("  " + "   ".join(parts))
        m, b = score.get("mandatory", {}), score.get("bonus", {})
        line = f"  mandatory {m.get('passed', 0)}/{m.get('total', 0)}"
        if b.get("total"):
            line += f"   bonus {b.get('passed', 0)}/{b.get('total', 0)}"
        grade = score.get("grade", 0)
        color = "green" if grade >= 100 and score.get("verdict") == "ok" else "red"
        line += "   grade " + c(f"{grade}/100", color, "bold")
        if score.get("flags"):
            line += c(f"   ⚠ {', '.join(score['flags'])}", "yellow")
        if score.get("regressions"):
            line += c(f"   {score['regressions']} regression(s)", "magenta")
        if score.get("fixed"):
            line += c(f"   {score['fixed']} fixed", "green")
        self._print(line)
        if run["status"] == "cancelled":
            self._print(c("  (run cancelled)", "yellow"))
        if run.get("error"):
            self._print(c(f"  engine error: {run['error']}", "red"))


def exit_code(run):
    if run.get("error"):
        return 2
    score = run.get("score") or {}
    failed = any(t["status"] in FAILED_STATUSES for g in run["groups"] for t in g["tests"])
    failed = failed or any(g["status"] == "build_error" for g in run["groups"])
    failed = failed or bool(score.get("flags"))
    return 1 if failed else 0


def junit(run):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<testsuites>"]
    for g in run["groups"]:
        tests = g["tests"]
        fails = sum(1 for t in tests if t["status"] in FAILED_STATUSES)
        skips = sum(1 for t in tests if t["status"] == SKIP)
        lines.append(f'  <testsuite name="{xml_escape(g["name"])}" tests="{len(tests)}" failures="{fails}" skipped="{skips}">')
        for t in tests:
            lines.append(f'    <testcase classname="{xml_escape(g["gid"])}" name="{xml_escape(t["id"])}" time="{t["ms"] / 1000:.3f}">')
            if t["status"] in FAILED_STATUSES:
                detail = "\n".join(f"{a['msg']}: expected {a.get('expected')!r}, got {a.get('actual')!r}" for a in t["asserts"])
                lines.append(f'      <failure type="{t["status"]}" message="{xml_escape(t.get("reason") or t["status"])}">'
                             f"{xml_escape(detail)}</failure>")
            elif t["status"] == SKIP:
                lines.append("      <skipped/>")
            lines.append("    </testcase>")
        lines.append("  </testsuite>")
    lines.append("</testsuites>")
    return "\n".join(lines) + "\n"


__all__ = ["PlainReporter", "exit_code", "junit", "visible", "c", "icon", "PASS"]
