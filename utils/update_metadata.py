#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Update company_metadata.csv with SP500 data."""
import csv
import re
from pathlib import Path


def parse_founding_year(founded_str):
    """
    Parse founding year from string.

    Examples:
        "1902" -> 1902
        "2013 (1888)" -> 1888 (use the older founding date)
        "1983 (1885)" -> 1885
    """
    if not founded_str or founded_str.strip() == "":
        return None

    # Extract all years from the string
    years = re.findall(r'\d{4}', str(founded_str))

    if not years:
        return None

    # Convert to integers and return the earliest (oldest) year
    years_int = [int(y) for y in years]
    return min(years_int)


def extract_country(location_str):
    """
    Extract country from headquarters location.

    Examples:
        "Saint Paul, Minnesota" -> "USA"
        "Dublin, Ireland" -> "Ireland"
        "London, United Kingdom" -> "United Kingdom"
    """
    if not location_str:
        return "Unknown"

    # Split by comma and get the last part
    parts = [p.strip() for p in location_str.split(',')]

    if len(parts) == 0:
        return "Unknown"

    last_part = parts[-1]

    # Map US states to USA
    us_states = {
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
        "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
        "New Hampshire", "New Jersey", "New Mexico", "New York",
        "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
        "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
        "West Virginia", "Wisconsin", "Wyoming"
    }

    if last_part in us_states:
        return "USA"

    return last_part


def main():
    """Main function to update company metadata."""
    project_root = Path(__file__).parent.parent
    sp500_file = project_root / "sp500.csv"
    metadata_file = project_root / "data" / "company_metadata.csv"

    print(f"Reading SP500 data from: {sp500_file}")
    print(f"Reading existing metadata from: {metadata_file}")

    # Read existing metadata
    existing_data = {}
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['ticker']
                existing_data[ticker] = row

    print(f"Found {len(existing_data)} existing entries in metadata")

    # Read SP500 data
    new_entries = []
    updated_count = 0
    skipped_count = 0

    with open(sp500_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row['Symbol']
            company_name = row['Security']
            founded_year = parse_founding_year(row['Founded'])
            country = extract_country(row['Headquarters Location'])

            if founded_year is None:
                print(f"  Skipping {ticker} ({company_name}): No valid founding year")
                skipped_count += 1
                continue

            # Check if already exists
            if ticker in existing_data:
                # Update if founding year is different
                if int(existing_data[ticker]['founding_year']) != founded_year:
                    print(f"  Updating {ticker}: {existing_data[ticker]['founding_year']} -> {founded_year}")
                    existing_data[ticker]['founding_year'] = founded_year
                    updated_count += 1
            else:
                # Add new entry
                new_entry = {
                    'ticker': ticker,
                    'company_name': company_name,
                    'founding_year': founded_year,
                    'country': country,
                    'index': 'SP500',
                    'notes': ''
                }
                existing_data[ticker] = new_entry
                new_entries.append(ticker)
                print(f"  Adding {ticker} ({company_name}, founded {founded_year}, {country})")

    print(f"\nSummary:")
    print(f"  New entries added: {len(new_entries)}")
    print(f"  Existing entries updated: {updated_count}")
    print(f"  Skipped (no founding year): {skipped_count}")
    print(f"  Total entries: {len(existing_data)}")

    # Write updated metadata
    print(f"\nWriting updated metadata to: {metadata_file}")

    with open(metadata_file, 'w', newline='') as f:
        fieldnames = ['ticker', 'company_name', 'founding_year', 'country', 'index', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Sort by ticker for consistency
        for ticker in sorted(existing_data.keys()):
            writer.writerow(existing_data[ticker])

    print("Done!")


if __name__ == "__main__":
    main()
