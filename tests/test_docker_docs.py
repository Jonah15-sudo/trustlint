"""Docker smoke tests — verify Dockerfile and documentation integrity.

These tests check that:
- Dockerfile exists and does not expose ports / run services
- .dockerignore exists
- docs/DOCKER_USAGE.md exists
- Image tag matches package version
- Dockerfile uses the CLI as entry point (not a web server)

Full Docker build/execution tests are environment-dependent and are
verified manually via the release verification script.
"""

from __future__ import annotations

import os
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPECTED_VERSION = "1.0.0"


class TestDockerDocs(unittest.TestCase):
    """Smoke tests for Dockerfile and Docker documentation."""

    def test_dockerfile_exists(self) -> None:
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        self.assertTrue(os.path.exists(path), "Dockerfile not found")

    def test_dockerfile_no_expose(self) -> None:
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path, "r") as f:
            content = f.read()
        self.assertNotIn("EXPOSE", content, "Dockerfile must not expose ports")
        self.assertNotIn("uvicorn", content, "Dockerfile must not run web server")
        self.assertNotIn("gunicorn", content, "Dockerfile must not run web server")

    def test_dockerfile_cli_entrypoint(self) -> None:
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("ENTRYPOINT", content, "Dockerfile must have ENTRYPOINT")
        self.assertIn("trustlint", content, "Dockerfile must use CLI entry point")

    def test_dockerfile_non_root(self) -> None:
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("USER appuser", content, "Dockerfile must run as non-root")

    def test_dockerfile_base_image(self) -> None:
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(path, "r") as f:
            for line in f:
                if line.startswith("FROM"):
                    self.assertIn("python:3.10", line, "Dockerfile must use Python 3.10")
                    break

    def test_dockerignore_exists(self) -> None:
        path = os.path.join(PROJECT_ROOT, ".dockerignore")
        self.assertTrue(os.path.exists(path), ".dockerignore not found")

    def test_dockerignore_excludes_git(self) -> None:
        path = os.path.join(PROJECT_ROOT, ".dockerignore")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(".git/", content, ".dockerignore must exclude .git/")

    def test_docker_usage_docs_exist(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "DOCKER_USAGE.md")
        self.assertTrue(os.path.exists(path), "DOCKER_USAGE.md not found")

    def test_docker_usage_docs_mentions_version(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "DOCKER_USAGE.md")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn(EXPECTED_VERSION, content,
                      f"DOCKER_USAGE.md must mention version {EXPECTED_VERSION}")

    def test_docker_usage_docs_no_production_claim(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "DOCKER_USAGE.md")
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("Not production ready", content,
                      "DOCKER_USAGE.md must include no-production disclaimer")


if __name__ == "__main__":
    unittest.main()
