"""Fresh API verification, including a real loopback HTTP server.

No key, request headers or response predictions are logged to the evidence file.
"""
import importlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from fastapi.testclient import TestClient
from analysis.config import ROOT, RESULTS
from .inference import ResearchModel

def verify():
    results = []
    key = secrets.token_urlsafe(32)
    previous = os.environ.get("OPENPLAY_DEMO_KEY")
    os.environ["OPENPLAY_DEMO_KEY"] = key
    from .service import create_app
    headers = {"X-API-Key": key}
    expected = ResearchModel()

    def check(name, condition):
        results.append({"check": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    try:
        with TestClient(create_app()) as client:
            response = client.get("/health", headers=headers)
            check("authenticated readiness", response.status_code == 200 and response.json()["ready"])
            for path in ("/health", "/metrics", "/predict"):
                method = client.post if path == "/predict" else client.get
                kwargs = {"json": {"example_id": "example_a"}} if path == "/predict" else {}
                check(f"missing key {path}", method(path, **kwargs).status_code == 401)
                check(f"wrong key {path}", method(path, headers={"X-API-Key": "wrong"}, **kwargs).status_code == 401)
            for name in ("example_a", "example_b", "example_c"):
                response = client.post("/predict", headers=headers, json={"example_id": name})
                check(f"real-model inference {name}", response.status_code == 200 and response.json() == expected.predict(name))
                check(f"no-store and request ID {name}", response.headers.get("Cache-Control") == "no-store" and bool(response.headers.get("X-Request-ID")))
            for name, body in (("unknown scenario", {"example_id": "unknown"}), ("missing field", {}),
                               ("extra field", {"example_id": "example_a", "participant": "fictional"}),
                               ("wrong field type", {"example_id": 1})):
                check(name, client.post("/predict", headers=headers, json=body).status_code == 422)
            response = client.get("/metrics", headers=headers)
            check("authenticated counters", response.status_code == 200 and response.json()["status_counts"].get("422", 0) >= 4)
            for path in ("/docs", "/redoc", "/openapi.json"):
                check(f"disabled {path}", client.get(path).status_code == 404)
            client.app.state.model = None
            check("not-ready model returns 503", client.post("/predict", headers=headers, json={"example_id": "example_a"}).status_code == 503)
        os.environ["OPENPLAY_DEMO_KEY"] = "short"
        try:
            create_app()
            check("short key refuses initialization", False)
        except RuntimeError:
            check("short key refuses initialization", True)
        os.environ["OPENPLAY_DEMO_KEY"] = key
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "deployment.service:app", "--host", "127.0.0.1",
                                 "--port", str(port), "--workers", "1", "--no-access-log", "--log-level", "warning"],
                                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            online = False
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers=headers, timeout=3) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        break
                    try:
                        online = client.get("/health").status_code == 200
                        if online:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                check("live loopback readiness", online)
                r = client.post("/predict", json={"example_id": "example_a"})
                check("live loopback prediction equals direct model", r.status_code == 200 and r.json() == expected.predict("example_a"))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    finally:
        if previous is None:
            os.environ.pop("OPENPLAY_DEMO_KEY", None)
        else:
            os.environ["OPENPLAY_DEMO_KEY"] = previous
        RESULTS.mkdir(exist_ok=True)
        record = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "checks": results,
                  "passed": sum(v["passed"] for v in results), "total": len(results),
                  "all_passed": bool(results) and all(v["passed"] for v in results),
                  "scope": "Functional checks, one loopback process. No cloud, HTTPS, uptime, load or penetration test."}
        (RESULTS / "api_verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"API checks: {record['passed']}/{record['total']}")

if __name__ == "__main__":
    verify()
