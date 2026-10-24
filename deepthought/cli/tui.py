"""Interactive terminal UI (curses, stdlib). Same engine and events as the web UI.

Keys: ↑/↓ or j/k move · enter collapse group · f failed only · r retest all ·
      R retest failed · w watch · s sanitizer · PgUp/PgDn scroll details · q quit
"""

import curses
import queue
import textwrap
import time
from pathlib import Path

from deepthought.core.executor import RunError
from deepthought.core.models import FAILED_STATUSES

ICON = {"pass": "✓", "fail": "✗", "crash": "✸", "timeout": "⏱", "leak": "◍", "error": "!",
        "build_error": "⚒", "skip": "–", "pending": "·", "running": "◌", "warn": "!"}
COLOR = {"pass": 1, "fail": 2, "crash": 2, "error": 2, "build_error": 3, "timeout": 4, "leak": 3,
         "warn": 3, "skip": 5, "pending": 5, "running": 6}


def visible(s):
    if s is None:
        return "(null)"
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\n":
            out.append("↵\n")
        elif ch == "\t":
            out.append("→")
        elif o == 0:
            out.append("\\0")
        elif o < 32 or 127 <= o <= 159:
            out.append(f"\\x{o:02x}")
        else:
            out.append(ch)
    text = "".join(out)
    if s.endswith(" "):
        text = text.rstrip(" ") + "·" * (len(s) - len(s.rstrip(" ")))
    return text


