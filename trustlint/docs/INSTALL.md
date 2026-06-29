# Installation — spl-tls-analyze

## Prerequisites

- Python 3.10 or later
- `pip` (included with Python 3.10+)

## Quick Install (Local Editable)

```bash
# Clone or cd into the project root (use the **complete** variant)
cd spl_v7_project_with_frontier/spl_v7_project

# (Optional) Create and activate a virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Install in editable mode with extras needed for tests and dashboard
pip install -e ".[spl-core,dev]"

# Verify the installation
spl-tls-analyze --help
```

> **Note:** The CLI alone requires zero third-party packages, so `pip install -e .`
> works for basic usage. The `[spl-core,dev]` extras are only needed to run the
> test suite and import the `spl_v7` package (see Dependencies below).

## Run the CLI

```bash
# Analyze a single domain
spl-tls-analyze example.com

# With explicit profile and JSON output
spl-tls-analyze example.com --profile strict --json-out report.json

# Batch analysis from a file
spl-tls-analyze domains.txt --profile conservative --markdown-out report.md

# Quiet mode — batch summary only
spl-tls-analyze domains.txt --quiet
```

## Run Tests

```bash
# All tests
python -m unittest discover -s tests -v

# Golden acceptance tests
python -m pytest tests/test_cli_golden_acceptance.py -v

# Package entry point tests
python -m pytest tests/test_package_entry.py -v

# Full release verification
python scripts/verify_release.py
```

Tests require the `dev` extra: `pip install ".[dev]"`.

## Uninstall

```bash
pip uninstall spl-tls-analyze -y
```

## Dependencies

The CLI has **zero external dependencies** — it uses only Python standard
library modules. The `spl-tls-analyze` entry point requires no pip packages
beyond the project itself.

Optional extras are available for additional functionality:

| Extra | Packages | Needed For |
|-------|----------|------------|
| `spl-core` | numpy, networkx, plotly, fastapi, uvicorn | Importing `spl_v7` (dashboard, visualization) |
| `kafka` | confluent-kafka | Kafka pipeline (optional; memory backend is default) |
| `dev` | pytest | Running tests and `scripts/verify_release.py` |

Install with `pip install ".[spl-core,dev]"` to get everything.

## Windows Notes

- Use `python -m venv .venv` to create a virtual environment.
- Activate with `.venv\Scripts\activate`.
- The `spl-tls-analyze` command is installed as a `.exe` wrapper in the
  virtual environment's `Scripts\` directory.
- If you see encoding errors with non-ASCII output, set `PYTHONUTF8=1`:
  ```powershell
  $env:PYTHONUTF8=1
  spl-tls-analyze example.com
  ```

## macOS / Linux Notes

- On some systems you may need `python3` instead of `python`.
- The `spl-tls-analyze` command is installed in the virtual environment's
  `bin/` directory.
- If you installed system-wide, you may need `pip3 install -e .`.

## No PyPI Publishing

This package is **not published on PyPI**. It is intended for local
development and evaluation only. Install from source as shown above.
