# Release Process

This document describes the steps to produce a new TrustLint release. These are manual steps intended for maintainers.

## Prerequisites

- Push access to the repository
- PyPI account with trusted publisher configured (or API token)
- Python build tools installed (`pip install build twine`)

---

## 1. Version Bump

Update the version string in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (X): Breaking changes to CLI interface, exit codes, or output format.
- **MINOR** (Y): New features, new policy rules, new output fields (backward-compatible).
- **PATCH** (Z): Bug fixes, documentation corrections, dependency updates.

## 2. Update CHANGELOG.md

Add a new section under `[Unreleased]` with the version number and date:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...
```

Move items from `[Unreleased]` into the new version section. Update the comparison links at the bottom of the file.

## 3. Generate SBOM (Software Bill of Materials)

The SBOM (`sbom.json`) is a CycloneDX-format bill of materials. It MUST be
regenerated for every release to reflect the actual dependency set.

```bash
# Install cyclonedx-bom if not present
pip install cyclonedx-bom

# Generate SBOM from the current environment
cyclonedx-py environment --force --output-file sbom.json --output-format json
```

**Provenance requirements:**
- The SBOM must include a `metadata` section with the generation command,
  tool version, and timestamp.
- The committed `sbom.json` is a reference copy; the release artifact SBOM
  should be generated from the exact build environment used for the wheel.
- Attach the release-specific SBOM to the GitHub Release as an artifact.

Store the SBOM artifact alongside the release or attach it to the GitHub Release.

## 4. Build and Verify

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# Verify the build
pip install dist/trustlint-X.Y.Z-py3-none-any.whl --force-reinstall
trustlint --version
```

Confirm the version output matches the intended release version.

## 5. Run Full Test Suite

```bash
# Run all tests including network tests
pytest -m "" --tb=short
```

Ensure all tests pass before proceeding.

## 6. Git Tag (Manual Only)

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare v$X.Y.Z"
git tag -a v$X.Y.Z -m "Release v$X.Y.Z"
git push origin main --tags
```

**Do not use automated release tools or CI-driven tagging.** Tags are created manually by a maintainer.

## 7. Publish to PyPI

```bash
# Upload to Test PyPI first (recommended)
twine upload --repository testpypi dist/*

# Verify on Test PyPI
pip install --index-url https://test.pypi.org/simple/ trustlint

# Upload to production PyPI
twine upload dist/*
```

Alternatively, if trusted publishers are configured on PyPI, push the tag and trigger the publish workflow manually from the GitHub Actions UI.

## 8. Create GitHub Release

1. Go to the repository's **Releases** page on GitHub.
2. Click **Draft a new release**.
3. Select the tag you just pushed (`vX.Y.Z`).
4. Set the title to `vX.Y.Z`.
5. Paste the changelog entry for this version into the description.
6. Attach any artifacts (SBOM, checksums) if applicable.
7. Click **Publish release**.

## 9. Post-Release

- Verify the package appears on [PyPI](https://pypi.org/project/trustlint/).
- Verify `pip install trustlint` installs the correct version.
- Announce the release if applicable (README badge update, social media, etc.).

---

## Hotfix Releases

For critical bug fixes on a released version:

1. Create a branch from the release tag: `git checkout -b hotfix/X.Y.Z v$X.Y.Z`
2. Apply the fix, bump the patch version, update `CHANGELOG.md`.
3. Follow steps 5-9 above.

---

## Rollback

If a broken release is published to PyPI:

1. Yank the release on PyPI (via the web UI or `twine`).
2. Publish a corrected version with a patch bump.
3. Do not delete the tag. Create a new tag for the corrected version.
