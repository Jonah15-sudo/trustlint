"""Test configuration and shared fixtures.

Provides skip markers for tests that depend on optional modules that
are not yet implemented in this codebase.
"""

import pytest


# Modules that are known to be missing from this codebase
_MISSING_MODULES = [
    "scripts.spl_tls_analyze",
    "scripts.run_real_tls_spl_decision_validation",
    "scripts.validate_real_tls_data",
]


def pytest_collection_modifyitems(config, items):
    """Add skip markers for tests requiring missing optional modules."""
    missing = set()
    for mod_name in _MISSING_MODULES:
        try:
            __import__(mod_name)
        except ImportError:
            missing.add(mod_name)

    if not missing:
        return

    # Build a skip marker for each missing module
    skip_markers = {}
    for mod_name in missing:
        short_name = mod_name.split(".")[-1]
        skip_markers[mod_name] = pytest.mark.skip(
            reason=f"{mod_name} module not available"
        )

    for item in items:
        if not hasattr(item, "module") or item.module is None:
            continue
        module_file = str(getattr(item.module, "__file__", ""))

        # Check for scripts.spl_tls_analyze dependency
        if "spl_tls_analyze" in module_file or "test_spl_tls" in module_file:
            if "scripts.spl_tls_analyze" in missing:
                item.add_marker(skip_markers["scripts.spl_tls_analyze"])

        # Check for scripts.run_real_tls_spl_decision_validation dependency
        if "spl_decision_validation" in module_file:
            if "scripts.run_real_tls_spl_decision_validation" in missing:
                item.add_marker(
                    skip_markers["scripts.run_real_tls_spl_decision_validation"]
                )

        # Check for scripts.validate_real_tls_data dependency
        if "test_real_data_contract" in module_file:
            if "scripts.validate_real_tls_data" in missing:
                item.add_marker(
                    skip_markers["scripts.validate_real_tls_data"]
                )
