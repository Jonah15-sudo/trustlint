# Contributing to TrustLint

Thank you for considering contributing to TrustLint. This guide covers the workflow and standards expected for contributions.

## Development Environment Setup

**Prerequisites:**
- Python 3.10 or later
- `pip` (or a compatible package manager)
- Git

**Steps:**

```bash
# Clone the repository
git clone https://github.com/<owner>/trustlint.git
cd trustlint

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Code Quality

### Linting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint issues
ruff check .

# Auto-fix safe issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking

```bash
# Run type checking (if mypy is configured)
mypy src/trustlint
```

### Testing

```bash
# Run tests (excluding network-dependent and slow tests by default)
pytest -m "not network and not slow"

# Run the full test suite (requires network access)
pytest

# Run with coverage
pytest --cov=trustlint --cov-report=term-missing
```

**Important:** Do not commit tests that hit live TLS endpoints unless they are explicitly marked with `@pytest.mark.network`.

## Branch Naming

Use the following prefixes:

| Prefix | Purpose |
|--------|---------|
| `feat/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation changes |
| `refactor/*` | Code refactoring (no feature or fix) |
| `test/*` | Adding or updating tests |
| `chore/*` | Maintenance, CI, tooling |
| `perf/*` | Performance improvements |

Example: `feat/add-certificate-chain-validation`

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>

<optional footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`

**Examples:**

```
feat(parser): add support for PEM certificate chain parsing

fix(scanner): handle expired certificates without crashing

docs(readme): update installation instructions
```

**Rules:**
- Summary line: 72 characters max, imperative mood, no period
- Reference issue numbers in the footer: `Closes #42`
- Breaking changes must include `BREAKING CHANGE:` in the footer

## Pull Request Expectations

1. **Branch from `main`** (or the current development branch).
2. **Keep PRs focused.** One logical change per PR.
3. **Include tests** for new functionality or bug fixes.
4. **All CI checks must pass** before merge.
5. **Require at least one review** from a maintainer.
6. **Do not force-push** over reviewed commits. Add new commits instead.

### PR Description Template

```markdown
## What does this PR do?
<!-- Brief description -->

## How to test
<!-- Steps to verify -->

## Checklist
- [ ] Tests pass locally
- [ ] Linting passes (`ruff check . && ruff format --check .`)
- [ ] Documentation updated (if applicable)
- [ ] Changelog entry added (if user-facing change)
```

## Security-Sensitive Changes

TrustLint analyzes TLS/SSL configurations. Changes to parsing logic, cipher suite handling, or vulnerability detection are security-sensitive.

**Process:**
1. Open an issue first describing the change and its security implications.
2. Reference the issue in your PR.
3. Security-sensitive PRs require **two maintainer approvals** before merge.
4. Do not disclose vulnerability details publicly until a fix is released.

**Do not** introduce code that:
- Executes arbitrary shell commands
- Writes to locations outside the project directory without user consent
- Transmits data over the network without explicit opt-in
- Logs or exposes secrets, private keys, or credential material

## Reproducing Bugs Safely

When reporting or reproducing TLS-related bugs:

1. **Use a local certificate, not a production endpoint.** Generate a self-signed cert for testing:

   ```bash
   openssl req -x509 -newkey rsa:2048 -keyout test-key.pem -out test-cert.pem -days 30 -nodes -subj "/CN=localhost"
   ```

2. **Do not paste real private keys** in issues or PRs.
3. **Use test endpoints** like `expired.badssl.com` or `self-signed.badssl.com` for validation scenarios.
4. **Mark network tests** with `@pytest.mark.network` so they are excluded from default CI runs.

## Reporting Issues

Open an issue on GitHub with:
- TrustLint version (`trustlint --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs. actual behavior
- Full error output (if applicable)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see `LICENSE`).
