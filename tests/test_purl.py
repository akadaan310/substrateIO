"""Computational addresses (substrate/purl.py, substrate/purl_store.py, tools/purl_server.py)."""

import importlib.util
import json
import random
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from substrate import purl as P
from substrate.core import eca, increment
from substrate.purl_store import Store, compare


class TestResolution(unittest.TestCase):
    def test_derivation_matches_the_instruments(self):
        s, d = P.get("/map/eca/90/8/state/5/next")
        self.assertEqual(s, 200)
        self.assertEqual(d["kind"], "state")
        self.assertEqual(d["value"]["x"], eca(90, 8).table[5])
        self.assertEqual([x["purl"] for x in d["derivation"]], ["/map/eca/90/8", "/map/eca/90/8/state/5", "/map/eca/90/8/state/5/next"])
        self.assertEqual(d["execution"]["effects"], ["pure"])

    def test_resolution_is_pure_and_deterministic(self):
        a, b = P.get("/map/random/6/7/graph")[1], P.get("/map/random/6/7/graph")[1]
        self.assertEqual(a["execution"]["deterministic_sha256"], b["execution"]["deterministic_sha256"])
        self.assertEqual(a["value"], b["value"])

    def test_known_but_not_materialized(self):
        s, d = P.get("/map/eca/30/40/state/5/next")
        self.assertEqual(s, 200)  # a step needs no table
        s, d = P.get("/map/eca/30/40/graph")
        self.assertEqual((s, d["error"]["code"]), (409, "not_materialized"))
        self.assertIn("rule 7", d["error"]["note"])

    def test_known_but_unavailable_in_this_environment(self):
        s, d = P.get("/map/eca/90/4/spectrum")
        if importlib.util.find_spec("numpy") is None:
            self.assertEqual((s, d["error"]["code"], d["error"]["missing"]), (501, "unavailable_here", ["numpy"]))
            self.assertEqual(d["error"]["operation"]["requires"], ["numpy"])
        else:
            self.assertEqual(s, 200)

    def test_errors_are_explanatory(self):
        s, d = P.get("/map/eca/90/8/state/5/teleport")
        self.assertEqual((s, d["error"]["code"]), (404, "unknown_operation"))
        self.assertIn("next", d["error"]["applicable"])
        self.assertEqual(P.get("/map/eca/300/8")[0], 422)
        self.assertEqual(P.get("/map/eca/x/8")[0], 400)
        self.assertEqual(P.get("/map/eca/90")[0], 400)
        self.assertEqual(P.get("/map/eca/90/8/state/256")[0], 422)
        self.assertEqual(P.get("/space/3/state/2/next")[1]["error"]["code"], "no_dynamics")
        self.assertEqual(P.get("/map/eca/90/8/state/5/damage/4")[1]["error"]["code"], "no_baseline")

    def test_derived_maps_and_materialization_are_addressable(self):
        d = P.get("/map/increment/3/power/8/table")[1]
        self.assertEqual(d["value"]["table"], list(range(8)))
        self.assertEqual(d["execution"]["materialized"][0]["why"], "explicit materialization")
        self.assertIn("table_sha256", d["identity"])
        r = P.get("/map/increment/4/rewire/15/15/table")[1]
        self.assertEqual(r["value"]["table"], increment(4).table[:15] + [15])


