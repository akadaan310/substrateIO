"""EXP-A — one-bit deterministic transitions.

The complete space of deterministic one-bit dynamics is Sigma^Sigma, which has
|Sigma|^|Sigma| = 4 elements. We enumerate all of them rather than pick one,
so nothing is hidden by selection.
"""

from substrate.core import one_bit_maps, StateSpace
from substrate.graph import functional_graph_analysis, public
from substrate.projection import information_loss
from substrate.trace import run as run_trace
from . import check, ev

SPEC = {
    "experiment_id": "EXP-A",
    "title": "One-bit deterministic transition",
    "question": "What distinguishes the deterministic dynamics available on a single bit, and what does a recorded transition event add to a bare transition?",
    "hypotheses": ["H-004"],
    "objective": "Exhaustively characterise f: {0,1}->{0,1}; record events with logical time; measure per-step information loss.",
    "model": "All 4 maps Sigma->Sigma; traces of length 4 from each initial state.",
    "procedure": "Enumerate maps; functional-graph analysis; run traces; compute H(X)-H(f(X)) under uniform X.",
    "expected_result": "identity: 2 fixed points; not: one 2-cycle; const0/const1: one fixed point with basin 2 and 1 bit lost per step. Bijective maps lose 0 bits.",
    "falsification_condition": "Any map whose information loss is nonzero while injective, or zero while non-injective; or a count of maps != 4.",
    "epistemic_status_of_result": "SIMULATED (model executions) corroborating DERIVED facts.",
}

CONFIG = {"steps": 4, "seed": None}


def run(config):
    X = StateSpace(1)
    maps = one_bit_maps()
    rows, checks_ok = [], True
    for f in maps:
        an = functional_graph_analysis(f.table)
        loss = information_loss(list(X.states()), f)
        traces = {}
        for x0 in X.states():
            tr = run_trace(f, 1, x0, config["steps"], clock=False)
            traces[str(x0)] = {
                "states": tr.states,
                "events": [e.deterministic() for e in tr.events],
                "changed": [e.delta for e in tr.events],
            }
        rows.append({"map": f.name, "table": f.table, "graph": public(an),
                     "info_loss_bits": loss["H_X_given_PX"], "traces": traces})
        if (loss["H_X_given_PX"] > 0) == f.is_injective():
            checks_ok = False

    by = {r["map"]: r for r in rows}
    checks = [
        check("A1", "exactly 4 distinct one-bit maps", len({tuple(r["table"]) for r in rows}) == 4, len(rows)),
        check("A2", "information loss > 0 iff map non-injective", checks_ok),
        check("A3", "identity has 2 fixed points", by["identity"]["graph"]["n_fixed_points"] == 2),
        check("A4", "not has a single 2-cycle and no fixed point",
              by["not"]["graph"]["cycle_lengths"] == [2] and by["not"]["graph"]["n_fixed_points"] == 0),
        check("A5", "const maps: one attractor with basin 2",
              all(by[m]["graph"]["basin_sizes"] == [2] for m in ("const0", "const1"))),
        check("A6", "identity trace: every event is a transition with no state change",
              all(c == 0 for t in by["identity"]["traces"].values() for c in t["changed"])),
    ]
    evidence = [
        ev("loss_table", "Per-step information loss under uniform input: identity 0, not 0, const0 1 bit, const1 1 bit.",
           {r["map"]: r["info_loss_bits"] for r in rows}),
        ev("graph_table", "Functional-graph structure of all four one-bit maps.",
           {r["map"]: {k: r["graph"][k] for k in ("cycle_lengths", "basin_sizes", "n_fixed_points", "injective")} for r in rows}),
        ev("identity_events", "Under identity, the bare transition 0->0 is indistinguishable from 'no step'; only the recorded event (with logical time t) witnesses that a step occurred.",
           by["identity"]["traces"]["0"]["events"][:2]),
    ]
    return {"deterministic": {"maps": rows}, "nondeterministic": {}, "checks": checks, "evidence": evidence}
