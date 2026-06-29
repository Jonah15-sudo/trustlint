from __future__ import annotations

import html as html_mod
import logging
import os
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

import networkx as nx
import numpy as np
import plotly.graph_objects as go
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DashboardSnapshot:
    graph: Dict[str, Any]
    title: str = "SPL v7 Topology Dashboard"


class TopologySurfaceBuilder:
    def __init__(self, grid_size: int = 40, sigma: float = 0.65) -> None:
        self.grid_size = int(grid_size)
        self.sigma = float(sigma)

    def build(self, snapshot: Mapping[str, Any]) -> Dict[str, Any]:
        graph = nx.DiGraph()
        for node in snapshot.get("nodes", []):
            graph.add_node(node["id"], **node)
        for edge in snapshot.get("edges", []):
            graph.add_edge(edge["source"], edge["target"], **edge)

        positions = self._layout(graph)
        xs = np.linspace(-1.2, 1.2, self.grid_size)
        ys = np.linspace(-1.2, 1.2, self.grid_size)
        z = np.zeros((self.grid_size, self.grid_size), dtype=float)

        feature_edges = snapshot.get("edges", [])
        for edge in feature_edges:
            source = edge["source"]
            target = edge["target"]
            src_pos = positions.get(source, np.array([0.0, 0.0]))
            tgt_pos = positions.get(target, np.array([0.0, 0.0]))
            weight = float(edge.get("weight", 0.0))
            confidence = float(edge.get("confidence", 1.0))
            independence = float(edge.get("independence", 1.0))
            stability = float(edge.get("weighted_stability", 1.0))
            corroboration = float(edge.get("cross_source_corroboration", 1.0))
            intervention = float(edge.get("intervention_effect", 0.0))
            intervention_gate = 0.5 + min(0.5, abs(intervention))
            effective_weight = weight * confidence * independence * stability * corroboration * intervention_gate
            self._add_gaussian_ridge(z, xs, ys, src_pos, effective_weight * 0.45)
            self._add_gaussian_ridge(z, xs, ys, tgt_pos, effective_weight * 0.20)

        return {
            "graph": graph,
            "positions": positions,
            "x": xs,
            "y": ys,
            "z": z,
        }

    def _layout(self, graph: nx.DiGraph) -> Dict[str, np.ndarray]:
        if graph.number_of_nodes() == 0:
            return {}
        try:
            pos = nx.spring_layout(graph, seed=42, dim=2, k=0.9)
        except Exception:
            pos = nx.circular_layout(graph, dim=2)
        return {k: np.array(v, dtype=float) for k, v in pos.items()}

    def _add_gaussian_ridge(self, z: np.ndarray, xs: np.ndarray, ys: np.ndarray, center: np.ndarray, amplitude: float) -> None:
        cx, cy = float(center[0]), float(center[1])
        for iy, y in enumerate(ys):
            for ix, x in enumerate(xs):
                dist2 = (x - cx) ** 2 + (y - cy) ** 2
                z[iy, ix] += amplitude * float(np.exp(-dist2 / (2.0 * self.sigma ** 2)))


