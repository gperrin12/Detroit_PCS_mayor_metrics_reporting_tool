"""
Detroit PCS Mayor Metrics — Streamlit app (local + Streamlit Cloud).

Run locally:  streamlit run streamlit_app.py
Cloud: set Main file to streamlit_app.py and add SMARTSHEET_TOKEN in Secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Streamlit Cloud: App settings → Secrets → TOML with SMARTSHEET_TOKEN = "..."
try:
    if "SMARTSHEET_TOKEN" in st.secrets:
        os.environ["SMARTSHEET_TOKEN"] = st.secrets["SMARTSHEET_TOKEN"]
except Exception:
    pass

from analysis.paths import FULL_EXPORT_CSV, PCS_MAYOR_METRICS_CSV
from analysis.pull_smartsheet_report import run_pull_data
from analysis.generate_metrics_report import run_generate_metrics

st.set_page_config(page_title="PCS Mayor Metrics", layout="wide")

st.title("Detroit PCS Mayor Metrics")

st.markdown(
    "Pull the Smartsheet report, then generate the metrics table. "
    "On **Streamlit Community Cloud**, add `SMARTSHEET_TOKEN` under **App settings → Secrets** "
    "(same as a `.env` entry locally)."
)

has_token = bool(os.environ.get("SMARTSHEET_TOKEN"))
if not has_token:
    st.warning("No `SMARTSHEET_TOKEN` in environment or secrets — pull will fail until it is set.")

c1, c2 = st.columns(2)

with c1:
    if st.button("Pull data from Smartsheet", type="primary", disabled=not has_token):
        with st.spinner("Fetching report..."):
            ok, msg = run_pull_data()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

with c2:
    if st.button("Generate metrics"):
        if not FULL_EXPORT_CSV.exists():
            st.error(f"Run **Pull data** first — missing `{FULL_EXPORT_CSV.name}`.")
        else:
            with st.spinner("Computing metrics..."):
                try:
                    run_generate_metrics()
                    st.success(f"Saved `{PCS_MAYOR_METRICS_CSV.name}`.")
                    st.rerun()
                except Exception as e:
                    st.exception(e)

st.divider()
st.subheader("Download files")

if FULL_EXPORT_CSV.exists():
    st.download_button(
        label=f"Download {FULL_EXPORT_CSV.name}",
        data=FULL_EXPORT_CSV.read_bytes(),
        file_name=FULL_EXPORT_CSV.name,
        mime="text/csv",
    )
else:
    st.caption(f"`{FULL_EXPORT_CSV.name}` not yet created.")

if PCS_MAYOR_METRICS_CSV.exists():
    st.download_button(
        label=f"Download {PCS_MAYOR_METRICS_CSV.name}",
        data=PCS_MAYOR_METRICS_CSV.read_bytes(),
        file_name=PCS_MAYOR_METRICS_CSV.name,
        mime="text/csv",
    )
    st.subheader("Metrics preview")
    st.dataframe(pd.read_csv(PCS_MAYOR_METRICS_CSV), use_container_width=True)
else:
    st.caption(f"`{PCS_MAYOR_METRICS_CSV.name}` not yet created.")
