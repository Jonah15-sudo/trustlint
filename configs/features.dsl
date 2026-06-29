# SPL v7 production feature DSL
# Raw artifacts stay neutral. Interpretation happens here + in the learner.
feature tls_valid = data.valid
feature tls_expiry_urgency = normalize(30 - data.expiry_days, 0, 30)
feature hsts_missing = not data.headers.hsts
feature csp_missing = not data.headers.csp
feature timeout_flag = transport_meta.status == 'timeout'
feature partial_flag = transport_meta.status == 'partial'
feature http_error_flag = transport_meta.status == 'error'
feature source_latency_pressure = normalize(transport_meta.latency_ms, 0, 3000)
feature surface_tension = clamp(0.0, 1.0, 0.30 * tls_expiry_urgency + 0.20 * hsts_missing + 0.20 * csp_missing + 0.15 * timeout_flag + 0.10 * partial_flag + 0.05 * source_latency_pressure)
