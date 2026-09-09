// Run only through browser_ae.py. Browser control uses dictionary-backed Apple Events.
ObjC.import('AppKit');

function fail(code, message, details) {
    var error = new Error(message);
    error.code = code;
    error.details = details || {};
    throw error;
}

function session(browser) {
    var apps = $.NSRunningApplication.runningApplicationsWithBundleIdentifier(browser.bundle_id);
    var count = Number(apps.count);
    if (count === 0) fail('TARGET_NOT_RUNNING', 'Start the chosen browser yourself. No automatic launch.');
    if (count !== 1) fail('TARGET_AMBIGUOUS', 'Multiple processes use this bundle ID. Stop and select one explicitly.');
    var process = apps.objectAtIndex(0);
    if (ObjC.unwrap(process.bundleURL.path) !== browser.path) {
        fail('BROWSER_CHANGED', 'Running bundle path differs from the selected app.');
    }
    return {pid: Number(process.processIdentifier), launched: Number(process.launchDate.timeIntervalSince1970)};
}

function checkSession(request, expected) {
    var actual = session(request.browser);
    if (actual.pid !== expected.pid || actual.launched !== expected.launched) {
        fail('BROWSER_RESTARTED', 'Browser process changed. Review the task and bind again.');
    }
}

function describe(window, tab) {
    var id = String(tab.id());
    var row = {window_id: String(window.id()), tab_id: id,
        url: String(tab.url()), title: String(tab.title()), loading: Boolean(tab.loading())};
    if (String(tab.id()) !== id) fail('OBJECT_NOT_FOUND', 'Tab changed during inspection.');
    return row;
}

function locate(app, tabId) {
    var matches = [];
    app.windows.id().forEach(function (windowId) {
        var window = app.windows.byId(windowId);
        window.tabs.id().forEach(function (id) {
            if (String(id) === tabId) matches.push({window: window, tab: window.tabs.byId(id)});
        });
    });
    if (matches.length === 0) fail('OBJECT_NOT_FOUND', 'Bound tab is gone. Do not select a replacement.');
    if (matches.length !== 1) fail('TARGET_AMBIGUOUS', 'Tab ID is not unique across browser windows.');
    return matches[0];
}

function executePage(tab, source) {
    var raw = tab.execute({javascript: source});
    if (typeof raw !== 'string') fail('REPLY_COERCION_FAILED', 'Page did not return JSON text.', {outcome: 'unknown'});
    var reply;
    try { reply = JSON.parse(raw); }
    catch (_) { fail('REPLY_COERCION_FAILED', 'Invalid JSON page reply.', {outcome: 'unknown'}); }
    if (!reply || typeof reply.ok !== 'boolean') fail('REPLY_COERCION_FAILED', 'Invalid page envelope.', {outcome: 'unknown'});
    if (!reply.ok) fail(reply.error.code, reply.error.message, {outcome: reply.error.outcome});
    return reply.result;
}

function probeSource(url) {
    return '(function () {\n' +
        'if (location.href !== ' + JSON.stringify(url) + ') return JSON.stringify({ok:false,error:{code:"PAGE_CHANGED",message:"Expected URL differs from the rendered document.",outcome:"not_started"}});\n' +
        'return JSON.stringify({ok:true,result:{url:location.href,time_origin:performance.timeOrigin}});\n' +
        '})()';
}

function guardedSource(request) {
    var expected = JSON.stringify(request.target.document);
    // The guard and caller body run in one renderer task, not two Apple Events.
    return '(function () {\n' +
        '"use strict";\n' +
        'const expected = ' + expected + ';\n' +
        'if (location.href !== expected.url || performance.timeOrigin !== expected.time_origin)\n' +
        '  return JSON.stringify({ok:false,error:{code:"PAGE_CHANGED",message:"Bound URL or document changed. Body was not run.",outcome:"not_started"}});\n' +
        'try {\n' +
        '  const value = (function () {\n' + request.code + '\n}).call(undefined);\n' +
        '  if (value && typeof value.then === "function") return JSON.stringify({ok:false,error:{code:"UNSUPPORTED_ASYNC",message:"Promise results are unsupported. Work may already have started.",outcome:"unknown"}});\n' +
        '  const result = JSON.stringify({ok:true,result:{value:value === undefined ? null : value,document:{url:location.href,time_origin:performance.timeOrigin}}});\n' +
        '  if (result.length > ' + request.limit + ') return JSON.stringify({ok:false,error:{code:"OUTPUT_TOO_LARGE",message:"Return fewer fields or smaller batches.",outcome:"unknown"}});\n' +
        '  return result;\n' +
        '} catch (error) {\n' +
        '  return JSON.stringify({ok:false,error:{code:"JAVASCRIPT_EXECUTION_FAILED",message:String(error.message || error).slice(0,1500),outcome:"unknown"}});\n' +
        '}\n' +
        '})()';
}

