"""Card -> discussion session traceability: the card page's discussion chip and how it finds its session.

crew_card stamps the opening session on the card row and a plan's children keep the plan's discussion
(test_crew_card.py); here: crew_graph.find_origin_session for cards that carry neither (a `hermes kanban create`
from a terminal), and the chip itself - card.js, and the web dashboard tab that opens the session's chat.
"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
CREW_ROOT = os.path.dirname(HERE)
for p in (CREW_ROOT, os.path.join(CREW_ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)


class SessionTraceabilityJsTests(unittest.TestCase):
    """Run in node: the card page's discussion chip (card.js) and the web dashboard tab's open-session handler
    (dashboard/dist/index.js). The functions are sliced out of the shipped files, so the code under test is the
    code that ships; the DOM, clipboard and window are minimal stand-ins."""

    def setUp(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        self.node = str(node)

    def _read(self, *parts):
        with open(os.path.join(CREW_ROOT, *parts), "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _fn(src, name):
        start = src.index("function %s(" % name)
        return src[start:src.index("\n}", start) + 2]

    def _run(self, script):
        import subprocess
        out = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    # A DOM just big enough for the chip: elements with children, attributes, listeners and classList.
    DOM = r"""
function El(tag){ this.tagName = tag; this.children = []; this.attrs = {}; this.listeners = {}; this.textContent = "";
  var self = this; this.classList = {set: {}, add: function(c){ self.classList.set[c] = 1; },
  remove: function(c){ delete self.classList.set[c]; }}; }
El.prototype.appendChild = function(c){ this.children.push(c); return c; };
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.addEventListener = function(k, f){ this.listeners[k] = f; };
El.prototype.click = function(){ this.listeners.click({stopPropagation: function(){}}); };
var byId = {};
var document = {body: new El("body"), createElement: function(t){ return new El(t); },
  getElementById: function(id){ return byId[id] || null; }};
var origAppend = El.prototype.appendChild;
El.prototype.appendChild = function(c){ if(c.id) byId[c.id] = c; return origAppend.call(this, c); };
function setTimeout(){ return 0; } function clearTimeout(){}
var COPYFLASH = {};
function shortId(s){ s=String(s); return s.length<=14 ? s : s.slice(0,7)+".."+s.slice(-5); }
"""

    def _card_fns(self):
        src = self._read("scripts", "crew_dashboard", "card.js")
        self.assertIn("hermes:open-session", src)
        rx = src[src.index("var SESSION_ID_RX"):src.index("\n", src.index("var SESSION_ID_RX"))]
        return rx + "\n" + "\n".join(self._fn(src, n) for n in (
            "parseSessionCoord", "discussionCoord", "sessionRef", "openSessionTarget", "chatUrlFor",
            "openDiscussion", "sitDiscussionChip", "showToast"))

    def test_parse_session_coord_accepts_a_session_and_refuses_the_rest(self):
        script = self._card_fns() + r"""
console.log(JSON.stringify([
  parseSessionCoord("default/20261012_092737_07d8d5"), parseSessionCoord(" owner-chat/s-1 "),
  parseSessionCoord("default/no-session"), parseSessionCoord("default"), parseSessionCoord("a/b/c"),
  parseSessionCoord("x/../etc"), parseSessionCoord("x/a;b"), parseSessionCoord(""), parseSessionCoord(null),
  parseSessionCoord(42), discussionCoord({coordinator: "", session_id: "row_session"}),
  discussionCoord({coordinator: "leader/no-session", session_id: "row_session"}),
  discussionCoord({}), discussionCoord(null)]));
"""
        out = self._run(script)
        self.assertEqual({"profile": "default", "sessionId": "20261012_092737_07d8d5"}, out[0])
        self.assertEqual({"profile": "owner-chat", "sessionId": "s-1"}, out[1])
        self.assertEqual([None] * 8, out[2:10])
        self.assertEqual({"profile": "", "sessionId": "row_session"}, out[10])         # the row's session_id
        self.assertEqual({"profile": "leader", "sessionId": "row_session"}, out[11])
        self.assertEqual([None, None], out[12:])                                        # legacy card: no chip

    def test_the_chip_posts_open_session_to_a_host_parent(self):
        script = self.DOM + self._card_fns() + r"""
