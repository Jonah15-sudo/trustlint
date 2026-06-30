# GitHub Settings Checklist

This document lists manual GitHub repository settings that the repository owner should configure. These cannot be automated via code and must be set through the GitHub web UI.

---

## Branch Protection

Navigate to **Settings > Branches > Add branch protection rule**.

### `main` branch:

- [ ] **Require a pull request before merging**
  - [ ] Require approvals: 1 (minimum)
  - [ ] Dismiss stale pull request approvals when new commits are pushed
  - [ ] Require review from Code Owners (if `CODEOWNERS` file exists)
- [ ] **Require status checks to pass before merging**
  - [ ] Add required checks: `tests`, `lint`, `build` (match your CI workflow job names)
- [ ] **Require branches to be up to date before merging**
- [ ] **Require conversation resolution before merging**
- [ ] **Require linear history** (optional — enforces squash or rebase merges)
- [ ] **Do not allow bypassing the above settings** (recommended)
- [ ] **Restrict who can push to matching branches** (optional — limit to maintainers)

---

## Dependabot

Navigate to **Settings > Code security and analysis > Dependabot**.

- [ ] **Dependency graph**: Enabled
- [ ] **Dependabot alerts**: Enabled
- [ ] **Dependabot security updates**: Enabled

### Dependabot Configuration File

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Secret Scanning

Navigate to **Settings > Code security and analysis > Secret scanning**.

- [ ] **Secret scanning**: Enabled
- [ ] **Push protection**: Enabled (blocks commits containing detected secrets)

---

## Code Scanning (CodeQL)

Navigate to **Settings > Code security and analysis > Code scanning**.

- [ ] **Code scanning**: Enabled
- [ ] Set up CodeQL analysis for Python (via GitHub Actions workflow)

### Suggested Workflow

Create `.github/workflows/codeql.yml`:

```yaml
name: CodeQL Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Weekly on Monday at 06:00 UTC

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    strategy:
      matrix:
        language: [python]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
```

---

## Dependency Review

Navigate to **Settings > Code security and analysis > Dependency review**.

- [ ] **Dependency review**: Enabled
- [ ] **Block merges on vulnerabilities**: Enabled (blocks PRs that introduce known vulnerabilities)

---

## Repository Settings

- [ ] **Default branch**: `main`
- [ ] **Auto-delete head branches**: Enabled (deletes PR branches after merge)
- [ ] **Allow squash merging**: Enabled (default merge method)
- [ ] **Allow merge commits**: Optional (enable if preferred)
- [ ] **Allow rebase merging**: Optional
- [ ] **Automatically delete head branches**: Enabled

---

## Actions Permissions

Navigate to **Settings > Actions > General**.

- [ ] **Actions permissions**: Allow reusable workflows and specific actions (or allow all, per your policy)
- [ ] **Workflow permissions**: Read and write permissions (required for CodeQL, release workflows)
- [ ] **Allow Forked workflows**: Disabled (unless needed)

---

## Security Advisories

Navigate to **Settings > Code security and analysis > Security advisories**.

- [ ] **Private vulnerability reporting**: Enabled (allows private issue reporting)

---

## Access Controls

- [ ] **Branch protection rules** enforced for `main`
- [ ] **CODEOWNERS** file created (if applicable)
- [ ] **Issue templates** configured (optional but recommended)
- [ ] **PR templates** configured (optional but recommended)

---

## Badges

Update README.md with status badges:

```markdown
[![Tests](https://github.com/<owner>/trustlint/actions/workflows/tests.yml/badge.svg)](https://github.com/<owner>/trustlint/actions)
[![PyPI](https://img.shields.io/pypi/v/trustlint)](https://pypi.org/project/trustlint/)
[![Python](https://img.shields.io/pypi/pyversions/trustlint)](https://pypi.org/project/trustlint/)
```

---

## Notes

- These settings require repository admin or owner permissions.
- Some settings (e.g., CodeQL, secret scanning) are available on public repositories for free.
- Review these settings periodically as GitHub may update its interface.
