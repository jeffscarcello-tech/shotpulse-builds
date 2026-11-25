"""Browser test: Home tab, About ShotPulse button (Settings and FAQ) and the live server address folded under Advanced (v89).
Every request is answered from the bundle file. Usage: python3 -I test_nav_home.py BUNDLE.json [more]"""
import json, sys, urllib.parse
from playwright.sync_api import sync_playwright

def run(path, p, w, hgt, mobile):
    d = json.load(open(path, encoding='utf-8')); res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block')
    seen = []
    def route(r):
        u = urllib.parse.urlparse(r.request.url); seen.append(u.path)
        if u.path in ('/', '/index.html'): return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        if u.path == '/welcome': return r.fulfill(status=200, content_type='text/html', body='<h1 id="landing">ShotPulse</h1><a href="/">Open ShotPulse</a>')
        if u.path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        if u.path.startswith('/api/'): return r.fulfill(status=404, content_type='application/json', body='{}')
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    tabs = pg.locator('nav.tabs .tab').all_inner_texts()
    ok(tabs and tabs[0].strip() == 'Home', 'first tab says Home (%s)' % tabs[:1])
    ok(not any(t.strip() == 'Game' for t in tabs), 'no tab called Game')
    ok(pg.locator('nav.tabs .tab.on').inner_text().strip() == 'Home', 'Home is highlighted on the start screen')
    pg.evaluate("location.hash = '#teams'"); pg.wait_for_timeout(300)
    pg.locator('nav.tabs .tab', has_text='Home').click(); pg.wait_for_timeout(300)
    ok(pg.locator('nav.tabs .tab.on').inner_text().strip() == 'Home', 'Home tab goes back to the start screen')
    # FAQ: About first
    pg.evaluate("location.hash = '#faq'"); pg.wait_for_timeout(400)
    ab = pg.locator('button[data-about]'); ok(ab.count() == 1, 'FAQ has one About ShotPulse button')
    first = pg.locator('.page button, .page input').first
    ok(first.get_attribute('data-about') == '1', 'About ShotPulse is the first thing on the FAQ page')
    ok('Game tab' not in pg.locator('.faq').inner_text(), 'FAQ no longer says Game tab')
    # Settings
    pg.evaluate("location.hash = '#settings'"); pg.wait_for_timeout(400)
    ok(pg.locator('button[data-about]').count() == 1, 'Settings has the About ShotPulse button')
    sects = [x.strip().title() for x in pg.locator('.page .sect').all_inner_texts()]
    ok(sects and sects[0] != 'Live sharing' and 'Live sharing' not in sects, 'Live server is no longer the first card (%s)' % sects[:2])
    adv = pg.locator('details[data-advanced]'); ok(adv.count() == 1, 'Advanced section exists')
    ok(adv.get_attribute('open') is None, 'Advanced starts folded')
    ok(not pg.locator('details[data-advanced] input').is_visible(), 'address box hidden until Advanced is opened')
    ai = sects.index('Advanced') if 'Advanced' in sects else -1
    ok(ai >= 0 and 'About' in sects and ai < sects.index('About'), 'Advanced sits just above About %s' % sects)
    adv.locator('summary').click(); pg.wait_for_timeout(200)
    ok(pg.locator('details[data-advanced] input').is_visible(), 'address box shows after opening Advanced')
    # About goes to the landing page on the same site
    pg.locator('button[data-about]').click(); pg.wait_for_selector('#landing', timeout=5000)
    ok(urllib.parse.urlparse(pg.url).path == '/welcome' and 'shotpulse.test' in pg.url, 'About opens /welcome on the same site (%s)' % pg.url)
    pg.locator('text=Open ShotPulse').click(); pg.wait_for_selector('.brand', timeout=15000)
    ok(True, 'Open ShotPulse on the landing page comes back to the app')
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
