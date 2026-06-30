# TrustLint Phase 1 Dependency Review

## httpx2 Dependency

### Package Information

- **Package name:** httpx2
- **Version installed:** 2.5.0
- **Source:** PyPI (https://pypi.org/project/httpx2/)
- **License:** BSD-3-Clause

### Reason for Inclusion

The `httpx2` package was added to `pyproject.toml` dev dependencies to resolve test failures in `tests/security/test_dashboard_security.py`.

### Dependency Chain

```
fastapi (required by spl-core)
  └── starlette>=1.3.1
        └── httpx2 (for starlette.testclient)
```

### Technical Justification

Starlette 1.3.1 (a dependency of FastAPI) switched its test client implementation from `httpx` to `httpx2`. The `starlette.testclient` module requires `httpx2` to be installed:

```python
# From starlette/testclient.py
if TYPE_CHECKING:
    import httpx2 as httpx
else:
    try:
        import httpx2 as httpx
    except ModuleNotFoundError:
        try:
            import httpx
        except ModuleNotFoundError:
            raise RuntimeError(
                "The starlette.testclient module requires the httpx2 package to be installed.\n"
                "You can install this with:\n"
                "    $ pip install httpx2\n"
            )
```

### Test Path Affected

- `tests/security/test_dashboard_security.py` - Uses `fastapi.testclient.TestClient` which requires `starlette.testclient`

### Alternatives Considered

1. **Pin starlette to older version:** Not recommended as it would prevent security updates
2. **Use httpx instead:** Deprecated by starlette, will be removed in future versions
3. **Skip security tests:** Not acceptable as they validate critical security headers

### uv.lock Consistency

The `uv.lock` file has been updated to include httpx2 and its dependencies:
- httpx2==2.5.0
- httpcore2==2.5.0
- truststore==0.10.4

### Verification

```bash
# Verify httpx2 is installed
uv pip show httpx2

# Verify starlette testclient works
python -c "from starlette.testclient import TestClient; print('OK')"

# Verify security tests pass
uv run pytest tests/security/test_dashboard_security.py -v
```

### Conclusion

The `httpx2` dependency is the correct and intended dependency for the affected test path. It is required by starlette 1.3.1+ for its testclient module, which is used by FastAPI and our security tests. The dependency is well-maintained, has a permissive license, and is the official replacement for httpx in the starlette ecosystem.
