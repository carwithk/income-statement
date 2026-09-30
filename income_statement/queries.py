"""Select journal lines from a ledger and total them by account."""

from datetime import date
from decimal import Decimal

from income_statement.ledger import Ledger, Line


def lines_in_range(
    ledger: Ledger,
    start: date,
    end: date,
    statuses: frozenset[str] = frozenset({"posted"}),
) -> list[Line]:
    """Lines of entries with a status in `statuses` dated start..end, inclusive."""
    return [
        line
        for entry in ledger.entries
        if entry.status in statuses and start <= entry.date <= end
        for line in entry.lines
    ]


def net_by_account(lines: list[Line]) -> dict[str, Decimal]:
    """Total debit minus total credit for each account that has lines."""
    totals: dict[str, Decimal] = {}
    for line in lines:
        totals[line.account] = (
            totals.get(line.account, Decimal("0")) + line.debit - line.credit
        )
    return totals
