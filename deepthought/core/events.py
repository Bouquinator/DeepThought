"""A tiny thread-safe pub/sub bus. Every engine change is published here."""

import queue
import threading


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._queues = []
        self._callbacks = []

    def subscribe(self, maxsize=10000):
        q = queue.Queue(maxsize=maxsize)
        with self._lock:
            self._queues.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def on(self, callback):
        with self._lock:
            self._callbacks.append(callback)

    def off(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def publish(self, event):
        with self._lock:
            queues = list(self._queues)
            callbacks = list(self._callbacks)
        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:  # a stalled client must never block the engine
                pass
        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:  # pragma: no cover - reporter bugs must not kill runs
                print(f"event callback error: {e}")
