from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from income_statement.ledger import JournalEntry, Ledger, Line, load_ledger
from income_statement.queries import lines_in_range, net_by_account

LEDGER_PATH = Path(__file__).parent.parent / "ledger.json"


def entry(entry_id, day, status="posted", amount="100.00", debit="1000", credit="4000"):
    """A two-line balanced entry: debit one account, credit another."""
    return JournalEntry(
        id=entry_id,
        date=day,
        status=status,
        memo="",
        lines=(
            Line(debit, Decimal(amount), Decimal("0")),
            Line(credit, Decimal("0"), Decimal(amount)),
        ),
    )


def ledger_of(*entries):
    # Accounts are not looked at by the queries, so none are needed here.
    return Ledger(company="Test Co", currency="USD", accounts={}, entries=entries)


def entry_ids(ledger, lines):
    """Which entries the returned lines came from, in ledger order.

    Compares by identity: equal-looking lines (JE-009 and JE-010) are
    different objects from different entries.
    """
    returned = {id(l) for l in lines}
    return [e.id for e in ledger.entries if any(id(l) in returned for l in e.lines)]


JAN_1 = date(2026, 1, 1)
JAN_31 = date(2026, 1, 31)


# --- lines_in_range: status ---

# Only posted entries count by default; draft and void are left out.
def test_excludes_draft_and_void_by_default():
    ledger = ledger_of(
        entry("POSTED", JAN_1, "posted", "1.00"),
        entry("DRAFT", JAN_1, "draft", "2.00"),
        entry("VOID", JAN_1, "void", "3.00"),
    )
    lines = lines_in_range(ledger, JAN_1, JAN_31)
    assert entry_ids(ledger, lines) == ["POSTED"]
    assert net_by_account(lines) == {"1000": Decimal("1.00"), "4000": Decimal("-1.00")}


# Passing statuses explicitly brings draft and void entries back in.
def test_includes_draft_and_void_when_requested():
    ledger = ledger_of(
        entry("POSTED", JAN_1, "posted", "1.00"),
        entry("DRAFT", JAN_1, "draft", "2.00"),
        entry("VOID", JAN_1, "void", "3.00"),
    )
    lines = lines_in_range(ledger, JAN_1, JAN_31, frozenset({"posted", "draft"}))
    assert entry_ids(ledger, lines) == ["POSTED", "DRAFT"]

    lines = lines_in_range(ledger, JAN_1, JAN_31, frozenset({"posted", "draft", "void"}))
    assert entry_ids(ledger, lines) == ["POSTED", "DRAFT", "VOID"]


# --- lines_in_range: dates ---

# Entries on the start date and on the end date are both included.
def test_start_and_end_dates_are_inclusive():
    ledger = ledger_of(entry("ON_START", JAN_1), entry("ON_END", JAN_31))
    lines = lines_in_range(ledger, JAN_1, JAN_31)
    assert entry_ids(ledger, lines) == ["ON_START", "ON_END"]


# Entries one day before start or one day after end are excluded.
def test_one_day_outside_the_range_is_excluded():
    ledger = ledger_of(
        entry("DAY_BEFORE", date(2025, 12, 31)),
        entry("INSIDE", date(2026, 1, 15)),
        entry("DAY_AFTER", date(2026, 2, 1)),
    )
    lines = lines_in_range(ledger, JAN_1, JAN_31)
    assert entry_ids(ledger, lines) == ["INSIDE"]


# A one-day range (start == end) returns that day's entries only.
def test_single_day_range():
    ledger = ledger_of(entry("A", JAN_1), entry("B", date(2026, 1, 2)))
    lines = lines_in_range(ledger, JAN_1, JAN_1)
    assert entry_ids(ledger, lines) == ["A"]


# Entries out of date order are still filtered by date, not by position.
def test_unsorted_entries_still_work():
    ledger = ledger_of(
        entry("MAR", date(2026, 3, 1), amount="4.00"),
        entry("JAN", date(2026, 1, 15), amount="1.00"),
        entry("DEC", date(2025, 12, 1), amount="8.00"),
        entry("FEB", date(2026, 2, 1), amount="2.00"),
    )
    lines = lines_in_range(ledger, date(2026, 1, 1), date(2026, 2, 28))
    assert entry_ids(ledger, lines) == ["JAN", "FEB"]
    assert net_by_account(lines)["1000"] == Decimal("3.00")


# --- net_by_account ---

# Several lines on one account are netted: debits add, credits subtract.
def test_multiple_lines_on_same_account_are_netted():
    lines = [
        Line("6200", Decimal("1199.97"), Decimal("0")),
        Line("6200", Decimal("0"), Decimal("100.00")),
        Line("6200", Decimal("0.03"), Decimal("0")),
        Line("2000", Decimal("0"), Decimal("1100.00")),
    ]
    assert net_by_account(lines) == {
        "6200": Decimal("1100.00"),
        "2000": Decimal("-1100.00"),
    }


# No lines gives an empty result, not zeros for every account.
def test_no_lines_gives_empty_result():
    assert net_by_account([]) == {}


# --- real ledger ---

def _ranges_to_check():
    """Every (start, end) pair drawn from each entry date and the days around it."""
    ledger = load_ledger(LEDGER_PATH)
    days = sorted(
        {e.date + timedelta(days=d) for e in ledger.entries for d in (-1, 0, 1)}
    )
    return [(s, e) for s in days for e in days if s <= e]


# Double entry: for any date range, all accounts together net to exactly zero.
@pytest.mark.parametrize("statuses", [
    frozenset({"posted"}),
    frozenset({"posted", "draft", "void"}),
])
def test_real_ledger_nets_to_zero_for_any_range(statuses):
    ledger = load_ledger(LEDGER_PATH)
    ranges = _ranges_to_check()
    assert len(ranges) > 1000
    for start, end in ranges:
        totals = net_by_account(lines_in_range(ledger, start, end, statuses))
        assert sum(totals.values(), Decimal("0")) == Decimal("0"), (start, end)


# Q1 2026 on the real ledger picks exactly the posted entries in Jan-Mar.
def test_real_ledger_q1_selects_expected_entries():
    ledger = load_ledger(LEDGER_PATH)
    lines = lines_in_range(ledger, date(2026, 1, 1), date(2026, 3, 31))
    expected = [f"JE-{n:03d}" for n in range(2, 24) if n not in (9, 19)]
    assert sorted(entry_ids(ledger, lines)) == expected
