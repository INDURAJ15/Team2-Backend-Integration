
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class DataQualityEngine:

    def __init__(
        self,
        file_path: str,
        dataset_name: str = "Dataset",
        numeric_columns: Optional[List[str]] = None,
        id_cols: Optional[List[str]] = None
    ):
        self.file_path = str(file_path)
        self.dataset_name = dataset_name
        self.numeric_columns = numeric_columns
        self.id_cols = id_cols or []

        self.na_markers = [
            "", " ", "NULL", "null", "N/A",
            "n/a", "None", "NaN"
        ]

        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:

        suffix = self.file_path.lower()

        if suffix.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(self.file_path)
            sheet = xls.sheet_names[0]

            return pd.read_excel(
                self.file_path,
                sheet_name=sheet,
                na_values=self.na_markers
            )

        elif suffix.endswith(".csv"):
            return pd.read_csv(
                self.file_path,
                na_values=self.na_markers
            )

        else:
            raise ValueError("Unsupported file format.")

    def run_validation(self) -> Dict[str, Any]:

        violations: List[Dict[str, Any]] = []
        total_rows = len(self.df)

        # 1. NULL CHECK - Team 1 logic
        null_counts = self.df.isnull().sum()

        for col, count in null_counts.items():

            if count > 0:
                violations.append({
                    "rule_id": "NULL_CHECK",
                    "column": str(col),
                    "severity": "HIGH",
                    "failed_count": int(count),
                    "description": (
                        f"Found {int(count)} null values "
                        f"in column {col}."
                    )
                })

        # 2. DUPLICATE ROW CHECK - Team 1 logic
        duplicate_count = int(self.df.duplicated().sum())

        if duplicate_count > 0:
            violations.append({
                "rule_id": "DUP_ROW",
                "column": "ALL_COLUMNS",
                "severity": "CRITICAL",
                "failed_count": duplicate_count,
                "description": (
                    f"Found {duplicate_count} completely "
                    "duplicated rows."
                )
            })

        # 3. INVALID RANGE CHECK - Existing Team 2 rule
        if "VacationHours" in self.df.columns:

            values = pd.to_numeric(
                self.df["VacationHours"],
                errors="coerce"
            )

            invalid_count = int(
                ((values < 0) | (values > 99)).sum()
            )

            if invalid_count > 0:
                violations.append({
                    "rule_id": "INVALID_RANGE",
                    "column": "VacationHours",
                    "severity": "MEDIUM",
                    "failed_count": invalid_count,
                    "description": (
                        "VacationHours values must be "
                        "between 0 and 99."
                    )
                })

        # 4. OUTLIER CHECK - Team 1 IQR logic
        if self.numeric_columns is not None:

            numeric_columns = [
                col for col in self.numeric_columns
                if col in self.df.columns
            ]

        else:
            numeric_columns = list(
                self.df.select_dtypes(
                    include=["number"]
                ).columns
            )

        for col in numeric_columns:

            # Skip identifier columns
            if col in self.id_cols:
                continue

            if "id" in str(col).lower():
                continue

            values = pd.to_numeric(
                self.df[col],
                errors="coerce"
            ).dropna()

            if len(values) < 4:
                continue

            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)

            outlier_count = int(
                (
                    (values < lower_bound) |
                    (values > upper_bound)
                ).sum()
            )

            if outlier_count > 0:
                violations.append({
                    "rule_id": "OUTLIER_IQR",
                    "column": str(col),
                    "severity": "MEDIUM",
                    "failed_count": outlier_count,
                    "description": (
                        f"Found {outlier_count} statistical "
                        "outliers using 1.5x IQR rule."
                    )
                })

        # 5. FINAL STATUS
        status = (
            "FAILED_VALIDATION"
            if violations
            else "PASSED"
        )

        return {
            "dataset_name": self.dataset_name,
            "execution_timestamp": datetime.now(
                timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "total_rows_scanned": total_rows,
            "status": status,
            "violations": violations
        }
