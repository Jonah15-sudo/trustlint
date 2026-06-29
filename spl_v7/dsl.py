from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .utils import clamp, entropy, mean, safe_div, sigmoid, stdev


class DSLParseError(ValueError):
    pass


class DSLEvaluationError(RuntimeError):
    pass


def _func_clamp(*args: float) -> float:
    if len(args) == 2:
        lo, hi = 0.0, float(args[1])
        return clamp(args[0], lo, hi)
    if len(args) == 3:
        return clamp(args[2], args[0], args[1])
    raise DSLEvaluationError("clamp expects 2 or 3 arguments")


def _func_length(value: Any) -> int:
    try:
        return len(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def _func_normalize(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    if hi == lo:
        return 0.0
    return clamp((float(value) - lo) / (hi - lo), 0.0, 1.0)


SAFE_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sum": lambda xs: sum(float(x) for x in xs),
    "mean": mean,
    "stdev": stdev,
    "entropy": entropy,
    "sigmoid": sigmoid,
    "safe_div": safe_div,
    "clamp": _func_clamp,
    "length": _func_length,
    "normalize": _func_normalize,
}


@dataclass(slots=True)
class FeatureSpec:
    name: str
    expression: str
    dtype: str = "numeric"

    def __post_init__(self) -> None:
        self.dtype = self.dtype or "numeric"


class SafeAstEvaluator(ast.NodeVisitor):
    def __init__(self, context: Mapping[str, Any], functions: Optional[Dict[str, Callable[..., Any]]] = None):
        self.context = context
        self.functions = functions or SAFE_FUNCTIONS

    def visit(self, node: ast.AST) -> Any:  # type: ignore[override]
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, None)
        if visitor is None:
            raise DSLEvaluationError(f"Unsupported expression node: {node.__class__.__name__}")
        return visitor(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        name = node.id
        lowered = name.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        if name in self.context:
            return self.context[name]
        if name in self.functions:
            return self.functions[name]
        raise DSLEvaluationError(f"Unknown variable: {name}")

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        value = self.visit(node.value)
        return self._resolve_attr(value, node.attr)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        value = self.visit(node.value)
        key = self.visit(node.slice) if hasattr(node, "slice") else None
        try:
            return value[key]  # type: ignore[index]
        except Exception as exc:
            raise DSLEvaluationError(f"Invalid subscript access: {exc}") from exc

    def visit_Slice(self, node: ast.Slice) -> slice:
        lower = self.visit(node.lower) if node.lower else None
        upper = self.visit(node.upper) if node.upper else None
        step = self.visit(node.step) if node.step else None
        return slice(lower, upper, step)

    def visit_List(self, node: ast.List) -> list[Any]:
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> tuple[Any, ...]:
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Dict(self, node: ast.Dict) -> dict[Any, Any]:
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.Invert):
            return ~operand
        raise DSLEvaluationError(f"Unsupported unary operator: {node.op.__class__.__name__}")

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            for v in node.values:
                if not bool(self.visit(v)):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for v in node.values:
                if bool(self.visit(v)):
                    return True
            return False
        raise DSLEvaluationError(f"Unsupported boolean operator: {node.op.__class__.__name__}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.Pow):
            raise DSLEvaluationError("Power operator is disabled for safety")
        raise DSLEvaluationError(f"Unsupported binary operator: {op.__class__.__name__}")

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for operator, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(operator, ast.Eq):
                ok = left == right
            elif isinstance(operator, ast.NotEq):
                ok = left != right
            elif isinstance(operator, ast.Lt):
                ok = left < right
            elif isinstance(operator, ast.LtE):
                ok = left <= right
            elif isinstance(operator, ast.Gt):
                ok = left > right
            elif isinstance(operator, ast.GtE):
                ok = left >= right
            elif isinstance(operator, ast.In):
                ok = left in right
            elif isinstance(operator, ast.NotIn):
                ok = left not in right
            elif isinstance(operator, ast.Is):
                ok = left is right
            elif isinstance(operator, ast.IsNot):
                ok = left is not right
            else:
                raise DSLEvaluationError(f"Unsupported comparison: {operator.__class__.__name__}")
            if not ok:
                return False
            left = right
        return True

    def visit_Call(self, node: ast.Call) -> Any:
        func = self.visit(node.func)
        if not callable(func):
            raise DSLEvaluationError("Call target is not callable")
        args = [self.visit(arg) for arg in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords if kw.arg is not None}
        if kwargs:
            return func(*args, **kwargs)
        return func(*args)

    def generic_visit(self, node: ast.AST) -> Any:
        raise DSLEvaluationError(f"Unsupported node: {node.__class__.__name__}")

    @staticmethod
    def _resolve_attr(value: Any, attr: str) -> Any:
        if isinstance(value, Mapping):
            if attr in value:
                return value[attr]
            raise DSLEvaluationError(f"Missing key '{attr}' in mapping")
        if hasattr(value, attr):
            return getattr(value, attr)
        raise DSLEvaluationError(f"Cannot resolve attribute '{attr}' on {type(value).__name__}")


class ExpressionCompiler:
    def __init__(self, functions: Optional[Dict[str, Callable[..., Any]]] = None):
        self.functions = functions or SAFE_FUNCTIONS

    def compile(self, expression: str) -> ast.AST:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise DSLParseError(str(exc)) from exc
        self._validate_tree(tree)
        return tree

    def evaluate(self, compiled: ast.AST, context: Mapping[str, Any]) -> Any:
        evaluator = SafeAstEvaluator(context, self.functions)
        return evaluator.visit(compiled)

    def _validate_tree(self, tree: ast.AST) -> None:
        allowed = (
            ast.Expression,
            ast.Constant,
            ast.Name,
            ast.Attribute,
            ast.Subscript,
            ast.Slice,
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.UnaryOp,
            ast.BoolOp,
            ast.BinOp,
            ast.Compare,
            ast.Call,
            ast.Load,
            ast.And,
            ast.Or,
            ast.Not,
            ast.UAdd,
            ast.USub,
            ast.Invert,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.In,
            ast.NotIn,
            ast.Is,
            ast.IsNot,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise DSLParseError(f"Disallowed syntax in feature DSL: {node.__class__.__name__}")
            if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
                raise DSLParseError("Only direct function calls are allowed in the DSL")


class FeatureDSLParser:
    FEATURE_RE = re.compile(
        r"^feature\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s*:\s*(?P<dtype>[A-Za-z_][A-Za-z0-9_]*))?"
        r"\s*=\s*(?P<expr>.+)$"
    )

    def parse(self, text: str) -> list[FeatureSpec]:
        specs: list[FeatureSpec] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            line = self._strip_inline_comment(line)
            match = self.FEATURE_RE.match(line)
            if not match:
                raise DSLParseError(f"Invalid DSL syntax on line {line_no}: {raw_line}")
            specs.append(
                FeatureSpec(
                    name=match.group("name"),
                    dtype=match.group("dtype") or "numeric",
                    expression=match.group("expr").strip(),
                )
            )
        if not specs:
            raise DSLParseError("No feature definitions found")
        return specs

    @staticmethod
    def _strip_inline_comment(line: str) -> str:
        in_single = False
        in_double = False
        chars: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "#" and not in_single and not in_double:
                break
            chars.append(ch)
            i += 1
        return "".join(chars).strip()


class FeatureDSLProgram:
    def __init__(self, specs: Iterable[FeatureSpec], compiler: Optional[ExpressionCompiler] = None):
        self.specs = list(specs)
        self.compiler = compiler or ExpressionCompiler()
        self.compiled = {spec.name: self.compiler.compile(spec.expression) for spec in self.specs}

    @classmethod
    def from_text(cls, text: str) -> "FeatureDSLProgram":
        parser = FeatureDSLParser()
        return cls(parser.parse(text))

    def evaluate(self, context: Mapping[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        working_context: Dict[str, Any] = dict(context)
        for spec in self.specs:
            value = self.compiler.evaluate(self.compiled[spec.name], working_context)
            results[spec.name] = value
            working_context[spec.name] = value
        return results

    def ordered_feature_names(self) -> list[str]:
        return [spec.name for spec in self.specs]

    def feature_vector(self, context: Mapping[str, Any]) -> list[float]:
        values = self.evaluate(context)
        vector: list[float] = []
        for name in self.ordered_feature_names():
            value = values[name]
            if isinstance(value, bool):
                vector.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                vector.append(float(value))
            else:
                vector.append(0.0)
        return vector

    def describe(self) -> list[dict[str, str]]:
        return [{"name": spec.name, "dtype": spec.dtype, "expression": spec.expression} for spec in self.specs]


def compile_feature_dsl(text: str) -> FeatureDSLProgram:
    return FeatureDSLProgram.from_text(text)
