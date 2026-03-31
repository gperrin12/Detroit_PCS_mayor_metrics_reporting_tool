"""
Detroit PCS Mayor Metrics — Streamlit app (local + Streamlit Cloud).

Run locally:  streamlit run streamlit_app.py
Cloud: set Main file to streamlit_app.py and add SMARTSHEET_TOKEN in Secrets.

No row-level PII is written to disk; only aggregated metrics CSV after generate.
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
    "Click the button below to fetch the Smartsheet report and build the metrics table in one step "
    "(raw rows stay **in memory** only; only the aggregated metrics file is saved). "
    "On **Streamlit Community Cloud**, add `SMARTSHEET_TOKEN` under **App settings → Secrets**."
)

has_token = bool(os.environ.get("SMARTSHEET_TOKEN"))
if not has_token:
    st.warning("No `SMARTSHEET_TOKEN` in environment or secrets — the app cannot fetch data until it is set.")

if st.button(
    "Pull from Smartsheet and generate metrics",
    type="primary",
    disabled=not has_token,
):
    with st.spinner("Fetching report and computing metrics..."):
        ok, msg, records = run_pull_data()
        if not ok:
            st.session_state.pop(SESSION_RECORDS_KEY, None)
            st.error(msg)
        else:
            st.session_state[SESSION_RECORDS_KEY] = records
            try:
                run_generate_metrics(records)
                st.success(f"{msg} Saved `{PCS_MAYOR_METRICS_CSV.name}`.")
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
    st.caption(f"`{PCS_MAYOR_METRICS_CSV.name}` not yet created — run the button above.")
