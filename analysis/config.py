"""Project paths and fixed study definitions; no user-specific paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "eb0a68c1a7ca1fad54e57a1f89b9d5450f8be840"
RAW = f"https://raw.githubusercontent.com/digital-wellbeing/open-play/{COMMIT}/"
DATA = ROOT / "data" / "clean"
RESULTS = ROOT / "results"
MODELS = ROOT / "models"
F = ["baseline", "weekly_hours", "active_days", "sd_minutes", "max_minutes", "week_change"]
GDT = {label: n for n, label in enumerate(["Never", "Rarely", "Sometimes", "Often", "Very often"], 1)}

def prepare_dirs():
    for p in (DATA, RESULTS, MODELS, ROOT / "data/derived", ROOT / "docs/reference/provider"):
        p.mkdir(parents=True, exist_ok=True)
