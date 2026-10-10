// Hand-written React component registering Crew with Hermes Dashboard SDK.
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  var React = SDK.React;
  var h = React.createElement;

  function CrewPage() {
    var iframeRef = React.useRef(null);
    var htmlState = React.useState("");
    var html = htmlState[0];
    var setHtml = htmlState[1];

    var loadingState = React.useState(true);
    var loading = loadingState[0];
    var setLoading = loadingState[1];

    var errorState = React.useState(null);
    var error = errorState[0];
    var setError = errorState[1];

    var loadBoard = React.useCallback(function () {
      setLoading(true);
      setError(null);
      var fetchFn = (SDK && SDK.authedFetch) || window.fetch;
      var style = window.getComputedStyle(document.documentElement);
      var rawBg = style.getPropertyValue("--background-base").trim() || style.getPropertyValue("--background").trim() || "";
      var rawFg = style.getPropertyValue("--foreground-base").trim() || style.getPropertyValue("--foreground").trim() || "";
      var isDark = !rawBg || rawBg.toLowerCase().indexOf("fff") === -1;
      var theme = isDark ? "dark" : "light";
      var bg = rawBg.startsWith("#") ? rawBg : (isDark ? "#041c1c" : "#ffffff");
      var fg = rawFg.startsWith("#") ? rawFg : (isDark ? "#ffffff" : "#17171a");
      var query = "?theme=" + encodeURIComponent(theme) + "&bg=" + encodeURIComponent(bg) + "&fg=" + encodeURIComponent(fg);

      fetchFn("/api/plugins/crew/board" + query)
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
          setError(err.message || String(err));
          setLoading(false);
        });
    }, []);

    React.useEffect(function () {
      loadBoard();
    }, [loadBoard]);

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
          onClick: loadBoard,
          style: {
            padding: "0.5rem 1.25rem",
            backgroundColor: "var(--primary, #34d399)",
            color: "#041c1c",
            border: "none",
            borderRadius: "0.375rem",
            fontWeight: 600,
            cursor: "pointer"
          }
        }, "Retry")
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
