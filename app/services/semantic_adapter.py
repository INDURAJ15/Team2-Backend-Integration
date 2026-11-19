
import sys
from pathlib import Path

ENGINE_PATH = Path(__file__).resolve().parent / "semantic_engine"

if not ENGINE_PATH.exists():
    raise RuntimeError("Semantic engine folder not found.")

if str(ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ENGINE_PATH))

from run_detection import run_detection


def run_semantic_detection(payload: dict):
    profiles = payload.get("profiles")

    if not isinstance(profiles, list) or not profiles:
        raise ValueError("At least one profiling report is required.")

    allowed = {
        "quality",
        "goal",
        "overrides",
        "problem_type_override",
        "quality_dataset",
        "quality_settings",
        "approved_feature_columns",
        "leakage_settings"
    }

    options = {
        key: value
        for key, value in payload.items()
        if key in allowed and value is not None
    }

    return run_detection(profiles=profiles, **options)
