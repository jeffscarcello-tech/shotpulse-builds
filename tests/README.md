# ShotPulse tests

Browser tests kept here instead of in the Claude project (the project is nearly full).
The updater Worker only reads `test/` and `live/`, so nothing in this folder is ever installed.

Every test answers each request from a bundle file, so it checks exactly what phones download.
Each one runs at 390 px (phone) and 1280 px (desktop) and fails on any page error.

| File | What it checks | Added |
|---|---|---|
| `test_report_box.py` | Settings → Report a problem: button under Check for updates, the in-app box (two questions, fits the screen, Cancel / Open email), the email (address, subject, `1)` `2)` `•` layout, CRLF line breaks, still in order with line breaks removed, 1000-character cut), iPhone and Android device lines, counts only, no page errors | v88 / hotfix22 (replaces `test_report.py` from v87) |

Run: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 -I tests/test_report_box.py test/app.json live/app.json`

Rule: every new feature or fix adds or updates a test file here, in the same push as the build.
