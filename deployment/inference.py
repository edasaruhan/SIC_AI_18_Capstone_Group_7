"""Single inference implementation shared by Streamlit and FastAPI."""
import json
from functools import lru_cache
import joblib
import pandas as pd
import sklearn
from analysis.config import ROOT, COMMIT, F
from analysis.download import sha256

SCENARIOS = {
    "example_a": dict(zip(F, [8, 12, 10, 90, 300, 2])),
    "example_b": dict(zip(F, [12, 12, 10, 90, 300, 2])),
    "example_c": dict(zip(F, [8, 24, 10, 90, 300, 2])),
}
NOTICE = "Synthetic research example; not a diagnosis or alert."

class ResearchModel:
    def __init__(self, model_dir=None):
        directory = model_dir or ROOT / "models"
        manifest = json.loads((directory / "manifest.json").read_text())
        path = directory / manifest["artifact"]
        # Never accept a path or serialized model from an HTTP/UI request.
        if path.resolve().parent != directory.resolve() or path.suffix != ".joblib":
            raise ValueError("Invalid artifact path")
        if sha256(path) != manifest["sha256"]:
            raise ValueError("Model checksum mismatch")
        if sklearn.__version__ != manifest["versions"]["scikit-learn"]:
            raise ValueError("Model requires matching scikit-learn version")
        # Only the artifact generated locally by analysis.train is trusted here.
        bundle = joblib.load(path)
        if bundle["features"] != manifest["features"] or bundle["data_commit"] != COMMIT:
            raise ValueError("Model metadata mismatch")
        if bundle["model_version"] != manifest["model_version"] or bundle["features"] != [str(v) for v in bundle["model"].feature_names_in_]:
            raise ValueError("Model feature schema mismatch")
        if not set(bundle["features"]) <= set(F):
            raise ValueError("Unsupported feature set")
        self.bundle = bundle
        self.manifest = manifest
        self.version = bundle["model_version"]

    def predict(self, example_id):
        if example_id not in SCENARIOS:
            raise ValueError("Unknown synthetic scenario")
        row = SCENARIOS[example_id]
        columns = self.bundle["features"]
        for c in columns:
            lo, hi = self.manifest["training_ranges"][c]
            if not lo <= row[c] <= hi:
                raise ValueError("Synthetic scenario outside training range")
        frame = pd.DataFrame([row])[columns]
        total = float(self.bundle["model"].predict(frame)[0])
        return {"example_id": example_id, "predicted_gdt_total": round(total, 4),
                "predicted_change": round(total - row["baseline"], 4),
                "model_version": self.version, "notice": NOTICE}

@lru_cache(maxsize=1)
def get_model():
    return ResearchModel()
