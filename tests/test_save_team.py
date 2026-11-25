"""Browser test: Save team / Save opponent button at the bottom of a team page (v90).
Every request is answered from the bundle file. Usage: python3 -I test_save_team.py BUNDLE.json [more]"""
import json, sys, urllib.parse
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
    tid = pg.evaluate("""() => { const X = window.__shotTracker, S = X.S; S.settings.acct = { plans: [{ state: 'active', tid: null }] };
      const t = X.newTeam({ name: '', mine: true, sport: 'hockey' }); S.teams.push(t);
      const o1 = X.newTeam({ name: 'Wolves', mine: false, sport: 'hockey' }), o2 = X.newTeam({ name: 'Bears', mine: false, sport: 'hockey' }); S.teams.push(o1, o2);
      const g = X.newGame({ a: t.id, b: o1.id, sport: 'hockey' }); S.games.unshift(g); X.endGame(g); const g2 = X.newGame({ a: t.id, b: o2.id, sport: 'hockey' }); S.games.unshift(g2); X.endGame(g2);
      window.__o2 = o2.id; X.go('team', t.id); return t.id; }""")
    pg.wait_for_timeout(400)
    btn = pg.locator('button[data-saveteam]')
    ok(btn.count() == 1 and btn.inner_text().strip() == 'Save team', 'Save team button on your team page')
    dl = pg.locator('button.danger', has_text='Delete team')
    btn.scroll_into_view_if_needed(); bb, db_ = btn.bounding_box(), dl.bounding_box()
    ok(bb['y'] < db_['y'], 'it sits just above Delete team, at the bottom')
    ok(bb['height'] >= 48, 'it is a big button (%d px)' % bb['height'])
    pg.locator('input[placeholder="Team name"]').fill('Selkirk Steelers')   # type and press Save without leaving the box
    btn.click(); pg.wait_for_timeout(500)
    ok(pg.evaluate("location.hash") in ('#teams', '#/teams') or 'teams' in pg.evaluate("location.hash"), 'Save team goes back to the Teams list (%s)' % pg.evaluate("location.hash"))
    ok(pg.locator('.toast', has_text='Team saved').count() >= 1, 'shows "Team saved"')
    ok(pg.locator('text=Selkirk Steelers').count() >= 1, 'the new name shows in the Teams list')
    pg.reload(); pg.wait_for_selector('nav.tabs', timeout=15000)
    ok(pg.evaluate("() => window.__shotTracker.S.teams.some(t => t.mine && t.name === 'Selkirk Steelers')"), 'the name is still there after a reload')
    # opponent page: label, and a duplicate name opens the merge question instead of leaving
    pg.evaluate("() => window.__shotTracker.go('team', window.__shotTracker.S.teams.find(t => t.name === 'Bears').id)"); pg.wait_for_timeout(400)
    ob = pg.locator('button[data-saveteam]'); ok(ob.inner_text().strip() == 'Save opponent', 'opponent page says Save opponent')
    pg.locator('input[placeholder="Opponent name"]').fill('Wolves'); ob.click(); pg.wait_for_timeout(500)
    ok(pg.locator('.sheet', has_text='Merge').count() == 1, 'a duplicate opponent name asks to merge first')
    ok('team' in pg.evaluate("location.hash"), 'and stays on the page while asking')
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
