#!/usr/bin/env python3
"""
Convert a fellowship rotation schedule CSV into a Google Calendar import CSV.

The source schedule is expected to have one row per calendar day, standard date
columns such as BLOCK/MONTH/DATE/DAY, and one column per fellow.
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_START_DATE = "2026-07-01"
DATE_COLUMNS = {"BLOCK", "MONTH", "DATE", "DAY", "KEY"}
INPUT_ENCODINGS = ("utf-8-sig", "cp1252", "mac_roman", "latin-1")


def normalize(text):
    """Normalize text for matching column headers and schedule values."""
    return (text or "").replace("\xa0", " ").strip()


def normalize_for_match(text):
    """Normalize names for forgiving user input."""
    text = normalize(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def fellow_columns(headers):
    """Return schedule columns that appear to be fellow names."""
    return [header for header in headers if normalize(header).upper() not in DATE_COLUMNS]


def find_column(headers, requested_name):
    """Find a fellow column by exact, partial, or token-based match."""
    requested = normalize_for_match(requested_name)
    if not requested:
        return None

    candidates = fellow_columns(headers)
    normalized = {header: normalize_for_match(header) for header in candidates}

    for header, value in normalized.items():
        if value == requested:
            return header

    partial_matches = [
        header
        for header, value in normalized.items()
        if requested in value.split() or requested in value
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    requested_tokens = set(requested.split())
    token_matches = [
        header
        for header, value in normalized.items()
        if requested_tokens and requested_tokens.issubset(set(value.split()))
    ]
    if len(token_matches) == 1:
        return token_matches[0]

    return None


def prompt_with_default(prompt, default):
    """Prompt user and return default if they press Enter."""
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def clean_path_input(path_text):
    """Handle paths pasted from Terminal/Finder with quotes or backslash escapes."""
    path_text = path_text.strip().strip('"').strip("'")
    path_text = re.sub(r"\\(.)", r"\1", path_text)
    return path_text


def read_schedule(input_path):
    """Read the schedule CSV into a list of dictionaries."""
    last_error = None

    for encoding in INPUT_ENCODINGS:
        try:
            with open(input_path, newline="", encoding=encoding) as f:
                reader = csv.DictReader(f)
                rows = [
                    row
                    for row in reader
                    if any(normalize(row.get(column, "")) for column in ("MONTH", "DATE", "DAY"))
                ]
                headers = reader.fieldnames or []
            break
        except UnicodeDecodeError as error:
            last_error = error
    else:
        raise UnicodeDecodeError(
            last_error.encoding,
            last_error.object,
            last_error.start,
            last_error.end,
            "Could not decode CSV using common Excel encodings.",
        )

    if not headers:
        raise ValueError("The CSV appears to have no header row.")
    if not rows:
        raise ValueError("The CSV appears to have no schedule rows.")

    return headers, rows


def build_calendar_rows(rows, fellow_column, start_date):
    """Build Google Calendar import rows."""
    calendar_rows = []
    current_date = start_date
    weekday_warnings = []

    for row_number, row in enumerate(rows, start=2):
        raw_rotation = normalize(row.get(fellow_column, ""))

        if raw_rotation == "":
            subject = "Day Off"
        elif raw_rotation.upper() == "HOL":
            subject = "Holiday"
        else:
            subject = raw_rotation

        block = normalize(row.get("BLOCK", ""))
        weekday = normalize(row.get("DAY", ""))
        month = normalize(row.get("MONTH", ""))
        day_of_month = normalize(row.get("DATE", ""))

        if weekday and weekday.lower() != current_date.strftime("%A").lower():
            weekday_warnings.append(
                f"row {row_number}: sheet says {weekday}, generated date is "
                f"{current_date.strftime('%A %Y-%m-%d')}"
            )

        description_parts = []
        if block:
            description_parts.append(f"Block {block}")
        if weekday:
            description_parts.append(weekday)
        if month and day_of_month:
            description_parts.append(f"Original schedule date: {month} {day_of_month}")

        calendar_rows.append(
            {
                "Subject": subject,
                "Start Date": current_date.strftime("%m/%d/%Y"),
                "Start Time": "",
                "End Date": current_date.strftime("%m/%d/%Y"),
                "End Time": "",
                "All Day Event": "True",
                "Description": " - ".join(description_parts),
                "Location": "",
                "Private": "True",
            }
        )

        current_date += timedelta(days=1)

    return calendar_rows, weekday_warnings


def write_calendar_csv(output_path, calendar_rows):
    """Write Google Calendar-compatible CSV."""
    fieldnames = [
        "Subject",
        "Start Date",
        "Start Time",
        "End Date",
        "End Time",
        "All Day Event",
        "Description",
        "Location",
        "Private",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(calendar_rows)


def summarize(calendar_rows, weekday_warnings):
    """Print a short summary."""
    total = len(calendar_rows)
    days_off = sum(1 for row in calendar_rows if row["Subject"] == "Day Off")
    holidays = sum(1 for row in calendar_rows if row["Subject"] == "Holiday")
    working_days = total - days_off - holidays

    print()
    print("Summary")
    print("-------")
    print(f"Total calendar rows: {total}")
    print(f"Working / rotation days: {working_days}")
    print(f"Days off: {days_off}")
    print(f"Holidays: {holidays}")

    if weekday_warnings:
        print()
        print("Date warnings")
        print("-------------")
        print("The generated dates do not match the weekday labels in the CSV.")
        print("This usually means the academic year start date is wrong.")
        for warning in weekday_warnings[:5]:
            print(f"- {warning}")
        if len(weekday_warnings) > 5:
            print(f"- ...and {len(weekday_warnings) - 5} more")


def main():
    print("Fellowship Schedule to Google Calendar CSV")
    print("------------------------------------------")
    print("This will create a CSV you can import into Google Calendar.")
    print()

    input_csv = clean_path_input(input("Path to schedule CSV: "))
    input_path = Path(input_csv).expanduser()

    if not input_path.exists():
        raise FileNotFoundError(f"Could not find input file: {input_path}")

    headers, rows = read_schedule(input_path)

    fellow_name = input("Enter your last name or schedule column name: ").strip()
    fellow_column = find_column(headers, fellow_name)

    if fellow_column is None:
        print()
        print(f"Could not find a single fellow column matching: {fellow_name}")
        print("Available fellow columns are:")
        print(", ".join(fellow_columns(headers)))
        raise SystemExit(1)

    start_date_text = prompt_with_default(
        "Academic year start date in YYYY-MM-DD format",
        DEFAULT_START_DATE,
    )

    try:
        start_date = datetime.strptime(start_date_text, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Start date must be in YYYY-MM-DD format, e.g. 2026-07-01.")

    default_output = f"{fellow_column.lower().replace(' ', '_')}_google_calendar.csv"
    output_csv = prompt_with_default("Output CSV filename", default_output)
    output_path = Path(output_csv).expanduser()

    calendar_rows, weekday_warnings = build_calendar_rows(rows, fellow_column, start_date)
    write_calendar_csv(output_path, calendar_rows)

    summarize(calendar_rows, weekday_warnings)

    print()
    print(f"Done. Calendar CSV saved to: {output_path.resolve()}")
    print()
    print("Import into Google Calendar:")
    print("1. Open Google Calendar.")
    print("2. Click the gear icon, then Settings, then Import & export.")
    print("3. Select this CSV file.")
    print("4. Import it into a separate calendar for easiest deletion/color control.")


if __name__ == "__main__":
    main()
