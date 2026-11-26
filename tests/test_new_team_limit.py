"""Browser test: the free plan allows one team without a plan, on top of any teams that have an active plan (v92, accounts line only).
Usage: python3 -I test_new_team_limit.py BUNDLE.json [more]"""
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

    def setup(teams, plans):
        pg.evaluate("""([teams, plans, now]) => { const X = window.__shotTracker, S = X.S;
          document.querySelectorAll('.sheet,.scrim').forEach(e => e.remove());
          S.teams.splice(0); const ids = teams.map(n => { const t = X.newTeam({ name: n, mine: true, sport: 'hockey' }); S.teams.push(t); return t.id; });
          S.settings.acct = plans === null ? null : { email: 'jeff@test', dev: 'ABCDEFGHJK.' + '0'.repeat(32), plans: plans.map((p, i) => ({ id: 'p' + i, kind: 'season', exp: now + p[1] * 86400000, tid: p[0] == null ? null : ids[p[0]], movable: true })) };
          X.go('home'); X.render(true); }""", [teams, plans, now])
        pg.wait_for_timeout(250)

    def try_new(name):
        pg.evaluate("document.querySelectorAll('.sheet,.scrim').forEach(e => e.remove()); window.__shotTracker.newTeamSheet()")
        pg.wait_for_timeout(250)
        pg.locator('input[placeholder="Team name"]').last.fill(name)
        pg.locator('input[placeholder="Team name"]').last.press('Enter')
        pg.wait_for_timeout(400)
        made = pg.evaluate("n => window.__shotTracker.S.teams.some(t => t.name === n)", name)
        asked = pg.locator('text=More than one team needs a team plan').count() > 0
        return made, asked

    # 1. signed out, no teams: first team is free, the second asks for a plan
    setup([], None)
    m, a = try_new('First'); ok(m and not a, 'no plan: first team is allowed')
    m, a = try_new('Second'); ok(not m and a, 'no plan: a second team asks for a plan')
    # 2. two teams, both with an active plan (Jeff's case): one more free team is allowed, then a fourth asks
    setup(['Royals', 'Thrashers'], [[0, 90], [1, 90]])
    m, a = try_new('Move test'); ok(m and not a, 'two paid teams: a third (free) team is allowed')
    m, a = try_new('Fourth'); ok(not m and a, 'two paid teams + one free: a fourth team asks for a plan')
    # 3. one paid team and one free team already: no more free teams
    setup(['Paid', 'Free'], [[0, 90]])
    m, a = try_new('Extra'); ok(not m and a, 'one paid + one free: another team asks for a plan')
    # 4. a team whose plan ended (grace) counts as the free team
    setup(['Ended'], [[0, -5]])
    m, a = try_new('Another'); ok(not m and a, 'an ended-plan team uses up the free slot')
    # 5. an unused plan does not count as a team with a plan
    setup(['Paid'], [[0, 90], [None, 90]])
    m, a = try_new('Free one'); ok(m and not a, 'one paid team + an unused plan: one free team is allowed')
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
