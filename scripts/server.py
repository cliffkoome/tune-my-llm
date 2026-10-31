"""Shared helpers: config, a throwaway test llama-server, HTTP requests.

The config is read from $TUNE_CONFIG or ./config.json (see config.example.json).
Every benchmark talks to its own server on a spare port; nothing here touches the
user's live server except optionally asking a llama-server router to unload
models so the GPU is free.
"""
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("TUNE_CONFIG", "config.json")).expanduser()


def load_config():
    if not CONFIG_PATH.exists():
        raise SystemExit(f"no config at {CONFIG_PATH}: copy config.example.json and edit it, or set TUNE_CONFIG")
    cfg = json.loads(CONFIG_PATH.read_text())
    cfg.setdefault("port", 8090)
    cfg.setdefault("results_dir", "results")
    cfg["results_dir"] = Path(cfg["results_dir"]).expanduser()
    cfg["results_dir"].mkdir(parents=True, exist_ok=True)
    return cfg


CFG = load_config()
PORT = CFG["port"]
URL = f"http://127.0.0.1:{PORT}"
KEY = os.environ.get(CFG.get("api_key_env") or "", "")
RESULTS = CFG["results_dir"]


def model(name):
    """Model entry from the config: alias, path and optional mmproj/draft."""
    try:
        m = CFG["models"][name]
    except KeyError:
        raise SystemExit(f"model {name!r} is not in the config (have: {', '.join(CFG['models'])})")
    return {**m, "path": str(Path(m["path"]).expanduser())}


def backend(name):
    """Binaries and environment for one backend, e.g. vulkan / hip / cuda / metal / both."""
    try:
        b = CFG["backends"][name]
    except KeyError:
        raise SystemExit(f"backend {name!r} is not in the config (have: {', '.join(CFG['backends'])})")
    return {"server": str(Path(b["server"]).expanduser()), "bench": str(Path(b.get("bench", "")).expanduser()),
            "env": b.get("env", {})}


def request(path, body=None, timeout=1800, url=URL):
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return json.loads(data) if data[:1] in (b"{", b"[") else data.decode()


def free_router():
    """Ask the user's llama-server router (if configured) to unload models so VRAM is free."""
    url = CFG.get("router_url")
    if not url:
        return
    try:
        models = request("/v1/models", url=url, timeout=5)["data"]
    except OSError:
        return
    loaded = [m["id"] for m in models if m.get("status", {}).get("value") not in (None, "unloaded")]
    for mid in loaded:
        request("/models/unload", {"model": mid}, url=url, timeout=60)
    if loaded:
        time.sleep(3)


def vram_mib():
    """Used VRAM in MiB (AMD sysfs or nvidia-smi), or -1 if unknown."""
    for f in Path("/sys/class/drm").glob("card*/device/mem_info_vram_used"):
        return int(f.read_text()) // 2**20
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout
        return int(out.split()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return -1


class Server:
    """A test llama-server on CFG['port'] for one model; use as a context manager."""

    def __init__(self, model_name, args, backend_name, log, prompts_dir=None):
        m, b = model(model_name), backend(backend_name)
        self.alias = m["alias"]
        self.cmd = [b["server"], "-m", m["path"], "--alias", m["alias"], "--host", "127.0.0.1",
                    "--port", str(PORT), "--jinja", "--metrics", *args]
        if prompts_dir:
            self.cmd += ["--log-prompts-dir", str(prompts_dir)]
        self.env = {**os.environ, **b["env"]}
        self.log = Path(log)
        self.proc = None

    def __enter__(self):
        try:
            request("/health", timeout=2)
            raise RuntimeError(f"port {PORT} is already in use; stop that server first")
        except OSError:
            pass
        free_router()
        self.log.parent.mkdir(parents=True, exist_ok=True)
        # Own process group, so stopping it never needs pkill -f (which can match the caller's shell).
        self.proc = subprocess.Popen(self.cmd, env=self.env, stdout=open(self.log, "w"), stderr=subprocess.STDOUT,
                                     start_new_session=True)
        for _ in range(600):
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited (out of memory or bad flag?), see {self.log}")
            try:
                if "ok" in json.dumps(request("/health", timeout=2)):
                    return self
            except OSError:
                pass
            time.sleep(1)
        raise RuntimeError("server did not become healthy in 10 minutes")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
        time.sleep(2)

    def metrics(self):
        """Prometheus counters, e.g. llamacpp:prompt_tokens_total."""
        out = {}
        for line in request("/metrics").splitlines():
            if line and not line.startswith("#"):
                k, v = line.rsplit(" ", 1)
                out[k] = float(v)
        return out
