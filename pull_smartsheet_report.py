"""
Pull data from SmartSheets Report via API, deduplicate, and get counts by year.

Usage:
    1. Add SMARTSHEET_TOKEN to .env file
    2. python pull_smartsheet_report.py
"""

import os
import json
import requests
import csv
from collections import Counter
from dotenv import load_dotenv

load_dotenv()  # loads from .env file in the same directory

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

def analyze(records):
    """Deduplicate on SID Number, show counts by year."""
    
    # Find the right column names (they might vary)
    sample = records[0] if records else {}
    print(f"\nColumn names found: {list(sample.keys())}")
    
    # Try to find SID and date columns
    sid_col = None
    date_col = None
    for col in sample.keys():
        if "sid" in col.lower():
            sid_col = col
        if "created" in col.lower() or "date" in col.lower() or "registered" in col.lower():
            if not date_col:  # take the first match
                date_col = col
    
    print(f"Using SID column: {sid_col}")
    print(f"Using date column: {date_col}")
    
    if not sid_col:
        print("\nCouldn't auto-detect SID column. Here are the columns:")
        for i, col in enumerate(sample.keys()):
            print(f"  {i}: {col} (sample value: {sample[col]})")
        sid_col = input("Enter the SID column name: ").strip()
    
    if not date_col:
        print("\nCouldn't auto-detect date column. Here are the columns:")
        for i, col in enumerate(sample.keys()):
            print(f"  {i}: {col} (sample value: {sample[col]})")
        date_col = input("Enter the date column name: ").strip()
    
    # Extract year from date values
    def get_year(val):
        if val is None:
            return None
        val = str(val)
        # Try common date formats
        for fmt in ["%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                from datetime import datetime
                return datetime.strptime(val.split(" ")[0], fmt).year
            except:
                continue
        # Last resort: look for a 4-digit year
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
    print("DEDUPLICATED (first occurrence per SID Number)")
    print("="*50)
    seen_sids = set()
    deduped = []
    for r in records:
        sid = r.get(sid_col)
        if sid and sid not in seen_sids:
            seen_sids.add(sid)
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

def main():
    token = get_token()
    
    print(f"Fetching report {REPORT_ID}...")
    rows, column_map = fetch_report(token, REPORT_ID)
    
    if not rows:
        print("No data returned. Check your token and report ID.")
        return
    
    records = rows_to_dicts(rows, column_map)
    
    # Export full dataset to CSV
    export_to_csv(records, "full_export.csv")
    
    # Analyze and deduplicate
    deduped = analyze(records)
    
    # Export deduped dataset
    export_to_csv(deduped, "deduped_all_years.csv")

if __name__ == "__main__":
    main()