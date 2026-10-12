// Crew tab for the Hermes dashboard.
//
// Hand-written ES5 against window.__HERMES_PLUGIN_SDK__ - there is no build step;
// this file is shipped as-is (manifest.json "entry").
//
// Auth: /api/plugins/crew/* sits behind Hermes's auth middleware, and a plain
// iframe navigation carries no session header (401 in token mode). So every
// page is fetched with SDK.authedFetch and rendered into the iframe via srcDoc.
// Inside the iframe, the bridge script plugin_api.py injects routes the page's
// own requests through the same authedFetch and turns a click on a board/card
// link into a "crew:navigate" message, which this component answers by fetching
// that page the same way. No credential is ever placed in the iframe.
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  var React = SDK.React;
  var h = React.createElement;

  var API = "/api/plugins/crew/";
  // The pages the tab may show: the board (optionally ?all=1) and one card's graph.
  var PAGE_RE = /^(board|card\/[A-Za-z0-9_-]+)(\?all=1)?$/;

  // A card page's discussion chip posts { type: "hermes:open-session", sessionId, profile } (card.js
  // openDiscussion). Only plain identifiers pass: anything with a slash, a dot or a shell character is dropped
  // before it can shape a URL (same rule as card.js parseSessionCoord).
  var SESSION_IDENT_RE = /^[A-Za-z0-9_-]+$/;

  function parseOpenSession(data) {
    if (!data || typeof data !== "object" || data.type !== "hermes:open-session") return null;
    var sid = String(data.sessionId == null ? "" : data.sessionId).trim();
    var prof = String(data.profile == null ? "" : data.profile).trim();
    if (!sid || sid.length > 128 || sid === "no-session" || !SESSION_IDENT_RE.test(sid)) return null;
    if (prof && (prof.length > 64 || !SESSION_IDENT_RE.test(prof))) return null;
    return { sessionId: sid, profile: prof };
  }

  // The origins a card frame may post hermes:open-session from: the dashboard's own, or - when the dashboard
  // itself is served on loopback - any loopback origin (127.0.0.1 / localhost / [::1], any port), so a card page
  // served by the crew daemon (:8799) or reached as localhost while the dashboard is 127.0.0.1:9119 still opens
  // its session. A remote origin never qualifies, and the payload is re-validated by parseOpenSession anyway.
  var LOOPBACK_ORIGIN_RE = /^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(:\d{1,5})?$/i;

  function isSessionOriginAllowed(origin, own) {
    origin = String(origin || "");
    own = String(own || "");
    if (!origin || origin === "null") return false;
    if (origin === own) return true;
    return LOOPBACK_ORIGIN_RE.test(origin) && LOOPBACK_ORIGIN_RE.test(own);
  }

  // The dashboard's chat route for a session, under the base path the server injected when reverse-proxied.
  function chatResumePath(target, basePath) {
    var base = String(basePath || "");
    if (base && base.charAt(0) !== "/") base = "/" + base;
    base = base.replace(/\/+$/, "");
    var q = "resume=" + encodeURIComponent(target.sessionId);
    if (target.profile) q += "&profile=" + encodeURIComponent(target.profile);
    return base + "/chat?" + q;
  }

  // Navigate the dashboard (this window, the iframe's parent) to /chat?resume=<sid>&profile=<prof>. The SPA's
  // router follows history: push the entry the way the router does, then tell it with popstate, so the chat
  // page (kept mounted) resumes the session without a reload. A window without history gets a plain load.
  function openChatSession(target, win) {
    if (!target || !win) return false;
    var path = chatResumePath(target, win.__HERMES_BASE_PATH__);
    try {
      var hist = win.history, prev = hist && hist.state;
      var idx = prev && typeof prev.idx === "number" ? prev.idx + 1 : 0;
      hist.pushState({ usr: null, key: Math.random().toString(36).slice(2, 10), idx: idx }, "", path);
      win.dispatchEvent(new win.PopStateEvent("popstate", { state: hist.state }));
    } catch (e) {
      win.location.assign(path);
    }
    return true;
  }

  function themeQuery() {
    var style = window.getComputedStyle(document.documentElement);
    var rawBg = style.getPropertyValue("--background-base").trim() || style.getPropertyValue("--background").trim() || "";
    var rawFg = style.getPropertyValue("--foreground-base").trim() || style.getPropertyValue("--foreground").trim() || "";
    var isDark = !rawBg || rawBg.toLowerCase().indexOf("fff") === -1;
    var bg = rawBg.charAt(0) === "#" ? rawBg : (isDark ? "#041c1c" : "#ffffff");
    var fg = rawFg.charAt(0) === "#" ? rawFg : (isDark ? "#ffffff" : "#17171a");
    return "theme=" + encodeURIComponent(isDark ? "dark" : "light") +
      "&bg=" + encodeURIComponent(bg) + "&fg=" + encodeURIComponent(fg);
  }

  function CrewPage() {
    var iframeRef = React.useRef(null);
    var pageState = React.useState("board");
    var page = pageState[0];
    var setPage = pageState[1];

    var htmlState = React.useState("");
    var html = htmlState[0];
    var setHtml = htmlState[1];

    var loadingState = React.useState(true);
    var setLoading = loadingState[1];

    var errorState = React.useState(null);
    var error = errorState[0];
    var setError = errorState[1];

    var loadPage = React.useCallback(function () {
      setLoading(true);
      setError(null);
      var url = API + page + (page.indexOf("?") === -1 ? "?" : "&") + themeQuery();
      SDK.authedFetch(url)
        .then(function (res) {
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          return res.text();
        })
        .then(function (text) {
          setHtml(text);
          setLoading(false);
          setError(null);
        })
        .catch(function (err) {
          setHtml("");
          setError(err.message || String(err));
          setLoading(false);
        });
    }, [page]);

    React.useEffect(function () {
      loadPage();
    }, [loadPage]);

    // Board/card links clicked inside the srcdoc page arrive here (see the bridge in plugin_api.py), and so
    // does a card's discussion chip (hermes:open-session), which opens that session in the dashboard's chat.
    React.useEffect(function () {
      function onMessage(e) {
        var frame = iframeRef.current;
        if (!frame || e.source !== frame.contentWindow) return;
        var d = e.data;
        if (d && d.type === "hermes:open-session") {
          if (!isSessionOriginAllowed(e.origin, window.location.origin)) return;
          var target = parseOpenSession(d);
          if (target) openChatSession(target, window);
          return;
        }
        if (e.origin !== window.location.origin) return;
        if (!d || d.type !== "crew:navigate" || typeof d.path !== "string" || !PAGE_RE.test(d.path)) return;
        setPage(d.path);
      }
      window.addEventListener("message", onMessage);
      return function () { window.removeEventListener("message", onMessage); };
    }, []);

    if (error && !html) {
      return h("div", {
        style: {
          padding: "2rem",
          maxWidth: "32rem",
          margin: "4rem auto",
          border: "1px solid var(--border, rgba(255,255,255,0.1))",
          borderRadius: "0.5rem",
          backgroundColor: "var(--card, rgba(255,255,255,0.02))",
          color: "var(--foreground, #ffffff)",
          fontFamily: "var(--font-sans, system-ui, sans-serif)",
          textAlign: "center"
        }
      },
        h("h3", { style: { margin: "0 0 1rem", fontSize: "1.25rem" } }, "Crew Dashboard Unavailable"),
        h("p", { style: { margin: "0 0 1.5rem", opacity: 0.8, fontSize: "0.875rem", lineHeight: 1.5 } },
          "Could not load the Crew board (" + error + "). See the Hermes server log for the error."
        ),
        h("button", {
          onClick: page === "board" ? loadPage : function () { setPage("board"); },
          style: {
            padding: "0.5rem 1.25rem",
            backgroundColor: "var(--primary, #34d399)",
            color: "#041c1c",
            border: "none",
            borderRadius: "0.375rem",
            fontWeight: 600,
            cursor: "pointer"
          }
        }, page === "board" ? "Retry" : "Back to board")
      );
    }

    return h("div", {
      style: {
        width: "100%",
        height: "calc(100vh - 3.5rem)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--background, #041c1c)"
      }
    },
      h("iframe", {
        ref: iframeRef,
        srcDoc: html || undefined,
        style: {
          width: "100%",
          height: "100%",
          border: "none",
          flex: 1,
          backgroundColor: "var(--background, #041c1c)"
        },
        title: "Crew Board"
      })
    );
  }

  if (window.__HERMES_PLUGINS__ && window.__HERMES_PLUGINS__.register) {
    window.__HERMES_PLUGINS__.register("crew", CrewPage);
  }
})();
