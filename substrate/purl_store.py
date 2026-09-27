"""Execution records and continuations for computational addresses (substrate/purl.py).

Resolution (GET) is pure and writes nothing. *Recording* an execution is an
explicit act (POST), appended to an append-only store with the same
provenance vocabulary the experiment ledger uses (substrate/ledger.py):

    deterministic_sha256   hash of what must be identical on re-execution
    code_hash              hash of the instrument source
    operation versions     hash of each implementing function's source
    environment            interpreter, platform, observed optional modules
    wall_ns                instrument clock: nondeterministic, never hashed

"Rerun means comparison": recording an address that was recorded before
returns a comparison with the previous execution. As in the ledger, an
execution is *reproduced* when the same address gives the same
deterministic hash.

A recorded execution can reveal a relationship that no single resolution
shows: two different addresses whose maps have the same table are the same
map (extensional equality, charter rule 4). Such findings are returned as
OBSERVATIONS with status `computational`, never promoted automatically.

A continuation is the smallest navigable resume point: an immutable,
content-addressed trail of addresses (with an optional parent continuation,
so trails branch). It holds addresses, not transcripts; resuming re-resolves
the last address and offers its next links.

The store is instrument state, not research evidence: nothing here writes to
research/registries/ or runs/.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional

from . import artifacts as A
from . import purl as P

DEFAULT_DIR = os.environ.get("SUBSTRATE_PURL_STORE", os.path.join(A.ROOT, ".purl-store"))


class Store:
    def __init__(self, directory: str = DEFAULT_DIR):
        self.dir = directory
        os.makedirs(directory, exist_ok=True)
        self.exec_path = os.path.join(directory, "executions.jsonl")
        self.cont_path = os.path.join(directory, "continuations.jsonl")

    # -- append-only files -------------------------------------------------
    def _read(self, path: str) -> List[dict]:
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def _append(self, path: str, rec: dict) -> None:
        with open(path, "a") as f:
            f.write(A.canonical(rec) + "\n")

    def executions(self, purl: Optional[str] = None) -> List[dict]:
        rows = self._read(self.exec_path)
        return [r for r in rows if purl is None or r["purl"] == P.canonical(purl)]

    def execution(self, eid: str) -> dict:
        for r in self._read(self.exec_path):
            if r["execution_id"] == eid:
                return r
        raise P.PurlError(404, "not_found", "No execution {}.".format(eid))

    # -- recording ---------------------------------------------------------
    def record(self, purl: str) -> dict:
        t0 = time.perf_counter_ns()
        obj, ctx = P.resolve(purl)
        env = P.envelope(obj, ctx)
        wall = time.perf_counter_ns() - t0
        prior = self._read(self.exec_path)
        rec = {
            "execution_id": "X-{:06d}".format(len(prior) + 1),
            "purl": obj.purl,
            "kind": obj.kind,
            "value": obj.value,
            "deterministic_sha256": env["execution"]["deterministic_sha256"],
            "table_sha256": env["identity"].get("table_sha256"),
            "operations": env["execution"]["operations"],
            "materialized": env["execution"]["materialized"],
            "effects": env["execution"]["effects"],
            "epistemic_status": env["execution"]["epistemic_status"],
            "code_hash": A.code_hash(),
            "git": A.git_state(),
            "environment": dict(A.environment(), modules=P.environment()["modules"]),
            "recorded_utc": A.utcnow(),
            "wall_ns": wall,
        }
        self._append(self.exec_path, rec)
        same = [r for r in prior if r["purl"] == rec["purl"]]
        return {
            "protocol": P.PROTOCOL,
            "kind": "execution",
            "execution": rec,
            "rerun": compare(same[-1], rec) if same else None,
            "observations": self._observations(rec, prior),
            "next": env["next"],
            "links": {"self": "/executions/" + rec["execution_id"], "purl": rec["purl"],
                      "history": "/executions?purl=" + rec["purl"]},
        }

    def _observations(self, rec: dict, prior: List[dict]) -> List[dict]:
        out = []
        if rec.get("table_sha256"):
            others = sorted({r["purl"] for r in prior if r.get("table_sha256") == rec["table_sha256"] and r["purl"] != rec["purl"]})
            if others:
                out.append({"kind": "extensional_equivalence", "status": "computational",
                            "statement": "{} denotes the same map (same table) as {}".format(rec["purl"], ", ".join(others)),
                            "equivalence_relation": "equality of lookup tables", "addresses": [rec["purl"]] + others,
                            "table_sha256": rec["table_sha256"]})
        return out

    def history(self, purl: str) -> dict:
        rows = self.executions(purl)
        return {"protocol": P.PROTOCOL, "kind": "execution_history", "purl": P.canonical(purl), "count": len(rows),
                "executions": [{k: r[k] for k in ("execution_id", "deterministic_sha256", "code_hash", "recorded_utc", "wall_ns")} for r in rows],
                "comparisons": [compare(a, b) for a, b in zip(rows, rows[1:])]}

    # -- continuations -----------------------------------------------------
    def continuation(self, trail: List[str], parent: Optional[str] = None, note: str = "") -> dict:
        if not trail:
            raise P.PurlError(422, "empty_trail", "A continuation needs at least one address.")
        canon = []
        for p in trail:
            P.resolve(p)  # pure; raises if the address is not well-formed or not resolvable here
            canon.append(P.canonical(p))
        if parent is not None:
            self.get_continuation(parent)
        body = {"trail": canon, "at": canon[-1], "parent": parent, "note": note}
        cid = "cont-" + A.sha256_obj(body)[:16]
        if not any(r["id"] == cid for r in self._read(self.cont_path)):
            self._append(self.cont_path, dict(body, id=cid, created_utc=A.utcnow()))
        return self.get_continuation(cid)

    def get_continuation(self, cid: str) -> dict:
        for r in self._read(self.cont_path):
            if r["id"] == cid:
                obj, ctx = P.resolve(r["at"])
                return {"protocol": P.PROTOCOL, "kind": "continuation", "id": cid, "trail": r["trail"], "at": r["at"],
                        "parent": r["parent"], "note": r["note"],
                        "children": [c["id"] for c in self._read(self.cont_path) if c["parent"] == cid],
                        "resume": {"kind": obj.kind, "value_sha256": P.identity(obj)["value_sha256"], "next": P.next_links(obj)},
                        "semantics": "Addresses, not transcripts. Resuming re-resolves `at`; branch by creating a continuation with this id as parent."}
        raise P.PurlError(404, "not_found", "No continuation {}.".format(cid))


def compare(a: dict, b: dict) -> dict:
    """What changed between two executions: output, implementation, code, environment, timing."""
    same_out = a["deterministic_sha256"] == b["deterministic_sha256"]
    fields = {
        "output": same_out,
        "operation_versions": a["operations"] == b["operations"],
        "code_hash": a["code_hash"] == b["code_hash"],
        "environment": a["environment"] == b["environment"],
        "materialization": a["materialized"] == b["materialized"],
    }
    return {"a": a["execution_id"], "b": b["execution_id"], "same_purl": a["purl"] == b["purl"],
            "unchanged": fields, "changed": [k for k, v in fields.items() if not v],
            "wall_ns": {"a": a["wall_ns"], "b": b["wall_ns"], "note": "nondeterministic; not part of the verdict"},
            "verdict": ("reproduced" if same_out else "differs") if a["purl"] == b["purl"] else ("same_value" if same_out else "different_value")}
