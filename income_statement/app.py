"""Start the server: load the ledger once, then serve the API and frontend.

Run with: python -m income_statement.app [--port=8888]
"""

import asyncio
from pathlib import Path

import tornado.web
from tornado.options import define, options, parse_command_line

from income_statement.api import IncomeStatementHandler
from income_statement.ledger import Ledger, load_ledger

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "ledger.json"
STATIC_DIR = ROOT / "static"

define("port", default=8888, help="port to listen on", type=int)


def make_app(ledger: Ledger) -> tornado.web.Application:
    """Wire the API route and the static frontend to an already-loaded ledger."""
    return tornado.web.Application(
        [
            (r"/income-statement", IncomeStatementHandler, {"ledger": ledger}),
            (r"/()", tornado.web.StaticFileHandler,
             {"path": STATIC_DIR, "default_filename": "index.html"}),
        ],
        static_path=STATIC_DIR,
    )


async def main():
    """Entry point: read --port, load ledger.json once, and serve forever."""
    parse_command_line()
    ledger = load_ledger(LEDGER_PATH)
    make_app(ledger).listen(options.port)
    print(f"Serving on http://localhost:{options.port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
