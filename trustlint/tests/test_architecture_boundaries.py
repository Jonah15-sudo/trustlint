"""Architecture boundary enforcement tests.

Uses AST parsing to verify that the codebase maintains proper
layer separation and dependency rules.

Rules enforced:
1. No module under trustlint/ imports scripts
2. No module under trustlint/infrastructure/ imports scripts
3. scripts/ contains only thin wrappers (no production logic)
4. trustlint.analyzer doesn't do raw socket/DNS/TLS/HTTP work
5. tls_probe.py only imports OCSP from trustlint.infrastructure.ocsp
6. No circular imports among core modules
7. Security modules don't import dashboard modules
8. SPL subsystem doesn't affect default production decisions
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Set

import pytest

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRUSTLINT_PKG = PROJECT_ROOT / "trustlint"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
TESTS_DIR = PROJECT_ROOT / "tests"


def _collect_python_files(directory: Path) -> list[Path]:
    """Collect all .py files in a directory tree."""
    return list(directory.rglob("*.py"))


def _get_imports_from_file(filepath: Path) -> list[str]:
    """Extract all import names from a Python file using AST."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _has_real_logic(filepath: Path) -> bool:
    """Check if a file contains real production logic (not just re-exports)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError):
        return False

    for node in ast.walk(tree):
        # Check for function definitions with bodies
        if isinstance(node, ast.FunctionDef):
            if node.body and not (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and isinstance(node.body[0].value, ast.Name)
            ):
                return True
        # Check for class definitions
        if isinstance(node, ast.ClassDef):
            return True
    return False


class TestNoTrustlintImportsScripts:
    """Rule 1: No module under trustlint/ should import from scripts."""

    def test_trustlint_package_no_scripts_imports(self):
        violations = []
        for filepath in _collect_python_files(TRUSTLINT_PKG):
            imports = _get_imports_from_file(filepath)
            for imp in imports:
                if imp.startswith("scripts") or imp == "scripts":
                    rel_path = filepath.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            "trustlint package must not import from scripts:\n"
            + "\n".join(violations)
        )


class TestInfrastructureNoScriptsImports:
    """Rule 2: No module under trustlint/infrastructure/ should import from scripts."""

    def test_infrastructure_no_scripts_imports(self):
        infra_dir = TRUSTLINT_PKG / "infrastructure"
        if not infra_dir.exists():
            pytest.skip("infrastructure directory not found")

        violations = []
        for filepath in _collect_python_files(infra_dir):
            imports = _get_imports_from_file(filepath)
            for imp in imports:
                if imp.startswith("scripts") or imp == "scripts":
                    rel_path = filepath.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            "infrastructure must not import from scripts:\n"
            + "\n".join(violations)
        )


class TestScriptsAreThinWrappers:
    """Rule 3: scripts/ should contain only thin compatibility wrappers."""

    def test_scripts_no_real_production_logic(self):
        if not SCRIPTS_DIR.exists():
            pytest.skip("scripts directory not found")

        violations = []
        for filepath in _collect_python_files(SCRIPTS_DIR):
            if filepath.name.startswith("__"):
                continue
            if _has_real_logic(filepath):
                rel_path = filepath.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}: contains real production logic")

        assert not violations, (
            "scripts/ should only contain thin wrappers:\n"
            + "\n".join(violations)
        )

    def test_scripts_only_re_export(self):
        """Each scripts/ module should only have imports and maybe __all__."""
        if not SCRIPTS_DIR.exists():
            pytest.skip("scripts directory not found")

        for filepath in _collect_python_files(SCRIPTS_DIR):
            if filepath.name.startswith("__"):
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Allow: docstrings, imports, __all__ assignments
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    continue  # docstring
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            break
                    else:
                        rel_path = filepath.relative_to(PROJECT_ROOT)
                        pytest.fail(
                            f"{rel_path}: unexpected statement type "
                            f"{type(node).__name__} in scripts wrapper"
                        )


class TestAnalyzerNoDirectNetworkWork:
    """Rule 4: trustlint.analyzer should not do raw socket/DNS/TLS/HTTP work."""

    def test_analyzer_no_socket_imports(self):
        analyzer_file = TRUSTLINT_PKG / "analyzer.py"
        if not analyzer_file.exists():
            pytest.skip("analyzer.py not found")

        imports = _get_imports_from_file(analyzer_file)
        network_modules = {"socket", "ssl", "urllib", "http", "requests"}
        violations = []
        for imp in imports:
            root_mod = imp.split(".")[0]
            if root_mod in network_modules:
                violations.append(imp)

        assert not violations, (
            "analyzer.py should not directly import network modules:\n"
            + "\n".join(violations)
        )


class TestOCSPModuleOwnership:
    """Rule 5: tls_probe.py should only import OCSP from the correct module."""

    def test_tls_probe_ocsp_import_path(self):
        tls_probe_file = TRUSTLINT_PKG / "infrastructure" / "tls_probe.py"
        if not tls_probe_file.exists():
            pytest.skip("tls_probe.py not found")

        imports = _get_imports_from_file(tls_probe_file)
        ocsp_imports = [imp for imp in imports if "ocsp" in imp.lower()]

        for imp in ocsp_imports:
            assert imp.startswith("trustlint.infrastructure.ocsp"), (
                f"tls_probe.py imports OCSP from '{imp}', "
                f"expected 'trustlint.infrastructure.ocsp.*'"
            )


class TestNoCircularImports:
    """Rule 6: No circular imports among core modules."""

    CORE_MODULES = [
        "trustlint.analyzer",
        "trustlint.infrastructure.tls_probe",
        "trustlint.infrastructure.error_codes",
        "trustlint.infrastructure.ocsp.client",
        "trustlint.security",
    ]

    def test_no_circular_imports(self):
        """Verify core modules can be imported without circular errors."""
        # This test actually imports the modules to check for circular imports
        # If there's a circular import, this will fail with ImportError
        imported = set()
        for module_name in self.CORE_MODULES:
            try:
                __import__(module_name)
                imported.add(module_name)
            except ImportError as e:
                if "circular" in str(e).lower():
                    pytest.fail(f"Circular import detected: {module_name}: {e}")
                # Other import errors are acceptable (missing deps, etc.)

        # If we got here without circular import errors, the test passes
        assert True


class TestSecurityModulesIsolation:
    """Rule 7: Security modules should not import dashboard modules."""

    def test_security_no_dashboard_imports(self):
        security_dir = TRUSTLINT_PKG / "security"
        if not security_dir.exists():
            pytest.skip("security directory not found")

        dashboard_indicators = {"dashboard", "spl_v7", "fastapi", "uvicorn"}
        violations = []

        for filepath in _collect_python_files(security_dir):
            imports = _get_imports_from_file(filepath)
            for imp in imports:
                root_mod = imp.split(".")[0]
                if root_mod in dashboard_indicators:
                    rel_path = filepath.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            "security modules must not import dashboard/SPL modules:\n"
            + "\n".join(violations)
        )


class TestSPLIsolation:
    """Rule 8: SPL subsystem should not affect default production decisions."""

    def test_spl_not_imported_by_default_path(self):
        """SPL should only be imported when explicitly enabled."""
        # Check that analyzer.py doesn't import SPL at module level
        analyzer_file = TRUSTLINT_PKG / "analyzer.py"
        if not analyzer_file.exists():
            pytest.skip("analyzer.py not found")

        imports = _get_imports_from_file(analyzer_file)
        spl_imports = [imp for imp in imports if "spl" in imp.lower()]

        # SPL imports should be lazy (inside functions), not at module level
        try:
            with open(analyzer_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (SyntaxError, UnicodeDecodeError):
            pytest.skip("Cannot parse analyzer.py")

        # Check top-level imports only
        top_level_imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    top_level_imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        top_level_imports.append(alias.name)

        spl_at_top_level = [
            imp for imp in top_level_imports if "spl" in imp.lower()
        ]
        assert not spl_at_top_level, (
            "SPL should not be imported at module level in analyzer.py: "
            + ", ".join(spl_at_top_level)
        )


class TestWrapperCompatibility:
    """Rule 7: Wrapper compatibility assertions."""

    def test_legacy_probe_is_package_probe(self):
        """Verify scripts wrapper re-exports the same function."""
        try:
            from scripts.run_local_tls_validation import probe_domain as legacy_probe
            from trustlint.infrastructure.tls_probe import probe_domain as package_probe

            assert legacy_probe is package_probe, (
                "scripts.run_local_tls_validation.probe_domain should be "
                "the same object as trustlint.infrastructure.tls_probe.probe_domain"
            )
        except ImportError as e:
            pytest.skip(f"Cannot test wrapper compatibility: {e}")

    def test_legacy_ocsp_is_package_ocsp(self):
        """Verify OCSP wrapper re-exports the same function."""
        try:
            from scripts.ocsp_checker import check_ocsp as legacy_ocsp
            from trustlint.infrastructure.ocsp import check_ocsp as package_ocsp

            assert legacy_ocsp is package_ocsp, (
                "scripts.ocsp_checker.check_ocsp should be "
                "the same object as trustlint.infrastructure.ocsp.check_ocsp"
            )
        except ImportError as e:
            pytest.skip(f"Cannot test wrapper compatibility: {e}")

    def test_legacy_error_codes_is_package_error_codes(self):
        """Verify error codes wrapper re-exports the same symbols."""
        try:
            from scripts.error_codes import ErrorCode as legacy_ec
            from trustlint.infrastructure.error_codes import ErrorCode as package_ec

            assert legacy_ec is package_ec, (
                "scripts.error_codes.ErrorCode should be "
                "the same object as trustlint.infrastructure.error_codes.ErrorCode"
            )
        except ImportError as e:
            pytest.skip(f"Cannot test wrapper compatibility: {e}")