var posted = [];
var parentWin = {postMessage: function(msg, target){ posted.push([msg, target]); }};
var window = {parent: parentWin};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_092737_07d8d5"));
var chip = box.children[0], btn = chip.children[2];
btn.click();
console.log(JSON.stringify({n: box.children.length, label: chip.children[1].textContent, id: btn.id,
  posted: posted, after: btn.textContent, data: btn.attrs["data-session"]}));
"""
        out = self._run(script)
        self.assertEqual(1, out["n"])
        self.assertEqual("cardSessionJump", out["id"])
        self.assertEqual("default/2026101..7d8d5", out["label"])
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "20261012_092737_07d8d5",
                            "profile": "default"}, "*"]], out["posted"])
        self.assertEqual("opening", out["after"])                                       # visual click feedback
        self.assertEqual("20261012_092737_07d8d5", out["data"])

    def test_a_standalone_browser_copies_the_session_and_shows_a_toast(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_092737_07d8d5"));
box.children[0].children[2].click();
var toast = byId.crewToast;
console.log(JSON.stringify({copied: copied, toast: toast && toast.textContent, on: !!(toast && toast.classList.set.on),
  role: toast && toast.attrs.role}));
"""
        out = self._run(script)
        self.assertEqual(["@session:default/20261012_092737_07d8d5"], out["copied"])
        self.assertEqual("Session link copied: @session:default/20261012_092737_07d8d5", out["toast"])
        self.assertTrue(out["on"])
        self.assertEqual("status", out["role"])

    def test_the_web_dashboard_frame_posts_open_session_to_its_own_origin(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], posted = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {parent: {location: {origin: "http://127.0.0.1:9119"},
  postMessage: function(m, t){ posted.push([m, t]); }}, __crewNav: function(){}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, posted: posted, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "s1", "profile": "default"},
                           "http://127.0.0.1:9119"]], out["posted"])         # never "*" from the dashboard frame
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_a_frame_whose_parent_refuses_the_post_falls_back_to_copy(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [];
function copyText(text, done){ copied.push(text); done(true); }
var window = {parent: {postMessage: function(){ throw new Error("cross-origin"); }}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
box.children[0].children[2].click();
console.log(JSON.stringify({copied: copied}));
"""
        self.assertEqual(["@session:default/s1"], self._run(script)["copied"])

    def test_discovered_session_profile_names_the_chip(self):
        script = self._card_fns() + r"""
console.log(JSON.stringify([
  discussionCoord({coordinator: "", session_id: "20261012_131459_eb9bfb", session_profile: "default"}),
  discussionCoord({coordinator: "leader/no-session", session_id: "s9", session_profile: "coder"}),
  discussionCoord({coordinator: "", session_id: "s9", session_profile: "../x"}),
  discussionCoord({coordinator: "default/c1", session_id: "s9", session_profile: "coder"})]));
"""
        out = self._run(script)
        self.assertEqual({"profile": "default", "sessionId": "20261012_131459_eb9bfb"}, out[0])
        self.assertEqual({"profile": "coder", "sessionId": "s9"}, out[1])               # discovery wins over the line
        self.assertEqual({"profile": "", "sessionId": "s9"}, out[2])                    # a bad profile is dropped
        self.assertEqual({"profile": "default", "sessionId": "c1"}, out[3])             # Coordinator: still first

    def test_a_dashboard_frame_on_another_loopback_origin_posts_to_the_referrer_origin(self):
        # parent.location.origin throws cross-origin (dashboard on localhost:9119, page on 127.0.0.1:8799):
        # the old code fell through to the clipboard; now the embedding origin comes from document.referrer.
        script = self.DOM + self._card_fns() + r"""
var copied = [], posted = [];
function copyText(text, done){ copied.push(text); done(true); }
document.referrer = "http://localhost:9119/crew?x=1";
var parentWin = {postMessage: function(m, t){ posted.push([m, t]); }};
Object.defineProperty(parentWin, "location", {get: function(){ throw new Error("SecurityError"); }});
var window = {parent: parentWin, __crewNav: function(){}};
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, posted: posted, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([[{"type": "hermes:open-session", "sessionId": "s1", "profile": "default"},
                           "http://localhost:9119"]], out["posted"])
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_open_session_target_never_throws_and_scopes_the_bridge_frame(self):
        script = self._card_fns() + r"""
var document = {referrer: ""};
var out = [];
var window = {parent: {}};                                         out.push(openSessionTarget());   // host frame
window = {parent: {location: {origin: "http://127.0.0.1:9119"}}, __crewNav: 1}; out.push(openSessionTarget());
window = {parent: {location: {origin: "null"}}, __crewNav: 1};    document.referrer = "https://dash.example:8443/a";
out.push(openSessionTarget());
window = {parent: {get location(){ throw new Error("x"); }}, __crewNav: 1}; document.referrer = "javascript:alert(1)";
out.push(openSessionTarget());
console.log(JSON.stringify(out));
"""
        self.assertEqual(["*", "http://127.0.0.1:9119", "https://dash.example:8443", "*"], self._run(script))

    def test_a_standalone_browser_opens_the_dashboard_chat_when_it_knows_the_dashboard(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], opened = [];
function copyText(text, done){ copied.push(text); done(true); }
var state = {hermes_chat_url: "http://127.0.0.1:9119/"};
var window = {open: function(u, n, f){ opened.push([u, n, f]); return null; }}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/20261012_131459_eb9bfb"));
var btn = box.children[0].children[2];
btn.click();
console.log(JSON.stringify({copied: copied, opened: opened, after: btn.textContent}));
"""
        out = self._run(script)
        self.assertEqual([["http://127.0.0.1:9119/chat?resume=20261012_131459_eb9bfb&profile=default",
                           "_blank", "noopener"]], out["opened"])
        self.assertEqual([], out["copied"])
        self.assertEqual("opening", out["after"])

    def test_a_standalone_browser_with_an_unsafe_or_blocked_dashboard_url_copies_instead(self):
        script = self.DOM + self._card_fns() + r"""
var copied = [], opened = [];
function copyText(text, done){ copied.push(text); done(true); }
var state = {hermes_chat_url: "javascript:alert(1)"};
var window = {open: function(u){ opened.push(u); }}; window.parent = window;
var box = new El("div");
sitDiscussionChip(box, parseSessionCoord("default/s1"));
box.children[0].children[2].click();
state = {hermes_chat_url: "http://127.0.0.1:9119"};
window.open = function(){ throw new Error("popup blocked"); };
box.children[0].children[2].click();
console.log(JSON.stringify({copied: copied, opened: opened,
  urls: [chatUrlFor({sessionId: "s1", profile: ""}, "https://d.example/base/"), chatUrlFor({sessionId: "s1"}, "")]}));
"""
        out = self._run(script)
        self.assertEqual([], out["opened"])
        self.assertEqual(["@session:default/s1", "@session:default/s1"], out["copied"])
        self.assertEqual(["https://d.example/base/chat?resume=s1", ""], out["urls"])

    # dashboard/dist/index.js is one IIFE: its helpers are indented two spaces, so they end at "\n  }".
    def _dashboard_fns(self):
        src = self._read("dashboard", "dist", "index.js")
        out = []
        for rx in ("var SESSION_IDENT_RE", "var LOOPBACK_ORIGIN_RE"):
            rx_at = src.index(rx)
            out.append(src[rx_at:src.index("\n", rx_at)])
        for name in ("parseOpenSession", "isSessionOriginAllowed", "chatResumePath", "openChatSession"):
            start = src.index("function %s(" % name)
            out.append(src[start:src.index("\n  }", start) + 4])
        return "\n".join(out)

    def test_web_dashboard_accepts_open_session_from_loopback_origins_only(self):
        script = self._dashboard_fns() + r"""
var cases = [
  ["http://127.0.0.1:9119", "http://127.0.0.1:9119"], ["http://127.0.0.1:8799", "http://127.0.0.1:9119"],
  ["http://localhost:8799", "http://127.0.0.1:9119"], ["http://[::1]:9119", "http://localhost:9119"],
  ["https://dash.example", "https://dash.example"],
  ["http://evil.example", "http://127.0.0.1:9119"], ["http://127.0.0.1.evil.example", "http://127.0.0.1:9119"],
  ["http://127.0.0.1:8799", "https://dash.example"], ["null", "http://127.0.0.1:9119"],
  ["", "http://127.0.0.1:9119"], [null, "http://127.0.0.1:9119"]];
console.log(JSON.stringify(cases.map(function(c){ return isSessionOriginAllowed(c[0], c[1]); })));
"""
        self.assertEqual([True, True, True, True, True, False, False, False, False, False, False], self._run(script))

    def test_web_dashboard_listens_for_open_session_from_its_own_frame_only(self):
        src = self._read("dashboard", "dist", "index.js")
        handler = src[src.index("function onMessage(e)"):src.index("window.addEventListener(\"message\", onMessage)")]
        self.assertIn("e.source !== frame.contentWindow", handler)
        self.assertIn("d.type === \"hermes:open-session\"", handler)
        # open-session: the origin is checked (own or loopback) before the payload is acted on
        self.assertIn("isSessionOriginAllowed(e.origin, window.location.origin)", handler)
        self.assertLess(handler.index("isSessionOriginAllowed"), handler.index("openChatSession(target, window)"))
        self.assertIn("openChatSession(target, window)", handler)
        # crew:navigate stays same-origin only, checked before the page is changed
        self.assertIn("e.origin !== window.location.origin", handler)
        self.assertLess(handler.index("e.origin !== window.location.origin"), handler.index("setPage(d.path)"))
        self.assertIn("crew:navigate", handler)                                     # board/card links still work

    def test_web_dashboard_navigates_to_chat_resume_with_profile(self):
        script = self._dashboard_fns() + r"""
function makeWin(base){
  var events = [], pushed = [], assigned = [];
  var win = {__HERMES_BASE_PATH__: base, events: events, pushed: pushed, assigned: assigned,
    history: {state: {usr: null, key: "k0", idx: 3},
      pushState: function(s, t, u){ this.state = s; pushed.push(u); }},
    PopStateEvent: function(type, init){ this.type = type; this.state = init.state; },
    dispatchEvent: function(ev){ events.push([ev.type, ev.state.idx]); },
    location: {assign: function(u){ assigned.push(u); }}};
  return win;
}
var w1 = makeWin(""), w2 = makeWin("hermes/"), w3 = makeWin("");
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "20261012_092737_07d8d5",
  profile: "default"}), w1);
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "s1"}), w2);
w3.history = null;                                         // no history API: a plain page load
openChatSession(parseOpenSession({type: "hermes:open-session", sessionId: "s2", profile: "leader"}), w3);
console.log(JSON.stringify({w1: [w1.pushed, w1.events, w1.assigned], w2: w2.pushed, w3: [w3.pushed, w3.assigned]}));
"""
        out = self._run(script)
        self.assertEqual([["/chat?resume=20261012_092737_07d8d5&profile=default"], [["popstate", 4]], []], out["w1"])
        self.assertEqual(["/hermes/chat?resume=s1"], out["w2"])                    # reverse-proxied base path
        self.assertEqual([[], ["/chat?resume=s2&profile=leader"]], out["w3"])

    def test_web_dashboard_drops_malformed_open_session_payloads(self):
        script = self._dashboard_fns() + r"""
