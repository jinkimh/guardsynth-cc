import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest

from apps.research_portal.security import hash_secret
from apps.guardsynth_studio.server import make_server
from apps.guardsynth_studio.common import uid
from apps.guardsynth_studio.jobs import Worker
from apps.guardsynth_studio.store import Store
from apps.guardsynth_studio.service import Service
from .helpers import fixture
from .browser_driver import Browser


class HTTPTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store, self.service, self.ids, self.extraction, _, _ = fixture(Path(self.temp.name) / "store")
        self.auth = {"users": [{"actor_id": "reviewer", "secret_hash": hash_secret("studio-test-password"), "roles": ["REVIEWER"]}]}
        self.server = make_server(self.service, self.auth)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True);self.thread.start()
        self.port = self.server.server_port
        self.cookie = self.csrf = None

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.store.close();self.temp.cleanup()

    def request(self, path, method="GET", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdr = {"Content-Type": "application/json"}
        if self.cookie: hdr["Cookie"] = self.cookie
        if self.csrf: hdr["X-CSRF-Token"] = self.csrf
        if method != "GET": hdr["Idempotency-Key"] = uid()
        hdr.update(headers or {})
        connection.request(method, path, json.dumps(body).encode() if body is not None else None, hdr)
        response = connection.getresponse();data=response.read()
        result = (response.status, dict(response.getheaders()), data)
        connection.close();return result

    def login(self):
        status, headers, body = self.request("/api/studio/v1/login", "POST", {"actor_id": "reviewer", "secret": "studio-test-password"})
        self.assertEqual(status,200)
        self.cookie=headers["Set-Cookie"].split(";",1)[0]
        self.csrf=json.loads(body)["csrf_token"]

    def test_auth_csrf_path_disabled_provider_and_if_match(self):
        prefix="/api/studio/v1"
        self.assertEqual(self.request(prefix+"/videos")[0],401)
        self.login()
        status, headers, body=self.request(prefix+"/capabilities")
        self.assertEqual(status,200);self.assertEqual(json.loads(body)["provider_mode"],"DISABLED")
        self.assertEqual(self.request(prefix+"/videos",headers={"Origin":"https://outside.invalid"})[0],403)
        path=prefix+"/moments/"+self.ids[0]
        data={"revision":0,"kind":"coc","payload":{"edited_text":"<script>window.pwned=true</script>"}}
        self.assertEqual(self.request(path,"PATCH",data,{"X-CSRF-Token":"bad","If-Match":"0"})[0],403)
        self.assertEqual(self.request(path,"PATCH",data)[0],409)
        self.assertEqual(self.request(path,"PATCH",data,{"If-Match":"0"})[0],200)
        self.assertEqual(self.request(path,"PATCH",data,{"If-Match":"0"})[0],409)
        self.assertEqual(self.request(path+"/jobs","POST",{"revision":1,"type":"COC"})[0],503)
        for malicious in ("..", "%2e%2e%2fetc%2fpasswd", "%252e%252e%252fetc"):
            self.assertIn(self.request(prefix+"/assets/"+malicious)[0],(403,404))
        self.assertNotIn(b"secret_hash",body)
        self.assertIn("Content-Security-Policy",headers)

    def test_manual_is_read_only_and_does_not_expose_workspace(self):
        # A missing static route or an over-broad unauthenticated route is a regression.
        status, headers, body = self.request("/manual.html")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Content-Security-Policy", headers)
        from html.parser import HTMLParser
        class Page(HTMLParser):
            def __init__(self):
                super().__init__(); self.ids=set(); self.anchors=[]; self.scripts=[]
            def handle_starttag(self, tag, attrs):
                attrs=dict(attrs)
                if "id" in attrs: self.ids.add(attrs["id"])
                if tag=="a": self.anchors.append(attrs)
                if tag=="script": self.scripts.append(attrs)
        manual=Page(); manual.feed(body.decode())
        self.assertFalse(manual.scripts)
        for link in manual.anchors:
            if link.get("href", "").startswith("#"):
                self.assertIn(link["href"][1:], manual.ids)
        workspace=Page(); workspace.feed(self.request("/")[2].decode())
        links=[a for a in workspace.anchors if a.get("href", "").startswith("/manual.html")]
        self.assertTrue(links, "Workspace must expose the help page")
        for link in links:
            self.assertEqual(link.get("target"), "_blank")
            self.assertIn("noopener", link.get("rel", "").split())
            if "#" in link["href"]: self.assertIn(link["href"].split("#",1)[1], manual.ids)
        self.assertEqual(self.request("/api/studio/v1/videos")[0],401)
        self.assertNotEqual(self.request("/manual.html", "POST", {})[0],200)
        self.assertNotEqual(self.request("/../auth.json")[0],200)
        self.assertEqual(self.store.objects("job"),[])

    def test_browser_manual_tab_preserves_edit_and_explains_dynamic_fields(self):
        # Opening help must not replace the editing tab, clear values, or trigger jobs.
        try:
            browser=Browser(self.temp.name,f"http://127.0.0.1:{self.port}/")
        except FileNotFoundError as exc:
            self.skipTest(str(exc))
        try:
            self.assertTrue(browser.evaluate("!!document.getElementById('manual_link')"))
            browser.evaluate("document.getElementById('actor').value='reviewer';document.getElementById('secret').value='studio-test-password';document.getElementById('login_form').requestSubmit()")
            browser.wait("!document.getElementById('workspace').hidden")
            browser.evaluate(f"openExtraction({json.dumps(self.extraction)})")
            browser.evaluate("selectOrdinal(6)")
            browser.evaluate("document.getElementById('coc_edited_text').value='저장한 검토 문장';saveCoc().then(flush)")
            browser.evaluate("document.getElementById('coc_edited_text').value='매뉴얼을 보는 동안 유지할 입력'")
            # Real user gesture: untrusted JS click() is blocked by Chromium's popup policy.
            point=browser.evaluate("(()=>{const a=document.getElementById('manual_link');a.scrollIntoView();const r=a.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()")
            for event in ("mousePressed","mouseReleased"):
                browser.call("Input.dispatchMouseEvent", {"type":event,"button":"left","clickCount":1,**point})
            deadline=time.monotonic()+10
            help_targets=[]
            while time.monotonic()<deadline:
                targets=browser.call("Target.getTargets")["targetInfos"]
                help_targets=[t for t in targets if t["url"].endswith('/manual.html')]
                if help_targets: break
                time.sleep(.05)
            self.assertEqual(len(help_targets),1)
            self.assertEqual(browser.evaluate("location.pathname"),"/")
            self.assertEqual(browser.evaluate("state.moment.ordinal"),6)
            self.assertEqual(browser.evaluate("document.getElementById('coc_edited_text').value"),"매뉴얼을 보는 동안 유지할 입력")
            # Each generated field has a visible, accessible description; examples are not values.
            self.assertTrue(browser.evaluate("[...document.querySelectorAll('#coc_fields textarea,#action_fields select,#predicate_fields select')].every(el=>{const h=document.getElementById(el.getAttribute('aria-describedby'));return h && h.textContent.trim().length>0 && h.getBoundingClientRect().height>0;})"))
            self.assertEqual(browser.evaluate("document.getElementById('coc_assumptions').value"),"")
            browser.call("Target.closeTarget",{"targetId":help_targets[0]["targetId"]})
            browser.evaluate("saveCoc().then(flush)")
            self.assertEqual(self.store.moment(self.ids[6])["components"]["coc"]["payload"]["edited_text"],"매뉴얼을 보는 동안 유지할 입력")
            self.assertEqual(self.store.moment(self.ids[6])["approvals"],{})
            self.assertEqual(self.store.objects("job"),[])
        finally:
            browser.close()

    def test_browser_generation_blocks_duplicate_clicks_and_loads_saved_result(self):
        from apps.guardsynth_studio.provider import MockProvider
        self.service.provider=MockProvider()
        browser=Browser(self.temp.name,f"http://127.0.0.1:{self.port}/")
        try:
            browser.evaluate("document.getElementById('actor').value='reviewer';document.getElementById('secret').value='studio-test-password';document.getElementById('login_form').requestSubmit()")
            browser.wait("document.querySelectorAll('#videos button').length>0")
            browser.evaluate("document.querySelector('#videos button:last-child').click()")
            browser.wait("document.getElementById('timestamp').textContent.includes('시점 1')")
            browser.evaluate("document.getElementById('generate_coc').click();document.getElementById('generate_coc').click()")
            browser.wait("document.getElementById('generate_coc').disabled")
            end=time.monotonic()+5
            while not self.store.objects('job') and time.monotonic()<end:time.sleep(.05)
            self.assertEqual(len(self.store.objects('job')),1)
            Worker(self.service).run_once()
            browser.wait("!document.getElementById('generate_coc').disabled && document.getElementById('coc_edited_text').value.length>0")
            self.assertEqual(len(self.store.objects('job')),1)
            self.assertEqual(self.store.objects('job')[0]['status'],'SUCCEEDED')
            browser.evaluate("document.getElementById('generate_coc').click()")
            end=time.monotonic()+5
            while len(self.store.objects('job'))<2 and time.monotonic()<end:time.sleep(.05)
            self.assertEqual(len(self.store.objects('job')),2)
            from .helpers import edit
            edit(self.service,self.ids[0],"coc",{"edited_text":"다른 창에서 저장한 최신 문장"})
            Worker(self.service).run_once()
            browser.wait("!document.getElementById('generate_coc').disabled && document.getElementById('coc_edited_text').value==='다른 창에서 저장한 최신 문장' && document.getElementById('error').textContent.includes('자동 재시도하지 않았습니다')")
            self.assertEqual(self.store.objects('job')[1]['status'],'STALE_RESULT')
        finally:
            browser.close()

    def test_browser_navigation_zoom_outbox_reload_and_xss(self):
        from PIL import Image
        ex=self.store.get(self.extraction,"extraction")
        for frame in ex["frames"]:
            path=self.store.root/(frame["asset_id"]+".png")
            Image.new("RGB",(64,64),(90,150,190)).save(path)
            self.store.put("asset",{"relative_path":path.name,"content_type":"image/png"},frame["asset_id"])
        try:
            browser=Browser(self.temp.name,f"http://127.0.0.1:{self.port}/")
        except FileNotFoundError as exc:
            self.skipTest(str(exc))
        try:
            browser.evaluate("document.getElementById('actor').value='reviewer';document.getElementById('secret').value='studio-test-password';document.getElementById('login_form').requestSubmit()")
            browser.wait("!document.getElementById('workspace').hidden")
            browser.evaluate(f"openExtraction({json.dumps(self.extraction)})")
            browser.evaluate("selectOrdinal(6)")
            self.assertEqual(browser.evaluate("Array.from(document.querySelectorAll('#strip img'),x=>x.alt)"),[f"frame {i}" for i in range(1,8)])
            browser.evaluate("document.getElementById('next').click()")
            browser.wait("state.moment.ordinal===7")
            self.assertEqual(browser.evaluate("state.moment.frames.map(f=>f.ordinal)"),list(range(1,8)))
            browser.evaluate("document.getElementById('previous').click()")
            browser.wait("state.moment.ordinal===6")
            browser.evaluate("document.getElementById('enlarge').click()")
            browser.wait("document.getElementById('zoom').open")
            browser.evaluate("document.getElementById('close_zoom').click()")
            self.assertEqual(browser.evaluate("state.moment.ordinal"),6)
            browser.evaluate("document.getElementById('coc_edited_text').value='<script>window.pwned=true</script>';saveCoc()")
            browser.evaluate("flush()")
            self.assertFalse(browser.evaluate("!!window.pwned"))
            self.assertEqual(self.store.moment(self.ids[6])["components"]["coc"]["payload"]["edited_text"],"<script>window.pwned=true</script>")
            # Network outage after locally durable edit; reload restores fetch and replays the outbox.
            browser.evaluate("window.fetch=()=>Promise.reject(new Error('test offline'));document.getElementById('coc_edited_text').value='outbox recovery';saveCoc()")
            self.assertGreater(browser.evaluate("dbOp('getAll').then(x=>x.length)"),0)
            browser.call("Page.reload")
            browser.wait("typeof state!=='undefined' && !!state.csrf")
            browser.wait("document.getElementById('save_state').textContent==='저장됨'")
            self.assertEqual(self.store.moment(self.ids[6])["components"]["coc"]["payload"]["edited_text"],"outbox recovery")
        finally:
            browser.close()

    def test_http_server_restart_preserves_committed_edit(self):
        self.login()
        path = "/api/studio/v1/moments/" + self.ids[0]
        self.assertEqual(self.request(path,"PATCH",{"revision":0,"kind":"coc","payload":{"edited_text":"server restart"}},{"If-Match":"0"})[0],200)
        self.server.shutdown();self.server.server_close();self.thread.join();self.store.close()
        self.store = Store(Path(self.temp.name)/"store")
        self.service = Service(self.store)
        self.server = make_server(self.service,self.auth,self.port)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.assertEqual(self.request(path)[0],403)
        self.cookie=self.csrf=None;self.login()
        status,_,body=self.request(path)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["components"]["coc"]["payload"]["edited_text"],"server restart")

    def test_browser_human_review_to_smt_cnl_draft_export(self):
        from PIL import Image
        ex=self.store.get(self.extraction,"extraction")
        for frame in ex["frames"]:
            p=self.store.root/(frame["asset_id"]+".png");Image.new("RGB",(64,64),(80,130,170)).save(p)
            self.store.put("asset",{"relative_path":p.name,"content_type":"image/png"},frame["asset_id"])
        worker=Worker(self.service);worker.start()
        try:
            browser=Browser(self.temp.name,f"http://127.0.0.1:{self.port}/")
        except FileNotFoundError as exc:
            worker.stop();self.skipTest(str(exc))
        try:
            browser.evaluate("document.getElementById('actor').value='reviewer';document.getElementById('secret').value='studio-test-password';document.getElementById('login_form').requestSubmit()")
            browser.wait("!!state.csrf")
            browser.evaluate(f"openExtraction({json.dumps(self.extraction)})")
            browser.evaluate("document.getElementById('coc_edited_text').value='현재 사람 관찰';document.getElementById('causal').checked=true;saveCoc()")
            browser.evaluate("flush().then(()=>approve('coc','APPROVE'))")
            browser.evaluate("document.getElementById('action_DEFER_ENTRY').value='APPROPRIATE';document.getElementById('action_ENTER_ZONE').value='APPROPRIATE';saveAction()")
            browser.evaluate("flush().then(()=>approve('action','APPROVE'))")
            browser.evaluate("document.getElementById('source_version').value='1';document.getElementById('source_locator').value='section 1';document.getElementById('source_quote').value='진입 전 해제 확인 정책';document.getElementById('source_reviewed').checked=true;document.getElementById('save_source').click()")
            browser.wait("!!state.moment.components.source")
            browser.evaluate("flush().then(()=>approve('source','APPROVE'))")
            browser.evaluate("state.drawing={target_point:[.5,.5],zone_polygon:[[.1,.1],[.8,.1],[.8,.8]]};document.getElementById('binding_confirmed').checked=true;document.getElementById('ped_truth').value='FALSE';document.getElementById('road_truth').value='FALSE';document.getElementById('ped_valid').checked=true;document.getElementById('road_valid').checked=true;document.getElementById('road_context').checked=true;saveBinding()")
            browser.evaluate("approve('binding','APPROVE')")
            browser.evaluate("document.getElementById('prepare_proposal').click()")
            browser.wait("!!state.moment.components.proposal")
            browser.evaluate("flush().then(()=>approve('proposal','APPROVE'))")
            browser.evaluate("document.getElementById('prepare_contract').click()")
            browser.wait("!!state.moment.components.contract")
            browser.evaluate("flush().then(()=>approve('contract','APPROVE'))")
            browser.evaluate("job('CHECK')")
            self.assertEqual(browser.evaluate("data('check').status"),"PASS")
            browser.evaluate("job('CNL').then(()=>approve('cnl','APPROVE'))")
            browser.evaluate("job('COMBINE').then(()=>approve('combined','APPROVE'))")
            self.assertIn("현재",browser.evaluate("document.getElementById('combined_text').textContent"))
            self.assertEqual(browser.evaluate("state.moment.eligibility.state"),"HELD")
            self.assertIn("REAL_PROVIDER_REQUIRED",browser.evaluate("state.moment.eligibility.reasons"))
            browser.evaluate("document.getElementById('export').click()")
            browser.wait("document.getElementById('exports').textContent.includes('READY')")
            self.assertTrue(all(not row.get("training_eligible") for exp in self.store.objects("export") for row in
                                [json.loads(line) for line in self.service.asset_path(exp["files"][0]["asset_id"]).read_text().splitlines()]))
        finally:
            browser.close();worker.stop()


if __name__ == "__main__":unittest.main()
