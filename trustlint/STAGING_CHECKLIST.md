# Pre-Production Staging Checklist

Use this checklist before publishing a new TrustLint release to ensure quality and correctness.

---

## Code Quality

- [ ] All tests pass: `pytest -m "not network and not slow"`
- [ ] Full test suite passes (including network tests): `pytest -m ""`
- [ ] Linting passes: `ruff check .`
- [ ] Formatting is correct: `ruff format --check .`
- [ ] No type errors (if mypy is configured): `mypy src/trustlint`
- [ ] No new `# type: ignore` or `# noqa` comments added without justification

## Version and Metadata

- [ ] Version bumped in `pyproject.toml`
- [ ] Version matches Git tag (if tagging)
- [ ] `trustlint --version` outputs the correct version after install
- [ ] Project metadata in `pyproject.toml` is accurate (description, URLs, classifiers)

## Changelog

- [ ] `CHANGELOG.md` updated with new version section
- [ ] All user-facing changes documented
- [ ] Links at bottom of `CHANGELOG.md` are updated
- [ ] No placeholder text or TODO items left in changelog

## Build

- [ ] Clean build produces no warnings: `rm -rf dist/ build/ *.egg-info && python -m build`
- [ ] Source distribution (`sdist`) builds successfully
- [ ] Wheel (`bdist_wheel`) builds successfully
- [ ] Built wheel installs cleanly in a fresh virtual environment
- [ ] `trustlint --help` works after clean install
- [ ] No unexpected files included in the distribution (check with `twine check dist/*`)

## Functionality

- [ ] `trustlint --url <test-endpoint>` produces expected output
- [ ] `trustlint --file <local-cert>` produces expected output
- [ ] `--output json` produces valid JSON
- [ ] `--output human` produces readable table output
- [ ] Exit codes are correct for each scenario (0, 1, 2, 3)
- [ ] Error messages are clear and include error codes
- [ ] `--help` text is accurate and complete

## Security

- [ ] No secrets, private keys, or credentials committed
- [ ] No files written outside the current directory without user consent
- [ ] No arbitrary shell execution introduced
- [ ] Sensitive changes reviewed by a second maintainer (if applicable)
- [ ] SBOM generated and attached (if required)

## Documentation

- [ ] README.md is up to date
- [ ] Installation instructions work for a fresh user
- [ ] Usage examples are accurate
- [ ] API/documentation links are not broken

## Release

- [ ] Git tag created (manual only)
- [ ] Tag pushed to remote: `git push origin main --tags`
- [ ] PyPI upload successful: `twine upload dist/*`
- [ ] Package visible on PyPI: `pip install trustlint==<version>`
- [ ] GitHub Release created with changelog entry
- [ ] SBOM attached to GitHub Release (if applicable)

## Post-Release Verification

- [ ] `pip install trustlint` installs correct version
- [ ] `trustlint --version` works from a clean install
- [ ] No regression reports within 24 hours
