import json
import re
from decimal import Decimal

from tornado.testing import AsyncHTTPTestCase

from income_statement.api import to_json
from income_statement.app import LEDGER_PATH, make_app
from income_statement.ledger import load_ledger

MONEY = re.compile(r"-?\d+\.\d{2}")


def amounts(body):
    """Every line amount, section total, and subtotal in a response body."""
    found = []
    for item in body["items"]:
        if item["kind"] == "section":
            found += [line["amount"] for line in item["lines"]] + [item["total"]]
        else:
            found.append(item["amount"])
    return found


def item(body, name):
    return next(i for i in body["items"] if i["name"] == name)


class IncomeStatementApiTest(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(load_ledger(LEDGER_PATH))

    def get_json(self, url):
        response = self.fetch(url)
        return response, json.loads(response.body)

    def assert_400(self, url, message_part):
        response, body = self.get_json(url)
        self.assertEqual(response.code, 400)
        self.assertEqual(list(body), ["error"])
        self.assertIn(message_part, body["error"])

    # Q1 returns 200 JSON with every amount as a two-decimal string.
    def test_q1_returns_string_amounts(self):
        response, body = self.get_json("/income-statement?start=2026-01-01&end=2026-03-31")
        self.assertEqual(response.code, 200)
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(body["start"], "2026-01-01")
        self.assertEqual(body["end"], "2026-03-31")
        for amount in amounts(body):
            self.assertIsInstance(amount, str)
            self.assertRegex(amount, MONEY)
        self.assertEqual(item(body, "Net income")["amount"], "-44480.14")
        revenue_lines = {l["account"]: l["amount"] for l in item(body, "Revenue")["lines"]}
        self.assertEqual(revenue_lines["4900"], "-800.25")

    # A range with no activity shows zeros as "0.00", never "0" or "-0.00".
    def test_empty_range_shows_zeros_with_two_decimals(self):
        _, body = self.get_json("/income-statement?start=2030-01-01&end=2030-01-31")
        self.assertEqual(set(amounts(body)), {"0.00"})

    # start == end is a valid one-day range.
    def test_single_day_range_is_ok(self):
        response, body = self.get_json("/income-statement?start=2026-03-31&end=2026-03-31")
        self.assertEqual(response.code, 200)
        self.assertEqual(item(body, "Other income")["total"], "42.18")

    # Missing or empty start/end each return 400.
    def test_missing_params_return_400(self):
        self.assert_400("/income-statement", "start is required")
        self.assert_400("/income-statement?end=2026-03-31", "start is required")
        self.assert_400("/income-statement?start=2026-01-01", "end is required")
        self.assert_400("/income-statement?start=&end=2026-03-31", "start is required")

    # Dates that are not YYYY-MM-DD, or not real days, return 400.
    def test_bad_dates_return_400(self):
        for bad in ["not-a-date", "2026/01/01", "20260101", "2026-1-1", "2026-W01-1"]:
            self.assert_400(f"/income-statement?start={bad}&end=2026-03-31", "YYYY-MM-DD")
        for bad in ["2026-02-30", "2026-13-01"]:
            self.assert_400(f"/income-statement?start=2026-01-01&end={bad}", "not a real date")

    # start after end returns 400.
    def test_start_after_end_returns_400(self):
        self.assert_400("/income-statement?start=2026-03-31&end=2026-01-01", "on or before")

    # The frontend page is served at /.
    def test_root_serves_index_html(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])


# Decimals are formatted with exactly two places, without float conversion.
def test_to_json_formats_decimals_exactly():
    assert to_json({"a": [Decimal("1"), Decimal("-0.5"), Decimal("12450.75")]}) == {
        "a": ["1.00", "-0.50", "12450.75"],
    }
    assert to_json(Decimal("0.1") + Decimal("0.2")) == "0.30"
