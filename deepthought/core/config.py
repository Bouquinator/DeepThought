"""User configuration stored in ~/.deepthought/config.toml."""

import os
import threading

from deepthought.core import paths, toml

DEFAULTS = {
    "cc": "cc",
    "cflags": ["-Wall", "-Wextra", "-g"],
    "timeout": 5.0,
    "jobs": max(2, os.cpu_count() or 2),
    "sanitize": False,
    "leaks": True,
    "norminette": True,
    "cache_dir": "",
    "theme": "dark",
    "port": 4242,
    "open_browser": True,
    "check_updates": True,
    "editor": "vscode",
    "disabled_suites": [],
}


class Config:
    def __init__(self, path=None):
        self.path = path or paths.data_dir() / "config.toml"
        self._lock = threading.Lock()
        self.values = dict(DEFAULTS)
        if self.path.exists():
            try:
                self.values.update(toml.load_file(self.path))
            except (OSError, toml.TOMLDecodeError) as e:
                print(f"warning: ignoring invalid config {self.path}: {e}")

    def __getitem__(self, key):
        return self.values.get(key, DEFAULTS.get(key))

    def get(self, key, default=None):
        return self.values.get(key, default)

    def update(self, changes):
        with self._lock:
            for k, v in changes.items():
                if k not in DEFAULTS:
                    raise KeyError(f"unknown setting: {k}")
                expected = type(DEFAULTS[k])
                if expected is float and isinstance(v, int):
                    v = float(v)
                if not isinstance(v, expected):
                    raise ValueError(f"{k} must be {expected.__name__}")
                self.values[k] = v
            self.save()

    def save(self):
        changed = {k: v for k, v in self.values.items() if DEFAULTS.get(k) != v}
        self.path.write_text(toml.dumps(changed))

    def to_dict(self):
        return dict(self.values)
