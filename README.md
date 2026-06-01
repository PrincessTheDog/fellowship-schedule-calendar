# Fellowship Schedule to Google Calendar CSV

Convert the fellowship schedule CSV into a Google Calendar-compatible CSV.

The script prompts for:

1. The schedule CSV file path
2. Your last name or schedule column name
3. The academic year start date
4. The output file name

It treats blank schedule cells as `Day Off`, `HOL` as `Holiday`, and every row as an all-day calendar event.

## Privacy note

Do not commit the real schedule CSV if it includes names, call assignments, leave, clinical sites, pager details, or other sensitive information. Share the script on GitHub, and distribute the schedule CSV through whatever private channel your program normally uses.

## Requirements

Python 3 only. No extra packages are required.

## Usage

Download or clone this repository, then run:

```bash
python3 generate_calendar.py
```

When prompted, paste the path to the schedule CSV. On macOS, you can drag the CSV file into Terminal and it will paste the path.

For AY26-27, the default start date is:

```text
2026-07-01
```

The script checks the weekday labels in the CSV against the generated dates. If you see date warnings, double-check the start date before importing the output into Google Calendar.

## Import into Google Calendar

1. Open Google Calendar.
2. Click the gear icon, then `Settings`, then `Import & export`.
3. Select the generated CSV file.
4. Import into a separate calendar so it is easy to delete, hide, recolor, or re-import later.

## Notes

- Name matching is forgiving. For example, entering `Wong` can match a `LUNA WONG` column if it is the only matching fellow column.
- The script handles common CSV encodings exported by Excel, including UTF-8, Windows-1252, Mac Roman, and Latin-1.
- The trailing blank row sometimes produced by spreadsheet exports is ignored.
