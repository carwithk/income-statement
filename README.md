# income-statement
A full stack app for generating income statement

## Versions

- Python 3.12
- tornado 6.5.10, pytest 9.1.1 (pinned in `requirements.txt`)
- Tested on macOS with uv 0.11.9

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
