"""Projection P-ACSP-EV-1 over a real ACSP/0.1 event list (live field-trial resource, snapshot 2026-10-01)."""

import copy
import json
import os
import tempfile
import unittest

from substrate import acsp_events as AE
from substrate.purl import PurlError
from substrate.purl_store import Store

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "acsp", "live-8N2RXG1MW79S-2026-10-01.events.json")


class TestAcspEvents(unittest.TestCase):
    def setUp(self):
        with open(FIX) as f:
            self.doc = json.load(f)

    def test_live_snapshot_is_consistent(self):
        self.assertEqual(AE.verify(self.doc), [])

    def test_measurements(self):
        r = AE.project(self.doc, "service")
        m = r["measurements"]
        self.assertEqual(m["n"], 12)
        self.assertEqual(m["label_counts"], {"append": 3, "checkpoint": 1, "create": 1, "propose": 7})
        self.assertEqual(r["epistemic_status"], "UNRESOLVED")
        self.assertEqual(m["session_switches"], [6, 8, 9, 10, 11])

    def test_status_is_declared_not_inferred(self):
        self.assertEqual(AE.project(self.doc, "harness")["epistemic_status"], "SIMULATED")
        with self.assertRaises(ValueError):
            AE.project(self.doc, "observed")

    def test_wall_clock_excluded_from_hash(self):
        d2 = copy.deepcopy(self.doc)
        for e in d2["events"]:
            e["occurred_at"] = "1970-01-01T00:00:00.000Z"
        self.assertEqual(AE.project(d2, "service")["deterministic_sha256"], AE.project(self.doc, "service")["deterministic_sha256"])

    def test_tampering_detected(self):
        d2 = copy.deepcopy(self.doc)
        del d2["events"][3]
        self.assertTrue(AE.verify(d2))
        self.assertTrue(AE.project(d2, "service")["chain_problems"])

    def test_store_records_observation(self):
        s = Store(tempfile.mkdtemp())
        a = s.observe("P-ACSP-EV-1", "service", self.doc)
        b = s.observe("P-ACSP-EV-1", "service", self.doc)
        self.assertEqual(b["previous"], a["observation"]["observation_id"])
        self.assertEqual(a["observation"]["deterministic_sha256"], b["observation"]["deterministic_sha256"])
        with self.assertRaises(PurlError):
            s.observe("P-ACSP-EV-1", "service", {"type": "event_list"})


if __name__ == "__main__":
    unittest.main()
