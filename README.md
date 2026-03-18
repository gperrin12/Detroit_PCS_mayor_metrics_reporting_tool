# Detroit PCS Mayor Metrics Reporting Tool

A reporting tool for Detroit PCS mayor metrics.

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Detroit_PCS_mayor_metrics_reporting_tool
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Pull data from Smartsheet

```bash
python pull_smartsheet_report.py
```

Fetches the full report via the Smartsheet API (requires `SMARTSHEET_TOKEN` in `.env`) and exports `full_export.csv`.

### 2. Generate metrics report

```bash
python generate_metrics_report.py
```

Reads `full_export.csv` and produces `pcs_mayor_metrics.csv` with per-year breakdowns of:

- **Registered** -- all unique people (SID) and total rows
- **Under Review** -- CM 0/1/2 sheet names
- **Open Files** -- CM 3-7 sheet names
- **Expunged** (total, by petition, automatically) -- CM 8 sheet names
- **Denied** -- CM 9: Denied
- **Closed - Ineligible** -- CM 9: Ineligible / Active Warrant sheet names
- **No Michigan Convictions** -- CM 9: No Michigan Convictions sheet names
- **Expungement Success Rate** -- expunged / (expunged + denied)

Each metric is reported as both a people count (distinct SID) and a row count (total cases).

## License

*TBD*
