from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.semantic_adapter import run_semantic_detection

router = APIRouter(
    prefix="/api/v1/semantic",
    tags=["Semantic Understanding"]
)


class SemanticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[dict[str, Any]] = Field(min_length=1)
    quality: Any = None
    goal: str | None = None
    overrides: dict[str, Any] | None = None
    problem_type_override: Any = None
    quality_dataset: str | None = None
    quality_settings: dict[str, Any] | None = None
    approved_feature_columns: Any = None
    leakage_settings: dict[str, Any] | None = None


@router.post("/")
def semantic_detection(request: SemanticRequest):
    try:
        return run_semantic_detection(request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Semantic detection failed."
        )
