"""Income statement layout, as data, and the builder that fills it in."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from income_statement.ledger import Ledger
from income_statement.queries import lines_in_range, net_by_account

# How a section turns (debit - credit) into the amount shown.
DEBIT = 1    # expenses: shown as (debit - credit)
CREDIT = -1  # revenue:  shown as -(debit - credit)


@dataclass(frozen=True)
class Section:
    name: str
    subtypes: tuple[str, ...]
    sign: int


@dataclass(frozen=True)
class Subtotal:
    name: str
    terms: tuple[tuple[int, str], ...]  # (+1 or -1, name of an earlier item)


LAYOUT = (
    Section("Revenue", ("operating_revenue", "contra_revenue"), CREDIT),
    Section("Cost of goods sold", ("cogs",), DEBIT),
    Subtotal("Gross profit", ((+1, "Revenue"), (-1, "Cost of goods sold"))),
    Section("Operating expenses", ("operating_expense",), DEBIT),
    Subtotal("Operating income", ((+1, "Gross profit"), (-1, "Operating expenses"))),
    Section("Other income", ("other_income",), CREDIT),
    Subtotal("Net income", ((+1, "Operating income"), (+1, "Other income"))),
)


def build_income_statement(ledger: Ledger, start: date, end: date) -> dict:
    """Net posted lines in the range by account, then fill LAYOUT in order."""
    net = net_by_account(lines_in_range(ledger, start, end))
    values: dict[str, Decimal] = {}  # section totals and subtotals, by name
    items = []

    for entry in LAYOUT:
        if isinstance(entry, Section):
            item = _build_section(entry, ledger, net)
            values[entry.name] = item["total"]
        else:
            amount = sum(
                (_apply_sign(sign, values[name]) for sign, name in entry.terms),
                Decimal("0"),
            )
            item = {"kind": "subtotal", "name": entry.name, "amount": amount}
            values[entry.name] = amount
        items.append(item)

    return {
        "company": ledger.company,
        "currency": ledger.currency,
        "start": start,
        "end": end,
        "items": items,
    }


def _build_section(section: Section, ledger: Ledger, net: dict[str, Decimal]) -> dict:
    """One signed row per account in the section's subtypes, plus a total."""
    accounts = sorted(
        (a for a in ledger.accounts.values() if a.subtype in section.subtypes),
        key=lambda a: a.number,
    )
    lines = [
        {
            "account": a.number,
            "name": a.name,
            "amount": _apply_sign(section.sign, net.get(a.number, Decimal("0"))),
        }
        for a in accounts
    ]
    total = sum((line["amount"] for line in lines), Decimal("0"))
    return {"kind": "section", "name": section.name, "lines": lines, "total": total}


def _apply_sign(sign: int, value: Decimal) -> Decimal:
    """Return value as-is for +1, negated for -1."""
    # Negate instead of multiplying by -1: -1 * Decimal("0") is Decimal("-0"),
    # which would print as "-0.00"; -Decimal("0") stays "0".
    return value if sign == 1 else -value
