from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta

_REQUIRED_FIELDS = [
    "case_id", "timestamp", "tls_valid", "tls_expiry_days", "http_status",
    "partial_response", "timeout", "hsts_present", "csp_present",
    "latency_ms", "bytes_received", "label",
]

_BOOLEAN_FIELDS = {"tls_valid", "partial_response", "timeout", "hsts_present", "csp_present", "label"}

_INTEGER_FIELDS = {"tls_expiry_days", "latency_ms", "bytes_received"}


def _is_valid_iso8601(ts: str) -> bool:
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def _parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _parse_int(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return None


def _validate_row(row: Dict[str, Any], seen_ids: set) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for field in _REQUIRED_FIELDS:
        if field not in row or row[field] is None:
            return None, f"missing required field: {field}"

    case_id = str(row["case_id"])
    if case_id in seen_ids:
        return None, f"duplicate case_id: {case_id}"

    timestamp = str(row["timestamp"])
    if not _is_valid_iso8601(timestamp):
        return None, f"invalid timestamp: {timestamp}"

    parsed: Dict[str, Any] = {"case_id": case_id, "timestamp": timestamp}

    for field in _BOOLEAN_FIELDS:
        val = row[field]
        parsed_bool = _parse_bool(val)
        if parsed_bool is None:
            return None, f"invalid boolean in {field}: {val!r}"
        parsed[field] = parsed_bool

    for field in _INTEGER_FIELDS:
        val = row[field]
        parsed_int = _parse_int(val)
        if parsed_int is None:
            return None, f"invalid integer in {field}: {val!r}"
        parsed[field] = parsed_int

    if parsed["latency_ms"] < 0:
        return None, f"negative latency_ms: {parsed['latency_ms']}"

    if parsed["bytes_received"] < 0:
        return None, f"negative bytes_received: {parsed['bytes_received']}"

    if parsed["tls_expiry_days"] > 36500:
        return None, f"tls_expiry_days exceeds 36500: {parsed['tls_expiry_days']}"

    parsed["http_status"] = str(row["http_status"])

    return parsed, None


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _read_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def _row_to_artifact(row: Dict[str, Any], source: str = "real-tls") -> EvidenceArtifact:
    label = bool(row["label"])
    return EvidenceArtifact(
        source=source,
        type="tls",
        data={
            "valid": bool(row["tls_valid"]),
            "expiry_days": int(row["tls_expiry_days"]),
            "headers": {
                "hsts": bool(row["hsts_present"]),
                "csp": bool(row["csp_present"]),
            },
            "label": label,
            "label_weight": 1.0,
        },
        transport_meta=EvidenceTransportMeta(
            status=str(row["http_status"]),
            latency_ms=int(row["latency_ms"]),
            bytes_received=int(row["bytes_received"]),
        ),
    )


def load_real_tls_data(path: str, source: str = "real-tls") -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {
            "valid_rows": [],
            "validation": {
                "total": 0,
                "valid": 0,
                "skipped": 0,
                "duplicate_ids": [],
                "validation_errors": [],
                "positive_count": 0,
                "negative_count": 0,
                "error": f"file not found: {path}",
            },
        }

    ext = os.path.splitext(path)[1].lower()
    if ext == ".jsonl":
        raw_rows = _read_jsonl(path)
    elif ext == ".csv":
        raw_rows = _read_csv(path)
    else:
        return {
            "valid_rows": [],
            "validation": {
                "total": 0,
                "valid": 0,
                "skipped": 0,
                "duplicate_ids": [],
                "validation_errors": [],
                "positive_count": 0,
                "negative_count": 0,
                "error": f"unsupported format: {ext} (use .jsonl or .csv)",
            },
        }

    seen_ids: set = set()
    valid_rows: List[Dict[str, Any]] = []
    validation_errors: List[Dict[str, Any]] = []
    duplicate_ids: List[str] = []
    positive_count = 0
    negative_count = 0

    for i, raw in enumerate(raw_rows):
        parsed, error = _validate_row(raw, seen_ids)
        if error:
            entry = {"row": i, "error": error}
            if "duplicate" in error:
                dup_id = str(raw.get("case_id", ""))
                if dup_id not in duplicate_ids:
                    duplicate_ids.append(dup_id)
            validation_errors.append(entry)
            continue

        seen_ids.add(parsed["case_id"])
        valid_rows.append(parsed)

        if parsed["label"]:
            positive_count += 1
        else:
            negative_count += 1

    artifacts = [_row_to_artifact(r, source=source) for r in valid_rows]

    return {
        "raw_valid_rows": valid_rows,
        "valid_rows": artifacts,
        "validation": {
            "total": len(raw_rows),
            "valid": len(valid_rows),
            "skipped": len(raw_rows) - len(valid_rows),
            "duplicate_ids": duplicate_ids,
            "validation_errors": validation_errors,
            "positive_count": positive_count,
            "negative_count": negative_count,
        },
    }
