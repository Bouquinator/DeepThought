"""Run state: what the UI and reporters display. Everything serialises to JSON."""

from dataclasses import asdict, dataclass, field

PENDING, RUNNING = "pending", "running"
PASS, FAIL, CRASH, TIMEOUT, LEAK = "pass", "fail", "crash", "timeout", "leak"
ERROR, SKIP, BUILD_ERROR = "error", "skip", "build_error"

FAILED_STATUSES = {FAIL, CRASH, TIMEOUT, LEAK, ERROR, BUILD_ERROR}
DONE_STATUSES = FAILED_STATUSES | {PASS, SKIP}


@dataclass
class TestState:
    tid: str
    id: str
    name: str
    gid: str
    desc: str = ""
    file: str = ""
    line: int = 0
    source: str = ""
    status: str = PENDING
    ms: int = 0
    input: str = ""        # last input announced by the test (dt_input / given)
    asserts: list = field(default_factory=list)
    logs: list = field(default_factory=list)
    leaks: dict = None
    signal: str = ""
    reason: str = ""
    output: str = ""
    exit: int = None
    repro: str = ""
    carried: bool = False
    regression: bool = False
    fixed: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class GroupState:
    gid: str
    suite: str
    name: str
    category: str
    runner: str
    variant: dict = field(default_factory=dict)
    status: str = PENDING
    message: str = ""
    build_log: str = ""
    build_cmd: str = ""
    cwd: str = ""
    tests: dict = field(default_factory=dict)  # id -> TestState (ordered)

    def to_dict(self, with_tests=True):
        d = {k: v for k, v in asdict(self).items() if k != "tests"}
        if with_tests:
            d["tests"] = [t.to_dict() for t in self.tests.values()]
        return d

    def refresh_status(self):
        if self.status in (BUILD_ERROR, SKIP, ERROR) and not self.tests:
            return
        states = [t.status for t in self.tests.values()]
        if not states:
            return
        if any(s in (PENDING, RUNNING) for s in states):
            self.status = RUNNING if any(s != PENDING for s in states) else self.status
        elif any(s in FAILED_STATUSES for s in states):
            self.status = FAIL
        elif all(s == SKIP for s in states):
            self.status = SKIP
        else:
            self.status = PASS


@dataclass
class StageState:
    id: str
    name: str
    status: str = PENDING
    ms: int = 0
    log: str = ""
    message: str = ""
    hint: str = ""
    items: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class RunState:
    id: str
    project: dict
    suites: list
    options: dict
    status: str = PENDING
    started: float = 0.0
    finished: float = 0.0
    stages: list = field(default_factory=list)
    groups: list = field(default_factory=list)
    score: dict = None
    error: str = ""
    base_run: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "project": self.project,
            "suites": self.suites,
            "options": self.options,
            "status": self.status,
            "started": self.started,
            "finished": self.finished,
            "stages": [s.to_dict() for s in self.stages],
            "groups": [g.to_dict() for g in self.groups],
            "score": self.score,
            "error": self.error,
            "base_run": self.base_run,
        }

    def summary(self):
        return {
            "id": self.id,
            "project": self.project,
            "status": self.status,
            "started": self.started,
            "finished": self.finished,
            "score": self.score,
            "suites": self.suites,
        }

    def all_tests(self):
        for g in self.groups:
            yield from g.tests.values()
