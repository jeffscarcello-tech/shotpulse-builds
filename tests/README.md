# ShotPulse tests

Browser tests kept here instead of in the Claude project (the project is nearly full).
The updater Worker only reads `test/` and `live/`, so nothing in this folder is ever installed.

Every test answers each request from a bundle file, so it checks exactly what phones download.
Each one runs at 390 px (phone) and 1280 px (desktop) and fails on any page error.

| File | What it checks | Added |
|---|---|---|
| `test_report_box.py` | Settings → Report a problem: button under Check for updates, the in-app box (two questions, fits the screen, Cancel / Open email), the email (address, subject, `1)` `2)` `•` layout, CRLF line breaks, still in order with line breaks removed, 1000-character cut), iPhone and Android device lines, counts only, no page errors | v88 / hotfix22 (replaces `test_report.py` from v87) |
| `test_nav_home.py` | Home tab (first tab, highlighted, goes back to the start screen), About ShotPulse button first on FAQ and in Settings → About, opens /welcome on the same site and Open ShotPulse comes back, live server address folded under Advanced just above About, FAQ no longer says Game tab, no page errors | v89 |
| `test_save_team.py` | Save team button at the bottom of your team page (above Delete, big), saves a name typed without leaving the box, shows Team saved, goes back to Teams, still there after a reload; opponent page says Save opponent and a duplicate name asks to merge instead of leaving; no page errors | v90 |
| `test_plan_badge.py` | Settings → Team plans: an active plan shows a green ACTIVE badge (not the red LIVE style), an ended plan a grey ENDED badge; accounts line only (the live site has no plans) | v91 |
| `test_new_team_limit.py` | New team: the free plan allows one team without a plan on top of any teams with an active plan (an ended-plan team counts as the free one, an unused plan does not); accounts line only (the live site has no team limit) | v92 |
| `test_move_plan.py` | Settings → Team plans → Move to another team: the move reaches the server, the picker closes, the plan shows on the new team and then reads "Can be moved after …" (disabled); accounts line only | v93 |
| `test_plan_pick_team.py` | Team plans: "Which team is it for?" lists teams without a plan (one is picked for you when it is the only one), picking teams sets the number of teams, and after paying (checkout answers with `?paid=1`) the plans go on the picked teams; extra plans stay for later; nothing picked opens the team picker; accounts line only | v94 |

Run: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 -I tests/test_report_box.py test/app.json live/app.json` (same for each test file)

Rule: every new feature or fix adds or updates a test file here, in the same push as the build.
