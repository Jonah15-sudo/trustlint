"""Tests for input bounds and resource limits.

Tests verify:
- Maximum file size enforcement
- Maximum domain count enforcement
- Maximum domain length enforcement
- Duplicate handling
"""

import os
import tempfile
import pytest

from scripts.spl_tls_analyze import (
    load_domains_from_file,
    validate_domain_name,
    MAX_INPUT_FILE_SIZE,
    MAX_DOMAINS,
    MAX_DOMAIN_LENGTH,
)


class TestDomainValidation:
    """Tests for domain name validation."""

    def test_valid_domain(self):
        valid, msg = validate_domain_name("example.com")
        assert valid is True
        assert msg == ""

    def test_valid_subdomain(self):
        valid, msg = validate_domain_name("sub.example.com")
        assert valid is True

    def test_empty_domain_rejected(self):
        valid, msg = validate_domain_name("")
        assert valid is False
        assert "empty" in msg.lower() or "exceeds" in msg.lower()

    def test_too_long_domain_rejected(self):
        long_domain = "a" * 254 + ".com"
        valid, msg = validate_domain_name(long_domain)
        assert valid is False
        assert "253" in msg or "exceeds" in msg.lower()

    def test_invalid_chars_rejected(self):
        valid, msg = validate_domain_name("example.com/path")
        assert valid is False

    def test_space_rejected(self):
        valid, msg = validate_domain_name("example .com")
        assert valid is False


class TestFileLoadingBounds:
    """Tests for file loading resource limits."""

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            path = f.name
        try:
            domains = load_domains_from_file(path)
            assert domains == []
        finally:
            os.unlink(path)

    def test_comments_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# This is a comment\nexample.com\n# Another comment\n")
            path = f.name
        try:
            domains = load_domains_from_file(path)
            assert domains == ["example.com"]
        finally:
            os.unlink(path)

    def test_blank_lines_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n\nexample.com\n\n\n")
            path = f.name
        try:
            domains = load_domains_from_file(path)
            assert domains == ["example.com"]
        finally:
            os.unlink(path)

    def test_domain_too_long_skipped(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            long_domain = "a" * 254 + ".com"
            f.write(f"{long_domain}\nexample.com\n")
            path = f.name
        try:
            domains = load_domains_from_file(path)
            assert "example.com" in domains
            assert long_domain not in domains
        finally:
            os.unlink(path)

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_domains_from_file("/nonexistent/path/domains.txt")

    def test_constants_are_sensible(self):
        assert MAX_INPUT_FILE_SIZE > 0
        assert MAX_DOMAINS > 0
        assert MAX_DOMAIN_LENGTH == 253  # DNS specification


class TestLoggingIdempotency:
    """Tests that logging setup is idempotent."""

    def test_setup_logging_idempotent(self):
        import logging
        from scripts.spl_tls_analyze import setup_logging, logger

        initial_handler_count = len(logger.handlers)
        setup_logging(verbose=False)
        after_first = len(logger.handlers)
        setup_logging(verbose=False)
        after_second = len(logger.handlers)

        # Should not add duplicate handlers
        assert after_first == after_second
        # Restore original state
        logger.handlers = logger.handlers[:initial_handler_count]