def build_dashboard_html(snapshot: Mapping[str, Any], title: str = "SPL v7 Topology Dashboard") -> str:
    # Escape title to prevent XSS
    safe_title = html_mod.escape(str(title))

    builder = TopologySurfaceBuilder()
    surface = builder.build(snapshot)
    graph: nx.DiGraph = surface["graph"]
    positions = surface["positions"]
    x = surface["x"]
    y = surface["y"]
    z = surface["z"]

    feature_names = [node["id"] for node in snapshot.get("nodes", []) if node.get("type") == "feature"]
    edge_map = {(e["source"], e["target"]): float(e.get("weight", 0.0)) for e in snapshot.get("edges", [])}

    surface_fig = go.Figure(
        data=[
            go.Surface(x=x, y=y, z=z, colorscale="Viridis", showscale=True, opacity=0.95)
        ]
    )
    surface_fig.update_layout(
        title="Topology Surface",
        scene=dict(
            xaxis_title="Topology X",
            yaxis_title="Topology Y",
            zaxis_title="Risk / Tension",
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    for node in graph.nodes():
        pos = positions.get(node, np.array([0.0, 0.0]))
        node_x.append(float(pos[0]))
        node_y.append(float(pos[1]))
        node_text.append(html_mod.escape(str(node)))
        node_color.append(0.2 if node == snapshot.get("target") else 0.6)

    edge_x = []
    edge_y = []
    for source, target in graph.edges():
        sx, sy = positions.get(source, np.array([0.0, 0.0]))
        tx, ty = positions.get(target, np.array([0.0, 0.0]))
        edge_x.extend([float(sx), float(tx), None])
        edge_y.extend([float(sy), float(ty), None])

    network_fig = go.Figure()
    network_fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1, color="#9aa0a6"),
            hoverinfo="none",
        )
    )
    network_fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            marker=dict(size=16, color=node_color, colorscale="Blues", line=dict(width=1, color="#111")),
            hovertemplate="%{text}<extra></extra>",
        )
    )
    network_fig.update_layout(
        title="Learned Causal Topology",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    heatmap_data = np.zeros((len(feature_names), len(feature_names)), dtype=float)
    for i, src in enumerate(feature_names):
        for j, tgt in enumerate(feature_names):
            if src == tgt:
                heatmap_data[i, j] = 0.0
            else:
                heatmap_data[i, j] = edge_map.get((src, snapshot.get("target")), 0.0) - edge_map.get((tgt, snapshot.get("target")), 0.0)

    heatmap_fig = go.Figure(
        data=[
            go.Heatmap(
                z=heatmap_data if feature_names else [[0.0]],
                x=feature_names if feature_names else ["n/a"],
                y=feature_names if feature_names else ["n/a"],
                colorscale="RdBu",
                zmid=0.0,
                colorbar=dict(title="Delta Weight"),
            )
        ]
    )
    heatmap_fig.update_layout(
        title="Feature Influence Matrix",
        margin=dict(l=0, r=0, t=40, b=0),
    )

    samples_seen = int(snapshot.get('samples_seen', 0) or 0)
    accuracy = float(snapshot.get('accuracy', 0.0) or 0.0)
    avg_loss = float(snapshot.get('avg_loss', 0.0) or 0.0)
    weighted_acc = float(snapshot.get('weighted_accuracy', 0.0) or 0.0)
    bus_val = html_mod.escape(str(snapshot.get('bus', 'memory')))

    summary_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 16px;">
      <h1 style="margin: 0 0 8px 0;">{safe_title}</h1>
      <p style="margin: 0 0 12px 0;">
        Samples: <b>{samples_seen}</b> |
        Accuracy: <b>{accuracy:.3f}</b> |
        Avg loss: <b>{avg_loss:.4f}</b> |
        Weighted acc: <b>{weighted_acc:.3f}</b> |
        Bus: <b>{bus_val}</b>
      </p>
      <p style="margin: 0 0 12px 0; color:#444;">
        Constraints: stability v2 / independence v2 / cross-source corroboration / source verification / intervention approximation are applied to edge confidence and the topology surface.
      </p>
    </div>
    """

    return "\n".join(
        [
            "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
            f"<title>{safe_title}</title>",
            "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>",
            "<style>body{margin:0;background:#fafafa;} .grid{display:grid;grid-template-columns:1fr;gap:18px;padding:16px;} .card{background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,0.08);padding:12px;}</style>",
            "</head><body>",
            summary_html,
            "<div class='grid'>",
            f"<div class='card'>{surface_fig.to_html(full_html=False, include_plotlyjs=False)}</div>",
            f"<div class='card'>{network_fig.to_html(full_html=False, include_plotlyjs=False)}</div>",
            f"<div class='card'>{heatmap_fig.to_html(full_html=False, include_plotlyjs=False)}</div>",
            "</div>",
            "</body></html>",
        ]
    )


def create_app(
    state_provider: Optional[Callable[[], Mapping[str, Any]]] = None,
    auth_token: Optional[str] = None,
    allow_origins: Optional[list] = None,
) -> FastAPI:
    """Create a hardened FastAPI dashboard application.

    Security features:
    - Security headers on all responses (CSP, X-Content-Type-Options, etc.)
    - CORS restricted to specified origins (default: localhost only)
    - Optional bearer token authentication
    - /api/snapshot returns redacted data (no internal graph details)
    - Cache-Control headers to prevent sensitive data caching
    - /ready endpoint for Kubernetes readiness probes

    Args:
        state_provider: Callable returning dashboard state. None for default.
        auth_token: Bearer token for API auth. If None, auth is disabled
            (development mode). Set TRUSTLINT_DASHBOARD_TOKEN env var for prod.
        allow_origins: CORS origins. Default: ["http://127.0.0.1", "http://localhost"].
    """
    if auth_token is None:
        auth_token = os.environ.get("TRUSTLINT_DASHBOARD_TOKEN")

    if allow_origins is None:
        allow_origins = ["http://127.0.0.1", "http://localhost"]

    app = FastAPI(
        title="SPL v7 Dashboard",
        docs_url=None,       # Disable /docs in production
        redoc_url=None,      # Disable /redoc in production
    )

    # CORS - restrict to known origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.plot.ly; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'"
        )
        # Prevent caching of sensitive dashboard data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    def _check_auth_header(authorization: Optional[str]) -> None:
        """Validate bearer token if auth is configured."""
        if auth_token is None:
            return  # Auth disabled (dev mode)
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        if not secrets.compare_digest(parts[1], auth_token):
            raise HTTPException(status_code=403, detail="Invalid token")

    def _state() -> Mapping[str, Any]:
        if state_provider is None:
            return {
                "graph": {
                    "nodes": [],
                    "edges": [],
                    "target": "decision",
                    "samples_seen": 0,
                    "accuracy": 0.0,
                    "avg_loss": 0.0,
                    "bus": "memory",
                }
            }
        return state_provider()

    def _redact_state(state: Mapping[str, Any]) -> Dict[str, Any]:
        """Return a redacted copy of state safe for external consumption.
        Strips internal graph topology and source registry details.
        """
        graph = state.get("graph", {})
        return {
            "samples_seen": graph.get("samples_seen", 0),
            "accuracy": graph.get("accuracy", 0.0),
            "avg_loss": graph.get("avg_loss", 0.0),
            "weighted_accuracy": graph.get("weighted_accuracy", 0.0),
            "bus": state.get("bus", "memory"),
        }

    @app.get("/", response_class=HTMLResponse)
    async def index(authorization: Optional[str] = Header(None)) -> HTMLResponse:
        _check_auth_header(authorization)
        state = _state()
        graph = state.get("graph", state)
        return HTMLResponse(build_dashboard_html(graph, title="SPL v7 Topology Dashboard"))

    @app.get("/api/snapshot")
    async def snapshot(authorization: Optional[str] = Header(None)) -> JSONResponse:
        _check_auth_header(authorization)
        state = _state()
        return JSONResponse(content=_redact_state(state))

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
        """Kubernetes readiness probe — returns 200 only when auth passes."""
        _check_auth_header(authorization)
        return {"status": "ready"}

    return app


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8420,
    auth_token: Optional[str] = None,
    state_provider: Optional[Callable[[], Mapping[str, Any]]] = None,
) -> None:
    """Launch the dashboard with uvicorn.

    Default binding is 127.0.0.1 (localhost only) for security.
    Override host to 0.0.0.0 only behind a reverse proxy.

    Args:
        host: Bind address. Default: 127.0.0.1 (localhost only).
        port: Listen port. Default: 8420.
        auth_token: Bearer token for API auth.
        state_provider: Callable returning dashboard state.
    """
    import uvicorn

    app = create_app(
        state_provider=state_provider,
        auth_token=auth_token,
    )
    uvicorn.run(app, host=host, port=port)


app = create_app()
