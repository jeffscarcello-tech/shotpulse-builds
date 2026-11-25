"""Browser test for the Report a problem button. Every request is answered from the bundle file.
Usage: python3 -I test_report.py BUNDLE.json [more bundles]"""
import json, sys, urllib.parse
from playwright.sync_api import sync_playwright

def run(bundle_path, p, w, hgt, mobile):
    d = json.load(open(bundle_path, encoding='utf-8'))
    errors, mails, res = [], [], []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile,
                        service_workers='block',
                        user_agent=('Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1' if mobile else None))
    def route(r):
        u = urllib.parse.urlparse(r.request.url)
        if u.scheme == 'mailto':
            mails.append(r.request.url); return r.abort()
        path = u.path
        if path in ('/', '/index.html') or path.startswith('/l/'):
            return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        if path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        if path == '/manifest.webmanifest': return r.fulfill(status=200, content_type='application/manifest+json', body=d['manifest'])
        if path == '/api/health': return r.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'build': d['build'], 'loader': 'test'}))
        if path.startswith('/api/'): return r.fulfill(status=404, content_type='application/json', body='{"error":"not_found"}')
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: errors.append('CONSOLE ' + m.text) if m.type == 'error' else None)
    # catch the mailto navigation without leaving the page
    pg.add_init_script("""
      window.__mail = [];
      const desc = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
    """)
    pg.goto('http://shotpulse.test/')
    pg.wait_for_selector('.brand', timeout=15000)
    pg.evaluate("location.hash = '#settings'")
    pg.wait_for_timeout(600)
    btn = pg.locator('button[data-report]')
    ok(btn.count() == 1, 'Report a problem button shows once in Settings')
    ok(pg.locator('button[data-update]').count() == 1, 'Check for updates still there')
    btn.scroll_into_view_if_needed()
    box = btn.bounding_box()
    ub = pg.locator('button[data-update]').bounding_box()
    ok(box and box['height'] >= 40 and abs(box['width'] - ub['width']) < 2, 'button is tap-sized and as wide as Check for updates (%s)' % (box and int(box['height'])))
    pg.screenshot(path='/home/claude/work/shot-%s-%d.png' % (d['build'], w))
    info = pg.evaluate("window.__shotTracker.reportInfo()")
    ok(('Build: ' + d['build']) in info, 'report carries the build name')
    ok(('Device: iPhone (iOS 18.1)' in info) if mobile else ('Device:' in info), 'report names the device')
    ok('Teams / games on this phone: 0 / 0' in info, 'report counts teams and games')
    # click: the page tries to open a mailto: link
    with pg.expect_request(lambda r: r.url.startswith('mailto:'), timeout=5000) as rq:
        btn.click()
    url = rq.value.url
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    ok(url.startswith('mailto:support@shotpulse.app?'), 'email goes to support@shotpulse.app')
    ok(q.get('subject', [''])[0] == 'ShotPulse problem (%s)' % d['build'], 'subject has the build')
    body = q.get('body', [''])[0]
    ok(body.startswith('What happened?') and ('Build: ' + d['build']) in body, 'body asks what happened and carries the details')
    pg.wait_for_timeout(1500)
    ok(pg.locator('text=If no email opened').count() >= 1, 'fallback hint names the address')
    # rest of the app still works after the tap: start a demo and open Settings again
    pg.evaluate("window.__shotTracker.startDemo()"); pg.wait_for_timeout(300)
    pg.evaluate("location.hash = '#settings'"); pg.wait_for_timeout(400)
    ok('Teams / games on this phone: 1 / 1' in pg.evaluate("window.__shotTracker.reportInfo()"), 'counts update after the demo')
    pg.evaluate("location.hash = '#game'"); pg.wait_for_timeout(400)
    ok(pg.locator('.brand').count() >= 1, 'home screen still draws')
    ok(not errors, 'no page errors ' + ('' if not errors else str(errors[:3])))
    b.close()
    return res

with sync_playwright() as p:
    fails = 0
    for f in sys.argv[1:]:
        for w, hgt, mob in [(390, 844, True), (1280, 900, False)]:
            r = run(f, p, w, hgt, mob)
            print('==', f, w)
            for line in r: print(line)
            fails += sum(1 for x in r if x.startswith('FAIL'))
    print('FAILS', fails)
