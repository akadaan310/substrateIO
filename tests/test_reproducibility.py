"""Every registered experiment must be deterministic given its CONFIG, and
every pre-registered check must evaluate (pass or fail) without error."""

import importlib
import unittest

from substrate.artifacts import sha256_obj
from experiments.run_all import MODULES


class TestExperimentsReproduce(unittest.TestCase):
    def test_deterministic_hash_stable(self):
        for m in MODULES:
            mod = importlib.import_module(m)
            h1 = sha256_obj(mod.run(mod.CONFIG)["deterministic"])
            h2 = sha256_obj(mod.run(mod.CONFIG)["deterministic"])
            self.assertEqual(h1, h2, m)

    def test_specs_complete(self):
        required = {"experiment_id", "question", "hypotheses", "procedure", "expected_result",
                    "falsification_condition", "epistemic_status_of_result"}
        for m in MODULES:
            spec = importlib.import_module(m).SPEC
            self.assertFalse(required - set(spec), m)


if __name__ == "__main__":
    unittest.main()
