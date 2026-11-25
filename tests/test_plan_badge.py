"""Browser test: Settings -> Team plans shows an active plan with a green ACTIVE badge, not the red LIVE style (v91, accounts line only).
Usage: python3 -I test_plan_badge.py BUNDLE.json [more]"""
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
        if u.path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        if u.path.startswith('/api/'): return r.fulfill(status=404, content_type='application/json', body='{}')
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    now = int(time.time() * 1000)
    pg.evaluate("""now => { const X = window.__shotTracker, S = X.S; const t = X.newTeam({ name: 'Steelers', mine: true, sport: 'hockey' }); S.teams.push(t);
      S.settings.acct = Object.assign({}, S.settings.acct || {}, { email: 'jeff@test', dev: 'ABCDEFGHJK.' + '0'.repeat(32), plans: [
        { id: 'p1', kind: 'season', exp: now + 90 * 86400000, state: 'active', tid: t.id, tname: 'Steelers', movable: true },
        { id: 'p2', kind: 'month', exp: now - 5 * 86400000, state: 'grace', tid: null } ] }); }""", now)
    pg.evaluate("location.hash = '#settings'"); pg.wait_for_timeout(400)
    opened = pg.evaluate("() => { const f = window.__shotTracker.plansSheet || window.plansSheet; if (f) { f(); return true; } return false; }")
    if not opened:
        pg.locator('button', has_text='Team plans').first.click()
    pg.wait_for_selector('[data-plan-state]', timeout=5000)
    act = pg.locator('[data-plan-state="active"]'); ok(act.count() == 1, 'one active plan badge')
    ok(act.inner_text().strip() == 'ACTIVE', 'it says ACTIVE')
    col = act.evaluate("e => getComputedStyle(e).color"); bg = act.evaluate("e => getComputedStyle(e).backgroundColor")
    rgb = [int(x) for x in col[col.index('(') + 1:col.index(')')].split(',')[:3]]
    ok(rgb[1] > rgb[0] + 60 and rgb[1] > rgb[2], 'ACTIVE text is green (%s)' % col)
    ok('255, 90, 95' not in bg and '255, 116, 120' not in col, 'not the red LIVE style (%s / %s)' % (bg, col))
    end = pg.locator('[data-plan-state="grace"]'); ok(end.count() == 1 and end.inner_text().strip() == 'ENDED', 'an ended plan still shows a grey ENDED badge')
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
