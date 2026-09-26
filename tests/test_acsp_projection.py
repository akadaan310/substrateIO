"""The ACSP transition-history reader (substrate.acsp).

The fixture is an export produced by ACSP's Program 001 harness (Experiment
A, simulated actors). It is input data for the instrument, not evidence: no
registry entry cites it.
"""

import copy
import os
import unittest

from substrate import acsp

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "acsp", "p001-exp-a-kill-recover.transitions.json")


class TestAcspProjection(unittest.TestCase):
    def setUp(self):
        self.doc = acsp.load(FIXTURE)

    def test_export_is_consistent_and_hash_recomputes_independently(self):
        self.assertEqual(self.doc["format"], acsp.FORMAT)
        self.assertEqual(acsp.verify(self.doc), [])

    def test_tampering_is_detected(self):
        bad = copy.deepcopy(self.doc)
        ex = next(t for t in bad["transitions"] if t.get("execution"))
        ex["execution"]["outputs"] = {"s1": 41}
        self.assertTrue(any("deterministic_sha256" in p for p in acsp.verify(bad)))
        gap = copy.deepcopy(self.doc)
        del gap["transitions"][3]
        self.assertTrue(any("not contiguous" in p for p in acsp.verify(gap)))

    def test_one_identity_many_embodiments(self):
        s = acsp.summary(self.doc)
        embodied = [seg for seg in s["embodiments"] if seg["embodiment_id"]]
        self.assertEqual([seg["session_id"] for seg in embodied], ["session-a", "session-b", "session-c"])
        self.assertEqual(len({s["agent_id"]}), 1)
        self.assertEqual(s["observation_labels"]["RECOVERY"], 2)

    def test_operation_system_is_a_coarse_projection(self):
        g = acsp.operation_system(self.doc)
        self.assertEqual(set(g.adj), set(t["operation"] for t in self.doc["transitions"]))
        # Labels only: executions with different outputs are indistinguishable here.
        self.assertIn("execute", g.adj["execute"])


if __name__ == "__main__":
    unittest.main()
