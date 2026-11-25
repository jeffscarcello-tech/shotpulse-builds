"""Browser test: Report a problem opens an in-app box, then a ready-to-send email (v88 / hotfix22).
Every request is answered from the bundle file. Usage: python3 -I test_report_box.py BUNDLE.json [more]"""
import json, sys, urllib.parse
from playwright.sync_api import sync_playwright

IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
ANDROID = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36'

def page_for(p, d, w, hgt, mobile, ua):
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': w, 'height': hgt}, is_mobile=mobile, has_touch=mobile, service_workers='block', user_agent=ua)
    def route(r):
        u = urllib.parse.urlparse(r.request.url)
        if u.scheme == 'mailto': return r.abort()
        if u.path in ('/', '/index.html'): return r.fulfill(status=200, content_type='text/html; charset=utf-8', body=d['html'])
        if u.path == '/sw.js': return r.fulfill(status=200, content_type='text/javascript', body=d['sw'])
        if u.path == '/manifest.webmanifest': return r.fulfill(status=200, content_type='application/manifest+json', body=d['manifest'])
        if u.path == '/api/health': return r.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'build': d['build']}))
        if u.path.startswith('/api/'): return r.fulfill(status=404, content_type='application/json', body='{}')
        return r.fulfill(status=404, body='')
    ctx.route('**/*', route)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
    pg.on('console', lambda m: errs.append('CONSOLE ' + m.text) if m.type == 'error' else None)
    pg.goto('http://shotpulse.test/'); pg.wait_for_selector('.brand', timeout=15000)
    return b, pg, errs

