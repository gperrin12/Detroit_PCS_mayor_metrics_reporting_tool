# Detroit PCS Mayor Metrics Reporting Tool

A reporting tool for Detroit PCS mayor metrics: pull a Smartsheet report, deduplicate, and export mayor metrics as CSV. **Full row-level data is not written to disk** (PII); metrics are built in memory after each pull. Includes a **Streamlit** UI for local use and [Streamlit Community Cloud](https://streamlit.io/cloud).

## Layout

```
├── streamlit_app.py      # Streamlit entrypoint (set this on Cloud)
├── requirements.txt
├── data/                 # Outputs (gitignored except .gitkeep)
│   ├── deduped_all_years.csv   # optional deduped export from pull
│   └── pcs_mayor_metrics.csv   # aggregated metrics only
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

Use **Pull from Smartsheet and generate metrics** (one button: fetch + build metrics; rows stay in session memory only). There is no download for a full raw export.

## Streamlit Community Cloud

1. Push this repo to GitHub and connect it in Streamlit Cloud.
2. **Main file:** `streamlit_app.py`
3. **Secrets:** App settings → Secrets, add:

   ```toml
   SMARTSHEET_TOKEN = "your_token_here"
   ```

4. Deploy. Use the single **Pull from Smartsheet and generate metrics** action; only the metrics CSV is persisted under `data/` for that run.

## CLI (no UI)

Run from the **project root**:

```bash
python -m analysis.pull_smartsheet_report
```

This fetches the report, writes `data/deduped_all_years.csv`, builds metrics **in memory**, and writes `data/pcs_mayor_metrics.csv`. It does **not** write a full row-level CSV.

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
