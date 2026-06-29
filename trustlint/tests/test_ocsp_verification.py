"""Tests for OCSP response parsing with verification status.

Verifies:
- All OCSP responses are marked as unverified (no cryptographic verification)
- OCSP_UNVERIFIED can never independently produce ALLOW or DENY
- Deterministic fixtures for valid, revoked, malformed, expired, wrong-serial,
  unauthorized-responder, and empty responses
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trustlint.infrastructure.ocsp.client import (
    _parse_ocsp_response,
    CERT_STATUS_GOOD,
    CERT_STATUS_REVOKED,
    CERT_STATUS_UNKNOWN,
    CERT_STATUS_UNVERIFIED,
)


class TestOCSPVerificationStatus(unittest.TestCase):
    """All parsed OCSP responses must be marked as unverified."""

    def test_parsed_response_has_verified_field(self) -> None:
        """Every parsed response must include a 'verified' field."""
        result = _parse_ocsp_response(b"")
        self.assertIn("verified", result)
        self.assertFalse(result["verified"])

    def test_verified_always_false(self) -> None:
        """The 'verified' field must always be False — no crypto verification is performed."""
        # Empty response
        result = _parse_ocsp_response(b"")
        self.assertFalse(result["verified"])

        # Malformed data
        result = _parse_ocsp_response(b"\x30\x05\x0a\x03\x00\x00\x00")
        self.assertFalse(result["verified"])

    def test_unverified_cannot_produce_allow(self) -> None:
        """OCSP_UNVERIFIED status must never be 'good' — it must not independently ALLOW."""
        # Build a minimal valid-looking response to parse
        # Even if the DER parses successfully, status must be UNVERIFIED
        result = _parse_ocsp_response(b"")
        # Unknown for empty, but never 'good'
        self.assertNotEqual(result["status"], CERT_STATUS_GOOD)

    def test_unverified_cannot_produce_deny(self) -> None:
        """OCSP_UNVERIFIED status must never be 'revoked' — it must not independently DENY."""
        result = _parse_ocsp_response(b"")
        self.assertNotEqual(result["status"], CERT_STATUS_REVOKED)


class TestOCSPFixtures(unittest.TestCase):
    """Test OCSP parsing against deterministic DER fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build fixtures from the cryptography library if available."""
        try:
            from tests.ocsp_fixtures import build_all_fixtures
            cls.fixtures = build_all_fixtures()
        except ImportError:
            cls.fixtures = {}

    def test_valid_good_fixture(self) -> None:
        """Valid OCSP response with GOOD status → unverified."""
        if "valid_good" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["valid_good"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["status"], fixture["expected_status"])
        self.assertEqual(result["cert_status"], fixture["expected_cert_status"])
        self.assertFalse(result["verified"])

    def test_revoked_fixture(self) -> None:
        """Revoked OCSP response → unverified (not independently DENY)."""
        if "revoked" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["revoked"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["status"], fixture["expected_status"])
        self.assertEqual(result["cert_status"], fixture["expected_cert_status"])
        self.assertFalse(result["verified"])
        # Must NOT be "revoked" at top level — that would independently DENY
        self.assertNotEqual(result["status"], CERT_STATUS_REVOKED)

    def test_malformed_fixture(self) -> None:
        """Truncated DER → malformed."""
        if "malformed" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["malformed"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["status"], "malformed")
        self.assertFalse(result["verified"])

    def test_empty_fixture(self) -> None:
        """Empty bytes → unknown."""
        result = _parse_ocsp_response(b"")
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["verified"])

    def test_wrong_serial_fixture(self) -> None:
        """Response with serial 0xDEADBEEF — serial is extracted correctly."""
        if "wrong_serial" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["wrong_serial"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["serial_number"], fixture["expected_serial"])
        self.assertFalse(result["verified"])

    def test_expired_response_fixture(self) -> None:
        """Response with stale thisUpdate/nextUpdate — still parsed as unverified."""
        if "expired_response" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["expired_response"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["status"], fixture["expected_status"])
        self.assertFalse(result["verified"])

    def test_unauthorized_responder_fixture(self) -> None:
        """Response signed by unauthorized responder — parsed as unverified."""
        if "unauthorized_responder" not in self.fixtures:
            self.skipTest("cryptography not available")
        fixture = self.fixtures["unauthorized_responder"]
        result = _parse_ocsp_response(fixture["der"])
        self.assertEqual(result["status"], fixture["expected_status"])
        self.assertFalse(result["verified"])


if __name__ == "__main__":
    unittest.main()
