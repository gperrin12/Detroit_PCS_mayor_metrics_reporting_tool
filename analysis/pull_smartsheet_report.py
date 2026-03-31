"""
Pull data from SmartSheets Report via API, deduplicate, and get counts by year.

Usage:
    1. Add SMARTSHEET_TOKEN to .env (repo root) or Streamlit secrets
    2. python -m analysis.pull_smartsheet_report
       (from repo root)
"""

import os
import json
import requests
import csv
from collections import Counter
from dotenv import load_dotenv

from .paths import REPO_ROOT, ensure_data_dir, DEDUPED_ALL_YEARS_CSV

load_dotenv(REPO_ROOT / ".env")

REPORT_ID = "8843647500898180"

def get_token():
    token = os.environ.get("SMARTSHEET_TOKEN")
    if not token:
        raise ValueError("SMARTSHEET_TOKEN not found. Add it to the .env file.")
    return token

def fetch_report(token, report_id, page_size=10000):
    """Fetch all rows from a SmartSheet report, handling pagination."""
    base_url = f"https://api.smartsheet.com/2.0/reports/{report_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_rows = []
    column_map = {}
    page = 1
    total_row_count = None
    
    while True:
        params = {"pageSize": page_size, "page": page}
        print(f"Fetching page {page}...")
        
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None, None
        
        data = response.json()
        
        if not column_map:
            for col in data.get("columns", []):
                column_map[col["virtualId"]] = col["title"]
            print(f"Found {len(column_map)} columns: {list(column_map.values())}")
        
        rows = data.get("rows", [])
        if not rows:
            break
        
        all_rows.extend(rows)
        
        total_row_count = data.get("totalRowCount", total_row_count)
        total_pages = data.get("totalPages", None)
        print(f"  Got {len(rows)} rows (total so far: {len(all_rows)}"
              f"{f' of {total_row_count}' if total_row_count else ''})")
        
        # Stop if: we've hit totalPages, or fetched all rows, or got a partial page
        if total_pages and page >= total_pages:
            break
        if total_row_count and len(all_rows) >= total_row_count:
            break
        if len(rows) < page_size:
            break
        
        page += 1
    
    print(f"\nDone! Fetched {len(all_rows)} total rows across {page} page(s).")
    return all_rows, column_map

def rows_to_dicts(rows, column_map):
    """Convert SmartSheet rows to list of dicts."""
    records = []
    for row in rows:
        record = {}
        for cell in row.get("cells", []):
            col_name = column_map.get(cell.get("virtualColumnId"), "Unknown")
            record[col_name] = cell.get("displayValue") or cell.get("value")
        records.append(record)
    return records

def export_to_csv(records, filename="smartsheet_export.csv"):
    """Export records to CSV."""
    if not records:
        print("No records to export.")
        return
    
    fieldnames = list(records[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported {len(records)} rows to {filename}")

def make_person_key(record):
    """Build composite key from SID Number + Primary (full name).

    Treats null and "BLANK" SID values the same so people without
    a valid SID are still distinguished by name.
    """
    sid = record.get("SID Number") or ""
    if sid == "BLANK":
        sid = ""
    name = record.get("Primary") or ""
    return f"{sid}|{name}"


def analyze(records):
    """Deduplicate on person key (SID Number + Primary), show counts by year."""

    sample = records[0] if records else {}
    print(f"\nColumn names found: {list(sample.keys())}")

    date_col = "Created"
    if date_col not in sample:
        for col in sample.keys():
            if "created" in col.lower():
                date_col = col
                break
    print(f"Using date column: {date_col}")

    def get_year(val):
        if val is None:
            return None
        val = str(val)
        for fmt in ["%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                from datetime import datetime
                return datetime.strptime(val.split(" ")[0], fmt).year
            except Exception:
                continue
        import re
        match = re.search(r"20\d{2}", val)
        if match:
            return int(match.group())
        return None

    # --- All records (with dupes) ---
    print("\n" + "="*50)
    print("ALL RECORDS (before dedup)")
    print("="*50)
    year_counts_all = Counter()
    for r in records:
        year = get_year(r.get(date_col))
        year_counts_all[year] += 1

    for year in sorted(k for k in year_counts_all if k is not None):
        print(f"  {year}: {year_counts_all[year]:,}")
    if None in year_counts_all:
        print(f"  Unknown year: {year_counts_all[None]:,}")
    print(f"  TOTAL: {sum(year_counts_all.values()):,}")

    # --- Deduplicated ---
    print("\n" + "="*50)
    print("DEDUPLICATED (first occurrence per person key)")
    print("="*50)
    seen_keys = set()
    deduped = []
    for r in records:
        key = make_person_key(r)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(r)

    year_counts_deduped = Counter()
    for r in deduped:
        year = get_year(r.get(date_col))
        year_counts_deduped[year] += 1

    for year in sorted(k for k in year_counts_deduped if k is not None):
        print(f"  {year}: {year_counts_deduped[year]:,}")
    if None in year_counts_deduped:
        print(f"  Unknown year: {year_counts_deduped[None]:,}")
    print(f"  TOTAL: {sum(year_counts_deduped.values()):,}")

    # --- 2026 specifically ---
    print("\n" + "="*50)
    print("2026 ONLY (deduplicated)")
    print("="*50)
    count_2026 = year_counts_deduped.get(2026, 0)
    print(f"  2026 deduplicated count: {count_2026:,}")

    return deduped

def run_pull_data(token=None, report_id=None):
    """Fetch report, export deduped CSV only (no full row-level export — PII).

    Returns (success, message, records_or_none). ``records`` is the full list of
    row dicts for in-memory metrics generation; it is not written to disk.
    """
    load_dotenv(REPO_ROOT / ".env")
    token = token or get_token()
    report_id = report_id or REPORT_ID
    ensure_data_dir()

    rows, column_map = fetch_report(token, report_id)
    if not rows:
        return False, "No data returned. Check your token and report ID.", None

    records = rows_to_dicts(rows, column_map)
    deduped = analyze(records)
    export_to_csv(deduped, str(DEDUPED_ALL_YEARS_CSV))

    msg = (
        f"Fetched {len(records):,} rows (not saved as full export). "
        f"Exported {len(deduped):,} deduped rows to {DEDUPED_ALL_YEARS_CSV.name}."
    )
    return True, msg, records


def main():
    print(f"Fetching report {REPORT_ID}...")
    ok, msg, records = run_pull_data()
    print(msg if ok else msg)
    if not ok:
        raise SystemExit(1)
    if records:
        from .generate_metrics_report import run_generate_metrics

        run_generate_metrics(records)
        print("Metrics CSV written.")


if __name__ == "__main__":
    main()