function perform(request) {
    var initial = session(request.browser);
    if (request.selected_session) checkSession(request, request.selected_session);
    if (request.target) checkSession(request, request.target.session);
    var app = Application(request.browser.path);
    if (!app.running()) fail('TARGET_NOT_RUNNING', 'Browser stopped before the request.');

    if (request.operation === 'tabs') {
        var tabs = [];
        app.windows.id().forEach(function (id) {
            var window = app.windows.byId(id);
            window.tabs.id().forEach(function (tabId) {
                tabs.push(describe(window, window.tabs.byId(tabId)));
            });
        });
        checkSession(request, initial);
        return {session: initial, tabs: tabs};
    }
    if (request.operation === 'new-tab') {
        var window = app.windows.byId(request.window_id);
        if (String(window.id()) !== request.window_id) fail('OBJECT_NOT_FOUND', 'Requested window is gone.');
        checkSession(request, initial);
        var created = app.Tab({url: request.url});
        window.tabs.push(created);
        return {status: 'created', tab: describe(window, created), session: initial,
            note: 'Record this ID for cleanup. Creation may select the tab; do not restore stale focus.'};
    }
    if (request.operation === 'bind') {
        var match = locate(app, request.tab_id);
        var row = describe(match.window, match.tab);
        if (row.window_id !== request.window_id || row.url !== request.url) {
            fail('PAGE_CHANGED', 'Window or URL differs from the selection. Inspect again.');
        }
        if (row.loading) fail('PAGE_LOADING', 'Page is loading. Wait with a deadline, then bind.');
        var document = request.native_only ? null : executePage(match.tab, probeSource(request.url));
        if (match.tab.url() !== request.url) fail('PAGE_CHANGED', 'URL changed while binding.');
        checkSession(request, initial);
        return {schema: 1, browser: request.browser, session: initial,
            window_id: row.window_id, tab_id: row.tab_id, url: row.url, document: document};
    }

    var match = locate(app, request.target.tab_id);
    var row = describe(match.window, match.tab);
    if (row.url !== request.target.url) fail('PAGE_CHANGED', 'Bound tab navigated. Do not overwrite or silently rebind it.', {outcome: 'not_started'});
    checkSession(request, request.target.session);
    if (request.operation === 'ax-check') {
        if (row.loading) fail('PAGE_LOADING', 'Bound page is loading.', {outcome: 'not_started'});
        if (Number($.NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier) !== request.target.session.pid ||
            !app.frontmost() || Number(match.window.index()) !== 1 ||
            !match.window.visible() || match.window.minimized() ||
            String(match.window.activeTab().id()) !== request.target.tab_id) {
            fail('AX_FOCUS_REQUIRED', 'Exact bound tab must already be foreground. No focus was changed.', {outcome: 'not_started'});
        }
        var context = executePage(match.tab, guardedSource(request));
        checkSession(request, request.target.session);
        if (Number($.NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier) !== request.target.session.pid ||
            !app.frontmost() || Number(match.window.index()) !== 1 ||
            String(match.window.activeTab().id()) !== request.target.tab_id) {
            fail('AX_FOCUS_CHANGED', 'Foreground changed during the page guard.', {outcome: 'not_started'});
        }
        return {window_id: row.window_id, tab_id: row.tab_id, context: context.value};
    }
    if (request.operation === 'run') {
        if (row.loading) fail('PAGE_LOADING', 'Page is loading. Body was not sent.', {outcome: 'not_started'});
        var reply = executePage(match.tab, guardedSource(request));
        checkSession(request, request.target.session);
        return {tab: {window_id: row.window_id, tab_id: row.tab_id}, mode: request.mode,
            value: reply.value, document_after: reply.document,
            verification: 'JavaScript returned. Verify the task-specific postcondition separately.'};
    }
    if (request.operation === 'native') {
        if (request.target.document) executePage(match.tab, probeAndCheck(request.target.document));
        switch (request.action) {
        case 'navigate': match.tab.url = request.url; break;
        case 'reload': match.tab.reload(); break;
        case 'back': match.tab.goBack(); break;
        case 'forward': match.tab.goForward(); break;
        case 'stop': match.tab.stop(); break;
        case 'close': match.tab.close(); break;
        default: fail('CAPABILITY_UNAVAILABLE', 'Unknown native action.');
        }
        return {status: 'dispatched', action: request.action, window_id: row.window_id, tab_id: row.tab_id,
            verification: 'Not verified. Native guard and action are separate events; do not replay after a timeout.'};
    }
    fail('INVALID_INPUT', 'Unknown request.');
}

function probeAndCheck(document) {
    return '(function () { const expected = ' + JSON.stringify(document) + ';\n' +
        'if (location.href !== expected.url || performance.timeOrigin !== expected.time_origin) return JSON.stringify({ok:false,error:{code:"PAGE_CHANGED",message:"Bound document changed.",outcome:"not_started"}});\n' +
        'return JSON.stringify({ok:true,result:true}); })()';
}

function normalize(error) {
    var message = String(error.message || error).slice(0, 1500);
    var number = Number(error.errorNumber || error.number) || null;
    var code = error.code;
    if (!code) {
        if (number === -1743 || /not authorized to send apple events/i.test(message)) code = 'APPLE_EVENT_NOT_AUTHORIZED';
        else if (/javascript.*apple events.*(disabled|off)|allow javascript from apple events|executing javascript.*(disabled|turned off)/i.test(message)) code = 'JAVASCRIPT_APPLE_EVENTS_DISABLED';
        else if (/developer tools.*disabled|devtools.*disabled/i.test(message)) code = 'BROWSER_POLICY_BLOCKED';
        else if (number === -1728) code = 'OBJECT_NOT_FOUND';
        else if (number === -600 || number === -609) code = 'TARGET_NOT_RUNNING';
        else if (number === -1712) code = 'TIMEOUT';
        else if (number === -1708) code = 'COMMAND_UNAVAILABLE';
        else code = 'APPLE_EVENT_FAILED';
    }
    var result = {code: code, message: message, number: number, outcome: 'unknown'};
    Object.keys(error.details || {}).forEach(function (key) { result[key] = error.details[key]; });
    return result;
}

function run(argv) {
    try {
        var text = $.NSString.stringWithContentsOfFileEncodingError(argv[0], $.NSUTF8StringEncoding, null);
        var request = JSON.parse(ObjC.unwrap(text));
        return JSON.stringify({ok: true, result: perform(request)});
    } catch (error) {
        return JSON.stringify({ok: false, error: normalize(error)});
    }
}
