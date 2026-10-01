"""Typed terms (parse -> Term -> evaluate) and the identity decomposition (F-010)."""

import hashlib
import json
import tempfile
import unittest

from substrate import purl as P
from substrate.purl_store import Store, compare


def oracle_value_id(kind, value):
    """Independent of substrate.artifacts: plain hashlib + json with the documented canonical form."""
    s = json.dumps({"kind": kind, "value": value}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


class TestParse(unittest.TestCase):
    def test_parse_evaluates_nothing(self):
        # 2^40 states: evaluation of /graph is refused (409), but the term is well-formed and well-sorted.
        t = P.parse("/map/eca/30/40/graph")
        self.assertEqual(t.kind, "graph")
        self.assertEqual([s.op for s in t.steps], ["substrate.map.eca", "substrate.map.graph"])
        with self.assertRaises(P.PurlError) as e:
            P.evaluate(t)
        self.assertEqual(e.exception.code, "not_materialized")

    def test_sorts_are_checked_at_parse(self):
        with self.assertRaises(P.PurlError) as e:
            P.parse("/map/eca/90/8/cycle/0")          # cycle applies to graph, not map
        self.assertEqual((e.exception.status, e.exception.code), (404, "unknown_operation"))
        with self.assertRaises(P.PurlError) as e:
            P.parse("/map/eca/x/8")
        self.assertEqual(e.exception.code, "malformed")
        with self.assertRaises(P.PurlError) as e:
            P.parse("/map/eca/90/8/project/entropy")
        self.assertEqual(e.exception.code, "invalid_param")

    def test_unavailable_is_an_evaluation_fact_not_a_typing_fact(self):
        t = P.parse("/map/eca/90/4/spectrum")         # numpy declared
        self.assertEqual(t.kind, "spectrum")
        if P.missing_requirements(P._by_id("numpy.map.spectrum")):
            with self.assertRaises(P.PurlError) as e:
                P.evaluate(t)
            self.assertEqual(e.exception.status, 501)

    def test_resolve_equals_evaluate_of_parse(self):
        for a in ["/map/eca/110/6/state/1/orbit/at/5/flip/2/damage/16", "/map/increment/3/power/8/table", "/space/4/state/3"]:
            o1, _ = P.resolve(a)
            o2, _ = P.evaluate(P.parse(a))
            self.assertEqual(o1.value, o2.value)

    def test_derivation_id_is_available_without_evaluation_and_differs_from_address_id(self):
        t = P.parse("/map/eca/30/40/graph")
        self.assertTrue(P.derivation_id(t).startswith("sha256:"))
        self.assertNotEqual(P.derivation_id(t), P.address_id(t.address))
        self.assertEqual(P.derivation_id(P.parse("/map/eca/30/40/graph/")), P.derivation_id(t))


class TestIdentityDecomposition(unittest.TestCase):
    def test_value_id_matches_independent_oracle(self):
        o, _ = P.resolve("/map/eca/90/8/state/5")
        self.assertEqual(P.value_id(o), oracle_value_id("state", {"n": 8, "x": 5}))

    def test_one_value_two_addresses(self):
        a = P.get("/space/8/state/5")[1]["identity"]
        b = P.get("/map/eca/90/8/state/5")[1]["identity"]
        self.assertEqual(a["value_id"], b["value_id"])
        self.assertNotEqual(a["address_id"], b["address_id"])
        self.assertNotEqual(a["derivation_id"], b["derivation_id"])

    def test_extensionally_equal_maps_share_value_id(self):
        a = P.get("/map/increment/3/power/8/table")[1]["identity"]
        b = P.get("/map/eca/204/3/table")[1]["identity"]
        self.assertEqual(a["value_id"], b["value_id"])
        self.assertEqual(a["value_id"], oracle_value_id("map", {"n": 3, "table": list(range(8))}))

    def test_not_materialized_map_has_no_value_id(self):
        d = P.get("/map/eca/90/8")[1]["identity"]
        self.assertIsNone(d["value_id"])
        self.assertIn("not materialized", d["value_rule"])

    def test_store_compare_uses_value_id_across_addresses(self):
        s = Store(tempfile.mkdtemp())
        a = s.record("/map/increment/3/power/8/table")["execution"]
        b = s.record("/map/eca/204/3/table")["execution"]
        self.assertEqual(compare(a, b)["verdict"], "same_value")      # was "different_value" before F-010
        c = s.record("/map/eca/90/8")["execution"]
        d = s.record("/map/eca/90/8/power/1")["execution"]
        self.assertEqual(compare(c, d)["verdict"], "value_not_comparable")
        e = s.record("/map/eca/204/3/table")["execution"]
        self.assertEqual(compare(b, e)["verdict"], "reproduced")
        self.assertNotEqual(b["execution_hash"], e["execution_hash"])  # two occurrences, one derivation
        self.assertEqual(b["derivation_id"], e["derivation_id"])


if __name__ == "__main__":
    unittest.main()
