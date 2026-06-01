# Fellowship Schedule to Google Calendar CSV

Convert the fellowship schedule CSV into a Google Calendar-compatible CSV.

The script prompts for:

1. The schedule CSV file path
2. Your last name or schedule column name
3. The academic year start date
4. The output file name

It treats blank schedule cells as `Day Off`, `HOL` as `Holiday`, and every row as an all-day calendar event.

## Requirements

Python 3 only. No extra packages are required.

## How to run it

Download or clone this repository, then open Terminal and move into the project folder:

```bash
cd fellowship-schedule-calendar
```

Run the script:

```bash
python3 generate_calendar.py
```

The script will ask for:

```text
Path to schedule CSV:
```

Paste the path to the schedule CSV. On macOS, you can also drag the CSV file into Terminal and it will paste the path for you.

Then enter your last name or schedule column name:

```text
Enter your last name or schedule column name:
```

For the academic year start date, press Enter to accept the default unless your schedule starts on a different date.

For AY26-27, the default start date is:

```text
2026-07-01
```

The script checks the weekday labels in the CSV against the generated dates. If you see date warnings, double-check the start date before importing the output into Google Calendar.

Finally, choose an output filename or press Enter to accept the default. The script will create a new CSV file in the project folder.

## Import into Google Calendar

1. Open Google Calendar.
2. Click the gear icon, then `Settings`, then `Import & export`.
3. Select the generated CSV file.
4. Import into a separate calendar so it is easy to delete, hide, recolor, or re-import later.

## Notes

- Name matching is forgiving. For example, entering `Rivera` can match a `MAYA RIVERA` column if it is the only matching fellow column.
- The script handles common CSV encodings exported by Excel, including UTF-8, Windows-1252, Mac Roman, and Latin-1.
- The trailing blank row sometimes produced by spreadsheet exports is ignored.