class TestNavigation(unittest.TestCase):
    ROOTS = ["/map/eca/90/8", "/map/eca/110/6", "/map/increment/4", "/map/random/5/3", "/map/permutation/4/1", "/space/3", "/map/eca/30/40"]

    def test_every_next_link_is_followable_or_refused_with_a_reason(self):
        for root in self.ROOTS:
            frontier, seen = [root], set()
            while frontier and len(seen) < 60:
                u = frontier.pop()
                if u in seen:
                    continue
                seen.add(u)
                s, d = P.get(u)
                self.assertIn(s, (200, 409, 501), (u, d))
                if s != 200:
                    self.assertIn(d["error"]["code"], ("not_materialized", "unavailable_here"), u)
                    continue
                frontier += [l["purl"] for l in d["next"]]

    def test_a_23_step_walk_arrives_somewhere_else_and_is_reproducible(self):
        rng = random.Random(23)
        u, kinds = "/map/eca/110/6", []
        for _ in range(23):
            s, d = P.get(u)
            self.assertEqual(s, 200, u)
            kinds.append(d["kind"])
            ok = [l["purl"] for l in d["next"] if P.get(l["purl"])[0] == 200]
            u = ok[rng.randrange(len(ok))]
        self.assertGreater(len(set(kinds)), 2)
        final = P.get(u)[1]
        self.assertEqual(final["purl"], u)  # the address alone is the continuation
        self.assertEqual(final["execution"]["deterministic_sha256"], P.get(u)[1]["execution"]["deterministic_sha256"])


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_writes_nothing(self):
        P.get("/map/eca/90/8/graph")
        self.assertEqual(self.store.executions(), [])

    def test_record_rerun_and_compare(self):
        a = self.store.record("/map/eca/90/8/graph")
        self.assertIsNone(a["rerun"])
        b = self.store.record("map/eca/90/8/graph/")
        self.assertEqual(b["rerun"]["verdict"], "reproduced")
        self.assertEqual(b["rerun"]["changed"], [])
        self.assertEqual(self.store.history("/map/eca/90/8/graph")["count"], 2)
        changed = dict(b["execution"], code_hash="0" * 64, deterministic_sha256="sha256:other")
        c = compare(a["execution"], changed)
        self.assertEqual((c["verdict"], sorted(c["changed"])), ("differs", ["code_hash", "output"]))

    def test_recorded_executions_reveal_extensional_equivalence(self):
        self.store.record("/map/increment/3/power/8/table")
        r = self.store.record("/map/eca/204/3/table")
        self.assertEqual(r["observations"][0]["kind"], "extensional_equivalence")
        self.assertEqual(r["observations"][0]["status"], "computational")
        self.assertIn("/map/increment/3/power/8/table", r["observations"][0]["addresses"])

    def test_continuations_are_content_addressed_and_branch(self):
        c1 = self.store.continuation(["/map/eca/90/8", "/map/eca/90/8/state/5"])
        self.assertEqual(self.store.continuation(["map/eca/90/8", "/map/eca/90/8/state/5/"])["id"], c1["id"])
        c2 = self.store.continuation(["/map/eca/90/8/state/5/flip/1"], parent=c1["id"])
        self.assertEqual(self.store.get_continuation(c1["id"])["children"], [c2["id"]])
        self.assertTrue(c2["resume"]["next"])
        with self.assertRaises(P.PurlError):
            self.store.continuation(["/map/eca/90/8/teleport"])
        with self.assertRaises(P.PurlError):
            self.store.continuation(["/map/eca/90/8"], parent="cont-nope")


class TestRegistry(unittest.TestCase):
    def test_contracts_are_complete_and_versions_stable(self):
        doc = P.registry_document()
        for o in doc["operations"]:
            for k in ("id", "applies_to", "yields", "template", "description", "effects", "determinism", "implementation", "version"):
                self.assertTrue(o[k] not in (None, "", []), (o["id"], k))
            for ref in o["implementation"]:
                self.assertTrue(ref["locator"].startswith("substrate/"), ref)
        self.assertEqual(P.registry_document(), doc)
        self.assertEqual(len({o["id"] for o in doc["operations"]}), len(doc["operations"]))


class TestHttp(unittest.TestCase):
    def test_curl_surface(self):
        from tools.purl_server import serve
        with tempfile.TemporaryDirectory() as d:
            srv = serve(0, d)
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                base = "http://127.0.0.1:{}".format(port)
                get = lambda p: json.load(urllib.request.urlopen(base + p))
                self.assertEqual(get("/map/eca/90/8/state/5/next")["value"]["x"], 136)
                self.assertEqual(get("/environment")["kind"], "environment")
                post = urllib.request.urlopen(urllib.request.Request(base + "/map/eca/90/8/graph", method="POST"))
                self.assertEqual(post.status, 201)
                self.assertEqual(get("/executions?purl=/map/eca/90/8/graph")["count"], 1)
                with self.assertRaises(urllib.error.HTTPError) as e:
                    urllib.request.urlopen(base + "/map/eca/30/40/graph")
                self.assertEqual(e.exception.code, 409)
            finally:
                srv.shutdown()


if __name__ == "__main__":
    unittest.main()
