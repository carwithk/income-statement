from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from income_statement.ledger import load_ledger
from income_statement.queries import lines_in_range, net_by_account
from income_statement.statements import build_income_statement

LEDGER = load_ledger(Path(__file__).parent.parent / "ledger.json")

Q1 = (date(2026, 1, 1), date(2026, 3, 31))
JANUARY = (date(2026, 1, 1), date(2026, 1, 31))
FEBRUARY = (date(2026, 2, 1), date(2026, 2, 28))


def build(start, end):
    return build_income_statement(LEDGER, start, end)


def item(statement, name):
    return next(i for i in statement["items"] if i["name"] == name)


def line(section, account):
    return next(l for l in section["lines"] if l["account"] == account)


def accounts_in(section):
    return [l["account"] for l in section["lines"]]


# The statement lists sections and subtotals in the required order.
def test_items_are_in_statement_order():
    statement = build(*Q1)
    assert [(i["kind"], i["name"]) for i in statement["items"]] == [
        ("section", "Revenue"),
        ("section", "Cost of goods sold"),
        ("subtotal", "Gross profit"),
        ("section", "Operating expenses"),
        ("subtotal", "Operating income"),
        ("section", "Other income"),
        ("subtotal", "Net income"),
    ]


# Interest Income (type revenue, subtype other_income) goes under Other income.
def test_interest_income_is_other_income_not_revenue():
    statement = build(*Q1)
    assert "7000" not in accounts_in(item(statement, "Revenue"))
    other = item(statement, "Other income")
    assert accounts_in(other) == ["7000"]
    assert line(other, "7000")["amount"] == Decimal("42.18")


# Sales Returns & Discounts shows negative inside Revenue and lowers its total.
def test_contra_revenue_is_negative_and_reduces_revenue():
    revenue = item(build(*Q1), "Revenue")
    assert line(revenue, "4900")["amount"] == Decimal("-800.25")  # 650.25 + 150.00
    assert line(revenue, "4000")["amount"] == Decimal("35650.75")
    assert line(revenue, "4100")["amount"] == Decimal("3000.00")
    assert revenue["total"] == Decimal("37850.50")


# The vendor's 100.00 credit (JE-020) is netted against Software expense.
def test_vendor_credit_reduces_software_expense():
    march = build(date(2026, 3, 1), date(2026, 3, 31))
    assert line(item(march, "Operating expenses"), "6200")["amount"] == Decimal("1099.97")

    credit_day_only = build(date(2026, 3, 20), date(2026, 3, 20))
    assert line(item(credit_day_only, "Operating expenses"), "6200")["amount"] == Decimal("-100.00")


# Inactive Marketing (legacy) still shows, with its January posting.
def test_inactive_account_still_appears():
    opex = item(build(*JANUARY), "Operating expenses")
    assert line(opex, "6300") == {
        "account": "6300", "name": "Marketing (legacy)", "amount": Decimal("2500.10"),
    }


# The 12,000 annual billing hits Deferred Revenue, not revenue; only the
# 1,000 monthly recognitions do.
def test_annual_billing_is_not_revenue():
    billing_day = build(date(2026, 1, 10), date(2026, 1, 10))
    assert item(billing_day, "Revenue")["total"] == Decimal("0")

    january = item(build(*JANUARY), "Revenue")
    assert line(january, "4100")["amount"] == Decimal("1000.00")
    assert january["total"] == Decimal("13450.75")  # 12450.75 product + 1000.00


# Rent for Jan-Mar is booked on Jan 1 and is not spread across the quarter.
def test_january_includes_full_quarter_of_rent():
    assert line(item(build(*JANUARY), "Operating expenses"), "6100")["amount"] == Decimal("9000.00")
    assert line(item(build(*FEBRUARY), "Operating expenses"), "6100")["amount"] == Decimal("0")


