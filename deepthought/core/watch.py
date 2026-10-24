"""Watch mode: poll the project's files and call back (debounced) on change."""

import threading
import time

from deepthought.core.workspace import fingerprint

BUSY = 0.1  # at most this share of one CPU core goes to scanning, even for huge folders


class Watcher:
    def __init__(self, path, on_change, interval=0.8, debounce=0.6):
        self.path = path
        self.on_change = on_change
        self.interval = interval
        self.debounce = debounce
        self._scan_time = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"watch-{path}")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _fingerprint(self):
        start = time.monotonic()
        try:
            return fingerprint(self.path)
        finally:
            self._scan_time = time.monotonic() - start

    def _wait(self, seconds):
        """Sleep, longer when scans are slow. True when the watcher was stopped."""
        return self._stop.wait(max(seconds, self._scan_time / BUSY))

    def _loop(self):
        try:
            last = self._fingerprint()
        except OSError:
            return
        while not self._wait(self.interval):
            try:
                cur = self._fingerprint()
                if cur == last:
                    continue
                # wait until the editor finished writing
                while not self._wait(self.debounce):
                    nxt = self._fingerprint()
                    if nxt == cur:
                        break
                    cur = nxt
            except OSError:
                continue
            last = cur
            if not self._stop.is_set():
                self.on_change()
