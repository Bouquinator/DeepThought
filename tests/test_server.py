import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from tests.helpers import FIXTURES, fresh_home


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fresh_home()
        from deepthought.server.app import App, Handler

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.app = App()
        cls.server.token = "secret-token"
        cls.server.bind_host = "127.0.0.1"
        cls.server.verbose = False
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def req(self, path, method="GET", body=None, token="secret-token", host=None):
        r = urllib.request.Request(self.base + path, method=method,
                                   data=json.dumps(body).encode() if body is not None else None)
        if token:
            r.add_header("X-DT-Token", token)
        if host:
            r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def test_token_required(self):
        self.assertEqual(self.req("/api/state", token=None)[0], 401)
        self.assertEqual(self.req("/api/state", token="wrong")[0], 401)

    def test_foreign_host_rejected(self):
        self.assertEqual(self.req("/api/state", host="evil.example")[0], 403)

    def test_state_and_project_run(self):
        code, state = self.req("/api/state")
        self.assertEqual(code, 200)
        self.assertTrue(any(s["id"] == "get_next_line" for s in state["suites"]))
        code, proj = self.req("/api/projects", "POST", {"path": str(FIXTURES / "gnl_good")})
        self.assertEqual((code, proj["kind"]), (200, "get_next_line"))
        code, run = self.req("/api/runs", "POST", {"project": proj["path"], "options": {"norminette": False}})
        self.assertEqual(code, 200)
        self.server.app.manager.contexts[run["id"]]  # exists
        import time
        for _ in range(300):
            code, data = self.req(f"/api/runs/{run['id']}")
            if data["status"] not in ("pending", "running"):
                break
            time.sleep(0.1)
        self.assertEqual(data["status"], "done")
        self.assertGreater(len(data["groups"]), 0)

    def test_project_config_and_link(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            code, proj = self.req("/api/projects", "POST", {"path": d, "kind": "my_project"})
            self.assertEqual((code, proj["kind"], proj["mode"], proj["suites"]), (200, "my_project", "kind", []))
            code, proj = self.req("/api/projects/link", "POST", {"path": d, "suite": "get_next_line"})
            self.assertEqual((proj["mode"], proj["suites"]), ("linked", ["get_next_line"]))
            code, proj = self.req("/api/projects/config", "POST", {"path": d, "kind": "", "suites": []})
            self.assertEqual(proj["mode"], "auto")
            code, err = self.req("/api/projects/link", "POST", {"path": d, "suite": "nope"})
            self.assertEqual(code, 400)

    def test_browse_survives_unreadable_entries(self):
        """~/sgoinfre on 42 machines: stat() can fail with Permission denied."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "closed"))
            os.mkdir(os.path.join(d, "closed", "inside"))
            os.symlink(os.path.join(d, "closed", "inside"), os.path.join(d, "sgoinfre"))
            open(os.path.join(d, "Makefile"), "w").close()
            os.chmod(os.path.join(d, "closed"), 0)
            try:
                if os.access(os.path.join(d, "closed", "inside"), os.F_OK):
                    self.skipTest("running with privileges that ignore permissions")
                code, data = self.req(f"/api/fs/browse?path={d}")
                self.assertEqual(code, 200, data)
                entry = next(x for x in data["dirs"] if x["name"] == "sgoinfre")
                self.assertTrue(entry["locked"])
                self.assertIn("Makefile", data["files"])
            finally:
                os.chmod(os.path.join(d, "closed"), 0o755)

    def test_static_and_traversal(self):
        with urllib.request.urlopen(self.base + "/app.js") as r:
            self.assertIn("text/javascript", r.headers["Content-Type"])
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.base + "/../../etc/passwd")
        cm.exception.close()


if __name__ == "__main__":
    unittest.main()
