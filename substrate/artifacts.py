"""Canonical serialisation, hashing, and run manifests (the provenance of a run).

Each run directory runs/<EXP>/<run_id>/ contains:
  config.json            inputs, seeds, parameters
  deterministic.json     everything that must be bit-identical on re-execution
  nondeterministic.json  wall-clock timings (observations of the instrument)
  manifest.json          environment, code version, file hashes, deterministic hash
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical(obj))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict:
    def g(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    commit = g("rev-parse", "HEAD")
    dirty = bool(g("status", "--porcelain", "--", "substrate", "experiments"))
    return {"commit": commit or None, "code_dirty": dirty}


def code_hash() -> str:
    """Hash of the instrument source (substrate/ + experiments/), independent of git."""
    h = hashlib.sha256()
    for d in ("substrate", "experiments"):
        base = os.path.join(ROOT, d)
        for dp, _, fs in sorted(os.walk(base)):
            if "__pycache__" in dp:
                continue
            for f in sorted(fs):
                if f.endswith(".py"):
                    p = os.path.join(dp, f)
                    h.update(os.path.relpath(p, ROOT).encode())
                    with open(p, "rb") as fh:
                        h.update(fh.read())
    return h.hexdigest()


def environment() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "dependencies": "stdlib only"}


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump(path: str, obj: Any) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True, allow_nan=False)
        f.write("\n")
    return sha256_file(path)


def load(path: str) -> Any:
    with open(path) as f:
        return json.load(f)
