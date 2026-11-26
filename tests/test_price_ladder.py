"""Browser test: the Team plans screen shows the three price levels (1, 2-4, 5+ teams) and highlights the one you'd pay,
counting plans you already have (v95, accounts line only).
Usage: python3 -I test_price_ladder.py BUNDLE.json [more]"""
import json, sys, urllib.parse, time
from playwright.sync_api import sync_playwright

def run(path, p, w, hgt, mobile):
    d = json.load(open(path, encoding='utf-8')); res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block')
    def route(r):
        u = urllib.parse.urlparse(r.request.url)
        if u.path in ('/', '/index.html'): return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        return r.fulfill(status=404, content_type='application/json', body='{}')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    def open_with(active):
        pg.reload(); pg.wait_for_selector('.brand', timeout=15000)   # the plan choice is kept between openings, so start fresh
        pg.evaluate("""a => { const X = window.__shotTracker, S = X.S, now = Date.now(); document.querySelectorAll('.sheet,.scrim').forEach(e => e.remove());
          S.teams.splice(0); const ts = ['A','B','C','D','E','F','G'].map(n => X.newTeam({ name: 'Team ' + n, mine: true, sport: 'hockey' })); S.teams.push(...ts.slice(0, a + 1));
          S.settings.acct = { email: 'j@t', dev: 'ABCDEFGHJK.' + '0'.repeat(32), devices: [], plans: Array.from({length: a}, (_, i) => ({ id: 'p' + i, kind: 'year', exp: now + 9e9, tid: ts[i].id, tname: ts[i].name, movable: true })) };
          X.plansSheet(); }""", active)
        pg.wait_for_selector('[data-price-ladder]', timeout=5000); pg.wait_for_timeout(150)
    tier = lambda: pg.locator('[data-tier-on="true"]').get_attribute('data-tier')
    note = lambda: pg.locator('[data-price-ladder] .small').inner_text()
    lad = lambda: pg.locator('[data-price-ladder]').inner_text()
    open_with(0)
    t = lad(); ok('1 team' in t and '2–4 teams' in t and '5+ teams' in t, 'three levels shown')
    ok('$24.99' in t and '$21.25 each' in t and '$17.50 each' in t, '6-month prices shown')
    ok(tier() == '0', 'no plans, 1 team: first level highlighted')
    ok('Add 1 more team' in note() and '$21.25' in note(), 'says one more team lowers the price')
    pg.locator('button[aria-label="More teams"]').click(); pg.wait_for_timeout(150)
    ok(tier() == '1', '2 teams: 2–4 level highlighted')
    for _ in range(3): pg.locator('button[aria-label="More teams"]').click(); pg.wait_for_timeout(100)
    ok(tier() == '2' and 'lowest price' in note(), '5 teams: 5+ level highlighted, lowest price')
    pg.locator('[data-kind="month"]').click(); pg.wait_for_timeout(150)
    ok('$3.50/mo each' in lad(), 'monthly prices show /mo')
    open_with(2)
    ok(tier() == '1' and 'Counts the 2 plans you already have' in note(), 'two plans owned + 1 new: 2–4 level, explains the count')
    open_with(4)
    ok(tier() == '2', 'four plans owned + 1 new: 5+ level')
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
