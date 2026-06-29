"""Phase 11 — Tests for package entry point and console script.

Verifies the CLI works through the installed package, not just as a script.
All tests use mocks — no live network calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.spl_tls_analyze import (
    parse_args,
    analyze_domain,
    format_structured_text,
    format_json_output,
    format_markdown_output,
    compute_exit_code,
    main,
    __version__,
    TOOL_NAME,
)


def _make_mock_probe(
    domain: str = "example.com",
    classification: str = "VALID_TLS",
    tls_version: str = "TLSv1.3",
    expiry_days: int = 89,
    resolved_ip: str = "1.2.3.4",
    cert_is_expired: bool = False,
    chain_complete: bool = True,
    dns_error: str | None = None,
) -> dict:
    tls = {
        "tls_version": tls_version,
        "cert_expiry_days": expiry_days,
        "cert_is_expired": cert_is_expired,
        "cert_chain_complete": chain_complete,
        "handshake_time_ms": 45.2,
    }
    if classification == "DNS_FAILURE":
        tls = None
    return {
        "domain": domain,
        "probe_timestamp": "2026-06-01T12:00:00Z",
        "resolved_ip": resolved_ip if classification != "DNS_FAILURE" else None,
        "dns_error": dns_error,
        "tls": tls,
        "overall_status": classification.lower(),
        "classification": classification,
    }


class TestConsoleScriptExists(unittest.TestCase):
    """Verify the console script entry point is installed."""

    def test_entry_point_accessible(self) -> None:
        import importlib.metadata
        dist = importlib.metadata.distribution("trustlint")
        entry_points = dist.entry_points
        cli_eps = [ep for ep in entry_points if ep.name == "trustlint"]
        self.assertEqual(len(cli_eps), 1,
                         "Expected one 'trustlint' entry point")
        self.assertEqual(cli_eps[0].value, "scripts.spl_tls_analyze:main")

    def test_trustlint_alias_entry_point_accessible(self) -> None:
        import importlib.metadata
        dist = importlib.metadata.distribution("trustlint")
        entry_points = dist.entry_points
        trustlint_eps = [ep for ep in entry_points if ep.name == "trustlint"]
        self.assertEqual(len(trustlint_eps), 1,
                         "Expected one 'trustlint' entry point")
        self.assertEqual(trustlint_eps[0].value, "scripts.spl_tls_analyze:main")


class TestMainThroughEntryPoint(unittest.TestCase):
    """Verify main() can be called through the module directly."""

    @patch("trustlint.analyzer.probe_domain")
    def test_main_valid_tls_fallback_allow(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("test.example.com", "VALID_TLS")
        exit_code = main(["test.example.com", "--quiet"])
        self.assertEqual(exit_code, 0, "VALID_TLS without SPL exits 0 (ALLOW via fallback)")

    @patch("trustlint.analyzer.probe_domain")
    def test_main_expired_cert(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "expired.example.com", "EXPIRED_CERT",
            tls_version="TLSv1.2", expiry_days=-1, cert_is_expired=True,
        )
        exit_code = main(["expired.example.com", "--quiet"])
        self.assertEqual(exit_code, 1, "EXPIRED_CERT should exit 1 (REVIEW)")

    @patch("trustlint.analyzer.probe_domain")
    def test_main_wrong_host_deny(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "wrong.example.com", "WRONG_HOST_CERT",
            tls_version="TLSv1.2", expiry_days=200,
        )
        exit_code = main(["wrong.example.com", "--quiet"])
        self.assertEqual(exit_code, 2, "WRONG_HOST_CERT should exit 2 (DENY)")

    def test_main_invalid_profile_exits_4(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["example.com", "--profile", "invalid"])

    @patch("trustlint.analyzer.probe_domain")
    def test_main_json_output_still_works(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("json-test.example.com", "VALID_TLS")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            tmp = f.name
        try:
            exit_code = main(["json-test.example.com", "--json-out", tmp, "--quiet"])
            self.assertEqual(exit_code, 0)
            with open(tmp, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            self.assertEqual(parsed["metadata"]["tool"], "trustlint")
            self.assertEqual(parsed["metadata"]["production_ready"], False)
            self.assertEqual(len(parsed["results"]), 1)
        finally:
            os.unlink(tmp)

    @patch("trustlint.analyzer.probe_domain")
    def test_main_markdown_output_still_works(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("md-test.example.com", "VALID_TLS")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            tmp = f.name
        try:
            exit_code = main(["md-test.example.com", "--markdown-out", tmp, "--quiet"])
            self.assertEqual(exit_code, 0)
            with open(tmp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Executive Summary", content)
            self.assertIn("Not production ready", content)
        finally:
            os.unlink(tmp)

    @patch("trustlint.analyzer.probe_domain")
    def test_main_batch_summary_multi_domain(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("batch.example.com", "VALID_TLS")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("domain-a.example.com\n")
            f.write("domain-b.example.com\n")
            tmp = f.name
        try:
            exit_code = main([tmp, "--quiet"])
            self.assertEqual(exit_code, 0, "Batch of VALID_TLS now exits 0 (ALLOW via fallback)")
        finally:
            os.unlink(tmp)


class TestImportPaths(unittest.TestCase):
    """Verify all modules import cleanly through the installed package."""

    def test_import_spl_v7(self) -> None:
        import spl_v7  # noqa: F811

    def test_import_tls_policy_adapter(self) -> None:
        import tls_policy_adapter  # noqa: F811
        from tls_policy_adapter import classify_risk  # noqa: F811

    def test_import_decision_orchestrator(self) -> None:
        import decision_orchestrator  # noqa: F811
        from decision_orchestrator import decide  # noqa: F811


class TestVersionFlag(unittest.TestCase):
    """Verify the --version flag prints the tool version and exits cleanly."""

    def test_version_constant_defined(self) -> None:
        self.assertIsInstance(__version__, str)
        self.assertTrue(len(__version__) > 0)

    def test_tool_name_constant(self) -> None:
        self.assertEqual(TOOL_NAME, "trustlint")

    def test_version_flag_parsed(self) -> None:
        args = parse_args(["--version"])
        self.assertTrue(args.version)

    def test_version_flag_prints_and_exits_0(self) -> None:
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(["--version"])
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn(TOOL_NAME, output)
        self.assertIn(__version__, output)

    def test_version_flag_does_not_probe(self) -> None:
        with patch("trustlint.analyzer.probe_domain") as mock_probe:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["--version"])
            mock_probe.assert_not_called()


class TestListClassificationsFlag(unittest.TestCase):
    """Verify the --list-classifications flag."""

    def test_list_classifications_flag_parsed(self) -> None:
        args = parse_args(["--list-classifications"])
        self.assertTrue(args.list_classifications)

    def test_list_classifications_prints_all_entries(self) -> None:
        import io
        from contextlib import redirect_stdout
        from tls_policy_adapter import RISK_MAP
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(["--list-classifications"])
        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn(TOOL_NAME, output)
        self.assertIn(f"Registered TLS classifications: {len(RISK_MAP)}", output)
        for name in sorted(RISK_MAP.keys()):
            self.assertIn(name, output)

    def test_list_classifications_does_not_probe(self) -> None:
        with patch("trustlint.analyzer.probe_domain") as mock_probe:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["--list-classifications"])
            mock_probe.assert_not_called()

    def test_list_classifications_does_not_require_target(self) -> None:
        # No domain argument should NOT produce an error when only
        # --list-classifications is supplied.
        exit_code = main(["--list-classifications"])
        self.assertEqual(exit_code, 0)


class TestTrustlintCommandAlias(unittest.TestCase):
    """Verify the trustlint console script is wired to the same main()."""

    def test_trustlint_entry_point(self) -> None:
        import importlib.metadata
        dist = importlib.metadata.distribution("trustlint")
        eps = {ep.name: ep.value for ep in dist.entry_points}
        self.assertIn("trustlint", eps)
        self.assertEqual(eps["trustlint"], "scripts.spl_tls_analyze:main")

    def test_main_callable_as_trustlint_entry(self) -> None:
        # Simulate the trustlint console script invocation.
        with patch("trustlint.analyzer.probe_domain") as mock_probe:
            mock_probe.return_value = _make_mock_probe("alias.example.com", "VALID_TLS")
            exit_code = main(["alias.example.com", "--quiet"])
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
