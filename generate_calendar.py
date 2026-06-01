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


# The first date represented by the first schedule row. Fellows can override
# this at the prompt if the schedule changes in a future academic year.
DEFAULT_START_DATE = "2026-07-01"

# These columns describe the schedule itself, rather than an individual fellow.
# Every other column is treated as a possible fellow name.
DATE_COLUMNS = {"BLOCK", "MONTH", "DATE", "DAY", "KEY"}

# Excel sometimes exports CSV files in different text encodings. The script
# tries these in order so most people can run it without knowing the encoding.
INPUT_ENCODINGS = ("utf-8-sig", "cp1252", "mac_roman", "latin-1")


def normalize(text):
    """Normalize text for matching column headers and schedule values."""
    # Convert None or empty values to "", replace non-breaking spaces from Excel,
    # and remove extra spaces at the beginning/end of the cell.
    return (text or "").replace("\xa0", " ").strip()


def normalize_for_match(text):
    """Normalize names for forgiving user input."""
    # Start with the basic cleanup, then make matching case-insensitive.
    text = normalize(text).lower()

    # Replace punctuation and repeated spaces with a single plain space so
    # "Luna-Wong", "LUNA WONG", and "luna wong" compare more similarly.
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def fellow_columns(headers):
    """Return schedule columns that appear to be fellow names."""
    # Keep every header except the schedule metadata columns like MONTH and DAY.
    return [header for header in headers if normalize(header).upper() not in DATE_COLUMNS]


