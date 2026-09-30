"""HTTP handler for GET /income-statement."""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import tornado.web

from income_statement.ledger import Ledger
from income_statement.statements import build_income_statement

# date.fromisoformat also accepts forms like "20260101" and "2026-W01-1",
# so check the exact YYYY-MM-DD shape first.
DATE_FORMAT = re.compile(r"\d{4}-\d{2}-\d{2}")
CENTS = Decimal("0.01")


class IncomeStatementHandler(tornado.web.RequestHandler):
    def initialize(self, ledger: Ledger):
        """Receive the ledger that app.py loaded at startup."""
        self.ledger = ledger

    def get(self):
        """Validate start/end, build the statement, and write it as JSON (or a 400)."""
        try:
            start = parse_date(self.get_query_argument("start", None), "start")
            end = parse_date(self.get_query_argument("end", None), "end")
            if start > end:
                raise ValueError(f"start ({start}) must be on or before end ({end})")
        except ValueError as e:
            self.set_status(400)
            self.write({"error": str(e)})
            return

        statement = build_income_statement(self.ledger, start, end)
        self.write(to_json(statement))


def parse_date(value: str | None, name: str) -> date:
    """Turn a YYYY-MM-DD query value into a date, or raise a clear ValueError."""
    if not value:
        raise ValueError(f"{name} is required, as YYYY-MM-DD")
    if not DATE_FORMAT.fullmatch(value):
        raise ValueError(f"{name} must be a date as YYYY-MM-DD, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} is not a real date: {value!r}") from None


def to_json(value):
    """Copy of `value` with Decimals as two-decimal strings and dates as ISO."""
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json(v) for v in value]
    if isinstance(value, Decimal):
        return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))
    if isinstance(value, date):
        return value.isoformat()
    return value
