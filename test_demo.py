import json
from threading import Thread
from unittest import TestCase
from urllib.error import HTTPError
from urllib.request import urlopen

from serve import FIXTURE, Handler, ThreadingHTTPServer, run


class HttpTest(TestCase):
    def test_routes_and_validation(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base, timeout=3) as response:
                    self.assertIn(b'name="viewport"', response.read())
                with urlopen(base + "/api/replay", timeout=3) as response:
                    self.assertEqual(json.load(response), run(FIXTURE, {}))
                for query in ("unknown=1", "budget=NaN", "test=1&test=2"):
                    with self.assertRaises(HTTPError) as failure:
                        urlopen(base + "/api/replay?" + query, timeout=3)
                    with failure.exception as response:
                        self.assertEqual(response.code, 400)
                with self.assertRaises(HTTPError) as failure:
                    urlopen(base + "/not-a-route", timeout=3)
                failure.exception.close()
                self.assertEqual(failure.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=3)

class WalletTest(TestCase):
    def test_balances_and_duplicate_signature(self):
        result = run(FIXTURE, {})
        self.assertEqual(len(result["rows"]), 7)
        self.assertEqual(dict(result["metrics"])["Copied swaps"], "3")
        self.assertEqual(dict(result["metrics"])["Cash remaining (USDC)"], "46.84")
        self.assertEqual(result["rows"][0][1:5], ["Buy MOSS", "2.0000", "Copied", "10.0000"])

    def test_transfer_failure_and_no_inventory_are_not_fills(self):
        rows = run(FIXTURE, {})["rows"]
        self.assertEqual(rows[2][-1], "Not an unambiguous quote-token swap")
        self.assertEqual(rows[4][-1], "No copied inventory to sell")
        self.assertEqual(rows[5][-1], "Source transaction failed")

    def test_lower_cap_removes_buy_and_subsequent_sell(self):
        rows = run(FIXTURE, {"cap": "1.50"})["rows"]
        self.assertEqual(rows[0][-1], "Source price exceeds buy cap")
        self.assertEqual(rows[3][-1], "No copied inventory to sell")

    def test_quote_fee_counts_against_budget(self):
        rows = run(FIXTURE, {"budget": "20"})["rows"]
        self.assertEqual(rows[0][-1], "Insufficient simulated USDC")
        self.assertEqual(run(FIXTURE, {"budget": "20", "fee": "0"})["rows"][0][3], "Copied")
