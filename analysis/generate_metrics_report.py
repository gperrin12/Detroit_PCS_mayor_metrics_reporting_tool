"""
Generate PCS Mayor Metrics report from Smartsheet export data.

Builds pcs_mayor_metrics.csv from in-memory row data (preferred) or an optional
local CSV for development. Full row-level exports are not written by the pull
step to reduce PII exposure. Metrics include distinct people and row (case) counts.

People are identified by a composite key of SID Number + Primary (full name)
to handle rows where SID is missing or "BLANK".

Year attribution per metric:
  - Registered / Under Review / Open Files: Created year (registration date)
  - Expunged / Denied: Hearing Date year
  - Closed-Ineligible / No Michigan Convictions / No Client Response /
    Client Not Interested: Case Close Date year
  - Filed: **Filing Date** year (any sheet; row counts when that date is set)
  - Fallback chain when date is missing: sheet name year -> Created year
  - Year columns are clipped to 2016–2035 so bad parses (e.g. 1360, 1451) never appear.

Usage:
    python -m analysis.pull_smartsheet_report   # fetches, then builds metrics in memory
    python -m analysis.generate_metrics_report --csv path/to/file.csv   # dev only
"""

import argparse
import re
from pathlib import Path

import pandas as pd

from .paths import PCS_MAYOR_METRICS_CSV

OUTPUT_FILE = str(PCS_MAYOR_METRICS_CSV)

# Plausible calendar years for PCS mayor metrics (drops bad parses e.g. 1360, 1451).
REPORT_YEAR_MIN = 2016
REPORT_YEAR_MAX = 2035

UNDER_REVIEW_SHEETS = [
    "CM 0: Eligibility Review",
    "CM 0: ICHAT Updates",
    "CM 0: Pre-Eligibility",
    "CM 1: Row Opening",
    "CM 2: Attorney Review",
]

OPEN_FILES_SHEETS = [
    "CM 3: Waiting on Client and/or Records",
    "CM 4: File Review and Assembling Application",
    "CM 5: Application Filed",
    "CM 6: Waiting for Hearing Date",
    "CM 7: Hearing Scheduled",
]

DENIED_SHEETS = ["CM 9: Denied"]


def resolve_filing_date_column(df):
    """Return the Smartsheet column for filing date, or None."""
    for col in df.columns:
        if str(col).strip().lower() == "filing date":
            return col
    for col in df.columns:
        lc = str(col).lower()
        if "filing" in lc and "date" in lc:
            return col
    return None


def _invalidate_out_of_range_years(df):
    """Clear year values outside REPORT_YEAR_MIN..MAX (bad dates / junk)."""
    for col in (
        "created_year",
        "hearing_metric_year",
        "close_metric_year",
        "filed_metric_year",
    ):
        if col not in df.columns:
            continue
        s = df[col]
        bad = s.notna() & ((s < REPORT_YEAR_MIN) | (s > REPORT_YEAR_MAX))
        n_bad = int(bad.sum())
        if n_bad:
            df.loc[bad, col] = pd.NA
            print(
                f"Note: cleared {n_bad} out-of-range {col} values "
                f"(kept {REPORT_YEAR_MIN}–{REPORT_YEAR_MAX} only)."
            )


def extract_sheet_year(sheet_name):
    """Extract year from sheet name. Returns a single year int or None.

    Single-year sheets like "(2026)" return that year.
    Range sheets like "(2019-2022)" return None.
    """
    if pd.isna(sheet_name):
        return None
    if re.search(r"\d{4}\s*[-–]\s*\d{2,4}", sheet_name):
        return None
    match = re.search(r"(20\d{2})", sheet_name)
    return int(match.group(1)) if match else None


