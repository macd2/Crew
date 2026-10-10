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

    // Board/card links clicked inside the srcdoc page arrive here (see the bridge in plugin_api.py).
    React.useEffect(function () {
      function onMessage(e) {
        var frame = iframeRef.current;
        if (!frame || e.source !== frame.contentWindow || e.origin !== window.location.origin) return;
        var d = e.data;
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
          "Could not load the Crew board (" + error + "). Make sure the crew daemon is running on 127.0.0.1:8799."
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
