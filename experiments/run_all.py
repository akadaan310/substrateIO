"""Run every registered experiment, record artifacts/evidence, and sync the
experiment registry.

    python3 -m experiments.run_all            # run + record all
    python3 -m experiments.run_all EXP-D      # run + record one
    python3 -m experiments.run_all --dry      # run, record nothing

Running twice with unchanged code/config records a reproduction (identical
deterministic hash) or, if outputs differ, an automatic failure-ledger entry.
"""

import sys

from substrate.ledger import run_experiment, sync_experiment_registry

MODULES = [
    "experiments.exp_a_one_bit",
    "experiments.exp_b_one_bit_trace",
    "experiments.exp_c_multibit_graph",
    "experiments.exp_d_perturbation",
    "experiments.exp_e_structural_comparison",
    "experiments.exp_f_projection",
    "experiments.exp_g_cross_layer",
]


def main(argv):
    dry = "--dry" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    failed = False
    for m in MODULES:
        if wanted and not any(w.lower().replace("exp-", "exp_") in m for w in wanted):
            continue
        out = run_experiment(m, record=not dry)
        bad = [c["id"] for c in out["checks"] if not c["passed"]]
        failed |= bool(bad)
        print("{:<42} {}  {:6.2f}s  checks {}/{}{}".format(
            m, out["run_id"], out["wall_s"], len(out["checks"]) - len(bad), len(out["checks"]),
            "  FAILED: " + ",".join(bad) if bad else ""))
    if not dry:
        sync_experiment_registry(MODULES)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
