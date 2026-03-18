"""
Generate PCS Mayor Metrics report from Smartsheet export data.

Reads full_export.csv and produces pcs_mayor_metrics.csv with per-year counts
for both distinct people (SID Number) and rows (cases).

Usage:
    python generate_metrics_report.py
"""

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


def load_data(path):
    df = pd.read_csv(path)
    df["Created"] = pd.to_datetime(df["Created"])
    df["year"] = df["Created"].dt.year
    return df


def people_count(df):
    """Distinct SID Numbers (excludes nulls)."""
    return df["SID Number"].nunique()


def row_count(df):
    return len(df)


def compute_metrics_for_group(group):
    """Compute all metrics for a single year group (or the full DataFrame for totals)."""
    metrics = {}

    metrics["registered_people"] = people_count(group)
    metrics["registered_rows"] = row_count(group)

    under_review = group[group["Sheet Name"].isin(UNDER_REVIEW_SHEETS)]
    metrics["under_review_people"] = people_count(under_review)
    metrics["under_review_rows"] = row_count(under_review)

    open_files = group[group["Sheet Name"].isin(OPEN_FILES_SHEETS)]
    metrics["open_files_people"] = people_count(open_files)
    metrics["open_files_rows"] = row_count(open_files)

    expunged = group[group["Sheet Name"].str.contains("CM 8", na=False)]
    metrics["expunged_people"] = people_count(expunged)
    metrics["expunged_rows"] = row_count(expunged)

    petition = expunged[expunged["Case Status"] == "Expunged"]
    metrics["expunged_petition_people"] = people_count(petition)
    metrics["expunged_petition_rows"] = row_count(petition)

    auto = expunged[expunged["Case Status"] == "Expunged Automatically"]
    metrics["expunged_auto_people"] = people_count(auto)
    metrics["expunged_auto_rows"] = row_count(auto)

    denied = group[group["Sheet Name"].isin(DENIED_SHEETS)]
    metrics["denied_people"] = people_count(denied)
    metrics["denied_rows"] = row_count(denied)

    closed_ineligible = group[
        group["Sheet Name"].str.contains("CM 9: Ineligible", na=False)
        | group["Sheet Name"].str.contains("CM 9: Active Warrant", na=False)
    ]
    metrics["closed_ineligible_people"] = people_count(closed_ineligible)
    metrics["closed_ineligible_rows"] = row_count(closed_ineligible)

    no_mi = group[
        group["Sheet Name"].str.contains("CM 9: No Michigan Convictions", na=False)
    ]
    metrics["no_michigan_convictions_people"] = people_count(no_mi)
    metrics["no_michigan_convictions_rows"] = row_count(no_mi)

    no_response = group[
        group["Sheet Name"].str.contains("CM 9: No Client Response", na=False)
    ]
    metrics["no_client_response_people"] = people_count(no_response)
    metrics["no_client_response_rows"] = row_count(no_response)

    not_interested = group[
        group["Sheet Name"].str.contains("CM 9: Client Not Interested", na=False)
    ]
    metrics["client_not_interested_people"] = people_count(not_interested)
    metrics["client_not_interested_rows"] = row_count(not_interested)

    exp = metrics["expunged_people"]
    den = metrics["denied_people"]
    if exp + den > 0:
        metrics["expungement_success_rate"] = round(exp / (exp + den), 4)
    else:
        metrics["expungement_success_rate"] = None

    return metrics


def main():
    df = load_data(INPUT_FILE)
    print(f"Loaded {len(df):,} rows with {df['SID Number'].nunique():,} unique SIDs")

    rows = []
    for year in sorted(df["year"].dropna().unique()):
        year_int = int(year)
        group = df[df["year"] == year]
        metrics = compute_metrics_for_group(group)
        metrics["year"] = year_int
        rows.append(metrics)
        print(f"  {year_int}: {metrics['registered_people']:,} people, "
              f"{metrics['registered_rows']:,} rows")

    totals = compute_metrics_for_group(df)
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