def run(path, p, w, hgt, mobile):
    d = json.load(open(path, encoding='utf-8')); B = d['build']; res = []
    ok = lambda c, m: res.append(('PASS ' if c else 'FAIL ') + m)
    b, pg, errs = page_for(p, d, w, hgt, mobile, IPHONE if mobile else None)
    pg.evaluate("location.hash = '#settings'"); pg.wait_for_timeout(500)
    btn = pg.locator('button[data-report]'); ub = pg.locator('button[data-update]')
    ok(btn.count() == 1, 'Report a problem shows once in Settings')
    btn.scroll_into_view_if_needed()
    bb, ubb = btn.bounding_box(), ub.bounding_box()
    ok(bb['y'] > ubb['y'] and bb['y'] - (ubb['y'] + ubb['height']) < 20, 'it sits right under Check for updates')
    ok(bb['height'] >= 40, 'it is tap-sized (%d px)' % bb['height'])
    ok(btn.locator('svg').count() == 1, 'it has the mail icon')
    ok(pg.locator('text=Your version and phone type are added for you').count() == 1, 'new line under the button')
    btn.click(); pg.wait_for_timeout(700)
    sheet = pg.locator('.sheet')
    ok(sheet.count() == 1 and pg.locator('.sheet h2', has_text='Report a problem').count() == 1, 'tapping opens the Report a problem box')
    sb = sheet.bounding_box()
    ok(sb['y'] >= 0 and sb['y'] + sb['height'] <= hgt + 1 and sb['width'] <= w, 'box fits the screen')
    ok(pg.locator('.sheet .lbl', has_text='What happened?').count() == 1 and pg.locator('.sheet .lbl', has_text='What did you expect?').count() == 1, 'both questions show')
    ok(pg.evaluate("document.activeElement && document.activeElement.hasAttribute('data-rp-what')"), 'first box has focus')
    pg.screenshot(path='/home/claude/work/box-%s-%d.png' % (B, w))
    pg.locator('[data-rp-what]').fill('Tapped GOAL\nscore stayed 0')
    pg.locator('[data-rp-exp]').fill('Score goes to 1')
    ob = pg.locator('[data-rp-open]'); obb = ob.bounding_box()
    ok(obb['height'] >= 40, 'Open email is tap-sized (%d px)' % obb['height'])
    with pg.expect_request(lambda r: r.url.startswith('mailto:'), timeout=5000) as rq:
        ob.click()
    url = rq.value.url
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    body = q.get('body', [''])[0]
    ok(url.startswith('mailto:support@shotpulse.app?'), 'address is support@shotpulse.app')
    ok(q.get('subject', [''])[0] == 'ShotPulse problem (%s)' % B, 'subject is "ShotPulse problem (build)"')
    ok('1) What happened: Tapped GOAL / score stayed 0' in body and '2) What I expected: Score goes to 1' in body, 'typed answers are in the email')
    pg.wait_for_timeout(1500)
    ok(pg.locator('.sheet').count() == 0, 'box closes after Open email')
    ok(pg.locator('text=If no email opened').count() >= 1, 'backup toast names the address')
    # reportUrl details
    u2 = pg.evaluate("window.__shotTracker.reportUrl('line one\\nline two', 'x')")
    raw_body = u2.split('&body=', 1)[1]
    ok('%0D%0A' in raw_body and '%0A' not in raw_body.replace('%0D%0A', ''), 'line breaks are CRLF only')
    bd = urllib.parse.unquote(raw_body)
    ok('1) What happened: line one / line two' in bd and '2) What I expected: x' in bd, 'inner line breaks become " / "')
    ok('— Details for the fix (please leave) —' in bd, 'details heading present')
    info = pg.evaluate("window.__shotTracker.reportInfo()").split('\n')
    ok(all(('• ' + l) in bd for l in info), 'every detail is a • line (%d lines)' % len(info))
    flat = ' '.join(bd.split())
    i1, i2, i3 = flat.find('1) What happened:'), flat.find(' 2) What I expected:'), flat.find(' • Device: ')
    ok(-1 < i1 < i2 < i3, 'still reads in order with line breaks removed')
    ok(len(pg.evaluate("window.__shotTracker.reportUrl('a'.repeat(1500), '')")) < 4000, 'answers are cut to 1000 characters')
    ok(('• Build: ' + B) in bd, 'build in the details')
    if mobile: ok('• Device: iPhone (iOS 18.1)' in bd, 'device line right for iPhone')
    ok('Teams / games on this phone: 0 / 0' in bd, 'counts only, no names')
    # empty boxes allowed; Cancel closes
    pg.evaluate("window.__shotTracker.reportSheet()"); pg.wait_for_timeout(500)
    pg.locator('.sheet button', has_text='Cancel').click(); pg.wait_for_timeout(300)
    ok(pg.locator('.sheet').count() == 0, 'Cancel closes the box')
    e = pg.evaluate("window.__shotTracker.reportUrl('', '')")
    ok('1)%20What%20happened%3A%20%0D%0A' in e, 'empty answers allowed')
    pg.evaluate("window.__shotTracker.startDemo()"); pg.wait_for_timeout(300)
    ok('Teams / games on this phone: 1 / 1' in pg.evaluate("window.__shotTracker.reportInfo()"), 'counts update after the demo')
    pg.evaluate("location.hash = '#game'"); pg.wait_for_timeout(400)
    ok(pg.locator('.brand').count() >= 1, 'home screen still draws')
    ok(not errs, 'no page errors ' + ('' if not errs else str(errs[:3])))
    b.close()
    if mobile:
        b, pg, errs = page_for(p, d, w, hgt, True, ANDROID)
        ok('Device: Android (Android 14)' in pg.evaluate("window.__shotTracker.reportInfo()"), 'device line right for Android')
        b.close()
    return res

with sync_playwright() as p:
    fails = 0
    for f in sys.argv[1:]:
        for w, hgt, mob in [(390, 844, True), (1280, 900, False)]:
            r = run(f, p, w, hgt, mob)
            print('==', f, w); [print(x) for x in r]
            fails += sum(1 for x in r if x.startswith('FAIL'))
    print('FAILS', fails)
