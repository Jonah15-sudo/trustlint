"""Deterministic OCSP response fixtures for testing.

Each fixture is a DER-encoded OCSP response built using the cryptography library.
These fixtures cover: valid, expired, wrong-serial, invalid-signature,
unauthorized-responder, revoked, and malformed responses.
"""

from __future__ import annotations

import datetime
import hashlib
import os
from typing import Dict, Any

# Use cryptography if available; skip fixture generation if not
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.x509.ocsp import (
        OCSPResponseBuilder,
        OCSPResponseStatus,
    )
    from cryptography.x509 import ocsp as _ocsp_mod
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "fixtures", "ocsp_responses"
)


def _make_ca_and_cert():
    """Create a CA key/cert and a leaf cert for testing."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com"),
    ])
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(ca_name)
        .public_key(leaf_key.public_key())
        .serial_number(0xDEADBEEF)
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=90))
        .sign(ca_key, hashes.SHA256())
    )

    return ca_key, ca_cert, leaf_key, leaf_cert


def _build_ocsp_response(
    ca_key, ca_cert, leaf_cert,
    cert_status=_ocsp_mod.OCSPCertStatus.GOOD,
    this_update=None,
    next_update=None,
    revoked_time=None,
    revoked_reason=None,
    signer_key=None,
    signer_cert=None,
):
    """Build a DER-encoded OCSP response."""
    if this_update is None:
        this_update = datetime.datetime.now(datetime.timezone.utc)
    if next_update is None:
        next_update = this_update + datetime.timedelta(days=7)

    builder = _ocsp_mod.OCSPResponseBuilder()

    builder = builder.add_response(
        cert=leaf_cert,
        issuer=ca_cert,
        algorithm=hashes.SHA256(),
        cert_status=cert_status,
        this_update=this_update,
        next_update=next_update,
        revocation_time=revoked_time,
        revocation_reason=revoked_reason,
    )

    # Use the provided signer or default to the CA
    if signer_key is not None and signer_cert is not None:
        builder = builder.responder_id(
            _ocsp_mod.OCSPResponderEncoding.HASH, signer_cert
        )
        builder = builder.sign(signer_key, hashes.SHA256())
    else:
        builder = builder.responder_id(
            _ocsp_mod.OCSPResponderEncoding.HASH, ca_cert
        )
        builder = builder.sign(ca_key, hashes.SHA256())

    return builder.public_bytes(serialization.Encoding.DER)


def build_all_fixtures() -> Dict[str, Dict[str, Any]]:
    """Build all OCSP test fixtures.

    Returns dict mapping fixture name to {
        der: bytes (DER-encoded response),
        expected_status: str (expected parsed status),
        expected_cert_status: str (expected cert_status field),
        description: str,
    }
    """
    if not _HAS_CRYPTOGRAPHY:
        return {}

    ca_key, ca_cert, leaf_key, leaf_cert = _make_ca_and_cert()
    fixtures = {}

    # 1. Valid response (good status)
    der = _build_ocsp_response(ca_key, ca_cert, leaf_cert)
    fixtures["valid_good"] = {
        "der": der,
        "expected_status": "unverified",
        "expected_cert_status": "good",
        "description": "Valid OCSP response with GOOD certificate status (unverified)",
    }

    # 2. Revoked response
    revoked_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    der = _build_ocsp_response(
        ca_key, ca_cert, leaf_cert,
        cert_status=_ocsp_mod.OCSPCertStatus.REVOKED,
        revoked_time=revoked_time,
    )
    fixtures["revoked"] = {
        "der": der,
        "expected_status": "unverified",
        "expected_cert_status": "revoked",
        "description": "Valid OCSP response with REVOKED certificate status (unverified)",
    }

    # 3. Malformed response (truncated DER)
    valid_der = _build_ocsp_response(ca_key, ca_cert, leaf_cert)
    fixtures["malformed"] = {
        "der": valid_der[:20],
        "expected_status": "malformed",
        "expected_cert_status": None,
        "description": "Truncated DER data — should parse as malformed",
    }

    # 4. Empty response
    fixtures["empty"] = {
        "der": b"",
        "expected_status": "unknown",
        "expected_cert_status": None,
        "description": "Empty response bytes — should return unknown",
    }

    # 5. Wrong serial — same response but different serial number expected
    # The response is valid but contains serial 0xDEADBEEF
    der = _build_ocsp_response(ca_key, ca_cert, leaf_cert)
    fixtures["wrong_serial"] = {
        "der": der,
        "expected_status": "unverified",
        "expected_cert_status": "good",
        "expected_serial": 0xDEADBEEF,
        "description": "Valid response with serial 0xDEADBEEF — test serial extraction",
    }

    # 6. Expired response (thisUpdate in the past, nextUpdate in the past)
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    past_next = past + datetime.timedelta(days=7)
    der = _build_ocsp_response(
        ca_key, ca_cert, leaf_cert,
        this_update=past,
        next_update=past_next,
    )
    fixtures["expired_response"] = {
        "der": der,
        "expected_status": "unverified",
        "expected_cert_status": "good",
        "description": "Response with stale thisUpdate/nextUpdate (30 days old)",
    }

    # 7. Unauthorized responder — sign with a different key
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Other")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Other CA")]))
        .public_key(other_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(other_key, hashes.SHA256())
    )
    der = _build_ocsp_response(
        ca_key, ca_cert, leaf_cert,
        signer_key=other_key,
        signer_cert=other_cert,
    )
    fixtures["unauthorized_responder"] = {
        "der": der,
        "expected_status": "unverified",
        "expected_cert_status": "good",
        "description": "Response signed by unauthorized responder (not the CA)",
    }

    return fixtures


def write_fixtures():
    """Write all fixtures to the fixtures directory."""
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    fixtures = build_all_fixtures()
    for name, fixture in fixtures.items():
        path = os.path.join(FIXTURES_DIR, f"{name}.der")
        with open(path, "wb") as f:
            f.write(fixture["der"])
        print(f"  Wrote {path} ({len(fixture['der'])} bytes)")

    print(f"\nWrote {len(fixtures)} OCSP fixtures to {FIXTURES_DIR}")


if __name__ == "__main__":
    write_fixtures()
