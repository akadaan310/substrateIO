"""Projection P-ACSP-EV-1: an ACSP/0.1 event list -> a transition sequence.

The ACSP format substrate/acsp.py reads (``acsp-transition-history/1``, the
program-001 extension) is not served by any ACSP deployment that exists in
the repositories (see purl/circle/RECONSTRUCTION.md). What ACSP/0.1 does
serve is ``GET /r/{id}/events?format=json`` (``type: event_list``). This
module reads that document and nothing else. It never imports or calls ACSP.

An observation is a map + a recording + a clock (ONTOLOGY). This projection
declares all three, plus what it forgets:

    source          ACSP/0.1 event_list document (one resource, events (after, current_version])
    transformation  event e  ->  transition (t = e.version, label = e.operation,
                                 actor = e.actor.session_id, assurance = e.identity_assurance)
    representation  a sequence of labels in logical time; the transition system
                    over labels (states = labels, edge a->b iff b directly followed a)
    lost            event payload (data, summary), agent_id and actor kind, capability_id,
                    on_behalf_of, request bodies (only request_hash is kept), wall clock
    clock           logical: t = event version (contiguous). occurred_at is an observation
                    of the service clock, carried but excluded from every hash
    resolution      one event (one state change)
    measurement     label counts, label bigrams, session switches (t where actor differs
                    from t-1), chain consistency

Epistemic status of the output depends on where the events came from, and is
declared by the caller, never inferred:

    origin="harness"   actors were driven by test code      -> SIMULATED
    origin="service"   events recorded by a running service -> UNRESOLVED
                       (the status vocabulary defines OBSERVED only for physical hardware
                        and this repository's history; an external service's record has
                        no status yet. Recorded as an open gap, not resolved here.)
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from . import artifacts as A
from .graph import Digraph

PROJECTION_ID = "P-ACSP-EV-1"
DECLARATION = {
    "id": PROJECTION_ID,
    "source": "ACSP/0.1 event_list (GET /r/{id}/events?format=json)",
    "transformation": "event -> (t=version, label=operation, actor=session_id, assurance=identity_assurance, request_hash)",
    "representation": "label sequence in logical time + transition system over labels",
    "lost": ["data", "summary", "actor.agent_id", "actor.kind", "capability_id", "on_behalf_of", "request bodies", "occurred_at (from hashes)"],
    "clock": {"logical": "t = event version", "wall": "occurred_at: service clock observation, excluded from hashes"},
    "resolution": "one event",
    "measurement": ["label_counts", "label_bigrams", "session_switches", "chain_problems"],
}
ORIGIN_STATUS = {"harness": "SIMULATED", "service": "UNRESOLVED"}


def verify(doc: Dict[str, Any]) -> List[str]:
    """Checks that need no trust in the exporter. Empty list = consistent."""
    if doc.get("type") != "event_list":
        return ["type is {!r}, expected 'event_list'".format(doc.get("type"))]
    out = []
    evs = doc.get("events", [])
    expect = doc.get("after", 0) + 1
    for e in evs:
        if e["version"] != expect:
            out.append("version {} where {} was expected (gap or reorder)".format(e["version"], expect))
        if e.get("parent_version") != e["version"] - 1:
            out.append("v{}: parent_version does not chain".format(e["version"]))
        if not e.get("actor", {}).get("session_id"):
            out.append("v{}: no actor session (unattributable)".format(e["version"]))
        expect = e["version"] + 1
    if evs and doc.get("next") is None and evs[-1]["version"] != doc.get("current_version"):
        out.append("last event v{} but current_version {} and no next page".format(evs[-1]["version"], doc.get("current_version")))
    return out


def project(doc: Dict[str, Any], origin: str) -> Dict[str, Any]:
    if origin not in ORIGIN_STATUS:
        raise ValueError("origin must be one of {}".format(sorted(ORIGIN_STATUS)))
    evs = doc["events"]
    transitions = [{"t": e["version"], "label": e["operation"], "actor": e["actor"]["session_id"],
                    "assurance": e.get("identity_assurance"), "request_hash": e.get("request_hash")} for e in evs]
    labels = [x["label"] for x in transitions]
    g = Digraph()
    for l in labels:
        g.add_node(l)
    for a, b in zip(labels, labels[1:]):
        if b not in g.adj[a]:
            g.add_edge(a, b)
    actors = [x["actor"] for x in transitions]
    det = {"projection": PROJECTION_ID, "resource_id": doc.get("resource_id"), "transitions": transitions}
    return {
        "projection": DECLARATION,
        "resource_id": doc.get("resource_id"),
        "origin": origin,
        "epistemic_status": ORIGIN_STATUS[origin],
        "chain_problems": verify(doc),
        "transitions": transitions,
        "wall_clock": [e.get("occurred_at") for e in evs],
        "measurements": {
            "n": len(transitions),
            "label_counts": dict(sorted(Counter(labels).items())),
            "label_bigrams": dict(sorted(Counter("{} -> {}".format(a, b) for a, b in zip(labels, labels[1:])).items())),
            "sessions": sorted(set(actors)),
            "session_switches": [transitions[i]["t"] for i in range(1, len(actors)) if actors[i] != actors[i - 1]],
            "transition_system": dict(g.degree_stats(), is_dag=g.is_dag()),
        },
        "deterministic_sha256": "sha256:" + A.sha256_obj(det),
    }
