"""Project paths: repo root and shared data directory for exports."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

FULL_EXPORT_CSV = DATA_DIR / "full_export.csv"
DEDUPED_ALL_YEARS_CSV = DATA_DIR / "deduped_all_years.csv"
PCS_MAYOR_METRICS_CSV = DATA_DIR / "pcs_mayor_metrics.csv"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
