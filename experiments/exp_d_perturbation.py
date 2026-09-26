"""EXP-D — controlled state perturbation (single-bit flips) in ECA dynamics.

Established name for the measured phenomenon: *damage spreading* (e.g.
Stanley et al. 1987; Derrida & Pomeau 1986 for random Boolean networks);
for linear rules the damage pattern is determined algebraically (Martin,
Odlyzko & Wolfram 1984).

Design: ring of n = 16 cells (65536 states, tabulated, so injectivity is known
exactly). For each rule, each initial state seed, each bit position i: flip
bit i at t0 and compare against the unperturbed baseline for H steps.
Control: the null intervention must yield class "null" and zero distance.
"""

import random
from collections import Counter

from substrate.core import eca
from substrate.perturb import Intervention, compare_state_sequences
from substrate.trace import run as run_trace, step_states
from . import check, ev

SPEC = {
    "experiment_id": "EXP-D",
    "title": "Controlled perturbation",
    "question": "How does a single injected state difference propagate, persist, transform, or vanish under different deterministic dynamics?",
    "hypotheses": ["H-004"],
    "objective": "Measure damage spreading metrics and outcome classes for ECA rules; test that masking/recovery occurs only in non-injective dynamics.",
    "model": "ECA rules on a 16-cell ring; single-bit flips at t0 at every position; horizon H.",
    "procedure": "baseline trace; perturbed trace with recorded Intervention; compare_state_sequences; aggregate per rule. Null-intervention control.",
    "expected_result": "No masked/recovered outcomes for injective rules (DERIVED). Rule 90 on n=16: every single-site difference annihilates exactly 8 steps later (DERIVED, Frobenius in GF(2)[x]/(x^16-1)). Null control 100% 'null'.",
    "falsification_condition": "Any masked/recovered outcome under an injective rule; rule 90 differences not annihilating at k=8; any non-null class for the null control.",
    "epistemic_status_of_result": "SIMULATED",
}

CONFIG = {"seed": 424242, "n": 16, "rules": [0, 30, 51, 90, 110, 150, 170, 184, 204, 232],
          "n_initial": 12, "t0": 4, "horizon": 40}


def run(config):
    n, t0, H = config["n"], config["t0"], config["horizon"]
    rng = random.Random(config["seed"])
    inits = [rng.randrange(1 << n) for _ in range(config["n_initial"])]
    steps = t0 + H
    summary, control_ok, examples = {}, True, {}
    for rule in config["rules"]:
        f = eca(rule, n)
        injective = f.is_injective()
        classes = Counter()
        rec_times, max_d, spreads, esc = Counter(), [], [], []
        pos_class = {}
        for s, x0 in enumerate(inits):
            base = step_states(run_trace(f, n, x0, steps, clock=False))
            null = Intervention("null", t0)
            pn = step_states(run_trace(f, n, x0, steps, {t0: null.state_fn()}, clock=False))
            cmp0 = compare_state_sequences(base, pn, t0, n, [])
            if cmp0["class"] != "null" or cmp0["max_distance"] != 0:
                control_ok = False
            for i in range(n):
                iv = Intervention("state_bit_flip", t0, {"bit": i})
                pert = step_states(run_trace(f, n, x0, steps, {t0: iv.state_fn()}, clock=False))
                c = compare_state_sequences(base, pert, t0, n, [i])
                classes[c["class"]] += 1
                pos_class.setdefault(i, Counter())[c["class"]] += 1
                if c["recovery_time"] is not None:
                    rec_times[c["recovery_time"]] += 1
                max_d.append(c["max_distance"]); spreads.append(c["spread"])
                if c["first_escape_time"] is not None:
                    esc.append(c["first_escape_time"])
                if s == 0 and i == 0:
                    examples[str(rule)] = {"intervention": iv.record(), "distance_series": c["distance_series"], "class": c["class"]}
        total = sum(classes.values())
        # is the class distribution the same at every bit position? (translation symmetry of the rule
        # vs asymmetry of initial states)
        pos_dists = {tuple(sorted(pc.items())) for pc in pos_class.values()}
        summary[str(rule)] = {
            "injective_on_ring": injective,
            "classes": dict(sorted(classes.items())),
            "fractions": {k: round(v / total, 6) for k, v in sorted(classes.items())},
            "recovery_time_hist": {str(k): v for k, v in sorted(rec_times.items())},
            "mean_max_distance": round(sum(max_d) / len(max_d), 6),
            "max_spread": max(spreads),
            "mean_first_escape": round(sum(esc) / len(esc), 6) if esc else None,
            "position_invariant_class_distribution": len(pos_dists) == 1,
        }

    viol = [r for r, s in summary.items() if s["injective_on_ring"] and (s["classes"].get("masked", 0) + s["classes"].get("recovered", 0)) > 0]
    r90 = summary.get("90")
    checks = [
        check("D1", "null intervention control: always class 'null' with zero distance", control_ok),
        check("D2", "no masking/recovery under any injective rule", not viol, viol),
        check("D3", "rule 90 on n=16: all single-site differences recover exactly 8 steps after injection",
              r90 is not None and r90["classes"] == {"recovered": n * config["n_initial"]} and list(r90["recovery_time_hist"]) == ["8"],
              r90 and r90["recovery_time_hist"]),
        check("D4", "rule 0 masks every perturbation immediately",
              summary["0"]["classes"] == {"masked": n * config["n_initial"]}),
        check("D5", "rule 204 (identity) leaves every perturbation persistent_local",
              summary["204"]["classes"] == {"persistent_local": n * config["n_initial"]}),
    ]
    evidence = [
        ev("class_table", "Outcome class fractions per ECA rule (n=16 ring, 12 initial states x 16 positions, horizon 40).",
           {r: s["fractions"] for r, s in summary.items()}),
        ev("injective_vs_masking", "Injectivity of each rule on the 16-ring vs presence of masking/recovery.",
           {r: {"injective": s["injective_on_ring"], "masked_or_recovered": s["classes"].get("masked", 0) + s["classes"].get("recovered", 0)} for r, s in summary.items()}),
        ev("rule90_annihilation", "Rule 90 single-site damage on a 16-ring: recovery-time histogram.", r90["recovery_time_hist"]),
        ev("damage_metrics", "Mean max Hamming distance, max spread, mean first-escape time per rule.",
           {r: {"mean_max_distance": s["mean_max_distance"], "max_spread": s["max_spread"], "mean_first_escape": s["mean_first_escape"]} for r, s in summary.items()}),
    ]
    return {"deterministic": {"initial_states": inits, "summary": summary, "examples": examples},
            "nondeterministic": {}, "checks": checks, "evidence": evidence}