class Tui:
    def __init__(self, manager, project, suites):
        self.manager = manager
        self.project = str(Path(project).resolve())
        self.suites = suites
        self.events = manager.bus.subscribe()
        self.run_id = None
        self.cursor = 0
        self.scroll = 0
        self.detail_scroll = 0
        self.failed_only = False
        self.collapsed = set()
        self.options = {}
        self.watching = False
        self.message = ""

    # ------------------------------------------------------------ data
    @property
    def run(self):
        return self.manager.get(self.run_id) if self.run_id else None

    def rows(self, run):
        rows = []
        for g in run["groups"]:
            tests = [t for t in g["tests"] if not self.failed_only or t["status"] in FAILED_STATUSES]
            if self.failed_only and not tests and g["status"] != "build_error":
                continue
            rows.append(("group", g, None))
            if g["gid"] not in self.collapsed:
                rows.extend(("test", g, t) for t in tests)
        return rows

    def start(self, failed=False):
        try:
            if failed and self.run_id:
                r = self.manager.rerun(self.run_id, failed_only=True, options=self.options)
            else:
                r = self.manager.start(self.project, self.suites, self.options)
            self.run_id = r.id
            self.message = ""
        except RunError as e:
            self.message = str(e)

    # ------------------------------------------------------------ drawing
    def put(self, win, y, x, text, attr=0, width=None):
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        width = min(width or w - x, w - x)
        try:
            win.addnstr(y, x, text.replace("\n", " "), max(0, width - (1 if y == h - 1 else 0)), attr)
        except curses.error:
            pass

    def draw(self, scr):
        scr.erase()
        h, w = scr.getmaxyx()
        run = self.run
        if not run:
            self.put(scr, 1, 2, self.message or "Starting…", curses.A_BOLD)
            scr.refresh()
            return
        total = sum(len(g["tests"]) for g in run["groups"])
        done = sum(1 for g in run["groups"] for t in g["tests"] if t["status"] not in ("pending", "running"))
        failed = sum(1 for g in run["groups"] for t in g["tests"] if t["status"] in FAILED_STATUSES)
        score = run.get("score") or {}
        grade = f"{score.get('grade')}/100" if score else "…"
        head = f" DeepThought · {run['project']['name']} ({run['project']['kind']}) · {run['status']} · {done}/{total} tests"
        self.put(scr, 0, 0, head.ljust(w), curses.A_REVERSE | curses.A_BOLD)
        self.put(scr, 0, max(0, w - len(grade) - 2), grade, curses.A_REVERSE | curses.A_BOLD)
        stages = "  ".join(f"{ICON.get(st['status'], '?')} {st['name']}" for st in run["stages"] if st["id"] != "workspace")
        self.put(scr, 1, 1, stages, curses.color_pair(5))
        bar_w = max(10, w // 3)
        fill = int(bar_w * done / total) if total else 0
        bad = int(bar_w * failed / total) if total else 0
        self.put(scr, 2, 1, "█" * (fill - bad), curses.color_pair(6))
        self.put(scr, 2, 1 + fill - bad, "█" * bad, curses.color_pair(2))
        self.put(scr, 2, 1 + fill, "░" * (bar_w - fill), curses.color_pair(5))
        if failed:
            self.put(scr, 2, bar_w + 3, f"{failed} failing", curses.color_pair(2))

        left_w = min(48, w // 2 - 1)
        top, bottom = 4, h - 2
        rows = self.rows(run)
        self.cursor = max(0, min(self.cursor, len(rows) - 1))
        visible_h = bottom - top
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + visible_h:
            self.scroll = self.cursor - visible_h + 1
        for i, (kind, g, t) in enumerate(rows[self.scroll:self.scroll + visible_h]):
            y = top + i
            sel = self.scroll + i == self.cursor
            attr = curses.A_REVERSE if sel else 0
            if kind == "group":
                arrow = "▸" if g["gid"] in self.collapsed else "▾"
                n_pass = sum(1 for x in g["tests"] if x["status"] == "pass")
                label = f"{arrow} {ICON.get(g['status'], '?')} {g['name']}"
                self.put(scr, y, 0, label.ljust(left_w), attr | curses.A_BOLD | curses.color_pair(COLOR.get(g["status"], 0)))
                self.put(scr, y, left_w - 8, f"{n_pass}/{len(g['tests'])}".rjust(7), attr)
            else:
                label = f"    {ICON.get(t['status'], '?')} {t['id']}"
                self.put(scr, y, 0, label.ljust(left_w), attr | curses.color_pair(COLOR.get(t["status"], 0)))
        for y in range(top, bottom):
            self.put(scr, y, left_w, "│", curses.color_pair(5))
        if rows:
            self.draw_detail(scr, rows[self.cursor], top, left_w + 2, bottom, w - left_w - 3)
        keys = " ↑↓ move · ⏎ fold · f failed · r retest · R retest failed · w watch · s sanitizer · PgUp/PgDn scroll · q quit "
        flags = ("  [watching]" if self.watching else "") + ("  [sanitizer]" if self.options.get("sanitize") else "")
        self.put(scr, h - 1, 0, (keys + flags + "  " + self.message).ljust(w), curses.A_REVERSE)
        scr.refresh()

    def detail_lines(self, row, width):
        kind, g, t = row
        lines = []

        def add(text="", attr=0):
            for part in str(text).split("\n") or [""]:
                wrapped = textwrap.wrap(part, width, replace_whitespace=False, drop_whitespace=False) or [""]
                lines.extend((x, attr) for x in wrapped)

        if kind == "group":
            add(g["name"], curses.A_BOLD)
            add(f"{g['status']} · {g['category']} · runner {g['runner']}", curses.color_pair(COLOR.get(g["status"], 0)))
            if g.get("message"):
                add(g["message"])
            if g.get("build_cmd"):
                add()
                add("Compile command:", curses.A_BOLD)
                add(g["build_cmd"], curses.color_pair(5))
            if g.get("build_log"):
                add()
                add("Build log:", curses.A_BOLD)
                add(g["build_log"])
            return lines
        add(t["id"], curses.A_BOLD)
        add(f"{t['status'].upper()}{'  (' + t['signal'] + ')' if t.get('signal') else ''}  {t['ms']} ms"
            + ("  REGRESSION" if t.get("regression") else ""), curses.color_pair(COLOR.get(t["status"], 0)) | curses.A_BOLD)
        if t["desc"]:
            add(t["desc"])
        if t.get("reason"):
            add()
            add(t["reason"], curses.color_pair(3))
        for a in t["asserts"]:
            add()
            add(f"✗ {a['msg']}  ({Path(a.get('file') or '').name}:{a.get('line')})", curses.color_pair(2))
            add("  expected: " + visible(a.get("expected")), curses.color_pair(1))
            add("  actual:   " + visible(a.get("actual")), curses.color_pair(2))
        if t.get("leaks"):
            add()
            add(f"Leaked {t['leaks']['bytes']} byte(s) in {t['leaks']['count']} allocation(s)", curses.color_pair(3))
        for log in t.get("logs", []):
            add(f"· {log}", curses.color_pair(5))
        if t.get("output"):
            add()
            add("Output:", curses.A_BOLD)
            from deepthought.cli.reporter_plain import decode_output
            add(visible(decode_output(t["output"])))
        if t.get("source"):
            add()
            add("Test code:", curses.A_BOLD)
            for i, line in enumerate(t["source"].split("\n")):
                add(f"{t['line'] + i:4} {line.expandtabs(4)}", curses.color_pair(5))
        if t.get("repro"):
            add()
            add("Reproduce:", curses.A_BOLD)
            add(t["repro"], curses.color_pair(6))
        return lines

    def draw_detail(self, scr, row, top, x, bottom, width):
        lines = self.detail_lines(row, max(20, width))
        self.detail_scroll = max(0, min(self.detail_scroll, max(0, len(lines) - (bottom - top))))
        for i, (text, attr) in enumerate(lines[self.detail_scroll:self.detail_scroll + bottom - top]):
            self.put(scr, top + i, x, text, attr, width)

    # ------------------------------------------------------------ loop
    def handle(self, key):
        run = self.run
        rows = self.rows(run) if run else []
        if key in (ord("q"), 27):
            return False
        if key in (curses.KEY_DOWN, ord("j")):
            self.cursor += 1
            self.detail_scroll = 0
        elif key in (curses.KEY_UP, ord("k")):
            self.cursor = max(0, self.cursor - 1)
            self.detail_scroll = 0
        elif key == curses.KEY_NPAGE:
            self.detail_scroll += 10
        elif key == curses.KEY_PPAGE:
            self.detail_scroll = max(0, self.detail_scroll - 10)
        elif key in (10, 13, curses.KEY_ENTER, ord(" ")) and rows:
            kind, g, _ = rows[min(self.cursor, len(rows) - 1)]
            self.collapsed ^= {g["gid"]}
        elif key == ord("f"):
            self.failed_only = not self.failed_only
            self.cursor = 0
        elif key == ord("s"):
            self.options["sanitize"] = not self.options.get("sanitize")
            self.message = "sanitizer " + ("on" if self.options["sanitize"] else "off") + " (applies to the next run)"
        elif key == ord("r") and (not run or run["status"] not in ("pending", "running")):
            self.start()
        elif key == ord("R") and run and run["status"] not in ("pending", "running"):
            self.start(failed=True)
        elif key == ord("w"):
            self.watching = not self.watching
            self.manager.watch(self.project, self.watching, self.options, self.suites)
            self.message = "watching: save a file to re-run" if self.watching else "watch off"
        return True

    def loop(self, scr):
        curses.curs_set(0)
        curses.use_default_colors()
        for i, c in enumerate((curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_MAGENTA,
                               8 if curses.COLORS > 8 else curses.COLOR_WHITE, curses.COLOR_CYAN), start=1):
            curses.init_pair(i, c, -1)
        scr.timeout(120)
        self.start()
        dirty = True
        instant = 0  # getch() returning "no key" at once, again and again: the terminal is gone
        while True:
            try:
                while True:
                    ev = self.events.get_nowait()
                    if ev.get("type") == "snapshot" and ev["run"]["project"]["path"] == self.project:
                        self.run_id = ev["run_id"]  # follow watch-mode runs
                    dirty = True
            except queue.Empty:
                pass
            if dirty:
                self.draw(scr)
                dirty = False
            asked = time.monotonic()
            key = scr.getch()
            if key == -1:
                instant = instant + 1 if time.monotonic() - asked < 0.01 else 0
                if instant >= 50:
                    break
                continue
            instant = 0
            if key == curses.KEY_RESIZE:
                dirty = True
                continue
            if not self.handle(key):
                break
            dirty = True


def run_tui(path, suites=None):
    from deepthought.core.config import Config
    from deepthought.core.executor import RunManager
    from deepthought.core.registry import Registry

    config = Config()
    manager = RunManager(config, Registry(config))
    tui = Tui(manager, path, suites)
    try:
        curses.wrapper(tui.loop)
    except KeyboardInterrupt:
        pass
    if tui.run_id:
        manager.cancel(tui.run_id)
        time.sleep(0.1)
    return 0
