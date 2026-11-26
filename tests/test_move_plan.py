"""Browser test: Settings -> Team plans -> Move to another team sends the move to the server and shows it (v93, accounts line only).
Before v93 the confirm step read e.currentTarget after an await, threw, and the move never reached the server.
Usage: python3 -I test_move_plan.py BUNDLE.json [more]"""
import json, sys, urllib.parse, time
from playwright.sync_api import sync_playwright

def run(path, p, w, hgt, mobile):
    d = json.load(open(path, encoding='utf-8')); res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block')
    now = int(time.time() * 1000); st = {'plan': None, 'calls': []}
    def me():
        return {'email': 'jeff@test', 'devices': [], 'max': 5, 'plans': [st['plan']]}
    def route(r):
        u = urllib.parse.urlparse(r.request.url)
        if u.path in ('/', '/index.html'): return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        if u.path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        if u.path == '/api/acct/assign':
            body = json.loads(r.request.post_data or '{}'); st['calls'].append(body)
            pl = st['plan']
            if pl['tid'] != body['tid'] and not pl['movable']:
                return r.fulfill(status=409, content_type='application/json', body=json.dumps({'error': 'too_soon', 'at': pl['movableAt']}))
            pl.update({'tid': body['tid'], 'tname': body['tname'], 'movable': False, 'movableAt': int(time.time() * 1000) + 30 * 86400000})
            return r.fulfill(status=200, content_type='application/json', body=json.dumps(me()))
        if u.path == '/api/acct/me': return r.fulfill(status=200, content_type='application/json', body=json.dumps(me()))
        if u.path.startswith('/api/'): return r.fulfill(status=404, content_type='application/json', body='{}')
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    ids = pg.evaluate("""() => { const X = window.__shotTracker, S = X.S;
      const a = X.newTeam({ name: 'Test', mine: true, sport: 'hockey' }), b = X.newTeam({ name: 'Move test', mine: true, sport: 'hockey' }); S.teams.push(a, b); return [a.id, b.id]; }""")
    st['plan'] = {'id': 'NX', 'kind': 'year', 'exp': now + 300 * 86400000, 'tid': ids[0], 'tname': 'Test', 'movable': True}
    pg.evaluate("""p => { const S = window.__shotTracker.S; S.settings.acct = { email: 'jeff@test', dev: 'ABCDEFGHJK.' + '0'.repeat(32), plans: [p], devices: [], max: 5 }; window.__shotTracker.render(true); }""", st['plan'])
    pg.evaluate("window.__shotTracker.plansSheet()"); pg.wait_for_selector('[data-use-plan]', timeout=5000)
    btn = pg.locator('[data-use-plan="NX"]'); ok(btn.inner_text().strip() == 'Move to another team', 'plan offers Move to another team')
    btn.click(); pg.wait_for_selector('[data-pick-team]', timeout=5000)
    pg.locator('[data-pick-team="%s"]' % ids[1]).click(); pg.wait_for_timeout(300)
    pg.locator('button', has_text='Move plan').last.click(); pg.wait_for_timeout(1500)
    ok(len(st['calls']) == 1 and st['calls'][0].get('tid') == ids[1], 'the move reached the server (%d call)' % len(st['calls']))
    ok(pg.locator('[data-pick-team]').count() == 0, 'the team picker closed')
    plans = pg.evaluate("window.__shotTracker.S.settings.acct.plans")
    ok(plans and plans[0]['tid'] == ids[1], 'the app now has the plan on Move test')
    pg.evaluate("document.querySelectorAll('.sheet,.scrim').forEach(e => e.remove()); window.__shotTracker.plansSheet()"); pg.wait_for_selector('[data-use-plan]', timeout=5000)
    b2 = pg.locator('[data-use-plan="NX"]')
    ok(b2.inner_text().strip().startswith('Can be moved after') and b2.is_disabled(), 'after the move it reads Can be moved after… and cannot be tapped')
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
