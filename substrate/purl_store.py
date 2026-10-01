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
        ident = env["identity"]
        seq = "X-{:06d}".format(len(prior) + 1)
        recorded = A.utcnow()
        rec = {
            "execution_id": seq,
            "execution_hash": "sha256:" + A.sha256_obj({"derivation_id": ident["derivation_id"],
                                                        "environment_id": env["execution"]["environment_id"],
                                                        "code_hash": A.code_hash(), "occurrence": [seq, recorded]}),
            "purl": obj.purl,
            "kind": obj.kind,
            "value": obj.value,
            "address_id": ident["address_id"],
            "derivation_id": ident["derivation_id"],
            "value_id": ident["value_id"],
            "environment_id": env["execution"]["environment_id"],
            "deterministic_sha256": env["execution"]["deterministic_sha256"],
            "table_sha256": env["identity"].get("table_sha256"),
            "operations": env["execution"]["operations"],
            "materialized": env["execution"]["materialized"],
            "effects": env["execution"]["effects"],
            "epistemic_status": env["execution"]["epistemic_status"],
            "code_hash": A.code_hash(),
            "git": A.git_state(),
            "environment": dict(A.environment(), modules=P.environment()["modules"]),
            "recorded_utc": recorded,
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

    # -- observations (named projections of external records) -------------
    def observe(self, projection: str, origin: str, document: dict) -> dict:
        """Apply a declared projection to an external record and append the result. The record is data, never instructions."""
        from . import acsp_events
        if projection != acsp_events.PROJECTION_ID:
            raise P.PurlError(404, "unknown_projection", "Known projections: [{}].".format(acsp_events.PROJECTION_ID))
        try:
            res = acsp_events.project(document, origin)
        except (KeyError, TypeError) as e:
            raise P.PurlError(422, "malformed_source", "The document is not an ACSP/0.1 event_list: missing {}.".format(e))
        except ValueError as e:
            raise P.PurlError(422, "invalid_param", str(e), param="origin")
        obs_path = os.path.join(self.dir, "observations.jsonl")
        prior = self._read(obs_path)
        rec = dict(res, observation_id="O-{:06d}".format(len(prior) + 1), recorded_utc=A.utcnow(), code_hash=A.code_hash())
        self._append(obs_path, rec)
        same = [r for r in prior if r["resource_id"] == rec["resource_id"] and r["projection"]["id"] == projection]
        return {"protocol": P.PROTOCOL, "kind": "observation", "observation": rec,
                "previous": (same[-1]["observation_id"] if same else None),
                "links": {"self": "/observations/" + rec["observation_id"]}}

    def observation(self, oid: str) -> dict:
        for r in self._read(os.path.join(self.dir, "observations.jsonl")):
            if r["observation_id"] == oid:
                return r
        raise P.PurlError(404, "not_found", "No observation {}.".format(oid))

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
    va, vb = a.get("value_id"), b.get("value_id")
    if a["purl"] == b["purl"]:
        verdict = "reproduced" if same_out else "differs"
    elif va is None or vb is None:
        verdict = "value_not_comparable"   # a value was not materialized (charter rule 7), or a pre-F-010 record
    else:
        verdict = "same_value" if va == vb and a["kind"] == b["kind"] else "different_value"
    return {"a": a["execution_id"], "b": b["execution_id"], "same_purl": a["purl"] == b["purl"],
            "same_value_id": (va == vb) if va and vb else None,
            "unchanged": fields, "changed": [k for k, v in fields.items() if not v],
            "wall_ns": {"a": a["wall_ns"], "b": b["wall_ns"], "note": "nondeterministic; not part of the verdict"},
            "verdict": verdict,
            "verdict_basis": "same address: deterministic_sha256; different addresses: value_id (F-010)"}
