"""Registry I/O and the experiment runner (the "computational court").

Sources of truth
  experiments/<exp>.py           SPEC (question, hypotheses, falsification) + code
  research/registries/*.json     hand-curated registries (hypotheses, nomenclature, ...)
  research/registries/evidence_sources.json   hand-curated evidence (literature,
                                              derivations, interpretations)
  research/registries/evidence.jsonl          machine evidence, append-only
  research/registries/executions.jsonl        one line per execution, append-only
  research/registries/experiments.json        generated: SPEC + run status
  runs/<EXP>/<det_hash12>/                    content-addressed run outputs

Reproduction: a run is *reproduced* when two or more executions with the same
config hash produced the same deterministic hash. A mismatch under the same
config and code hash is appended to the failure ledger automatically.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from typing import Dict, List

from . import artifacts as A
from .epistemic import check_evidence_record

REG = os.path.join(A.ROOT, "research", "registries")
RUNS = os.path.join(A.ROOT, "runs")


def reg_path(name: str) -> str:
    return os.path.join(REG, name)


def load_json(name: str, default=None):
    p = reg_path(name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def save_json(name: str, obj) -> None:
    with open(reg_path(name), "w") as f:
        json.dump(obj, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")


def read_jsonl(name: str) -> List[dict]:
    p = reg_path(name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(name: str, rec: dict) -> None:
    with open(reg_path(name), "a") as f:
        f.write(A.canonical(rec) + "\n")


def all_evidence() -> List[dict]:
    """Latest record per evidence id (machine) + curated evidence."""
    latest: Dict[str, dict] = {}
    for rec in read_jsonl("evidence.jsonl"):
        latest[rec["id"]] = rec
    for rec in load_json("evidence_sources.json", []):
        latest[rec["id"]] = rec
    return list(latest.values())


def run_index() -> Dict[str, dict]:
    """run_id -> {exp, det_hash, executions, reproduced}"""
    idx: Dict[str, dict] = {}
    for ex in read_jsonl("executions.jsonl"):
        r = idx.setdefault(ex["run_id"], {"exp": ex["exp"], "det_hash": ex["det_hash"],
                                          "config_hash": ex["config_hash"], "executions": 0})
        r["executions"] += 1
    for r in idx.values():
        r["reproduced"] = r["executions"] >= 2
    return idx


def run_experiment(module_name: str, record: bool = True) -> dict:
    mod = importlib.import_module(module_name)
    spec, config = mod.SPEC, mod.CONFIG
    exp = spec["experiment_id"]
    cfg_hash = A.sha256_obj(config)
    t0 = time.perf_counter()
    result = mod.run(config)
    wall = time.perf_counter() - t0
    det = result["deterministic"]
    det_hash = A.sha256_obj(det)
    run_id = "{}-{}".format(exp, det_hash[:12])
    out = {"run_id": run_id, "det_hash": det_hash, "config_hash": cfg_hash,
           "checks": result["checks"], "result": result, "wall_s": wall}
    if not record:
        return out

    rdir = os.path.join(RUNS, exp, det_hash[:12])
    hashes = {
        "config.json": A.dump(os.path.join(rdir, "config.json"), config),
        "deterministic.json": A.dump(os.path.join(rdir, "deterministic.json"), det),
        "checks.json": A.dump(os.path.join(rdir, "checks.json"), result["checks"]),
    }
    code_hash = A.code_hash()
    git = A.git_state()
    manifest = {"experiment_id": exp, "run_id": run_id, "det_hash": det_hash,
                "config_hash": cfg_hash, "code_hash": code_hash,
                "software_version": __import__("substrate").__version__,
                "environment": A.environment(), "files": hashes,
                "first_recorded_utc": A.utcnow(), "git_at_first_record": git}
    mpath = os.path.join(rdir, "manifest.json")
    if not os.path.exists(mpath):  # content-addressed: first recording wins
        A.dump(mpath, manifest)

    # reproducibility check against prior executions with the same config+code
    prior = [e for e in read_jsonl("executions.jsonl")
             if e["exp"] == exp and e["config_hash"] == cfg_hash and e["code_hash"] == code_hash]
    mismatches = [e for e in prior if e["det_hash"] != det_hash]
    append_jsonl("executions.jsonl", {
        "execution_utc": A.utcnow(), "exp": exp, "run_id": run_id, "det_hash": det_hash,
        "config_hash": cfg_hash, "code_hash": code_hash, "git_commit": git["commit"],
        "code_dirty": git["code_dirty"], "wall_s": round(wall, 4),
        "nondeterministic": result.get("nondeterministic", {}),
        "checks_passed": all(c["passed"] for c in result["checks"]),
    })
    if mismatches:
        fails = load_json("failures.json", [])
        fails.append({"id": "F-AUTO-{}-{}".format(exp, det_hash[:8]), "type": "reproducibility_failure",
                      "summary": "{} produced det_hash {} but earlier executions with identical config and code produced {}".format(
                          exp, det_hash[:12], sorted({m['det_hash'][:12] for m in mismatches})),
                      "status": "UNRESOLVED", "recorded_utc": A.utcnow(), "related_experiments": [exp]})
        save_json("failures.json", fails)

    # machine evidence (append-only; identical re-derivations are not duplicated)
    existing = {(r["id"], r.get("value_hash")) for r in read_jsonl("evidence.jsonl")}
    for ev in result.get("evidence", []):
        rec = dict(ev)
        rec["id"] = "EV-{}-{}".format(exp, ev["key"])
        rec.pop("key")
        rec["run_id"] = run_id
        rec["experiment_id"] = exp
        rec["value_hash"] = A.sha256_obj(rec.get("value"))
        problems = check_evidence_record(rec)
        if problems:
            raise ValueError("evidence rejected by epistemic guard: {}".format(problems))
        if (rec["id"], rec["value_hash"]) not in existing:
            rec["recorded_utc"] = A.utcnow()
            append_jsonl("evidence.jsonl", rec)
    return out


def sync_experiment_registry(module_names: List[str]) -> None:
    idx = run_index()
    entries = []
    for m in module_names:
        mod = importlib.import_module(m)
        spec = dict(mod.SPEC)
        exp = spec["experiment_id"]
        runs = sorted((rid for rid, r in idx.items() if r["exp"] == exp))
        spec["module"] = m
        spec["config"] = mod.CONFIG
        spec["random_seed"] = mod.CONFIG.get("seed")
        spec["runs"] = [{"run_id": r, "executions": idx[r]["executions"], "reproduced": idx[r]["reproduced"],
                         "artifacts": "runs/{}/{}/".format(exp, idx[r]["det_hash"][:12])} for r in runs]
        entries.append(spec)
    save_json("experiments.json", entries)