def load_data(source):
    """Load from CSV path, DataFrame, or list of row dicts (Smartsheet export shape)."""
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    elif isinstance(source, list):
        df = pd.DataFrame(source)
    else:
        df = pd.read_csv(Path(source))
    df["Created"] = pd.to_datetime(df["Created"], errors="coerce")
    df["created_year"] = df["Created"].dt.year

    sid = df["SID Number"].fillna("").astype(str).replace("BLANK", "")
    name = df["Primary"].fillna("").astype(str)
    df["person_key"] = sid + "|" + name

    df["sheet_year"] = df["Sheet Name"].apply(extract_sheet_year)

    has_hearing = "Hearing Date" in df.columns
    has_close = "Case Close Date" in df.columns

    if has_hearing:
        df["Hearing Date"] = pd.to_datetime(df["Hearing Date"], errors="coerce")
        df["hearing_year"] = df["Hearing Date"].dt.year
    else:
        df["hearing_year"] = pd.NA
        print("Warning: 'Hearing Date' column not found — falling back to sheet year / Created year")

    if has_close:
        df["Case Close Date"] = pd.to_datetime(df["Case Close Date"], errors="coerce")
        df["close_year"] = df["Case Close Date"].dt.year
    else:
        df["close_year"] = pd.NA
        print("Warning: 'Case Close Date' column not found — falling back to sheet year / Created year")

    fallback = df["sheet_year"].fillna(df["created_year"])
    df["hearing_metric_year"] = df["hearing_year"].fillna(fallback).astype("Int64")
    df["close_metric_year"] = df["close_year"].fillna(fallback).astype("Int64")

    filing_col = resolve_filing_date_column(df)
    if filing_col is not None:
        raw = df[filing_col]
        try:
            fd = pd.to_datetime(raw, errors="coerce", format="mixed")
        except (ValueError, TypeError):
            fd = pd.to_datetime(raw, errors="coerce")
        df["filed_metric_year"] = fd.dt.year.astype("Int64")
    else:
        df["filed_metric_year"] = pd.NA
        print(
            "Warning: no 'Filing Date' column found — "
            "filed_people / filed_rows will be empty."
        )

    _invalidate_out_of_range_years(df)

    return df


def people_count(df):
    """Distinct people by composite key (SID Number + Primary name)."""
    return df["person_key"].nunique()


def row_count(df):
    return len(df)


def compute_metrics_for_year(year, created_grp, hearing_grp, close_grp, filed_grp,
                             full_df=None):
    """Compute metrics using the appropriate year-grouped data for each metric.

    Under Review and Open Files are current-state pipeline snapshots (no year
    attribution), so they use the full unfiltered dataset when provided.
    """
    m = {}

    m["registered_people"] = people_count(created_grp)
    m["registered_rows"] = row_count(created_grp)

    if full_df is not None:
        under_review = full_df[full_df["Sheet Name"].isin(UNDER_REVIEW_SHEETS)]
        m["under_review_people"] = people_count(under_review)
        m["under_review_rows"] = row_count(under_review)

        open_files = full_df[full_df["Sheet Name"].isin(OPEN_FILES_SHEETS)]
        m["open_files_people"] = people_count(open_files)
        m["open_files_rows"] = row_count(open_files)
    else:
        m["under_review_people"] = None
        m["under_review_rows"] = None
        m["open_files_people"] = None
        m["open_files_rows"] = None

    # Hearing Date year metrics
    expunged = hearing_grp[hearing_grp["Sheet Name"].str.contains("CM 8", na=False)]
    m["expunged_people"] = people_count(expunged)
    m["expunged_rows"] = row_count(expunged)

    petition = expunged[expunged["Case Status"] == "Expunged"]
    m["expunged_petition_people"] = people_count(petition)
    m["expunged_petition_rows"] = row_count(petition)

    auto = expunged[expunged["Case Status"] == "Expunged Automatically"]
    m["expunged_auto_people"] = people_count(auto)
    m["expunged_auto_rows"] = row_count(auto)

    denied = hearing_grp[hearing_grp["Sheet Name"].isin(DENIED_SHEETS)]
    m["denied_people"] = people_count(denied)
    m["denied_rows"] = row_count(denied)

    # Filing Date year (any sheet)
    m["filed_people"] = people_count(filed_grp)
    m["filed_rows"] = row_count(filed_grp)

    # Case Close Date year metrics
    closed_ineligible = close_grp[
        close_grp["Sheet Name"].str.contains("CM 9: Ineligible", na=False)
        | close_grp["Sheet Name"].str.contains("CM 9: Active Warrant", na=False)
    ]
    m["closed_ineligible_people"] = people_count(closed_ineligible)
    m["closed_ineligible_rows"] = row_count(closed_ineligible)

    no_mi = close_grp[
        close_grp["Sheet Name"].str.contains("CM 9: No Michigan Convictions", na=False)
    ]
    m["no_michigan_convictions_people"] = people_count(no_mi)
    m["no_michigan_convictions_rows"] = row_count(no_mi)

    no_response = close_grp[
        close_grp["Sheet Name"].str.contains("CM 9: No Client Response", na=False)
    ]
    m["no_client_response_people"] = people_count(no_response)
    m["no_client_response_rows"] = row_count(no_response)

    not_interested = close_grp[
        close_grp["Sheet Name"].str.contains("CM 9: Client Not Interested", na=False)
    ]
    m["client_not_interested_people"] = people_count(not_interested)
    m["client_not_interested_rows"] = row_count(not_interested)

    exp = m["expunged_people"]
    den = m["denied_people"]
    if exp + den > 0:
        m["expungement_success_rate"] = round(exp / (exp + den), 4)
    else:
        m["expungement_success_rate"] = None

    return m


