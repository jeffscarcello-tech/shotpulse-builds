"""Browser test: in Simple mode the two teams' SHOT / GOAL buttons stay the same size when only one team has a goalie set (v97 / hotfix23).
Usage: python3 -I test_simple_symmetry.py BUNDLE.json [more]"""
import json, sys, urllib.parse
from playwright.sync_api import sync_playwright

SETUP = """([simple, ga, gb]) => { const X = window.__shotTracker, S = X.S; if (S.settings.acct !== undefined || true) S.settings.acct = Object.assign({}, S.settings.acct || {}, { plans: [{ state: 'active', tid: null }] });
  S.teams = []; S.games = [];
  const t = X.newTeam({ name: 'Selkirk Steelers', mine: true, sport: 'hockey' }); t.goalies = [{ id: 'ga1', name: 'Sam', num: '30' }];
  const o = X.newTeam({ name: 'Winnipeg Wolves', mine: false, sport: 'hockey' }); o.goalies = [{ id: 'gb1', name: 'Max', num: '1' }];
  S.teams.push(t, o); const g = X.newGame({ a: t.id, b: o.id, sport: 'hockey' }); g.simple = simple; g.net.a = ga ? 'ga1' : null; g.net.b = gb ? 'gb1' : null; S.games.unshift(g); X.go('g', g.id); }"""

def boxes(pg):
    out = {}
    for side in ('a', 'b'):
        s = pg.locator(f'button.shot[data-side="{side}"]').bounding_box(); g = pg.locator(f'button.goal[data-side="{side}"]').bounding_box()
        out[side] = (round(s['height']), round(g['height']), round(s['y']), round(g['y']))
    return out

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
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('nav.tabs', timeout=15000)
    for simple, ga, gb, name in ((True, True, False, 'Simple, only our goalie set'), (True, False, True, 'Simple, only their goalie set'), (True, True, True, 'Simple, both goalies set'), (True, False, False, 'Simple, no goalies set'), (False, True, False, 'Full, only our goalie set')):
        pg.evaluate(SETUP, [simple, ga, gb]); pg.wait_for_selector('button.goal[data-side="b"]', timeout=5000); pg.wait_for_timeout(250)
        x = boxes(pg)
        ok(abs(x['a'][0] - x['b'][0]) <= 1 and abs(x['a'][1] - x['b'][1]) <= 1, f'{name}: SHOT and GOAL buttons the same height on both sides {x}')
        ok(abs(x['a'][2] - x['b'][2]) <= 1 and abs(x['a'][3] - x['b'][3]) <= 1, f'{name}: buttons line up across the two sides')
        if simple and ga != gb:
            ok(pg.locator('button.net').count() == 1, f'{name}: the team with a goalie still shows its IN NET button')
            ok(pg.locator('[data-netgap]').count() == 1 and not pg.locator('[data-netgap]').is_visible(), f'{name}: the other side has an invisible space, not a "Choose goalie" button')
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
