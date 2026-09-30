from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from income_statement.ledger import load_ledger, parse_ledger

LEDGER_PATH = Path(__file__).parent.parent / "ledger.json"


def make_raw(lines, status="posted"):
    """A one-entry ledger with two accounts, for the validation tests."""
    return {
        "company": "Test Co",
        "currency": "USD",
        "accounts": [
            {"number": "1000", "name": "Cash", "type": "asset",
             "subtype": "balance_sheet", "is_active": True},
            {"number": "4000", "name": "Sales", "type": "revenue",
             "subtype": "operating_revenue", "is_active": True},
        ],
        "journal_entries": [
            {"id": "JE-1", "date": "2026-01-05", "status": status,
             "memo": "test", "lines": lines},
        ],
    }


def line(account, debit, credit):
    return {"account": account, "debit": debit, "credit": credit}


GOOD_LINES = [line("1000", "10.00", "0.00"), line("4000", "0.00", "10.00")]


# --- the real file ---

# The real ledger.json loads with the right company, currency, and counts.
def test_real_ledger_loads_with_expected_counts():
    ledger = load_ledger(LEDGER_PATH)
    assert ledger.company == "Northwind Coffee Roasters"
    assert ledger.currency == "USD"
    assert len(ledger.accounts) == 15
    assert len(ledger.entries) == 25


# Loading keeps every entry; draft and void are filtered later, not here.
def test_real_ledger_keeps_draft_and_void_entries():
    ledger = load_ledger(LEDGER_PATH)
    statuses = [e.status for e in ledger.entries]
    assert statuses.count("posted") == 22
    assert statuses.count("draft") == 1
    assert statuses.count("void") == 2


# Amounts become exact Decimals and dates become date objects (JE-016 has 3 lines).
def test_real_ledger_parses_amounts_as_decimal_and_dates_as_date():
    ledger = load_ledger(LEDGER_PATH)
    je016 = next(e for e in ledger.entries if e.id == "JE-016")
    assert je016.date == date(2026, 3, 2)
    assert [(l.account, l.debit, l.credit) for l in je016.lines] == [
        ("1100", Decimal("14850.00"), Decimal("0.00")),
        ("4900", Decimal("150.00"), Decimal("0.00")),
        ("4000", Decimal("0.00"), Decimal("15000.00")),
    ]
    for entry in ledger.entries:
        for l in entry.lines:
            assert type(l.debit) is Decimal
            assert type(l.credit) is Decimal


# The inactive account 6300 is still loaded, since its history counts.
def test_real_ledger_keeps_inactive_account():
    ledger = load_ledger(LEDGER_PATH)
    assert ledger.accounts["6300"].is_active is False


# Sanity check: the small example used below is valid on its own.
def test_valid_example_parses():
    ledger = parse_ledger(make_raw(GOOD_LINES))
    assert len(ledger.entries) == 1


# --- validation rules ---

# Amounts given as JSON numbers or null (not strings) are rejected.
@pytest.mark.parametrize("bad", [10, 10.0, None])
def test_rejects_amount_that_is_not_a_string(bad):
    lines = [line("1000", bad, "0.00"), line("4000", "0.00", "10.00")]
    with pytest.raises(ValueError, match="must be a string"):
        parse_ledger(make_raw(lines))


# Strings that are not plain decimals (commas, exponents, NaN, spaces) are rejected.
@pytest.mark.parametrize("bad", ["", "abc", "1,000.00", "1e3", "NaN", "Infinity", " 10.00"])
def test_rejects_amount_in_invalid_format(bad):
    lines = [line("1000", bad, "0.00"), line("4000", "0.00", "10.00")]
    with pytest.raises(ValueError, match="invalid amount"):
        parse_ledger(make_raw(lines))


# A negative debit or credit is rejected.
def test_rejects_negative_amount():
    # Balanced overall, so only the negative check can catch it.
    lines = [line("1000", "-10.00", "0.00"), line("4000", "-10.00", "0.00"),
             line("4000", "0.00", "-20.00")]
    with pytest.raises(ValueError, match="must not be negative"):
        parse_ledger(make_raw(lines))


# A line with both a debit and a credit is rejected.
def test_rejects_line_with_both_debit_and_credit():
    lines = [line("1000", "10.00", "10.00"), line("4000", "0.00", "0.00")]
    with pytest.raises(ValueError, match="exactly one of debit or credit"):
        parse_ledger(make_raw(lines))


# A line with zero debit and zero credit is rejected.
def test_rejects_line_with_neither_debit_nor_credit():
    lines = GOOD_LINES + [line("1000", "0.00", "0.00")]
    with pytest.raises(ValueError, match="exactly one of debit or credit"):
        parse_ledger(make_raw(lines))


# An entry whose debits and credits differ (even by one cent) is rejected.
def test_rejects_unbalanced_entry():
    lines = [line("1000", "10.00", "0.00"), line("4000", "0.00", "9.99")]
    with pytest.raises(ValueError, match="do not equal"):
        parse_ledger(make_raw(lines))


# A line posting to an account not in the chart of accounts is rejected.
def test_rejects_unknown_account():
    lines = [line("1000", "10.00", "0.00"), line("9999", "0.00", "10.00")]
    with pytest.raises(ValueError, match="unknown account '9999'"):
        parse_ledger(make_raw(lines))


# A status other than posted, draft, or void is rejected.
def test_rejects_unknown_status():
    with pytest.raises(ValueError, match="unknown status 'pending'"):
        parse_ledger(make_raw(GOOD_LINES, status="pending"))