def find_column(headers, requested_name):
    """Find a fellow column by exact, partial, or token-based match."""
    # Clean up what the user typed so matching is case-insensitive and tolerant
    # of spaces/punctuation.
    requested = normalize_for_match(requested_name)
    if not requested:
        return None

    # Limit matching to fellow columns so someone cannot accidentally select
    # MONTH, DATE, DAY, etc.
    candidates = fellow_columns(headers)
    normalized = {header: normalize_for_match(header) for header in candidates}

    # First try the safest match: the typed name exactly equals a column name
    # after normalization.
    for header, value in normalized.items():
        if value == requested:
            return header

    # Next, allow a single partial match. For example, "Rivera" can match
    # "MAYA RIVERA" as long as no other fellow column also matches.
    partial_matches = [
        header
        for header, value in normalized.items()
        if requested in value.split() or requested in value
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    # Finally, handle multi-word input where all typed words appear in the
    # column name, even if punctuation or spacing differs.
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
    # Show the default in brackets. If the user presses Enter, use the default.
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def clean_path_input(path_text):
    """Handle paths pasted from Terminal/Finder with quotes or backslash escapes."""
    # Remove surrounding quotes if the user pasted a quoted path.
    path_text = path_text.strip().strip('"').strip("'")

    # Convert Terminal-style escaped paths, such as "My\ File.csv", back to
    # normal paths, such as "My File.csv".
    path_text = re.sub(r"\\(.)", r"\1", path_text)
    return path_text


def read_schedule(input_path):
    """Read the schedule CSV into a list of dictionaries."""
    last_error = None

    # Try each common CSV encoding until one works. If the file is already
    # UTF-8, the first attempt succeeds. If it came from Excel, cp1252 or
    # another fallback may be needed.
    for encoding in INPUT_ENCODINGS:
        try:
            with open(input_path, newline="", encoding=encoding) as f:
                # DictReader uses the first row as column names. Each later
                # schedule row becomes a dictionary keyed by those column names.
                reader = csv.DictReader(f)

                # Keep only rows that look like real schedule dates. This drops
                # trailing blank rows that spreadsheet programs often export.
                rows = [
                    row
                    for row in reader
                    if any(normalize(row.get(column, "")) for column in ("MONTH", "DATE", "DAY"))
                ]
                headers = reader.fieldnames or []
            break
        except UnicodeDecodeError as error:
            # Save the error so we can report it if none of the encodings work.
            last_error = error
    else:
        # This else runs only if the loop never reached "break".
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
    # This list will become the rows in the Google Calendar import CSV.
    calendar_rows = []

    # The schedule has one row per day, so each loop advances this by one day.
    current_date = start_date

    # If the generated date says Tuesday but the schedule row says Wednesday,
    # the start date is probably wrong. Store those warnings for the summary.
    weekday_warnings = []

    # row_number starts at 2 because row 1 is the CSV header in a spreadsheet.
    for row_number, row in enumerate(rows, start=2):
        # Pull this fellow's assignment from the selected fellow column.
        raw_rotation = normalize(row.get(fellow_column, ""))

        # Convert blank cells and HOL into friendlier calendar event names.
        if raw_rotation == "":
            subject = "Day Off"
        elif raw_rotation.upper() == "HOL":
            subject = "Holiday"
        else:
            subject = raw_rotation

        # Pull the schedule metadata columns. These go into the event
        # description so the imported calendar keeps useful context.
        block = normalize(row.get("BLOCK", ""))
        weekday = normalize(row.get("DAY", ""))
        month = normalize(row.get("MONTH", ""))
        day_of_month = normalize(row.get("DATE", ""))

        # Compare the weekday printed in the schedule to the weekday generated
        # from the start date. This catches off-by-one or wrong-year mistakes.
        if weekday and weekday.lower() != current_date.strftime("%A").lower():
            weekday_warnings.append(
                f"row {row_number}: sheet says {weekday}, generated date is "
                f"{current_date.strftime('%A %Y-%m-%d')}"
            )

        # Build a readable Google Calendar description from any available
        # schedule metadata.
        description_parts = []
        if block:
            description_parts.append(f"Block {block}")
        if weekday:
            description_parts.append(weekday)
        if month and day_of_month:
            description_parts.append(f"Original schedule date: {month} {day_of_month}")

        # Add one all-day Google Calendar event row for this schedule day.
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

        # Move to the next calendar day for the next schedule row.
        current_date += timedelta(days=1)

    return calendar_rows, weekday_warnings


def write_calendar_csv(output_path, calendar_rows):
    """Write Google Calendar-compatible CSV."""
    # These column names are the format Google Calendar expects for CSV import.
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

    # newline="" prevents extra blank lines in CSV output on some systems.
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # DictWriter writes dictionaries using the column order above.
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(calendar_rows)


def summarize(calendar_rows, weekday_warnings):
    """Print a short summary."""
    # Count the different event types so the user can sanity-check the output.
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

    # Print only the first few date warnings so a wrong start date does not
    # flood the Terminal with hundreds of lines.
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
    # Print a small heading so the user knows the script started correctly.
    print("Fellowship Schedule to Google Calendar CSV")
    print("------------------------------------------")
    print("This will create a CSV you can import into Google Calendar.")
    print()

    # Ask for the source CSV file, clean up common macOS path paste formats,
    # and turn the text path into a Path object Python can use.
    input_csv = clean_path_input(input("Path to schedule CSV: "))
    input_path = Path(input_csv).expanduser()

    # Stop early with a clear message if the file path is wrong.
    if not input_path.exists():
        raise FileNotFoundError(f"Could not find input file: {input_path}")

    # Read the CSV header row and schedule rows.
    headers, rows = read_schedule(input_path)

    # Ask which fellow's column should be exported.
    fellow_name = input("Enter your last name or schedule column name: ").strip()
    fellow_column = find_column(headers, fellow_name)

    # If the typed name cannot be matched to exactly one fellow column, show
    # the available fellow columns so the user can rerun with the right name.
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

    # Convert the start date text into a datetime object. The script then adds
    # one day per CSV row.
    try:
        start_date = datetime.strptime(start_date_text, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Start date must be in YYYY-MM-DD format, e.g. 2026-07-01.")

    # Suggest an output filename based on the matched fellow column.
    default_output = f"{fellow_column.lower().replace(' ', '_')}_google_calendar.csv"
    output_csv = prompt_with_default("Output CSV filename", default_output)
    output_path = Path(output_csv).expanduser()

    # Convert the schedule rows to Google Calendar rows, then write them to the
    # requested output CSV.
    calendar_rows, weekday_warnings = build_calendar_rows(rows, fellow_column, start_date)
    write_calendar_csv(output_path, calendar_rows)

    # Print row counts and any date warnings.
    summarize(calendar_rows, weekday_warnings)

    # Tell the user where the file was saved and remind them how to import it.
    print()
    print(f"Done. Calendar CSV saved to: {output_path.resolve()}")
    print()
    print("Import into Google Calendar:")
    print("1. Open Google Calendar.")
    print("2. Click the gear icon, then Settings, then Import & export.")
    print("3. Select this CSV file.")
    print("4. Import it into a separate calendar for easiest deletion/color control.")


if __name__ == "__main__":
    # This makes main() run only when the file is executed directly, e.g.
    # "python3 generate_calendar.py". It would not run automatically if another
    # Python file imported this file for testing.
    main()
