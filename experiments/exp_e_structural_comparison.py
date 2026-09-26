"""EXP-E — baseline vs perturbed comparison of transition *structure*.

EXP-D perturbs a state; EXP-E perturbs the dynamics itself: a single edge
x -> f(x) of the functional graph is rewired to x -> y. We compare the
baseline graph G with G' and ask how much structure changes.

Derived bound (DERIVED, see evidence_sources DRV-003): a rewire at vertex s can
only change the forward orbit of states whose orbit passes through s, i.e. the
set Anc(s) = {x : s in orbit(x)}. Hence
    states_attractor_changed <= |Anc(s)|.
The experiment checks the bound (instrument test) and measures how tight it is.
Control: the null rewire (y = f(s)) must change nothing.
"""

import random
from collections import defaultdict

from substrate.core import eca, increment, random_map, random_permutation
from substrate.graph import functional_graph_analysis
from substrate.perturb import Intervention, compare_functional_graphs
from . import check, ev

SPEC = {
    "experiment_id": "EXP-E",
    "title": "Baseline versus perturbed comparison (structural)",
    "question": "How much does a single-edge change in the dynamics alter the transition graph's attractor structure, and what predicts the size of the change?",
    "hypotheses": ["H-010"],
    "objective": "Rewire each edge once (random target), compare G vs G'; verify the ancestor bound; measure its tightness.",
    "model": "increment, eca30, eca90, random map, random permutation on 8 bits.",
    "procedure": "for each s: Intervention(edge_rewire); analyse G'; compare; compute |Anc(s)|. Null control per system.",
    "expected_result": "Bound never violated; null control zero change; single-cycle systems highly sensitive; random maps mostly insensitive.",
    "falsification_condition": "Any rewire changing the attractor of a state outside Anc(s); any nonzero change under the null control.",
    "epistemic_status_of_result": "SIMULATED",
}

CONFIG = {"seed": 8675309, "n_bits": 8}


def ancestors(table):
    """Anc(s) sizes for all s: number of x whose orbit contains s."""
    n = len(table)
    pre = defaultdict(list)
    for x, y in enumerate(table):
        pre[y].append(x)
    sizes = []
    for s in range(n):
        seen, stack = {s}, [s]
        while stack:
            v = stack.pop()
            for u in pre[v]:
                if u not in seen:
                    seen.add(u); stack.append(u)
        sizes.append(len(seen))
    return sizes


def run(config):
    n = config["n_bits"]
    rng = random.Random(config["seed"])
    systems = [increment(n), eca(30, n), eca(90, n), random_map(n, rng.randrange(1 << 30)), random_permutation(n, rng.randrange(1 << 30))]
    out, bound_ok, control_ok = {}, True, True
    for f in systems:
        base = functional_graph_analysis(f.table)
        anc = ancestors(f.table)
        null = Intervention("null")
        c0 = compare_functional_graphs(base, functional_graph_analysis(null.apply_to_table(f.table)))
        if c0["states_attractor_changed"] or c0["states_transient_changed"] or c0["attractors_added"]:
            control_ok = False
        fracs, tight, on_cycle_fracs, off_cycle_fracs = [], [], [], []
        cyc = {v for c in base["_cycles"] for v in c}
        for s in range(len(f.table)):
            y = rng.randrange(len(f.table))
            iv = Intervention("edge_rewire", params={"src": s, "new_dst": y})
            cmp = compare_functional_graphs(base, functional_graph_analysis(iv.apply_to_table(f.table)))
            ch = cmp["states_attractor_changed"]
            if ch > anc[s]:
                bound_ok = False
            fracs.append(cmp["fraction_attractor_changed"])
            tight.append(ch / anc[s])
            (on_cycle_fracs if s in cyc else off_cycle_fracs).append(cmp["fraction_attractor_changed"])
        mean = lambda xs: round(sum(xs) / len(xs), 6) if xs else None
        out[f.name] = {
            "mean_fraction_attractor_changed": mean(fracs),
            "max_fraction_attractor_changed": round(max(fracs), 6),
            "mean_bound_tightness": mean(tight),
            "on_cycle_mean_fraction": mean(on_cycle_fracs),
            "off_cycle_mean_fraction": mean(off_cycle_fracs),
            "n_on_cycle": len(on_cycle_fracs),
            "mean_ancestor_set_fraction": mean([a / len(f.table) for a in anc]),
        }
    # rank correlation (Spearman, no ties handling needed at this precision) between
    # mean ancestor-set fraction and mean sensitivity across systems
    checks = [
        check("E1", "null rewire changes nothing (control)", control_ok),
        check("E2", "ancestor bound never violated", bound_ok),
        check("E3", "increment (single cycle) is maximally sensitive: mean fraction changed > 0.5",
              out["increment"]["mean_fraction_attractor_changed"] > 0.5, out["increment"]["mean_fraction_attractor_changed"]),
        check("E4", "random map is insensitive: mean fraction changed < 0.2",
              out["random_map"]["mean_fraction_attractor_changed"] < 0.2, out["random_map"]["mean_fraction_attractor_changed"]),
    ]
    evidence = [
        ev("sensitivity_table", "Structural sensitivity to single-edge rewires per system (8-bit).", out),
    ]
    return {"deterministic": {"systems": out}, "nondeterministic": {}, "checks": checks, "evidence": evidence}
