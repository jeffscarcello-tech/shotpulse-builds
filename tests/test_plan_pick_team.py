"""Browser test: the plans screen asks which team a new plan is for, and after paying the plan goes on that team (v94, accounts line only).
The Stripe page is skipped: checkout answers with the app's own ?paid=1 address, as Stripe does after a payment.
Usage: python3 -I test_plan_pick_team.py BUNDLE.json [more]"""
import json, sys, urllib.parse, time
from playwright.sync_api import sync_playwright

DAY = 86400000

def run(path, p, w, hgt, mobile, case):
    d = json.load(open(path, encoding='utf-8')); res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + case + ': ' + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block')
    now = int(time.time() * 1000)
    st = {'plans': [], 'assign': [], 'checkout': []}
    me = lambda: {'email': 'jeff@test', 'devices': [], 'max': 5, 'plans': st['plans']}
    def route(r):
        u = urllib.parse.urlparse(r.request.url)
        if u.path in ('/', '/index.html'): return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        if u.path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        js = lambda o, s=200: r.fulfill(status=s, content_type='application/json', body=json.dumps(o))
        if u.path == '/api/pay/checkout':
            body = json.loads(r.request.post_data or '{}'); st['checkout'].append(body)
            for i in range(body.get('qty', 1)): st['plans'].append({'id': 'N%d' % len(st['plans']), 'kind': body['kind'], 'exp': now + 180 * DAY, 'tid': None, 'movable': True})
            return js({'url': 'http://shotpulse.test/?paid=1'})
        if u.path == '/api/acct/assign':
            body = json.loads(r.request.post_data or '{}'); st['assign'].append(body)
            for pl in st['plans']:
                if pl['id'] == body['slot']: pl.update({'tid': body['tid'], 'tname': body['tname'], 'movable': False, 'movableAt': now + 30 * DAY})
            return js(me())
        if u.path in ('/api/acct/me', '/api/acct/refresh'): return js(me())
        if u.path.startswith('/api/'): return js({}, 404)
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    names = {'one': ['Paid', 'Hawks'], 'two': ['Paid', 'Hawks', 'Wolves'], 'later': ['Paid', 'Hawks'], 'none': ['Paid', 'Hawks', 'Wolves']}[case]
    ids = pg.evaluate("""names => { const X = window.__shotTracker; const ts = names.map(n => X.newTeam({ name: n, mine: true, sport: 'hockey' }));
      localStorage.setItem('st.teams', JSON.stringify(ts)); return ts.map(t => t.id); }""", names)
    st['plans'].append({'id': 'P0', 'kind': 'year', 'exp': now + 300 * DAY, 'tid': ids[0], 'tname': 'Paid', 'movable': False, 'movableAt': now + 9 * DAY})
    pg.evaluate("""plans => { const s = JSON.parse(localStorage.getItem('st.settings') || '{}'); s.acct = { email: 'jeff@test', dev: 'ABCDEFGHJK.' + '0'.repeat(32), plans, devices: [], max: 5 }; localStorage.setItem('st.settings', JSON.stringify(s)); }""", st['plans'])
    pg.reload(); pg.wait_for_selector('.brand', timeout=15000)
    pg.evaluate("window.__shotTracker.plansSheet()"); pg.wait_for_selector('[data-plan-for]', timeout=5000)
    chips = pg.locator('[data-for-team]')
    ok(chips.count() == len(ids) - 1, 'lists only the teams without a plan (%d)' % chips.count())
    pre = pg.locator('[data-for-team].on').count()
    if case in ('one', 'later'):
        ok(pre == 1 and pg.locator('[data-for-team="%s"].on' % ids[1]).count() == 1, 'the only team without a plan is picked already')
        ok('goes on Hawks' in pg.locator('[data-plan-for-note]').inner_text(), 'it says the plan goes on Hawks')
        if case == 'later':
            pg.locator('button[aria-label="More teams"]').click(); pg.wait_for_timeout(200)
            ok('other plan' in pg.locator('[data-plan-for-note]').inner_text(), 'a second plan is for later')
    if case == 'two':
        ok(pre == 0, 'with two teams nothing is picked for you')
        pg.locator('[data-for-team="%s"]' % ids[1]).click(); pg.locator('[data-for-team="%s"]' % ids[2]).click(); pg.wait_for_timeout(200)
        ok('2 teams' in pg.locator('[data-plan-for]').locator('xpath=..').inner_text(), 'picking two teams makes it 2 teams')
    if case == 'none':
        ok(pre == 0 and 'choose the team after' in pg.locator('[data-plan-for-note]').inner_text(), 'nothing picked: you can choose after paying')
    pg.locator('[data-pay]').click()
    pg.wait_for_timeout(6500)
    want = ids[1:3] if case == 'two' else ([] if case == 'none' else [ids[1]])
    got = [a['tid'] for a in st['assign']]
    ok(len(st['checkout']) == 1 and st['checkout'][0]['qty'] == {'one': 1, 'two': 2, 'later': 2, 'none': 1}[case], 'paid for the right number of teams')
    if case == 'none':
        ok(got == [] and pg.locator('[data-pick-team]').count() > 0, 'after paying, the app asks which team')
    else:
        ok(sorted(got) == sorted(want), 'after paying, the plan went on the picked team(s) %s' % got)
        ok(pg.locator('[data-pick-team]').count() == 0, 'no team picker after paying')
        if case == 'later':
            ok(any(pl['tid'] is None for pl in st['plans']), 'the extra plan is kept for later')
    ok(pg.evaluate("!JSON.parse(localStorage.getItem('st.settings')||'{}').payFor"), 'the pick is cleared after use')
    ok(not errs, 'no page errors %s' % errs[:2])
    b.close(); return res

if __name__ == '__main__':
    bad = 0
    with sync_playwright() as p:
        for path in sys.argv[1:]:
            for w, hgt, mob in ((390, 844, True), (1280, 800, False)):
                r = []
                for case in ('one', 'two', 'later', 'none'): r += run(path, p, w, hgt, mob, case)
                f = [x for x in r if x.startswith('FAIL')]; bad += len(f)
                print(path, w, 'pass', len(r) - len(f), 'fail', len(f)); [print('  ' + x) for x in f]
    sys.exit(1 if bad else 0)