var bad = [null, "x", {type: "crew:navigate", sessionId: "s1"}, {type: "hermes:open-session"},
  {type: "hermes:open-session", sessionId: "../../etc/passwd"}, {type: "hermes:open-session", sessionId: "a&b=c"},
  {type: "hermes:open-session", sessionId: "no-session"}, {type: "hermes:open-session", sessionId: "s1", profile: "a/b"},
  {type: "hermes:open-session", sessionId: "s1", profile: "x?y"}, {type: "hermes:open-session", sessionId: "javascript:1"},
  {type: "hermes:open-session", sessionId: new Array(200).join("a")}];
var parsed = bad.map(parseOpenSession);
var calls = 0, win = {location: {assign: function(){ calls++; }}};
parsed.forEach(function(t){ openChatSession(t, win); });
console.log(JSON.stringify({parsed: parsed, calls: calls}));
"""
        out = self._run(script)
        self.assertEqual([None] * 11, out["parsed"])
        self.assertEqual(0, out["calls"])

    def test_a_card_without_a_session_renders_no_chip_and_throws_nothing(self):
        script = self.DOM + self._card_fns() + r"""
var box = new El("div");
sitDiscussionChip(box, discussionCoord({coordinator: "default/no-session"}));
sitDiscussionChip(box, discussionCoord({}));
console.log(JSON.stringify(box.children.length));
"""
        self.assertEqual(0, self._run(script))

    def test_render_sit_fields_adds_the_chip_after_the_coordinator(self):
        src = self._read("scripts", "crew_dashboard", "card.js")
        fields = self._fn(src, "renderSitFields")
        self.assertIn("sitDiscussionChip(box, discussionCoord(state))", fields)
        self.assertLess(fields.index("cardCoCopy"), fields.index("sitDiscussionChip"))


class OriginSessionDiscoveryTests(unittest.TestCase):
    """crew_graph.find_origin_session: a card with no tasks.session_id and no Coordinator: line (a `hermes kanban
    create` from a terminal) still names the discussion it came from,
    read from the profiles' state.db; the card's own worker sessions are never taken for its origin."""

    CREATED = 1791811364

    def setUp(self):
        import sqlite3
        import crew_graph
        self.cg = crew_graph
        self.cg._ORIGIN_CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory(prefix="crew-origin-")
        base = self.tmp.name
        self.board = os.path.join(base, "kanban.db")

        def state(path, sessions, messages):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            db = sqlite3.connect(path)
            db.execute("create table sessions (id text primary key, parent_session_id text, source text, model text, "
                       "title text, started_at real, ended_at real, message_count integer, tool_call_count integer, "
                       "input_tokens integer, output_tokens integer, profile_name text)")
            db.execute("create table messages (id integer primary key autoincrement, session_id text, role text, "
                       "content text, tool_calls text, timestamp real)")
            for sid, src in sessions:
                db.execute("insert into sessions (id, source, started_at) values (?,?,?)", (sid, src, self.CREATED - 900))
            db.executemany("insert into messages (session_id, role, content, tool_calls, timestamp) values (?,?,?,?,?)",
                           messages)
            db.commit()
            db.close()

        c = self.CREATED
        # default: the desktop discussion that ran `hermes kanban create` and saw "Created t_ea95ab52" first
        state(os.path.join(base, "state.db"), [("20261012_131459_eb9bfb", "desktop"), ("old_chat", "desktop")], [
            ("old_chat", "user", "talk about t_ea95ab52 last week", None, c - 86400),          # outside the window
            ("20261012_131459_eb9bfb", "assistant", "", '[{"function":{"name":"terminal","arguments":'
             '"{\\"command\\":\\"hermes kanban create ...\\"}"}}]', c - 2),
            ("20261012_131459_eb9bfb", "tool", '{"output": "Created t_ea95ab52  (ready, assignee=coder)"}', None, c + 1),
        ])
        # coder: the card's own worker session mentions it too (earlier than nothing, but it is the worker)
        state(os.path.join(base, "profiles", "coder", "state.db"), [("worker_sess", "kanban")], [
            ("worker_sess", "user", "work kanban task t_ea95ab52", None, c - 1),
        ])
        # leader: a later reviewer-style mention that must lose to the earliest
        state(os.path.join(base, "profiles", "leader", "state.db"), [("later_sess", "oneshot")], [
            ("later_sess", "tool", "read t_ea95ab52 card", None, c + 600),
        ])
        db = sqlite3.connect(self.board)
        db.execute("create table task_events (id integer primary key autoincrement, task_id text, run_id integer, "
                   "kind text, payload text, created_at integer)")
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_ea95ab52", 1, "session", json.dumps({"session": "worker_sess"}), c + 30))
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_crew", None, "origin", json.dumps({"session": "20261012_092737_07d8d5", "by": "default"}), c))
        db.execute("insert into task_events (task_id, run_id, kind, payload, created_at) values (?,?,?,?,?)",
                   ("t_nosess", None, "origin", json.dumps({"session": "no-session", "by": "default"}), c))
        db.commit()
        db.close()
        self.env = patch.dict(os.environ, {"HERMES_HOME": base})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.cg._ORIGIN_CACHE.clear()
        self.tmp.cleanup()

    def test_a_cli_created_card_resolves_its_discussion_from_state_db(self):
        prof, sid = self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        self.assertEqual(("default", "20261012_131459_eb9bfb"), (prof, sid))

    def test_the_cards_own_worker_session_is_never_its_origin(self):
        import sqlite3
        db = sqlite3.connect(os.path.join(self.tmp.name, "state.db"))
        db.execute("delete from messages where session_id = '20261012_131459_eb9bfb'")
        db.commit()
        db.close()
        prof, sid = self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        self.assertNotEqual("worker_sess", sid)
        self.assertEqual(("leader", "later_sess"), (prof, sid))          # next earliest non-worker mention

    def test_the_row_session_id_wins_and_crews_origin_record_is_next(self):
        self.assertEqual(("", "row_sid"), self.cg.find_origin_session(self.board, "t_ea95ab52", "row_sid", self.CREATED))
        self.assertEqual(("default", "20261012_092737_07d8d5"),
                         self.cg.find_origin_session(self.board, "t_crew", None, self.CREATED))

    def test_no_mention_no_session_and_unsafe_ids_give_no_chip(self):
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_unknown", None, self.CREATED))
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_nosess", None, None))
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "", None, self.CREATED))
        # a row session_id that is not a plain id is not trusted; discovery runs instead
        self.assertEqual(("default", "20261012_131459_eb9bfb"),
                         self.cg.find_origin_session(self.board, "t_ea95ab52", "../etc", self.CREATED))

    def test_a_found_origin_is_cached_and_a_miss_is_retried_after_the_ttl(self):
        self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)
        with patch.object(self.cg, "discover_state_dbs", side_effect=AssertionError("re-scanned")):
            self.assertEqual("20261012_131459_eb9bfb",
                             self.cg.find_origin_session(self.board, "t_ea95ab52", None, self.CREATED)[1])
        self.assertEqual(("", ""), self.cg.find_origin_session(self.board, "t_late", None, self.CREATED))
        prof, sid, found, ts = self.cg._ORIGIN_CACHE["t_late"]
        self.cg._ORIGIN_CACHE["t_late"] = (prof, sid, found, ts - self.cg.ORIGIN_MISS_TTL_S - 1)
        with patch.object(self.cg, "_origin_from_messages", return_value=("coder", "late_sess")) as again:
            self.assertEqual(("coder", "late_sess"),
                             self.cg.find_origin_session(self.board, "t_late", None, self.CREATED))
            again.assert_called_once()

    def test_card_box_fields_carries_the_discovered_profile(self):
        f = self.cg.card_box_fields({"session_id": "20261012_131459_eb9bfb", "session_profile": "default"})
        self.assertEqual("20261012_131459_eb9bfb", f["session_id"])
        self.assertEqual("default", f["session_profile"])
        self.assertEqual("", self.cg.card_box_fields({})["session_profile"])

    def test_hermes_chat_url_is_an_http_base_or_the_loopback_default(self):
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": "https://dash.example/"}):
            self.assertEqual("https://dash.example", self.cg.hermes_chat_url())
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": "javascript:alert(1)"}):
            self.assertEqual("http://127.0.0.1:9119", self.cg.hermes_chat_url())
        with open(os.path.join(self.tmp.name, "config.yaml"), "w") as fh:
            fh.write("dashboard:\n  theme: default\n  public_url: https://dash.example\n")
        with patch.dict(os.environ, {"CREW_HERMES_DASHBOARD_URL": ""}):
            self.assertEqual("https://dash.example", self.cg.hermes_chat_url())


if __name__ == "__main__":
    unittest.main()
