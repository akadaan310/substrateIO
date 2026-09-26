"""EXP-F — representation projections and measurable information loss.

F1  static projections of X_8 (uniform): what survives, what is lost, fibers.
F2  distribution dependence: the same projection loses different amounts of
    information depending on where in the dynamics one observes (X vs f(X)).
F3  dynamics compatibility: is ker P a congruence of f (does the projected
    layer have its own autonomous dynamics)?
F4  coarsest congruence for an observable O: the minimum number of states any
    representation must retain to predict O's entire future under f.
F5  sequence projection states -> transitions (XOR differencing) on {0,1}^L.
"""

from substrate.core import StateSpace, eca, increment, popcount
from substrate.projection import (compatibility, congruence_summary, from_transitions,
                                  information_loss, to_transitions)
from . import check, ev

SPEC = {
    "experiment_id": "EXP-F",
    "title": "Representation projection with measurable information loss",
    "question": "What information survives a representation map, what equivalence does it induce, and what is the minimum information that must survive to preserve a given property?",
    "hypotheses": ["H-002", "H-006"],
    "objective": "Quantify H(X|P(X)), fibers, dynamics-compatibility and coarsest congruences for several (f, P) pairs.",
    "model": "X_8 with increment, eca90, eca30, eca204; projections low4, high4, parity, popcount, threshold, identity, constant; sequences of length 10.",
    "procedure": "Exact enumeration (no sampling).",
    "expected_result": "identity loses 0 bits, constant loses 8; low4 compatible with increment, high4 not; transition recoding of length-L sequences loses exactly 1 bit (fibers {x, complement}); minimum retained states depend on the observable.",
    "falsification_condition": "Transition recoding fibers not all of size 2; identity/constant losses not 0/8; coarsest congruence for (increment, bit0) not 2 blocks; congruence summaries independent of the observable.",
    "epistemic_status_of_result": "SIMULATED (exact enumeration), corroborating DERIVED statements.",
}

CONFIG = {"n_bits": 8, "seq_len": 10, "seed": None}


def projections(n):
    half = n // 2
    return {
        "identity": lambda x: x,
        "low4": lambda x: x & ((1 << half) - 1),
        "high4": lambda x: x >> half,
        "parity": lambda x: popcount(x) & 1,
        "popcount": popcount,
        "threshold": lambda x: int(x >= (1 << (n - 1))),
        "bit0": lambda x: x & 1,
        "constant": lambda x: 0,
    }


def run(config):
    n = config["n_bits"]
    X = list(StateSpace(n).states())
    P = projections(n)
    F1 = {k: information_loss(X, p) for k, p in P.items()}

    systems = {"increment": increment(n), "eca90": eca(90, n), "eca30": eca(30, n), "eca204": eca(204, n)}
    # F2: observe P on f(X) instead of X (push-forward of uniform through one step)
    F2 = {}
    for sname, f in systems.items():
        w = [0] * len(X)
        for x in X:
            w[f(x)] += 1
        F2[sname] = {k: {"H_PX_uniform": round(F1[k]["H_PX"], 9),
                         "H_PfX": round(information_loss(X, P[k], w)["H_PX"], 9) + 0.0} for k in ("parity", "popcount", "bit0", "high4")}
    F3 = {s: {k: compatibility(f.table, p)["compatible"] for k, p in P.items()} for s, f in systems.items()}
    F4 = {s: {k: congruence_summary(f.table, p) for k, p in P.items() if k not in ("identity", "constant")}
          for s, f in systems.items()}

    L = config["seq_len"]
    seqs = list(range(1 << L))
    as_bits = lambda s: tuple((s >> i) & 1 for i in range(L))
    trans = lambda s: tuple(to_transitions(as_bits(s)))
    F5 = information_loss(seqs, trans)
    F5_with_x0 = information_loss(seqs, lambda s: (s & 1, trans(s)))
    roundtrip_ok = all(tuple(from_transitions(as_bits(s)[0], trans(s))) == as_bits(s) for s in seqs)

    for d in F1.values():
        for k in ("H_X", "H_PX", "H_X_given_PX", "fraction_lost"):
            d[k] = round(d[k], 9)
    for k in ("H_X", "H_PX", "H_X_given_PX", "fraction_lost"):
        F5[k] = round(F5[k], 9); F5_with_x0[k] = round(F5_with_x0[k], 9)

    blocks = {s: {k: v["n_blocks"] for k, v in d.items()} for s, d in F4.items()}
    checks = [
        check("F1", "identity loses 0 bits; constant loses n bits",
              F1["identity"]["H_X_given_PX"] == 0 and abs(F1["constant"]["H_X_given_PX"] - n) < 1e-9),
        check("F2", "transition recoding: every fiber has size 2 (x and its complement), loss exactly 1 bit",
              F5["fiber_size_histogram"] == {"2": 1 << (L - 1)} and abs(F5["H_X_given_PX"] - 1) < 1e-9, F5["fiber_size_histogram"]),
        check("F3", "transition recoding plus x0 is lossless and round-trips", F5_with_x0["reconstructible_on_support"] and roundtrip_ok),
        check("F4", "low4 is compatible with increment; high4 is not",
              F3["increment"]["low4"] and not F3["increment"]["high4"]),
        check("F5", "coarsest congruence (increment, bit0) has 2 blocks", blocks["increment"]["bit0"] == 2, blocks["increment"]["bit0"]),
        check("F6", "minimum retained states depend on the observable (not constant across observables) for increment",
              len(set(blocks["increment"].values())) > 1, blocks["increment"]),
        check("F7", "eca90: parity after one step is constant (H(P f X) = 0)", F2["eca90"]["parity"]["H_PfX"] == 0),
    ]
    evidence = [
        ev("static_loss", "Information loss H(X|P(X)) (bits) of projections on uniform X_8.",
           {k: v["H_X_given_PX"] for k, v in F1.items()}),
        ev("distribution_dependence", "Entropy of the projected value under uniform X vs under f(X).", F2),
        ev("compatibility", "Whether ker P is a congruence of f (projected layer has autonomous dynamics).", F3),
        ev("min_retained_states", "Coarsest congruence sizes: minimum states that must survive to predict observable O's future under f.", blocks),
        ev("transition_recoding", "States->transitions recoding on {0,1}^10: fiber histogram and information loss.",
           {"fibers": F5["fiber_size_histogram"], "loss_bits": F5["H_X_given_PX"], "with_x0_lossless": F5_with_x0["reconstructible_on_support"]}),
    ]
    return {"deterministic": {"F1": F1, "F2": F2, "F3": F3, "F4": F4, "F5": F5, "F5_with_x0": F5_with_x0},
            "nondeterministic": {}, "checks": checks, "evidence": evidence}
