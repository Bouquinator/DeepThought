"""Server-Sent Events: one long-lived response streaming EventBus events."""

import json
import queue

HEARTBEAT = 15.0


def stream_events(handler, bus):
    q = bus.subscribe()
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Connection", "keep-alive")
        handler.send_header("X-Accel-Buffering", "no")
        handler.end_headers()
        handler.wfile.write(b"retry: 1500\n: connected\n\n")
        handler.wfile.flush()
        while True:
            try:
                ev = q.get(timeout=HEARTBEAT)
            except queue.Empty:
                handler.wfile.write(b": ping\n\n")
                handler.wfile.flush()
                continue
            batch = [ev]
            # coalesce bursts (hundreds of test events) into one write
            while len(batch) < 200:
                try:
                    batch.append(q.get_nowait())
                except queue.Empty:
                    break
            data = b"".join(b"data: " + json.dumps(e, default=str).encode() + b"\n\n" for e in batch)
            handler.wfile.write(data)
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        bus.unsubscribe(q)
        handler.close_connection = True
