# Detroit PCS Mayor Metrics Reporting Tool

A reporting tool for Detroit PCS mayor metrics: pull a Smartsheet report, deduplicate, and export mayor metrics as CSV. Includes a **Streamlit** UI for local use and [Streamlit Community Cloud](https://streamlit.io/cloud).

## Layout

```
├── streamlit_app.py      # Streamlit entrypoint (set this on Cloud)
├── requirements.txt
├── data/                 # Exported CSVs (gitignored except .gitkeep)
│   ├── full_export.csv
│   ├── deduped_all_years.csv
│   └── pcs_mayor_metrics.csv
└── analysis/
    ├── paths.py          # Shared paths to data/
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

Use the buttons to pull data and generate metrics. CSVs are written under `data/`.

## Streamlit Community Cloud

1. Push this repo to GitHub and connect it in Streamlit Cloud.
2. **Main file:** `streamlit_app.py`
3. **Secrets:** App settings → Secrets, add:

   ```toml
   SMARTSHEET_TOKEN = "your_token_here"
   ```

4. Deploy. Ephemeral filesystem: pull + generate work for the session; downloads use the in-memory file contents from `data/` during the app run.

## CLI (no UI)

Run from the **project root** so imports resolve:

```bash
python -m analysis.pull_smartsheet_report
python -m analysis.generate_metrics_report
```

The first command fetches the report and writes `data/full_export.csv` and `data/deduped_all_years.csv`. The second reads `data/full_export.csv` and writes `data/pcs_mayor_metrics.csv`.

### Metrics overview

- **Registered** — unique people (composite key) and row counts by Created year
- **Under Review / Open Files** — current pipeline snapshot on the latest year row only
- **Expunged / Denied** — Hearing Date year (with fallbacks)
- **Closed–ineligible, No MI convictions, etc.** — Case Close Date year (with fallbacks)
- **Expungement success rate** — expunged / (expunged + denied) by people count

## License

*TBD*
