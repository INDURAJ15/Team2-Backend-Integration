
from app.services.profiling_adapter import profile_sample_dataset
from app.services.quality_adapter import check_team1_data_quality
from app.services.semantic_adapter import run_semantic_detection


def run_dataset_services(
    dataset_source,
    dataset_id,
    request_id=None,
    dataset_name=None,
    options=None,
    metadata=None,
    target_col=None,
    id_cols=None
):
    options = options or {}
    metadata = metadata or {}

    effective_dataset_name = dataset_name or dataset_id

    dataset_context = {
        "dataset_id": dataset_id,
        "dataset_name": effective_dataset_name,
        "source_type": "file"
    }

    # 1. Profiling
    try:
        profiling_result = profile_sample_dataset(
            dataset_source=dataset_source,
            dataset_id=dataset_id,
            request_id=request_id,
            options=options,
            metadata={
                **metadata,
                "name": effective_dataset_name
            }
        )
    except Exception:
        profiling_result = {
            "status": "failed",
            "columns": [],
            "errors": [{
                "code": "PROFILING_SERVICE_ERROR",
                "message": "Profiling service execution failed."
            }]
        }

    profiling_status = str(
        profiling_result.get("status", "failed")
    ).lower()

    # 2. Numeric columns
    profiled_columns = profiling_result.get("columns", [])

    numeric_columns = [
        column["name"]
        for column in profiled_columns
        if column.get("inferred_type") == "numerical"
        and not column.get("likely_identifier", False)
    ]

    # 3. Team 1 Data Quality
    try:
        quality_result = check_team1_data_quality(
            dataset_source=dataset_source,
            dataset_name=effective_dataset_name,
            target_col=target_col,
            id_cols=id_cols,
            numeric_columns=numeric_columns
        )

    except Exception:
        quality_result = {
            "status": "FAILED_VALIDATION",
            "violations": [],
            "errors": [{
                "code": "QUALITY_SERVICE_ERROR",
                "message": "Data quality service execution failed."
            }]
        }

    quality_summary = quality_result.get("summary", {})

    quality_status_value = str(
        quality_result.get(
            "status",
            quality_summary.get("status", "FAILED_VALIDATION")
        )
    ).upper()

    if quality_result.get("errors"):
        quality_status = "failed"
    elif quality_status_value == "FAILED_VALIDATION":
        quality_status = "warning"
    elif quality_status_value in ("PASSED", "SUCCESS"):
        quality_status = "success"
    else:
        quality_status = "warning"

    # 4. Quality issue count
    quality_violations = quality_result.get("violations", [])

    quality_issue_count = sum(
        item.get("failed_count", 0)
        for item in quality_violations
    )

    # 5. Semantic Analysis
    if profiling_status != "failed":
        try:
            semantic_result = run_semantic_detection({
                "profiles": [profiling_result],
                "overrides": {
                    effective_dataset_name: target_col
                } if target_col else None
            })

            semantic_status = "success"

        except Exception as exc:
            semantic_result = {
                "status": "failed",
                "message": "Semantic Analysis execution failed.",
                "error": str(exc)
            }
            semantic_status = "failed"
    else:
        semantic_result = {
            "status": "skipped",
            "message": "Semantic Analysis skipped because Profiling failed."
        }
        semantic_status = "not_run"

    # 6. Overall status
    failed_count = sum([
        profiling_status == "failed",
        quality_status == "failed",
        semantic_status == "failed"
    ])

    if failed_count >= 2:
        overall_status = "failed"
    elif failed_count == 1:
        overall_status = "partial_success"
    elif "warning" in [profiling_status, quality_status]:
        overall_status = "warning"
    else:
        overall_status = "success"

    # 7. Combined response
    return {
        "dataset_context": dataset_context,
        "status": overall_status,

        "service_status": {
            "profiling": profiling_status,
            "quality": quality_status,
            "semantic_analysis": semantic_status
        },

        "downstream_context": {
            "profiling_output_available": profiling_status != "failed",
            "quality_findings_available": quality_status != "failed",
            "semantic_output_available": semantic_status == "success",
            "quality_issue_count": quality_issue_count
        },

        "profiling": profiling_result,
        "quality": quality_result,
        "semantic_analysis": semantic_result
    }
