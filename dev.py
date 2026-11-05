"""Local preview: serve site/ and rebuild when sources change. Usage: python3 -I dev.py, stop with Ctrl+C.
Refresh the browser tab after "rebuilt"."""
import functools
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"  # localhost only; 0.0.0.0 would open it to the network
PORT = 8765
POLL = 1.0  # seconds between change checks
ROOT = Path(__file__).resolve().parent
WATCH = ["wiki", "data", "build.py", "site.js", "style.css", "i18n_en.json"]


def snapshot():
    """Newest modification time among the watched files."""
    files = (f for w in WATCH for f in ([ROOT / w] if (ROOT / w).is_file() else (ROOT / w).rglob("*")))
    return max((f.stat().st_mtime for f in files if f.is_file() and "__pycache__" not in f.parts), default=0)


def build():
    # a fresh process per build: wiki modules keep state at import time
    # --pages like GitHub Pages: icons as files, not inline base64
    ok = subprocess.run([sys.executable, "-I", str(ROOT / "build.py"), "--pages"], cwd=ROOT).returncode == 0
    print("rebuilt" if ok else "build failed, serving the previous site", flush=True)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


build()
server = ThreadingHTTPServer((HOST, PORT), functools.partial(Quiet, directory=str(ROOT / "site")))
threading.Thread(target=server.serve_forever, daemon=True).start()
print(f"http://{HOST}:{PORT}/", flush=True)
seen = snapshot()
try:
    while True:
        time.sleep(POLL)
        now = snapshot()
        if now != seen:
            seen = now
            build()
except KeyboardInterrupt:
    server.shutdown()
