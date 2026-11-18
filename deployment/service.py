"""Loopback FastAPI prototype; start with OPENPLAY_DEMO_KEY set."""
import json
import logging
import os
import secrets
import time
from collections import Counter, deque
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from .inference import ResearchModel

logger = logging.getLogger("openplay.request")

class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    example_id: Literal["example_a", "example_b", "example_c"]

def create_app(model_dir=None):
    credential = os.environ.get("OPENPLAY_DEMO_KEY", "")
    if len(credential) < 24:
        raise RuntimeError("OPENPLAY_DEMO_KEY must contain at least 24 characters")

    @asynccontextmanager
    async def lifespan(app):
        app.state.model = ResearchModel(model_dir)
        yield
        app.state.model = None

    app = FastAPI(title="Open Play local research demo", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.model = None
    app.state.counts = Counter()
    app.state.latencies = deque(maxlen=1000)

    def authorized(x_api_key: str | None = Header(default=None)):
        if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), credential.encode()):
            raise HTTPException(401, "Invalid API key")

    def ready():
        if app.state.model is None:
            raise HTTPException(503, "Model not ready")
        return app.state.model

    @app.middleware("http")
    async def monitor(request, call_next):
        request_id = uuid4().hex
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            app.state.counts[str(status)] += 1
            app.state.latencies.append(elapsed)
            event = {"request_id": request_id, "status": status, "elapsed_ms": round(elapsed, 3),
                     "model_version": getattr(app.state.model, "version", "not-ready")}
            logger.log(logging.ERROR if status >= 500 else logging.INFO, json.dumps(event))

    access = [Depends(authorized)]

    @app.get("/health", dependencies=access)
    def health(model=Depends(ready)):
        return {"ready": True, "model_version": model.version}

    @app.post("/predict", dependencies=access)
    def predict(body: Scenario, model=Depends(ready)):
        return model.predict(body.example_id)

    @app.get("/metrics", dependencies=access)
    def metrics():
        return {"status_counts": dict(app.state.counts),
                "latency_p95_ms": float(np.quantile(list(app.state.latencies), .95)) if app.state.latencies else 0.,
                "latency_window": len(app.state.latencies), "scope": "single-process, in-memory, resets on restart"}

    return app

app = create_app()
