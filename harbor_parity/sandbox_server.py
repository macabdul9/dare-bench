"""Minimal SandboxFusion-compatible /run_code service for DARE-Bench parity runs.

Implements the subset of SandboxFusion's API that DARE-Bench uses (scripts/tools/python_executor
and scripts/utils.call_code_executor): POST {"code", "language": "python", "files": {name: b64},
"fetch_files": [...], "run_timeout"} -> {"status", "run_result": {...}, "files": {name: b64}}.

Each request runs `python main.py` in a fresh empty directory containing only the uploaded files,
inside this container's Python, which is pinned to the same packages as the Harbor task image.
The Harbor side (dare_bench/sandbox_executor.py) produces the same run_result fields.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def run_code(request: dict) -> dict:
    run_dir = tempfile.mkdtemp(prefix="dare_sandbox_")
    try:
        for name, b64 in (request.get("files") or {}).items():
            with open(os.path.join(run_dir, os.path.basename(name)), "wb") as f:
                f.write(base64.b64decode(b64))
        with open(os.path.join(run_dir, "main.py"), "w") as f:
            f.write(request["code"])
        timeout = request.get("run_timeout") or 10
        start = time.time()
        try:
            proc = subprocess.run([sys.executable, "main.py"], cwd=run_dir, capture_output=True, text=True, timeout=timeout)
            run_result = {"status": "Finished", "execution_time": time.time() - start,
                          "return_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        except subprocess.TimeoutExpired as exc:
            decode = lambda b: b.decode(errors="replace") if isinstance(b, bytes) else (b or "")
            run_result = {"status": "TimeLimitExceeded", "execution_time": time.time() - start,
                          "return_code": None, "stdout": decode(exc.stdout), "stderr": decode(exc.stderr)}
        files = {}
        for name in request.get("fetch_files") or []:
            path = os.path.join(run_dir, os.path.basename(name))
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    files[name] = base64.b64encode(f.read()).decode()
        status = "Success" if run_result["status"] == "Finished" and run_result["return_code"] == 0 else "Failed"
        return {"status": status, "message": "", "compile_result": None, "run_result": run_result, "files": files}
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/run_code":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        data = json.dumps(run_code(body)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
