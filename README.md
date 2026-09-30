# income-statement

A small full-stack app that shows an income statement (profit and loss) for
Northwind Coffee Roasters for any date range, built from the journal entries
in `ledger.json`.

- Backend: Python + Tornado. `GET /income-statement?start=YYYY-MM-DD&end=YYYY-MM-DD`
  returns the statement as JSON, with amounts as exact two-decimal strings.
- Frontend: one plain HTML page (`static/index.html`) with start and end dates.
- Tests: pytest.

## Versions

- Python 3.12 (tested with 3.12.13)
- tornado 6.5.10, pytest 9.1.1 (pinned in `requirements.txt`)
- Tested on macOS 26.6 (Apple silicon) with uv 0.11.9

## Setup

Clone the repo and enter it:

```bash
git clone https://github.com/carwithk/income-statement.git
cd income-statement
```

Create a virtual environment and install dependencies. With
[uv](https://docs.astral.sh/uv/) (it downloads Python 3.12 if needed):

```bash
uv python install 3.12
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or without uv, using Homebrew's Python 3.12:

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

With the virtual environment active:

```bash
python -m income_statement.app               # serves on port 8888
python -m income_statement.app --port=9000   # or pick a port
```

Then open http://localhost:8888/ in a browser. It loads Q1 2026
(2026-01-01 to 2026-03-31) by default. Stop the server with `Ctrl+C`.

The API can also be called directly:

```bash
curl "http://localhost:8888/income-statement?start=2026-01-01&end=2026-03-31"
```

## Run the tests

With the virtual environment active:

```bash
pytest            # all tests
pytest -v         # list each test
pytest tests/test_statements.py -v   # one file
```

## Layout

| Path | What it does |
| --- | --- |
| `ledger.json` | Source data: chart of accounts and journal entries |
| `income_statement/ledger.py` | Load and validate `ledger.json` into models |
| `income_statement/queries.py` | Filter lines by status and date, net by account |
| `income_statement/statements.py` | Statement layout as data, and the builder |
| `income_statement/api.py` | `GET /income-statement` handler and JSON formatting |
| `income_statement/app.py` | Startup: load the ledger once, routes, static files |
| `static/index.html` | Frontend |
| `tests/` | Tests for each module above |
