"""
Generate PCS Mayor Metrics report from Smartsheet export data.

Reads full_export.csv and produces pcs_mayor_metrics.csv with per-year counts
for both distinct people and rows (cases).

People are identified by a composite key of SID Number + Primary (full name)
to handle rows where SID is missing or "BLANK".

Year attribution per metric:
  - Registered / Under Review / Open Files: Created year (registration date)
  - Expunged / Denied: Hearing Date year
  - Closed-Ineligible / No Michigan Convictions / No Client Response /
    Client Not Interested: Case Close Date year
  - Fallback chain when date is missing: sheet name year -> Created year

Usage:
    python generate_metrics_report.py
"""

import re
import pandas as pd

INPUT_FILE = "full_export.csv"
OUTPUT_FILE = "pcs_mayor_metrics.csv"

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


def load_data(path):
    df = pd.read_csv(path)
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

    return df


def people_count(df):
    """Distinct people by composite key (SID Number + Primary name)."""
    return df["person_key"].nunique()


def row_count(df):
    return len(df)


def compute_metrics_for_year(year, created_grp, hearing_grp, close_grp):
    """Compute metrics using the appropriate year-grouped data for each metric."""
    m = {}

    m["registered_people"] = people_count(created_grp)
    m["registered_rows"] = row_count(created_grp)

    under_review = created_grp[created_grp["Sheet Name"].isin(UNDER_REVIEW_SHEETS)]
    m["under_review_people"] = people_count(under_review)
    m["under_review_rows"] = row_count(under_review)

    open_files = created_grp[created_grp["Sheet Name"].isin(OPEN_FILES_SHEETS)]
    m["open_files_people"] = people_count(open_files)
    m["open_files_rows"] = row_count(open_files)

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


def main():
    df = load_data(INPUT_FILE)
    print(f"Loaded {len(df):,} rows with {df['person_key'].nunique():,} unique people")
    print(f"Columns: {list(df.columns[:12])}")

    if "hearing_year" in df.columns:
        n = df["hearing_year"].notna().sum()
        print(f"Hearing Date populated: {n:,} / {len(df):,} rows")
    if "close_year" in df.columns:
        n = df["close_year"].notna().sum()
        print(f"Case Close Date populated: {n:,} / {len(df):,} rows")

    all_years = sorted(
        set(df["created_year"].dropna().astype(int))
        | set(df["hearing_metric_year"].dropna().astype(int))
        | set(df["close_metric_year"].dropna().astype(int))
    )

    rows = []
    for year in all_years:
        year_int = int(year)
        created_grp = df[df["created_year"] == year]
        hearing_grp = df[df["hearing_metric_year"] == year]
        close_grp = df[df["close_metric_year"] == year]
        m = compute_metrics_for_year(year_int, created_grp, hearing_grp, close_grp)
        m["year"] = year_int
        rows.append(m)
        print(f"  {year_int}: registered={m['registered_people']:,} people, "
              f"expunged={m['expunged_rows']:,} rows")

    totals = compute_metrics_for_year("Total", df, df, df)
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


if __name__ == "__main__":
    main()
