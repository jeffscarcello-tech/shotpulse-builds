"""Browser test: Team plans shows every active plan and only the newest ended plan of a team with no active plan;
older ones fold under "Older plans (N)" and open on a tap (v96, accounts line only).
Usage: python3 -I test_older_plans.py BUNDLE.json [more]"""
import json, sys, urllib.parse, time
from playwright.sync_api import sync_playwright
DAY = 86400000

def run(path, p, w, hgt, mobile):
    d = json.load(open(path, encoding='utf-8')); res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block')
    ctx.route('**/*', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html']) if urllib.parse.urlparse(r.request.url).path in ('/', '/index.html') else r.fulfill(status=404, content_type='application/json', body='{}'))
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    now = int(time.time() * 1000)
    pg.evaluate("""([now, DAY]) => { const X = window.__shotTracker, S = X.S;
      const [mv, hk, ts, th] = ['Move Test', 'Hawks', 'Test', 'Thrashers'].map(n => X.newTeam({ name: n, mine: true, sport: 'hockey' })); S.teams.push(mv, hk, ts, th);
      const P = (id, t, exp, kind) => ({ id, kind: kind || 'season', exp: now + exp * DAY, tid: t ? t.id : null, tname: t ? t.name : '', movable: true });
      S.settings.acct = { email: 'j@t', dev: 'ABCDEFGHJK.' + '0'.repeat(32), devices: [], plans: [
        P('A1', mv, 300, 'year'),            // active
        P('H1', hk, -1), P('H2', hk, -2),     // two ended on Hawks: newest shows, other folds
        P('T1', ts, -1, 'month'),            // ended, only one on Test: shows
        P('R1', th, 100), P('R2', th, -3),    // Thrashers active + an old ended one: ended folds
        P('U1', null, 50) ] };               // unused active plan: shows
      X.plansSheet(); }""", [now, DAY])
    pg.wait_for_selector('[data-plan]', timeout=5000)
    shown = lambda: pg.evaluate("[...document.querySelectorAll('.sheet [data-plan]')].filter(e => !e.closest('[data-older-plans]') || e.offsetParent).map(e => e.dataset.plan)")
    main = shown()
    ok(sorted(main) == sorted(['A1', 'H1', 'T1', 'R1', 'U1']), 'main list: every active plan + newest ended per team without an active plan (%s)' % main)
    t = pg.locator('[data-older-toggle]'); ok(t.count() == 1 and t.inner_text().strip() == 'Older plans (2)', 'an "Older plans (2)" button')
    t.click(); pg.wait_for_timeout(200)
    ok(sorted(shown()) == sorted(['A1', 'H1', 'H2', 'T1', 'R1', 'R2', 'U1']), 'tapping it shows the older plans too')
    ok(pg.locator('[data-older-toggle]').inner_text().strip() == 'Hide older plans', 'button now says Hide older plans')
    pg.locator('[data-older-toggle]').click(); pg.wait_for_timeout(200)
    ok(sorted(shown()) == sorted(main), 'tapping again folds them away')
    ok(not errs, 'no page errors %s' % errs[:2])
    b.close(); return res

if __name__ == '__main__':
    bad = 0
    with sync_playwright() as p:
        for path in sys.argv[1:]:
            for w, hgt, mob in ((390, 844, True), (1280, 800, False)):
                r = run(path, p, w, hgt, mob); f = [x for x in r if x.startswith('FAIL')]; bad += len(f)
                print(path, w, 'pass', len(r) - len(f), 'fail', len(f)); [print('  ' + x) for x in f]
    sys.exit(1 if bad else 0)
