"""Reader for ACSP transition-history exports (format ``acsp-transition-history/1``).

ACSP (Agent Continuity & Session Protocol) is a separate system: the system
under observation. It exports an agent identity's history at
``GET /r/{id}/transitions``. This module is part of the instrument. It
never imports or calls ACSP; it reads that JSON document and nothing else.

What the document is (per ACSP's own ``epistemic_status``): RECORDED protocol
events. When the actors were simulated by ACSP's deterministic harness, as in
every export available so far, anything computed from them here is SIMULATED
by construction. Model fields in the export are labels declared by sessions;
nothing in it observes a model.

Vocabulary used here is the established one (nomenclature C-004, C-007):

    transition   one exported record, logical time t (= ACSP event version)
    operation    the label of a transition (the ACSP operation name)
    the transition system over operations: states are operation names and an
    edge o1 -> o2 means some transition labelled o2 directly followed one
    labelled o1. It is a coarse projection that forgets everything but labels.

``observations`` are labels ACSP derived from its own history; they are
carried through and counted, never reinterpreted.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Dict, List

from .graph import Digraph

FORMAT = "acsp-transition-history/1"


def load(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _acsp_canonical(obj: Any) -> str:
    # ACSP's canonical JSON: sorted keys, no whitespace, non-ASCII kept as-is
    # (JavaScript JSON.stringify). ACSP normalises -0 to 0, so numbers agree.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def deterministic_hash(doc: Dict[str, Any]) -> str:
    """Recompute ACSP's ``deterministic_sha256``: every transition minus its wall-clock ``occurred_at``."""
    det = [{k: v for k, v in t.items() if k != "occurred_at"} for t in doc["transitions"]]
    return "sha256:" + hashlib.sha256(_acsp_canonical(det).encode("utf-8")).hexdigest()


def verify(doc: Dict[str, Any]) -> List[str]:
    """Structural checks an instrument can make without trusting the exporter. Empty list = consistent."""
    problems = []
    if doc.get("format") != FORMAT:
        problems.append("format is {!r}, expected {!r}".format(doc.get("format"), FORMAT))
        return problems
    ts = doc.get("transitions", [])
    if doc.get("transition_count") != len(ts):
        problems.append("transition_count does not match the number of transitions")
    for i, t in enumerate(ts):
        if t["t"] != i + 1:
            problems.append("t={} at position {}: logical time is not contiguous".format(t["t"], i))
        if t["from_version"] != t["t"] - 1 or t["to_version"] != t["t"]:
            problems.append("t={}: from/to versions do not chain".format(t["t"]))
        if not t.get("actor", {}).get("session_id"):
            problems.append("t={}: no actor session (unattributable)".format(t["t"]))
        vocab = doc.get("vocabulary", {})
        for label in t.get("observations", []):
            if label not in vocab:
                problems.append("t={}: label {} is not in the exported vocabulary".format(t["t"], label))
    if deterministic_hash(doc) != doc.get("deterministic_sha256"):
        problems.append("deterministic_sha256 does not match the transitions (modified, or a different canonicalisation)")
    return problems


def operation_system(doc: Dict[str, Any]) -> Digraph:
    """The transition system over operation labels (see module docstring)."""
    g = Digraph()
    ops = [t["operation"] for t in doc["transitions"]]
    for o in ops:
        g.add_node(o)
    for a, b in zip(ops, ops[1:]):
        if b not in g.adj[a]:
            g.add_edge(a, b)
    return g


def embodiment_segments(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Maximal runs of transitions under one embodiment (None = no embodiment in effect)."""
    out: List[Dict[str, Any]] = []
    for t in doc["transitions"]:
        e = t.get("embodiment")
        key = e["embodiment_id"] if e else None
        if not out or out[-1]["embodiment_id"] != key:
            out.append({"embodiment_id": key, "session_id": e["session_id"] if e else None, "from_t": t["t"], "to_t": t["t"]})
        else:
            out[-1]["to_t"] = t["t"]
    return out


def summary(doc: Dict[str, Any]) -> Dict[str, Any]:
    ts = doc["transitions"]
    ops = [t["operation"] for t in ts]
    g = operation_system(doc)
    return {
        "agent_id": doc.get("agent_id"),
        "n_transitions": len(ts),
        "operations": dict(sorted(Counter(ops).items())),
        "operation_bigrams": dict(sorted(Counter("{} -> {}".format(a, b) for a, b in zip(ops, ops[1:])).items())),
        "observation_labels": dict(sorted(Counter(l for t in ts for l in t.get("observations", [])).items())),
        "sessions": sorted({t["actor"]["session_id"] for t in ts}),
        "embodiments": embodiment_segments(doc),
        "substrates": sorted({t["substrate_after"] for t in ts if t.get("substrate_after")}),
        "executions": [t["execution"] for t in ts if t.get("execution")],
        "operation_system": dict(g.degree_stats(), is_dag=g.is_dag()),
    }