def main(source=None):
    if source is None:
        raise ValueError(
            "No data source. Pass row records from pull, or use --csv for local development."
        )
    df = load_data(source)
    print(f"Loaded {len(df):,} rows with {df['person_key'].nunique():,} unique people")
    print(f"Columns: {list(df.columns[:12])}")

    if "hearing_year" in df.columns:
        n = df["hearing_year"].notna().sum()
        print(f"Hearing Date populated: {n:,} / {len(df):,} rows")
    if "close_year" in df.columns:
        n = df["close_year"].notna().sum()
        print(f"Case Close Date populated: {n:,} / {len(df):,} rows")
    if "filed_metric_year" in df.columns and df["filed_metric_year"].notna().any():
        n = df["filed_metric_year"].notna().sum()
        print(f"Filing Date (year usable): {n:,} / {len(df):,} rows")

    all_years = sorted(
        set(df["created_year"].dropna().astype(int))
        | set(df["hearing_metric_year"].dropna().astype(int))
        | set(df["close_metric_year"].dropna().astype(int))
        | set(df["filed_metric_year"].dropna().astype(int))
    )

    if not all_years:
        print(
            "No in-range years (2016–2035) after sanitization; per-year rows omitted; "
            "totals row only."
        )
    latest_year = max(all_years) if all_years else None

    rows = []
    for year in all_years:
        year_int = int(year)
        created_grp = df[df["created_year"] == year]
        hearing_grp = df[df["hearing_metric_year"] == year]
        close_grp = df[df["close_metric_year"] == year]
        filed_grp = df[df["filed_metric_year"] == year]
        is_current = latest_year is not None and (year_int == latest_year)
        m = compute_metrics_for_year(
            year_int, created_grp, hearing_grp, close_grp, filed_grp,
            full_df=df if is_current else None,
        )
        m["year"] = year_int
        rows.append(m)
        print(f"  {year_int}: registered={m['registered_people']:,} people, "
              f"expunged={m['expunged_rows']:,} rows"
              + (f", under_review={m['under_review_rows']:,} (current pipeline)"
                 if is_current else ""))

    filed_total_grp = df[df["filed_metric_year"].notna()]
    totals = compute_metrics_for_year(
        "Total", df, df, df, filed_total_grp, full_df=df,
    )
    totals["year"] = "Total"
    rows.append(totals)

    column_order = [
        "year",
        "registered_people", "registered_rows",
        "under_review_people", "under_review_rows",
        "open_files_people", "open_files_rows",
        "expunged_people", "expunged_rows",
        "expunged_petition_people", "expunged_petition_rows",
        "expunged_auto_people", "expunged_auto_rows",
        "denied_people", "denied_rows",
        "filed_people", "filed_rows",
        "closed_ineligible_people", "closed_ineligible_rows",
        "no_michigan_convictions_people", "no_michigan_convictions_rows",
        "no_client_response_people", "no_client_response_rows",
        "client_not_interested_people", "client_not_interested_rows",
        "expungement_success_rate",
    ]

    result = pd.DataFrame(rows)[column_order]
    result.to_csv(OUTPUT_FILE, index=False)
    print(f"\nExported to {OUTPUT_FILE}")
    print(result.to_string(index=False))
    return result


def run_generate_metrics(source):
    """Build metrics table from row dicts, DataFrame, or path; return DataFrame."""
    return main(source=source)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build metrics CSV from a local CSV (development only)."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        metavar="PATH",
        help="Optional local CSV (not used in production; pull keeps data in memory).",
    )
    args = parser.parse_args()
    if not args.csv:
        parser.error(
            "Pass --csv PATH for a local file, or run "
            "`python -m analysis.pull_smartsheet_report` to fetch and generate metrics."
        )
    main(source=args.csv)
