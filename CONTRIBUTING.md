# Contributing

1. Create a virtual environment and install `.[dev]`.
2. Keep all UN Comtrade network access inside `src/easy_trade_report/comtrade.py` and use the official `comtradeapicall` package.
3. Never commit subscription keys or raw files containing credentials.
4. Add an offline fixture or unit test for analytical changes.
5. Run `python -m pytest` and `python -m ruff check .` before opening a pull request.

