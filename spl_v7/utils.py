from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any, Iterable, List


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def sigmoid(x: float) -> float:
    x = float(x)
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    denominator = float(denominator)
    if abs(denominator) < 1e-12:
        return float(default)
    return float(numerator) / denominator


def mean(values: Iterable[float], default: float = 0.0) -> float:
    xs = [float(v) for v in values]
    if not xs:
        return float(default)
    return sum(xs) / len(xs)


def entropy(values: Iterable[float]) -> float:
    xs = [abs(float(v)) for v in values if float(v) != 0.0]
    total = sum(xs)
    if total <= 0.0:
        return 0.0
    probs = [x / total for x in xs]
    result = 0.0
    for p in probs:
        result -= p * math.log(p + 1e-12)
    return result / math.log(max(len(probs), 2))


def variance(values: Iterable[float]) -> float:
    xs = [float(v) for v in values]
    if not xs:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def stdev(values: Iterable[float]) -> float:
    return math.sqrt(max(variance(values), 0.0))


def stable_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update((part or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def deep_get(data: Any, path: str, default: Any = None) -> Any:
    current = data
    for segment in path.split("."):
        if current is None:
            return default
        if isinstance(current, Mapping):
            if segment in current:
                current = current[segment]
            else:
                return default
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            if segment.isdigit():
                index = int(segment)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return default
            else:
                return default
        else:
            current = getattr(current, segment, default)
    return current


def flatten_numeric(values: Iterable[Any]) -> List[float]:
    out: List[float] = []
    for value in values:
        try:
            out.append(float(value))
        except Exception:
            continue
    return out
