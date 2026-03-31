# Detroit PCS Mayor Metrics Reporting Tool

A reporting tool for Detroit PCS mayor metrics: pull a Smartsheet report and export **aggregated** mayor metrics as CSV only. **No row-level or identifiable export is written to disk**; raw rows exist only in memory during a run. Includes a **Streamlit** UI for local use and [Streamlit Community Cloud](https://streamlit.io/cloud).

## Layout

```
├── streamlit_app.py      # Streamlit entrypoint (set this on Cloud)
├── requirements.txt
├── data/                 # Outputs (gitignored except .gitkeep)
│   └── pcs_mayor_metrics.csv   # aggregated metrics only (no PII export)
└── analysis/
    ├── paths.py
    ├── pull_smartsheet_report.py
    └── generate_metrics_report.py
```

## Setup

1. Clone the repository and enter the project directory.

2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Local:** create a `.env` file in the project root with:

   ```
   SMARTSHEET_TOKEN=your_token_here
   ```

   Optionally copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set the token there for Streamlit (that file is gitignored).

## Streamlit app (local)

From the project root:

```bash
streamlit run streamlit_app.py
```

Use **Pull from Smartsheet and generate metrics** (one button: fetch + build metrics; row-level data is not persisted as CSV).

## Streamlit Community Cloud

1. Push this repo to GitHub and connect it in Streamlit Cloud.
2. **Main file:** `streamlit_app.py`
3. **Secrets:** App settings → Secrets, add:

   ```toml
   SMARTSHEET_TOKEN = "your_token_here"
   APP_PASSWORD = "shared_password_for_team"
   ```

   `APP_PASSWORD` is required to open the app when set (same value for everyone who should access it). Omit it only for local development without a login.

4. Deploy. Use the single **Pull from Smartsheet and generate metrics** action; only the metrics CSV is persisted under `data/` for that run.

## CLI (no UI)

Run from the **project root**:

```bash
python -m analysis.pull_smartsheet_report
```

This fetches the report, builds metrics **in memory**, and writes only `data/pcs_mayor_metrics.csv` (aggregated counts — no row-level or deduped CSV).

To build metrics from a **local CSV** (development only):

```bash
python -m analysis.generate_metrics_report --csv path/to/file.csv
```

### Metrics overview

- **Registered** — unique people (composite key) and row counts by Created year
- **Under Review / Open Files** — current pipeline snapshot on the latest year row only
- **Expunged / Denied** — Hearing Date year (with fallbacks)
- **Closed–ineligible, No MI convictions, etc.** — Case Close Date year (with fallbacks)
- **Expungement success rate** — expunged / (expunged + denied) by people count

## License

*TBD*
