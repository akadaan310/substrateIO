"""A minimal HTTP surface for computational addresses. Standard library only.

    python3 -m tools.purl_server [--port 8765] [--store DIR]

    GET  /<purl>                        resolve (pure; writes nothing)
    POST /<purl>                        resolve AND record the execution (append-only)
    GET  /operations[/<id>]             the operation registry / one contract
    GET  /environment                   an observation of this runtime (+ environment_id)
    GET  /term/<purl>                   the typed term (parse only; evaluates nothing)
    GET  /executions?purl=<purl>        execution history of an address, with rerun comparisons
    GET  /executions/<id>[/compare/<id>]
    POST /continuations                 {"trail": [purl, ...], "parent": id?, "note": str?}
    GET  /projections                   declared projections of external records
    POST /observations                  {"projection", "origin", "document"}: project and record
    GET  /observations/<id>
    GET  /continuations/<id>

Why two methods: GET must stay safe (resolution is pure and cacheable);
recording provenance is a write, so it is an explicit POST to the same address.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate import purl as P  # noqa: E402
from substrate.purl_store import Store, compare  # noqa: E402


def route(method: str, raw_path: str, body: bytes, store: Store):
    u = urlparse(raw_path)
    path = unquote(u.path).rstrip("/") or "/"
    q = parse_qs(u.query)
    try:
        if method == "GET" and path == "/":
            return 200, {"protocol": P.PROTOCOL, "kind": "index", "roots": P.registry_document()["roots"],
                         "try": ["/map/eca/90/8", "/map/eca/90/8/state/5/next", "/map/increment/3/power/8"],
                         "links": {"operations": "/operations", "environment": "/environment", "term": "/term/map/eca/90/8/state/5/next"}}
        if method == "GET" and path == "/operations":
            return 200, P.registry_document()
        if method == "GET" and path.startswith("/operations/"):
            oid = path.split("/", 2)[2]
            o = next((x for x in P.REGISTRY if x.id == oid), None)
            if not o:
                raise P.PurlError(404, "not_found", "No operation {}.".format(oid))
            return 200, dict(o.contract(), protocol=P.PROTOCOL, kind="operation", version=P.operation_version(o),
                             executable_here=not P.missing_requirements(o), missing=P.missing_requirements(o))
        if method == "GET" and path == "/environment":
            return 200, dict(P.environment(), environment_id=P.environment_id())
        if method == "GET" and (path == "/term" or path.startswith("/term/")):
            t = P.parse(path[len("/term"):])
            return 200, dict(t.doc(), protocol=P.PROTOCOL, kind_of_document="term", address_id=P.address_id(t.address),
                             semantics="The typed term this address denotes: parsed and sort-checked, NOT evaluated.",
                             links={"evaluate": t.address})
        if method == "GET" and path == "/executions":
            if "purl" not in q:
                raise P.PurlError(400, "malformed", "Use /executions?purl=<address>.")
            return 200, store.history(q["purl"][0])
        if method == "GET" and path.startswith("/executions/"):
            parts = path.split("/")
            if len(parts) == 5 and parts[3] == "compare":
                return 200, dict(compare(store.execution(parts[2]), store.execution(parts[4])), protocol=P.PROTOCOL, kind="comparison")
            return 200, dict(store.execution(parts[2]), protocol=P.PROTOCOL, kind="execution")
        if path == "/observations" and method == "POST":
            d = json.loads(body or b"{}")
            return 201, store.observe(d.get("projection", ""), d.get("origin", ""), d.get("document") or {})
        if method == "GET" and path.startswith("/observations/"):
            return 200, dict(store.observation(path.split("/")[2]), protocol=P.PROTOCOL, kind="observation")
        if method == "GET" and path == "/projections":
            from substrate import acsp_events
            return 200, {"protocol": P.PROTOCOL, "kind": "projection_registry", "projections": [acsp_events.DECLARATION],
                         "record": "POST /observations {projection, origin: harness|service, document}"}
        if path == "/continuations" and method == "POST":
            d = json.loads(body or b"{}")
            return 201, store.continuation(d.get("trail", []), d.get("parent"), d.get("note", ""))
        if method == "GET" and path.startswith("/continuations/"):
            return 200, store.get_continuation(path.split("/")[2])
        if method == "GET":
            return P.get(path)
        if method == "POST":
            return 201, store.record(path)
        raise P.PurlError(405, "method_not_allowed", "Use GET (resolve) or POST (record).")
    except P.PurlError as e:
        return e.status, e.doc(path)
    except json.JSONDecodeError:
        return 400, P.PurlError(400, "malformed", "Body must be JSON.").doc(path)


def make_handler(store: Store):
    class H(BaseHTTPRequestHandler):
        def _go(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            status, doc = route(method, self.path, self.rfile.read(n) if n else b"", store)
            data = (json.dumps(doc, indent=1) + "\n").encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._go("GET")

        def do_POST(self):
            self._go("POST")

        def log_message(self, *a):
            pass
    return H


def serve(port: int = 8765, store_dir: str = None) -> ThreadingHTTPServer:
    store = Store(store_dir) if store_dir else Store()
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(store))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--store", default=None)
    a = ap.parse_args()
    srv = serve(a.port, a.store)
    print("substrate PURL server on http://127.0.0.1:{}/ (store: {})".format(a.port, a.store or "default"))
    srv.serve_forever()


if __name__ == "__main__":
    main()
