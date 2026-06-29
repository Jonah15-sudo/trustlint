from __future__ import annotations

from typing import Any, Dict, Mapping

from spl_v7.dsl import ExpressionCompiler, FeatureDSLParser, FeatureDSLProgram


def _structural_signal(data: Any, name: str, default: float = 0.0) -> float:
    if isinstance(data, Mapping):
        signals = data.get("signals")
        if isinstance(signals, Mapping):
            try:
                return float(signals.get(name, default))
            except (TypeError, ValueError):
                return default
    return default


def _tls_field(data: Any, name: str, default: Any = None) -> Any:
    if isinstance(data, Mapping):
        return data.get(name, default)
    return default


def _tls_header(data: Any, name: str, default: Any = None) -> Any:
    if isinstance(data, Mapping):
        headers = data.get("headers")
        if isinstance(headers, Mapping):
            return headers.get(name, default)
    return default


def _tls_transport(meta: Any, attr: str, default: Any = None) -> Any:
    if isinstance(meta, Mapping):
        return meta.get(attr, default)
    return default


def build_experiment_dsl() -> FeatureDSLProgram:
    from spl_v7.dsl import SAFE_FUNCTIONS

    functions: Dict[str, Any] = dict(SAFE_FUNCTIONS)
    functions["structural_signal"] = _structural_signal
    functions["tls_field"] = _tls_field
    functions["tls_header"] = _tls_header
    functions["tls_transport"] = _tls_transport

    compiler = ExpressionCompiler(functions=functions)
    parser = FeatureDSLParser()

    dsl_text = """
# TLS features (safe access — use defaults when evidence lacks TLS fields)
feature tls_valid = tls_field(data, "valid", False)
feature tls_expiry_urgency = normalize(tls_field(data, "expiry_days", 30), 0, 30)
feature hsts_missing = not tls_header(data, "hsts", True)
feature csp_missing = not tls_header(data, "csp", True)
feature timeout_flag = tls_transport(transport_meta, "status", "ok") == 'timeout'
feature partial_flag = tls_transport(transport_meta, "status", "") == 'partial'
feature http_error_flag = tls_transport(transport_meta, "status", "") == 'error'
feature source_latency_pressure = normalize(tls_transport(transport_meta, "latency_ms", 0), 0, 3000)
feature surface_tension = clamp(0.0, 1.0, 0.30 * tls_expiry_urgency + 0.20 * hsts_missing + 0.20 * csp_missing + 0.15 * timeout_flag + 0.10 * partial_flag + 0.05 * source_latency_pressure)

# OFE structural signal features (safe access — defaults to 0.0 when signal absent)
feature ofe_contradiction_density = structural_signal(data, "contradiction_density", 0.0)
feature ofe_topology_drift = structural_signal(data, "topology_drift", 0.0)
feature ofe_symbol_entropy = structural_signal(data, "symbol_entropy", 0.0)
"""
    specs = parser.parse(dsl_text)
    return FeatureDSLProgram(specs, compiler=compiler)
