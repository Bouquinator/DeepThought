"""Watch mode: poll the project's files and call back (debounced) on change."""

import threading

from deepthought.core.workspace import fingerprint


class Watcher:
    def __init__(self, path, on_change, interval=0.8, debounce=0.6):
        self.path = path
        self.on_change = on_change
        self.interval = interval
        self.debounce = debounce
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"watch-{path}")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        try:
            last = fingerprint(self.path)
        except OSError:
            return
        while not self._stop.wait(self.interval):
            try:
                cur = fingerprint(self.path)
            except OSError:
                continue
            if cur == last:
                continue
            # wait until the editor finished writing
            while not self._stop.wait(self.debounce):
                nxt = fingerprint(self.path)
                if nxt == cur:
                    break
                cur = nxt
            last = cur
            if not self._stop.is_set():
                self.on_change()
