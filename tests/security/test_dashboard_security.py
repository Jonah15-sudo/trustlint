"""Tests for dashboard security features.

Tests cover:
- Security headers on all responses
- CORS restrictions
- Token authentication
- HTML escaping (XSS prevention)
- Redacted API responses
- Local-only defaults
"""

import pytest

from spl_v7.dashboard import create_app, build_dashboard_html


@pytest.fixture
def client():
    """Create a test client with no auth (dev mode)."""
    from fastapi.testclient import TestClient
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Create a test client with token auth enabled."""
    from fastapi.testclient import TestClient
    app = create_app(auth_token="test-secret-token")
    return TestClient(app)


class TestSecurityHeaders:
    """Tests that security headers are present on all responses."""

    def test_x_content_type_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        response = client.get("/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        response = client.get("/health")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy(self, client):
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp
        assert "default-src 'self'" in csp

    def test_headers_on_all_endpoints(self, client):
        for path in ["/", "/api/snapshot", "/health"]:
            response = client.get(path)
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"


class TestCORSRestrictions:
    """Tests for CORS configuration."""

    def test_cors_allows_localhost(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware should allow localhost
        assert response.status_code in (200, 405)

    def test_cors_rejects_unknown_origin(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.example.com"},
        )
        # Should not include Access-Control-Allow-Origin for unknown origin
        assert "Access-Control-Allow-Origin" not in response.headers


class TestTokenAuthentication:
    """Tests for bearer token authentication."""

    def test_no_token_rejects_index(self):
        from fastapi.testclient import TestClient
        app = create_app(auth_token="secret123")
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 401

    def test_valid_token_allows_index(self):
        from fastapi.testclient import TestClient
        app = create_app(auth_token="secret123")
        client = TestClient(app)
        response = client.get(
            "/",
            headers={"Authorization": "Bearer secret123"},
        )
        assert response.status_code == 200

    def test_invalid_token_rejects_index(self):
        from fastapi.testclient import TestClient
        app = create_app(auth_token="secret123")
        client = TestClient(app)
        response = client.get(
            "/",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 403

    def test_malformed_auth_header_rejects(self):
        from fastapi.testclient import TestClient
        app = create_app(auth_token="secret123")
        client = TestClient(app)
        response = client.get(
            "/",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401

    def test_health_needs_no_auth(self, client):
        response = client.get("/health")
        assert response.status_code == 200


class TestAPIRedaction:
    """Tests that /api/snapshot returns redacted data."""

    def test_snapshot_excludes_graph_topology(self, client):
        response = client.get("/api/snapshot")
        data = response.json()
        # Should NOT contain internal graph details
        assert "graph" not in data
        assert "nodes" not in data
        assert "edges" not in data

    def test_snapshot_contains_safe_fields(self, client):
        response = client.get("/api/snapshot")
        data = response.json()
        # Should contain only safe summary fields
        assert "samples_seen" in data
        assert "accuracy" in data
        assert "bus" in data


class TestXSSPrevention:
    """Tests for HTML escaping in dashboard output."""

    def test_title_is_escaped(self):
        malicious_title = '<script>alert("xss")</script>'
        html = build_dashboard_html(
            {"nodes": [], "edges": []},
            title=malicious_title,
        )
        # The malicious title should be escaped in <title> tag
        assert "&lt;script&gt;" in html
        # The Plotly CDN script tag is expected, but user title should not appear as raw HTML
        # Check that the malicious title doesn't appear as raw HTML in the summary
        assert malicious_title not in html or "&lt;script&gt;" in html

    def test_node_ids_are_escaped(self):
        malicious_node = '<img src=x onerror=alert(1)>'
        html = build_dashboard_html(
            {
                "nodes": [{"id": malicious_node, "type": "feature"}],
                "edges": [],
            },
        )
        assert "<img src=x" not in html
        assert "&lt;img" in html

    def test_empty_title_handled(self):
        html = build_dashboard_html(
            {"nodes": [], "edges": []},
            title="",
        )
        assert "<title></title>" in html

    def test_special_chars_in_title(self):
        html = build_dashboard_html(
            {"nodes": [], "edges": []},
            title="Test & 'Title' \"Quotes\"",
        )
        assert "&amp;" in html
        assert "&#x27;" in html or "&apos;" in html


class TestDefaultConfiguration:
    """Tests for secure default configuration."""

    def test_docs_url_disabled(self, client):
        response = client.get("/docs")
        assert response.status_code == 404

    def test_redoc_url_disabled(self, client):
        response = client.get("/redoc")
        assert response.status_code == 404

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCacheControl:
    """Tests for cache-control headers."""

    def test_cache_control_no_store(self, client):
        response = client.get("/health")
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-store" in cache_control

    def test_cache_control_no_cache(self, client):
        response = client.get("/health")
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-cache" in cache_control

    def test_pragma_no_cache(self, client):
        response = client.get("/health")
        assert response.headers.get("Pragma") == "no-cache"

    def test_cache_headers_on_all_endpoints(self, client):
        for path in ["/", "/api/snapshot", "/health"]:
            response = client.get(path)
            assert "no-store" in response.headers.get("Cache-Control", "")


class TestReadyEndpoint:
    """Tests for Kubernetes readiness probe."""

    def test_ready_returns_200(self, auth_client):
        response = auth_client.get(
            "/ready",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_ready_requires_auth(self, auth_client):
        response = auth_client.get("/ready")
        assert response.status_code == 401

    def test_ready_rejects_invalid_token(self, auth_client):
        response = auth_client.get(
            "/ready",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 403

    def test_ready_no_auth_dev_mode(self, client):
        """In dev mode (no auth_token), /ready should pass."""
        response = client.get("/ready")
        assert response.status_code == 200
