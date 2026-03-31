"""
Detroit PCS Mayor Metrics — Streamlit app (local + Streamlit Cloud).

Run locally:  streamlit run streamlit_app.py
Cloud: set Main file to streamlit_app.py and add SMARTSHEET_TOKEN in Secrets.

Full row-level data is not written to disk; metrics are computed in memory after pull.
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

try:
    if "SMARTSHEET_TOKEN" in st.secrets:
        os.environ["SMARTSHEET_TOKEN"] = st.secrets["SMARTSHEET_TOKEN"]
except Exception:
    pass

from analysis.paths import PCS_MAYOR_METRICS_CSV
from analysis.pull_smartsheet_report import run_pull_data
from analysis.generate_metrics_report import run_generate_metrics

SESSION_RECORDS_KEY = "smartsheet_records"

st.set_page_config(page_title="PCS Mayor Metrics", layout="wide")

st.title("Detroit PCS Mayor Metrics")

st.markdown(
    "Pull the Smartsheet report (data stays **in memory** — no full export CSV), "
    "then generate the aggregated metrics table. "
    "On **Streamlit Community Cloud**, add `SMARTSHEET_TOKEN` under **App settings → Secrets**."
)

has_token = bool(os.environ.get("SMARTSHEET_TOKEN"))
if not has_token:
    st.warning("No `SMARTSHEET_TOKEN` in environment or secrets — pull will fail until it is set.")

c1, c2 = st.columns(2)

with c1:
    if st.button("Pull data from Smartsheet", type="primary", disabled=not has_token):
        with st.spinner("Fetching report..."):
            ok, msg, records = run_pull_data()
        if ok:
            st.session_state[SESSION_RECORDS_KEY] = records
            st.success(msg)
        else:
            st.session_state.pop(SESSION_RECORDS_KEY, None)
            st.error(msg)

with c2:
    if st.button("Generate metrics"):
        records = st.session_state.get(SESSION_RECORDS_KEY)
        if not records:
            st.error("Run **Pull data** first in this session (full export is not stored on disk).")
        else:
            with st.spinner("Computing metrics..."):
                try:
                    run_generate_metrics(records)
                    st.success(f"Saved `{PCS_MAYOR_METRICS_CSV.name}`.")
                    st.rerun()
                except Exception as e:
                    st.exception(e)

st.divider()
st.subheader("Download")

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
