"""Two real loopback origins and independent SQLite readback. Context-managed only."""

from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading

GUARD = '''return {account:document.body.dataset.account,record:document.body.dataset.record,
state:document.body.dataset.state,revision:Number(document.body.dataset.revision)};'''

FRAME = '''<!doctype html><meta charset="utf-8"><title>Approval fixture</title>
<p>Record FIXTURE-1</p>
<button aria-label="Submit change for approval" onclick="save('submit')"></button>
<button onclick="save('pci')">PCI impact</button>
<button onclick="document.querySelector('#dialog').hidden=false">Reject</button>
<button>No effect</button>
<button disabled>Disabled</button><button>Duplicate</button><button>Duplicate</button>
<div id="dialog" role="dialog" aria-label="Rejection dialog" hidden>
<label>Rejection reason<textarea id="reason" aria-label="Rejection reason" oninput="committedReason=this.value"></textarea></label>
<button onclick="save('reject')">Confirm reject</button></div>
<label>Uncommitted text<textarea id="uncommitted" aria-label="Uncommitted text"></textarea></label>
<output id="result"></output>
<script>
let committedReason='';
async function save(action) {
 const response=await fetch('/event',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({action,reason:committedReason})});
 const state=await response.json();
 document.querySelector('#result').textContent=JSON.stringify(state);
 parent.postMessage(state,TOP_ORIGIN);
}
</script>'''


class Fixture(AbstractContextManager):
    def __enter__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="browser-ax-fixture-")
        self.database = Path(self.directory.name) / "state.sqlite"
        self.lock = threading.Lock()
        with sqlite3.connect(self.database) as db:
            db.execute("CREATE TABLE record (id TEXT, state TEXT, revision INTEGER, reason TEXT, pci INTEGER)")
            db.execute("INSERT INTO record VALUES ('FIXTURE-1','New',1,'',0)")
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, body, content_type="application/json", status=200):
                content = body.encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)

            def do_GET(self):
                if self.path == "/state":
                    self.reply(json.dumps(owner.readback()))
                elif self.path == "/approval":
                    self.reply(FRAME.replace("TOP_ORIGIN", json.dumps(owner.top_origin)), "text/html; charset=utf-8")
                elif self.path == "/ticket/1":
                    state = owner.readback()
                    self.reply('''<!doctype html><meta charset="utf-8"><title>AX same-title fixture</title>
<body data-account="fixture" data-record="FIXTURE-1" data-state="%s" data-revision="%s">
<h1>Record FIXTURE-1</h1><iframe title="Approval fixture" src="%s/approval"></iframe>
<script>addEventListener('message',e=>{if(e.origin!==%s || e.source!==document.querySelector('iframe').contentWindow)return;
if(e.data.record!=='FIXTURE-1')return;document.body.dataset.state=e.data.state;document.body.dataset.revision=e.data.revision;});</script>
''' % (state["state"], state["revision"], owner.frame_origin, json.dumps(owner.frame_origin)), "text/html; charset=utf-8")
                else:
                    self.reply('{}', status=404)

            def do_POST(self):
                if self.path != "/event":
                    self.reply('{}', status=404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    self.reply('{}', status=400)
                    return
                try:
                    event = json.loads(self.rfile.read(length))
                    with owner.lock, sqlite3.connect(owner.database) as db:
                        if event["action"] == "submit":
                            db.execute("UPDATE record SET state='Pending', revision=revision+1 WHERE state='New'")
                        elif event["action"] == "reject" and event.get("reason"):
                            db.execute("UPDATE record SET state='New', reason=?, revision=revision+1 WHERE state='Pending'", (event["reason"],))
                        elif event["action"] == "pci":
                            db.execute("UPDATE record SET pci=1-pci, revision=revision+1")
                        else:
                            self.reply('{}', status=400)
                            return
                    self.reply(json.dumps(owner.readback()))
                except (ValueError, KeyError, TypeError):
                    self.reply('{}', status=400)

        class BoundedServer(HTTPServer):
            def get_request(self):
                connection, address = super().get_request()
                connection.settimeout(2)
                return connection, address

        self.servers, self.threads = [], []
        try:
            for _ in range(2):
                self.servers.append(BoundedServer(("127.0.0.1", 0), Handler))
            self.top_origin, self.frame_origin = [f"http://127.0.0.1:{server.server_port}" for server in self.servers]
            self.url = self.top_origin + "/ticket/1"
            for server in self.servers:
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
                thread.start()
                self.threads.append(thread)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def readback(self):
        with self.lock, sqlite3.connect(self.database) as db:
            row = db.execute("SELECT id,state,revision,reason,pci FROM record").fetchone()
        return dict(zip(("record", "state", "revision", "reason", "pci"), row))

    def __exit__(self, *_):
        for server, thread in zip(self.servers, self.threads):
            server.shutdown()
            thread.join(timeout=3)
        for server in self.servers:
            server.server_close()
        self.directory.cleanup()
