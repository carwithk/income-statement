"""Load and validate ledger.json into immutable models.

Every entry is kept, whatever its status. Filtering happens in queries.py.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

STATUSES = {"posted", "draft", "void"}

# Digits with an optional fraction and an optional leading minus sign.
# The minus is allowed here so a negative amount gets its own clear error.
AMOUNT_FORMAT = re.compile(r"-?\d+(\.\d+)?")


@dataclass(frozen=True)
class Account:
    number: str
    name: str
    type: str
    subtype: str
    is_active: bool


@dataclass(frozen=True)
class Line:
    account: str
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True)
class JournalEntry:
    id: str
    date: date
    status: str
    memo: str
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Ledger:
    company: str
    currency: str
    accounts: dict[str, Account]
    entries: tuple[JournalEntry, ...]


def load_ledger(path) -> Ledger:
    """Read ledger.json from disk and return a validated Ledger."""
    with open(path) as f:
        return parse_ledger(json.load(f))


def parse_ledger(raw: dict) -> Ledger:
    """Build a validated Ledger from parsed JSON: accounts first, then entries."""
    accounts = {a["number"]: _parse_account(a) for a in raw["accounts"]}
    entries = tuple(_parse_entry(e, accounts) for e in raw["journal_entries"])
    return Ledger(
        company=raw["company"],
        currency=raw["currency"],
        accounts=accounts,
        entries=entries,
    )


def _parse_account(raw: dict) -> Account:
    """Copy one chart-of-accounts row into an Account."""
    return Account(
        number=raw["number"],
        name=raw["name"],
        type=raw["type"],
        subtype=raw["subtype"],
        is_active=raw["is_active"],
    )


def _parse_entry(raw: dict, accounts: dict[str, Account]) -> JournalEntry:
    """Validate one journal entry's status, lines, and balance, then build it."""
    entry_id = raw["id"]
    if raw["status"] not in STATUSES:
        raise ValueError(f"{entry_id}: unknown status {raw['status']!r}")

    lines = tuple(_parse_line(line, entry_id, accounts) for line in raw["lines"])

    debits = sum((line.debit for line in lines), Decimal("0"))
    credits = sum((line.credit for line in lines), Decimal("0"))
    if debits != credits:
        raise ValueError(
            f"{entry_id}: debits {debits} do not equal credits {credits}"
        )

    return JournalEntry(
        id=entry_id,
        date=date.fromisoformat(raw["date"]),
        status=raw["status"],
        memo=raw["memo"],
        lines=lines,
    )


def _parse_line(raw: dict, entry_id: str, accounts: dict[str, Account]) -> Line:
    """Validate one journal line's account and amounts, then build it."""
    if raw["account"] not in accounts:
        raise ValueError(f"{entry_id}: unknown account {raw['account']!r}")

    debit = _parse_amount(raw["debit"], f"{entry_id} debit")
    credit = _parse_amount(raw["credit"], f"{entry_id} credit")
    if (debit == 0) == (credit == 0):
        raise ValueError(
            f"{entry_id}: line on account {raw['account']} must have exactly "
            f"one of debit or credit non-zero (got {debit} / {credit})"
        )
    return Line(account=raw["account"], debit=debit, credit=credit)


def _parse_amount(value, where: str) -> Decimal:
    """Turn an amount string into a non-negative Decimal, or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError(f"{where}: amount must be a string, got {value!r}")
    if not AMOUNT_FORMAT.fullmatch(value):
        raise ValueError(f"{where}: invalid amount {value!r}")
    amount = Decimal(value)
    if amount < 0:
        raise ValueError(f"{where}: amount must not be negative, got {value!r}")
    return amount
