"""Project paths: repo root and shared data directory for exports."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Only aggregated metrics are written (no row-level / PII exports).
PCS_MAYOR_METRICS_CSV = DATA_DIR / "pcs_mayor_metrics.csv"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
