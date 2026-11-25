# ShotPulse tests

Browser tests kept here instead of in the Claude project (the project is nearly full).
The updater Worker only reads `test/` and `live/`, so nothing in this folder is ever installed.

Every test answers each request from a bundle file, so it checks exactly what phones download.
Each one runs at 390 px (phone) and 1280 px (desktop) and fails on any page error.

| File | What it checks | Added |
|---|---|---|
| `test_report.py` | Settings → Report a problem: button shows, email address, subject and body carry the build and phone details, app keeps working | v87 / hotfix21 |

Run: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 -I tests/test_report.py test/app.json pending/live-app.json`

Rule: every new feature or fix adds or updates a test file here, in the same push as the build.