# The draft 5,000 bonus accrual and the void duplicate sale are left out.
def test_draft_and_void_entries_are_excluded():
    statement = build(*Q1)
    assert line(item(statement, "Operating expenses"), "6000")["amount"] == Decimal("55500.00")
    assert line(item(statement, "Revenue"), "4000")["amount"] == Decimal("35650.75")


# A range with no entries lists every account at zero, with no "-0".
def test_range_with_no_entries_is_all_zeros():
    statement = build(date(2030, 1, 1), date(2030, 12, 31))
    for i in statement["items"]:
        if i["kind"] == "section":
            amounts = [l["amount"] for l in i["lines"]] + [i["total"]]
        else:
            amounts = [i["amount"]]
        for amount in amounts:
            assert amount == 0
            assert not amount.is_signed(), (i["name"], amount)
    assert len(accounts_in(item(statement, "Operating expenses"))) == 4


# Every P&L account appears, grouped by subtype and sorted by number.
def test_every_income_statement_account_listed_once_in_order():
    statement = build(*Q1)
    sections = {i["name"]: accounts_in(i) for i in statement["items"] if i["kind"] == "section"}
    assert sections == {
        "Revenue": ["4000", "4100", "4900"],
        "Cost of goods sold": ["5000"],
        "Operating expenses": ["6000", "6100", "6200", "6300"],
        "Other income": ["7000"],
    }


# The statement echoes the company, currency, and requested dates.
def test_header_fields():
    statement = build(*Q1)
    assert statement["company"] == "Northwind Coffee Roasters"
    assert statement["currency"] == "USD"
    assert (statement["start"], statement["end"]) == Q1


def _ranges_to_check():
    """(start, end) pairs drawn from each entry date and the days around it."""
    days = sorted({e.date + timedelta(days=d) for e in LEDGER.entries for d in (-1, 0, 1)})
    return [(s, e) for s in days for e in days if s <= e]


# For any range: section totals equal their lines, subtotals follow their
# formulas, and net income matches the raw ledger computed independently.
def test_totals_and_subtotals_are_consistent():
    ranges = _ranges_to_check()
    assert len(ranges) > 1000
    for start, end in ranges:
        _check_consistency(start, end)


def _check_consistency(start, end):
    statement = build(start, end)
    for i in statement["items"]:
        if i["kind"] == "section":
            assert i["total"] == sum((l["amount"] for l in i["lines"]), Decimal("0")), (start, end)

    revenue = item(statement, "Revenue")["total"]
    cogs = item(statement, "Cost of goods sold")["total"]
    opex = item(statement, "Operating expenses")["total"]
    other = item(statement, "Other income")["total"]
    gross = item(statement, "Gross profit")["amount"]
    operating = item(statement, "Operating income")["amount"]
    net_income = item(statement, "Net income")["amount"]

    assert gross == revenue - cogs, (start, end)
    assert operating == gross - opex, (start, end)
    assert net_income == operating + other, (start, end)

    # Independent check: net income is credits minus debits over every
    # non-balance-sheet account, without going through the layout.
    net = net_by_account(lines_in_range(LEDGER, start, end))
    pnl = [n for n, a in LEDGER.accounts.items() if a.subtype != "balance_sheet"]
    assert net_income == -sum((net.get(n, Decimal("0")) for n in pnl), Decimal("0")), (start, end)


# Golden test: Q1 2026 totals match the hand-computed statement.
def test_q1_2026_golden_values():
    statement = build(*Q1)
    assert item(statement, "Revenue")["total"] == Decimal("37850.50")
    assert item(statement, "Cost of goods sold")["total"] == Decimal("14272.75")
    assert item(statement, "Gross profit")["amount"] == Decimal("23577.75")
    assert item(statement, "Operating expenses")["total"] == Decimal("68100.07")
    assert item(statement, "Operating income")["amount"] == Decimal("-44522.32")
    assert item(statement, "Other income")["total"] == Decimal("42.18")
    assert item(statement, "Net income")["amount"] == Decimal("-44480.14")
