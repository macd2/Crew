// GENERATED from ui/src/desktop.tsx by ui/build.mjs. Do not edit by hand: change the source and run `node ui/build.mjs`.

// src/desktop.tsx
import { useMemo as useMemo4, useState as useState13 } from "react";
import * as sdk2 from "@hermes/plugin-sdk";
import { PANES_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA, useTheme as useTheme2 } from "@hermes/plugin-sdk";

// src/avatars.ts
import { useEffect, useState } from "react";
function faceName(name) {
  const n = String(name || "").toLowerCase().replace(/^crew-/, "").replace(/[^a-z0-9_-]/g, "");
  return n || "unknown";
}
var BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
var cache = /* @__PURE__ */ new Map();
function useAvatar(api, name) {
  const direct = name && api.avatarUrl ? api.avatarUrl(name) : "";
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!name || direct) return;
    const n = faceName(name);
    let hit = cache.get(n);
    if (!hit) {
      hit = api.get("/embed/avatar/role/" + n + ".svg").then((r) => {
        if (!r || !r.data_url) throw new Error("no data_url for " + n);
        return r.data_url;
      });
      hit.catch(() => cache.delete(n));
      cache.set(n, hit);
    }
    let live = true;
    hit.then((u) => {
      if (live) setUrl(u);
    }, () => {
    });
    return () => {
      live = false;
    };
  }, [api, name, direct]);
  return direct || url || BLANK;
}

// src/api.ts
function restApi(ctx) {
  return {
    get: (path) => ctx.rest(path),
    // The components speak the browser's paths; the Desktop plugin API answers acks as JSON under /embed/ack/.
    post: (path, body) => ctx.rest(path.startsWith("/ack/") ? "/embed" + path : path, { method: "POST", body })
  };
}

// src/blocked-watch.ts
function blockedWatch(read, onBlocked) {
  let seen = null;
  return async () => {
    let board;
    try {
      board = await read();
    } catch {
      return;
    }
    if (board.error) return;
    const now = /* @__PURE__ */ new Map();
    for (const lane of board.lanes || [])
      if (lane.key === "blocked") {
        for (const t of lane.tiles) if (t.status === "blocked") now.set(t.id, t.title);
      }
    const before = seen;
    seen = new Set(now.keys());
    if (!before) return;
    for (const [id, title] of now) if (!before.has(id)) onBlocked({ id, title, message: title || id, detail: id });
  };
}

// src/components/CrewPage.tsx
import { useEffect as useEffect10, useState as useState11 } from "react";
import * as sdk from "@hermes/plugin-sdk";
import { useTheme } from "@hermes/plugin-sdk";

// src/theme.ts
function crewVarsFromTheme(theme, mode = "light") {
  const c = mode === "dark" && theme.darkColors ? theme.darkColors : theme.colors;
  return {
    "--crew-bg": c.background,
    "--crew-fg": c.foreground,
    "--crew-font": theme.typography?.fontSans ?? "system-ui, sans-serif",
    "--crew-mono": theme.typography?.fontMono ?? "ui-monospace, monospace",
    "--crew-in-blocked": c.destructive,
    "--crew-in-ready": c.primary,
    "--crew-in-running": `var(--ui-success, ${c.primary})`,
    "--crew-in-done": "color-mix(in srgb, var(--crew-in-running) 55%, var(--crew-in-ready))",
    "--crew-in-review": "color-mix(in srgb, var(--crew-in-blocked) 45%, var(--crew-in-running))",
    colorScheme: mode
  };
}

// src/open-card.ts
var CREW_ROUTE = "/crew";
var cardLink = (id, stamp = Date.now()) => CREW_ROUTE + "?card=" + encodeURIComponent(id) + "&n=" + stamp;
var CARD_ID = /^[A-Za-z0-9_-]+$/;
function cardFromHash(hash) {
  const m = /^#?\/crew\?(.*)$/.exec(hash || "");
  const id = m ? new URLSearchParams(m[1]).get("card") || "" : "";
  return CARD_ID.test(id) ? id : "";
}
function cardFromSearch(search) {
  const id = new URLSearchParams((search || "").replace(/^\?/, "")).get("card") || "";
  return CARD_ID.test(id) ? id : "";
}
function cardFromHref(href) {
  const raw = (href || "").trim();
  if (!raw) return "";
  if (raw.startsWith("#")) return cardFromHash(raw);
  let url;
  try {
    url = new URL(raw, "http://crew.invalid");
  } catch {
    return "";
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return "";
  const p = url.pathname.replace(/\/+$/, "");
  if (p !== CREW_ROUTE && !p.endsWith(CREW_ROUTE)) return "";
  return cardFromSearch(url.search);
}
var pendingCard = "";
var openListeners = /* @__PURE__ */ new Set();
function openCardRoute(path, navigate) {
  const id = cardFromHash(path) || cardFromHref(path);
  if (id) {
    pendingCard = id;
    openListeners.forEach((fn) => {
      try {
        fn(id);
      } catch {
      }
    });
  }
  navigate?.(path);
}
function takePendingCard() {
  const id = pendingCard;
  pendingCard = "";
  return id;
}
function onOpenCard(fn) {
  openListeners.add(fn);
  return () => {
    openListeners.delete(fn);
  };
}

// src/card-open.ts
var open = false;
var subs = /* @__PURE__ */ new Set();
function setCardPageOpen(v) {
  if (open === v) return;
  open = v;
  subs.forEach((fn) => fn());
}
var cardPageOpen = () => open;
function subscribeCardPage(fn) {
  subs.add(fn);
  return () => {
    subs.delete(fn);
  };
}

// src/key-scope.ts
var EDITABLE = '[contenteditable=""],[contenteditable="true"],[contenteditable="plaintext-only"]';
function isEditable(el) {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return el.isContentEditable === true || !!el.closest(EDITABLE);
}
function isCrewKey(e, root) {
  const n = e.target;
  const t = n && n.nodeType === 1 ? n : null;
  if (isEditable(t) || isEditable(document.activeElement)) return false;
  if (!t || t === document.body || t === document.documentElement) return true;
  return !!root && root.contains(t);
}

// src/components/Board.tsx
import { useEffect as useEffect4, useMemo, useRef as useRef4, useState as useState4 } from "react";

// src/data.ts
import { useCallback, useEffect as useEffect2, useRef, useState as useState2 } from "react";
function useBoard(api, intervalMs = 2e3, query = "") {
  const [board, setBoard] = useState2(null);
  const [error, setError] = useState2(null);
  const [loading, setLoading] = useState2(true);
  const [tick, setTick] = useState2(0);
  useEffect2(() => {
    let live = true;
    const load = () => api.get("/board.json" + (query ? "?" + query : "")).then((b) => {
      if (live) {
        setBoard(b);
        setError(null);
      }
    }).catch((e) => {
      if (live) setError(String(e && e.message || e));
    }).finally(() => {
      if (live) setLoading(false);
    });
    load();
    const timer = setInterval(load, intervalMs);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [api, intervalMs, query, tick]);
  return { board, error, loading, refresh: () => setTick((n) => n + 1) };
}
function useCard(api, id, intervalMs = 2e3, paused = false) {
  const [card, setCard] = useState2(null);
  const [error, setError] = useState2(null);
  const [loading, setLoading] = useState2(true);
  const loadRef = useRef(() => {
  });
  useEffect2(() => {
    let live = true;
    setCard(null);
    setLoading(true);
    const load = () => api.get("/card/" + encodeURIComponent(id) + ".json").then((c) => {
      if (live) {
        setCard(c);
        setError(null);
      }
    }).catch((e) => {
      if (live) setError(String(e && e.message || e));
    }).finally(() => {
      if (live) setLoading(false);
    });
    loadRef.current = load;
    load();
    if (paused) return () => {
      live = false;
    };
    const timer = setInterval(load, intervalMs);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [api, id, intervalMs, paused]);
  const reload = useCallback(() => loadRef.current(), []);
  return { card, error, loading, reload };
}

// src/host.ts
import { createContext, useContext } from "react";
var CrewHostContext = createContext({});
var useCrewHost = () => useContext(CrewHostContext);

// src/mark.ts
var MARK_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB2aWV3Qm94PSIwIDAgNjQgNjQiPjxzdHlsZT4ub24tbGlnaHR7ZGlzcGxheTpub25lfUBtZWRpYSAocHJlZmVycy1jb2xvci1zY2hlbWU6bGlnaHQpey5vbi1kYXJre2Rpc3BsYXk6bm9uZX0ub24tbGlnaHR7ZGlzcGxheTppbmxpbmV9fTwvc3R5bGU+PGltYWdlIGNsYXNzPSJvbi1kYXJrIiB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIGhyZWY9ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBRUFBQUFCQUNBWUFBQUNxYVhIZUFBQVFVVWxFUVZSNDJzMWJmV3hjVlhZLzk3NzNadnlObmNRMmdaQ0ZoSUtXTE5rQTNRM2JzaVJwVnl5c3VpU0FKcWpidEJUVVpIZmJyaWlpNlc2N29vTlhyVmFzRmdVSmhKcHVWS1NHRU5WVDFpUkVRNFJJSnc3WlFCeWJPSVRZanJPeDQwbG04SXp0K1o1NW4vZWUvdUgzSmpmamVlTUpjV3llOUdScjNzeTk1M2ZPdWVmN0VaakRDeEVKQUVnQXdBZ2g2SHgrKysyM2UzZnYzcjJpdmIzOUR4UkZXZUgxZW05c2FtcHFIQjhmdnhrUmFYdDdleVNSU0dpRWtERlZWY2NZWTBQUFB2dnN5TUdEQi9YWjFyN1dpOHdoY0VvSVljNW4vZjM5ZHl4YXRPZzc5ZlgxRzd4ZTcycEprcjVTVTFQanJXWTlYZGQxeTdMQ2pMRlBKaVltamhtR2NmQ3V1KzRhRnZhVEFJRFBKU091QmJ6ay9MOWp4NDdtQ3hjdWJFMG1rOTJhcHBrNDgrS0lhTTF5czlJZmFacG1aclBaN2tna3N2WEFnUU10NWZaZUNPRFVsank4L3ZycmJXTmpZeDM1ZkQ1Y1FydkpHSE5BY2F6KzR2WnZMRVM4Z3BHRlFpRVNpOFU2M243NzdUWUFBRUlJSUNLZFYvQ2hVRWgyanRESXlNaFBzdGxzVktEUmtlVFZBSzZHSWM2NmlJaVl6K2VqNFhENEp3QkFiWUhJODRHZE9HclgxOWUzT3AxT2Q1ZEltMStGVk12ZHMycUx2VWRSSzVMSjVMRyt2cjdWd3BFZzEwdmxpYU5xRnk1YytCdFZWWE5WQU9mbDFMakt5NnlrU1NJak5FM0xYYng0Y2F0QVo5Vk1xRXB0L0g0L3BaUnlSTVJvTlByYTBxVkwvODUreEFCQXBuVEdFZVQyTGR1dUMzVERBTWFzVWRNd0wxaVdkWWxTR290R293QUEwTmJXQnB6emRrVlJsbm05M2x0bFdiN042L1dLdERGYnNzV05LS1hFWHA5NXZkNzZaY3VXL1djc0ZydVhFUEszMDN4QU1pZGV3dS8zVTBJSVBQWFVVelh4ZUh5L0lCMWVRZUtJaUtocVdqYVZTdjEyYkd4c1cyOXY3OTErdjk4ejIzNCtuODl6N05peHU4Zkd4cllsRW9tdVFrSE5sdGdYdDMxTlJNUllMUGJ1a1NOSFdrVWpmYzFxLzl4eno5VW1rOG4zN2MwTUY1VVZEZFJJSkJMNVdlaWpqMjUxOFI2eXl6MURsVDc4c0hmNXhNVEVQK2J6K1pGeWV4VTV3RGtpb29xSWVQNzgrZWV2MlREYTRDVUFJQk1URSsrNmdiYzN0dXl6bUloRUl2KzhhOWV1UnRGWGgwSWh1VnFKT0V5M2YxUDA4N3QyN1dxTXhXTGJDNFZDeW1HQ3ZUZUt0S1hUNmQ4Z291ZWFYYVBEdmZIeDhkZmR3TnVHaUNNaVRrMU43Zi80NDQ5dkUzL3Y5L3ZwSEJuZm9pUVBIVHEwY21wcXlqbUtYRFNHMld6MnY3NklJWFNON3M2ZS9mMjJDbXJQRUJFTncrQ1hMbDNhTGdLLzVyTlhCU011WHJ6NE04TXdITmNxZ3I5QzAveCtQNzJxaUJFUktTRUVUcDA2ZGFlcWFxcUw0V0cyeXVjSEJnWWVjNWcySHhHWkRWQUNBQmdjSEh4VTEzVTFuVTd2RldpNEFueEp2bEsxOUdrcWxmNnduTUZ4MU40d2pQVFkyTmdEOW0rVUJRakZaU2NnZSthWlp4cnRrSmlVUnF1aFVPaHJseTVkZXFVcUpnaXEvMFBCM2Mxd2M3cXVXOFBEd3c4dEZIaFJHeXFGNnNGZ2NHVTZuUjVGUkJ3ZEhmM3ppZ21VWXpnNk96c1g1ZlA1bUszbXJFeDBocU9qb3o5ZWFQRGxraklSWURBWVhKbE1KaTg0V3F5cTZxVmdNTmprYWlBRnEvK3ZMdEszN0VCano1Y0Z2SnRHN04yN2QyVXFsYnBnSDlsaUtCNE9oMThvR3g4NFhPbnE2bW91RkFvVFF1SWlHajFXS0JRaWUvYnNhVUZFT2hjdTducG93cEVqUjFhblVxbFJBYnhEUDgvbjh4TmRYVjNOTTdUQTRjalkyTmlQSzBrL0hBNy9vQ1FkL3RKY0RrMzkvZjEvNllMQjBZSy9GekVUUndNSUlTU1ZTcDI0NFlZYjdyRVRHUWtBZ0hQT0thVTBrVWg4dW5qeDRuc1FFUWdodkxJNGdQZ0NQaHB2amM5SlBOQTIwWWFCTXdHRUR1QlZ1SENleldhUE5UUTBmTXRPb2lRaG9hTFpiTGEvcWFucEQrMXNDWXZuNXVUSmsydE0wK1JsZkw2RmlEZzBOUFRrYk5MM281LzY4Zm9kamRuV2QyZ2JHaHJ5dWVRTTNEUk5mdmJzMmE4N0RKUDcrdm9rQU9DMzNITExuOG15VEFEQUV0SmtEZ0JTTHBlN3NIZnYzbjIycHJDeVdWeW5UK29nSFF3QTREdnZQM3FUcWNoM1VZNDNXZGExUllXeVRKQlRFbFZNYTZDRGRFU2R2UUtiQXpQbzJMQmhBME5FOHVLTEwrN2J2bjM3U0gxOS9Rb2JnOE0wSnN1eTNOemMvRGdBbk9ycjY1T0lvemFaVE9aM2pZMk5mMVNpTmhZQXlCTVRFNzlzYTJ2N0YwU1VDU0ZXT2NsMGtBNys0SHVidmtXOWREc2cvaWxWcENZaXpVMUVqQllDTjFtV1VEakVMWGlwKzZHdWo1MDl5M2t6UW9nVmk4WCtyYTJ0N2VjbEFtVUFJS1ZTcWVNdExTMzNJeUtsaEJBZURBWmJ2Vjd2M1U2dFFWaFA0cHhESXBIb0FnQVNDQVJLQ3d6RWxqeC84UDFOdjVCcTZPOGtqL1FZY0dpeUNpWTNzNlkxRjdlbG1od1FHcWxIM2tSbGNtejkrNXY4SGFTRCt6cDlNMHBnRG8yUlNHUWZZd3dFWVJheDFkWFZmZTJERHo1b0o0UndDZ0N3WXNXSzFSNlBwOUZXRnlLb1B5a1VDcEdkTzNkK0JnRG84L2w0aWRyVHdPWUErL2JCamE5NG03MHZjSU9qbVRNWU1rUkNDQ1VFNUxtNUNVV0dhT1lNeGsyT1NyUDN4VzhITjc0UzJCeGd2azRmTFNtb2NBQ0FOOTU0NDFOZDE4ZHNQRnpvZ3pDUHgxUGYzdDYrcHNpUmxwYVd1d1RRWWxrTEdHTTlPM2JzVUJGUkVrdE16amw4OE9DanozaWJhNTQxa3JvSkNJUVFJZ0c1RG9WSllxK05RSXlrYm5wYnZNK3VQL2pvWDloTUtFcVpFSUtJS0wzNjZxdTZxcXI5WlhBaEFFQjdlL3VxSWdNSWtiN3F0cStxcXAvTzZDSWhrTURtQUgvZ3dBOWFDQ0cvc2dvR0I4RHJBN3dNSXdCUXNsU0xJNlU3MW9VMk5nZDhBUTU0eGQ0RUFDQ1R5Wnh4VzRZaGZyWElBRVdSbDd1MXluSzUzSGtBZ01PSER4Yy9XM2Q0blFRQUtNbnFGcVhSdTVqcnlBSElQRWFHaEhLRGM2WEIwOG9OZUJJSW9FMFRpTFFpNHFCYk8xQlJsR1dDQnRBbGR0QkRTZzJHcnVzUkFJRDE2OWNYMWI5N2ZUZTN1d1RmUjRZSUN4UVVJME9rQ0J0dCtvcHE3dEJxR01hbFVzTmV4TWg1bTZBQlVwMWRhblk0NTNBS0xjdEtpbWZIVmtKK1grODJCUUJYY3BNUkFqanZMQ0FFS2JjWUFZRGJmVGp0aVFRTlJodkhKT2NjSFN3aXh0cmFXa1ZnZ0lKWExrNFFBSWhwV3JoMDZkSnNTWmdMQUFDZXFZa1dBTktLSEFHUWtQa1hQeUhJRUlCQVcveXcybktGaU95cm9hRkJZNHhodWFQdDlYcXh5QURPdWN0SkkyQ1E4dUE4SG00Z29MSGdXU0NBQlNCWjVaNlpwa2xkeUhlMGZKb0JtcVpCQ1NNSUFLQXNTU1NmU0RUYkFRYXhuK0MwSFhnbkRVREdpVXdCS1BKNVIwNFFpVVNCSU1TN0Q2L0ppQ2Jjb1hWaVltS1JKRWxVakc4Y2pMbGNqaFFaSU12eWxIMCtzQ1FPSUxJc3R3SUF0TGEyRWpFR0FFS1FBSnlpQ2tYazh6K29nRWc0OVZCRUlLZWdveGdWb2tqcmtpVkxXbXdOUUtHbGh2WXhUeFlaWUJqR1pJbWhLLzR2U2RLdHRtV2RRUVRuNUMzZ1NBQ1FMSUR5RStCSXFFVGVMSDNpME1vNXVjME5GMk5zUW5SMVliZHQ2bXZyWndSSmdjMEJCbjQvL2ZEajFlK1plYk5Ycmxja1JMRG1UL3BneWZXS1pPYk4zc05IVjc4SGZqOHRseDAyTnplNkJuZ21NMGVLREdDTW5YWUxHRHcxbm51RlRPcHl6TDFxZ0VCSEJ5Y0V0cUxKTmFwUUdSSFpQSlMrR0pXcHpDMnVJOUlmUWtjSDk2MGFLTlZBYmx2NnI3c0ZlRnBCTzFka1FDS1IrTXkyaWpNeUowVlI3dW5zN0x6WmpyR0pxQVcrVHAvVS9kMTkvVXhqVHhBSk5MbHVXaE9tR1lGOEx1L3B1aDVZY3AwaUVRa01yckxIUDN5azY1UFMyb0JkcytEQllMRFY0L0dzS1pQaFVrU0VWRDcxYWZGQmYzLy9rS1pwc1hLWlUxMWRYZTM5OTkrL1RoaFRnMUltSFBuZXZxQ1Y1ZXVRNFFtbFVaR1ZCbzlFUFRLbGlrU3BSNXIrVys3MlZQRmNrU2oxeUZScDhFaEtveUp6eGsrWkJmTlBqbnh2WDlDbE1DSWhJbG0xYXRYNm1wcWFScmc4V3dCMlVFUlZWWjNxL2FoM3dIWW1LQkZDV0RxZDdtcHFhdHBvMXdDZGVpQ2psRXFwVk9wQVMwdkw5NTN2bHFzR0JUWUhHUGg4MG9ZZnNTYzU0T01FWVJWeTlDSldTSkFRZ0FCeUpCWHlDQUpBQ1doQTZXZEE4QjNzVHZ4UGQwZTM1VllWY21pY25KenNXcng0OFNZSGc0T0hFQ0tsVXFtRGl4WXRlZ1FSSmRuaHp1VGs1QWROVFUyYlJGZElwK05Hckt1cmU2aW5wMmNGQUl3NkZhUlNUYkFyTkN3VWdMY0E0QzAvK3VtQnZzOHJOeVg3QUJydU9JdjV4anNyZXBHKyszWmFJS1Rpemw0dWZRRis0TUNCcjlUWDF6OE1BRWlGOFJVSG02cXF3U0o3bmFMby92MzdsMnVhVmhCYVlGZVVrNVBKNUNzVlcwdE9oUWg5a3BpZno5WGw2L1JKUHZSVkhJSnlTdDNoY1BqbE1xVnhiamQwOVZBb2RPc1ZyVFVIMU5UVTFEdml1SWs0M2FYcmV1SG8wYU1yeFdHcFdUUDNhZlcvdHZ2eUdsVTFSb0xCMERKN3JJYVhFU1Nmbkp3TXp1Z3JPZ3c0YytiTUl5N2xaQXNSTVpGSS9HL1oxdEtYb3pNa0F3REVZdkUzSzJFWUdocmFXTGE4ajRqVTUvTkpoVUxoazlKaEozR0I0ZUhoSjc1c1RCRDZBUTh6eHR6QTgzUTZQZWozKzUwQkRsSjJrZkh4OGNkY09NZ1FrZVh6K2NtalI0L2V0Q0FqcXU3ZElOaS9mLytTWEM0WEtkUFhMR0laUEh2MnJ5czJkMnhBTkpQSkhLK2tSdWwwK3FqRHlZVnNrZ3FEWEhJNm5YNS9GcHI3Nzd2dlBzWEc2Sm9qUzNaZzlJQmxXWWlJWnNra1ZySGpPalUxMWVVRUhRdWhDZmJzRHdVQWlNZmovMTJ1SVdyVGJqTEc4UFRwMHh1cThHS1h2M0R4NHNYWFhicXN4YytpMFdpWEV4M081K2k2dUZjNm5mNlAyZWlNeFdLL3FacEdSNkk3ZCs2c3kyYXpBMjZEaWM3aTZYVDY0SjQ5ZTVZNGh2RjZUSWhkV1FhWk5yNDdkKzY4WVhKeWNsOEY4QllpWWlhVCtmM3UzYnVicm1weXRMT3pVM0k2eHBxbWFTN2pNaWpNNTUwN2ZmcjBINWNZMUxsa0JBbUZRckpUM3VydDdWMmJ6V2JQdUlHM0I3a3NYZGYxbnA2ZWI0aVlydHExakl5TVBPbWNKWmM1WFFzUlVkZDFJeGFML2VLMTExNXJFSDN6dGRnSCs1d1hMZmEyYmR2cW90SG9DNnFxNmlVVElHWG5oa2RHUnY2cW90V3ZOcmdZSFIxOWJwWWhhU2JNQ1o4OWQrN2NWcC9QVjF0eXJHUm5sbER3dzhYYk9YcjJkNjQ0U2o2ZnJ6WWFqVzRScEk0dUdsa0VINGxFZmpvbjhVcHZiNjhDQUpCTUpwOFg0NEhaSnNXejJleFFOQnI5ZVU5UHo1M3V0WDBDcEVKRi9kQ2hRM2QrL3ZublA4MWtNa096VFl3N2FvK0lPREF3OEt0cXdaTnFOWUVRWW8yT2p2N0Q4dVhMZDlnSkZpdXREd2pWR0hTZTZicHVxcHJheXhuL3Yxd3VkendXaXcyZk9YTW05dlRUVDJmRUlzWExMNy9jdEhidDJ0YjI5dlk3R3hvYTF0YlYxVDBveS9MYXVybzZSYWhJa1pMaUJnalBKTnNsYm05dmIvKzEyeXpERjJLQXlJVGg0ZUVubGkxYjlrWnRiVzBqVEE4ZnVHVm80a3NUbDB0Um1zWTU1MGxFVE9xNmpvZ0lYcStYRWtKYUpFbHFycW1wS1FWbzJhQnB1ZHErRFZMV2RUMGZEb2QvZE1jZGQ3eHAwOHBtdGtybUtPRTRkdXpZM1psTXBxZlMvTDdMYXpOV0ZhL0tXTE85TGxONkZES1pUUCtwVTZmdW5aY2N4YkdvRHovOHNEY2FqZjY3cXFxR0NMUTBjaXpIRVB1OE12RVdSKzlkZjNqNTNRU0dpS2lxcWhXUHgzKzVaY3VXK211eTlsODBBUUVBNk9ucHVXZHljdkxkTXZFQnE0SVpzNzh2TjcwR0svWDNxVlRxd0lrVEo3NVprc2ZNZDNQcWNtZ1pEb2ZYSlpQSmZacW1XV1hjVXZGMXVFcE1zWitWdmw3SGhUZElXVEtaZkhkd2NQQzdZbGg4bmFQUHFpb3hSZTRmUDM1OFRUd2VmeW1YeXcxV0FDdUN0Q3E0VnVTY1l5NlhHeHdmSDMvcDVNbVRhOXoyWGZDcnM3T3o5SVVKK2VUSms5OGNHUm41cDNnOC90dHNOanVvcW1yS01BeFhEVEFNQXpWTlMrWHorVE9KUkNJUWpVYWZQMzM2OURkRVQ0S0k5S3JEMnJsd2cxZWpFVEQ5Sm5tcEQ1WkRvZENOTFMwdE45ZlUxTnk0ZlBueW1zSEJ3WnNsU1lLVksxZEd6cDgvYnlxS0Vvbkg0NUVOR3paOFh0cUpzcTA3bjNWTTl5cXYvd2Z5Yk5pa2t1R043UUFBQUFCSlJVNUVya0pnZ2c9PSIvPjxpbWFnZSBjbGFzcz0ib24tbGlnaHQiIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgaHJlZj0iZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFFQUFBQUJBQ0FZQUFBQ3FhWEhlQUFBU1gwbEVRVlI0MnMxYmVYU2MxWFgvM2Z2ZU55UEpsdkVpNzhhN0xiekpKa3FLU1JQa3BDU0IxQmdLa1JNYWNwS1FsbEtXSkNTbEpVMDVZamc5elVKeW9BZVNBQ1doVFZOYUxBNWdsNEJJbWdRVGtoRGpnRzNBZUYrMDJwSmwyVm9zelh6djNkcy81aHY1MDJnazJ5QTd2SE8rNDJQTnpQdmVYZDY5di91Nzd4RkdkaEFBQThBRDBOd2ZiNzMxMXVTR0RYVnpoWGdCMU05VjFTa24raktsaWNCT0p5Sk9wOU5OSmNWRmZhcDZVQlFIUnhjWDc3anNzZy92dS8vKys5T25tbnNrRmp4UzgzQzBPQkFSWnM4dVg1Z08wNWM2N3o2a2dnb3ZmaFlSSnhVQU5MdCtIYlFJQXFBZ0lBM21laVo2TlpHd3YwMlVKT29PN055eFMwK0tiUURJU0NoaUpCU1Fzd3FXTDE4K3R2WEk4V3BSdWk0TU0rOG5JcXVxMEpNcjEyamhwNk5NRUJHSUNLcnFESnZmSnBMQlQ4YlBuUHJFNnkrOTFKSC83aitHQWpnU1NPZk9yWmpVMWR0eHN3bytyNnJuaTJqT09DNTZSL3c1bmFFbkgxV0FMRUJnSmhDaE9abElQakpoM0tqdmJkdTJyVFcyRmptWENyQUFuS3JTckZrTGIrbE45MzdOQzZhcUNnRDEwYlE4Z2xzczhod0ZRSWFZUVlTV1JHQy9jY01YUHZ1OVZDb2x1VFdkYlFYMDcvVTVDeGRXZEIvdnUxOVVMeEh4T1d1YlllYlV2R2VvK1UvbExSb3AyUkl4ak9YZmpTNHF1bkgvL2wzYjNrNXNvRE1VbmdESWpCbHovcW8zNCs0VGxWRXE0b2hvS01FMXRpQ2JtNFlvbWk3K0M5VW9OdWJXcmc3WmIvTFFjNnNIMkRKVHo2aVM0dHZxRCt6K3Q5aDNkU1FWd0FDRWlEQjUycXdId3REZExDS0lBcEFwOEgySkhrdEVBRkgyUmFyN2d5QTRRS0JHVVRtY1NBUUFBT2M4UkdVeWdXYUV6czBHTUNmNzlmNEE2dVBCTVc5NEFJYVpZUVA3NEtIRy9UY1JrZmFubEJGUUFBT1FtcHFhb29jZStZOTFtWXk3UXRRN1FrR3JLNkRTdjArQmJtYit1VTBFZGNYRjluZVZGUlU3bjNpaU5xTTY5R0krVVYyZDJMWnRSM2wzdXUvaVRGLzZjbEc5VkVWSHgrSUxEL0ZlVDhRMm1VdytzM3pwd3V2cjZ1cmFUN0hkVGtzQkJJQnV1KzIyNU9PMTY5ZW5NK0ZIdkhjaEVRVkRXWUtZWVpqMjJ5QjRlRXhKNmYvczNMbjFRQUdGOGhEdmsveG92bmh4NWN6TzdzNjE2VXpmVFNJNlp6alBVOVUrYTRPaW9xTGc3eG9QN3YzdTZRUkdPbzJBSjFPbXo5NFFobTYxOTM0STRkV0QyREJSUnlJSTdubGY1YklITm16WTBCWEwxUlNMQlhxYXNTYVhaajBBckZtenBuVHpxMi9jbU02a3Y2Nks4MVRFSXh0N2NpTms1c0I3ZWVSWWUvUE5rZUR5VHJhQUJlQ216cGo3L2I1MCttOVZwSkR3Q2dETWhveWgveTBxTGZwUy9hNWQrMk8vbDdlYm53dEFZQWNBOCtjdm1kZlowMzJ2OTNLRmlNOHAweE96VmU4ZjdXaHZ1ZjVNQWlFTmgrNW16N3ZnaHE3dW5vZkUreEJBVU1CZG1abTF1S2o0SDVvYTl0d1RCU3c3MG5nOVh4RkVoR2t6NXR6Um04NzhpNG9vRWJPcWY3VGpTTXYxY1lBVzIzSTBGR0trb1lMZTdObmw1ZDBuZXJZNDhRRU5EandDZ0luNFJFbEo4WFdOQjNjL0ZTMU9SOERpcHhPVUNZQS9mL2E4TlNkT3BCOVgxYWVQdGpWZFd3QUh4QkZpd2F4UUtCaFJUVTBOZC9mMlB1SkZpNklFUm5sdVR3QTZGZjVqa2ZCQnBPR3pMWHhPK1I2QWJUaXdkNE1KOUtLSjQwZmZFUHRNNDF2d2dvcUtwZE5tekxrdnR1NUJyajdJOWZjZGJMNGhETjFOcXVKT0FwaVR3SWFaZFZSUjhWV0hXK3AvRlFrZjR0d1BBY0E5WFYySDJ0dmJNd00vcXJMQVFWZFpXVG52Y091eHVqRDBsNDBkVjdhcnU3UGo5WmluRHRvQ0JBQXJWNjRjdCtkQTAxdmUrYkxCWHFLTzJkaGtzdWltNW9ZOVAvZ2pDbCt3S0lzYnNiS3ljbDVEeTVGZmhKbHdGZ0J2akRrMGQ5YlV4WnMyYmVxS0IwaVRGL1VGWEhSN0puU3JvWnFmYXoyUnNZbkFQdGJTdE85cjd4TGg4eU05QTVBbFN5cm50YlNkRkQ1TE10RFk3dTdlM3U2dVl4dGpHYXJmdWdUQVYxVlZqZTFMcDIvVmJEM0xlZTVHeG5Eei9MbExib21USCsraXdRQjB6c0tGRlcxSDIvNHZKcndCd0NxaW9YTmZYTDU4K2RnWXRPNFgwZ0RRM2ZzYXJsVkZXZlNGdUFLVW1UbVpUTnorMGtzLzdYZ245ZmZaVmtDbXp5LzNYbVpEMWNVOE9HZXdzdGIyenVzaXJ6SHhHRUExTlRYMC9RZC85SXJ6Y21FV3ovZi9XQUJpSnRwMnkwMWZ1RENWU3VHVXdpdW91cmFhV3llMmpnZ2ZNS2x0a3RhK1dhdEluVkxwVENDWk1IbjZiNzNYaTdPMVE3OGNIaUJtUTF0dXVmRUw3MDJsVWdwQSsrSHVyRmtMVm5UMzlyNGFZZTM0d2owem01Sms4bE1ORFhzZkh3NWYxMmdOQTBDS1VtZkZPMDVqZmd2QVRaODVwN3F2TDF3bldhTENEUFJrUW1sSnlZVUhEdXplQ29CdERqejBwdE9yVlVHUmNEYTI5dzBCQitiT25iRytvV0h2a0lpcWVsMjFTVkhLQThDbFAxc3pMUXpzWWhhZDVweStJeSt3bGxTWW1vUFFiVTlScWpuM3J0cTF0WDZJZ296ZWY5RjcxLy95eGQvdEF6QTNseTV6bjZ1UzdVMW5yZ2F3TlpJTlRFUXljZkxNMzRUT3ZUL1BiUndSV3h2WWI3UTJIL2pIb2F4Zm96V2NvcFJjOHR4VkYzT1NiNGZxbjNGZ3hwQVpHVVpNblVKQzMwV01YNGpEdHpaKzlLbVhjKzhjeWdzbVRwMzV6OTdKMS9Pd2pBZklXTXUvUDNLNGNhV3FNZ0hBaWhVckp0WTNIOW1ySXFWNWlFbVptWXBIbGZ4SjQvNWRtd3RFZjZwZVY4MjFhMnY5SlQrNzZtNFQ4RDl4WU1qM09vZ1hBV2lFdG9JeUcyWlRiQ0VacitvazljSkhuMDVGbnBCUGdSa0Fmc2FNT2UvcnpZU2JKSnZSNkNUdkJETEVQVk1uVDUvM3hodS9QOHdBMEhxMHM0S0EwbHk2aTZjK0ltcWE4ZDdsYnhUQytUbmhQMWgzNVgzSnNjazdKU01hZG1lOGVsVWlZaUxZa1htSTFhdUczUmt2b1dnd05ublhCNSs5OHI3YXRiVytlbDAxRjBDSVdMcTBmSnVxSG95VjRsbW1IZkFnR3RYZGUyeEZmeHIwb1Z1c3NSL25KaUppQU5qMGNtMXRiejZFek8zRFMrcldYSjhjVy9TbFRFYzZoSUtJeUlCR2pBMk80OVRzM0FyS2RLVEQ1TGprbDFiVnJmbDBwQVNUQjR4TVhWMWRPZ2pzRnNvU2tKTEhIaUdUeVN3NWlRT1lGdzFWdkJybWJZTmdzNEpxMTliS0I1NzV5M0ZFOUcxM0lpT0FuaDNCQ3lnQ1VPTjZuU2p6dlZXL3VuSnNiWFd0WkJ0S0EyRjlZSU0zQ3hXOHFvQ0lMdXBYZ0lyTzFLd0dhRUF5SjBKeFNYSnZWR0NjTERWZXFESUExTmplNjRMUzVBUkpxMFJjM1RrYXhKSVJDVVluSmtvR253UkJvelVOR003N3Q0Z0tVUUFLRVptUnRUMFRWTFVzOGdDS3Z3UlFpS0lwKy8rTi9UNnljZFhHckV1UlhxRmVGZWRROUlGRW5Db3JyZ1NBVmF0V1NYNTlZQ3czRmlqN1NWVkJSSk9ZR2F3S2lQY2xoVFVGSlphT3ZLS0RRSkRLelRjRWdNNlQwQk5CejdrS2lKVEZlUUl3djFxclRaUVNCMUJoenVzUnpkSlVBOGdRSW9JTFhhQ3FZRlZGbENyeUt5d1NFVDNVZXJ5clVPMlZhRzhiQjlCRUZRV1U2TnlibjBpOUFvUkpyUy8waml2RUFQYW1NMzB4QlF4TUZTS3FwK084aVVTQ0N2OWRNZ3JOdkF0cVlRZVlndEJjVlU0cEh6TXpFb2xFdklXZDJ5Zkt6RlEyZnV6WUFWbUFzbnJldU9ycDR3QWRJc3NBNjdtdkRFbVZESU1VclJ0ZldOR1pGOEVJQUthWFRSaHZqR0hOZGxVbzFqOUFNcG1nS0FZb3ZKZjJxR0VYM3ljQ2dETHAzb241YWJCNlhiVUJrUkt3bFFOV0ZkSnpibmtsNFFTcmdyWWlsWklJQ3d3NGM5SFYyek11Q25nNjBHa0kzbXRIZnd4Z3cwZG9NTHNTNVVXZVBTUXBKL1FZUkNtcUtzOTVFSUFvc2FHZkRBMFplRTRCMWtpSkFEYmMxaDhEaUtsK0tNRGd3bkJSL3Q5cjE5WjYxTlR3cjErdWVDN3NDVGZiVVlGUlBmUGUvTnUzUHB3ZEZaaXdKOXo4d2tzVno2R21oZ3RWaHk1MGl3cjJJWWxBcXZ2Njh5TXBYaThnUDZrcW5NaDdJamc1NEFYVlM3WVRVaWtod2w5cktIMGNzTlVzajNpV2hWZlBscTA0U2F2eTN5Q1ZrdW9sMi9OWEwwUUVFVmtleGJhQkFBK0VSREt4dTE4QmllS2lOeWc3dVJsSU1TbFVjT0g4aW9ycCtieDZEb052L05qNkxiN1BYME1HZmJZazZ3bFpSYWlNNUtPcVhoWE9sZ1NHRERMUzY2Lys5ZVZQdlZxQUd5QUFzbno1OG9taXNpTFh2Y3NIZUJ6WWJmMGZsTTg5ZndjSWh5bHI2bmdueFFOYW5PbnFxNHExcHBDdmhCYy92djVaMXlWVjZ2V1ZvRFN3d2VpRTRZUmxEZ3h6d21UL0xmUWtUdVB6d0RBbkxBZWpFeVlvRGF4NDJScWVDRC84NHNmWFB6c0VNV0lBVU52UjdsV3FLSTBUb0pFUkdVRDd0SW5qdHNmN2JYN2lsSmxQZWUrdmpGS0dPVW1Ga3pHR24yazcxSEFGaGppVjFiK1E2bXJ6b1J2OUp3VjZOU21XcUdoU2RaZ0NTUUdDaXRJd2RRUUJUT2dEOHhzZ2ZWbzNIbjE4WTJxakc0WVZpc3R6bFE2azl6MFJHV3ROWFd0TC9lVVJJMVJsZ1kxdXhzeDVOL2YyWlI0UThYRUdSYU9VR0U2WU1uN1I3dGRmMzU5WFh3OWloZUwvZitZUExXYllEZjBIWVBUQ25kcGRXajVzRnZsRDVVTU9zVlEyREJ2RUFIVFJvZ3RudGg1cDNlRlZrelF3aFRzaXRvRzFYenpjY3VCK0FMYWZGRjI4dUhMbTRTT0hkb2hvY2Q1K2QwUnNTNHFULzlwWXYvZkxHUDVzSGxWck5hTTJ5aFFqT0tyWFZSdFVBN1ZVTzl3aEtBdkFUWjQ2ODd1aGs2L2swV0VLZ0pnNVV6WnVRbmwwY0lNcDdqYVRwODE2T2d6ZG1zaHQ0ajlVWWtxUEh6TjIyWjQ5Yis0Ynlnc0dPVzlCRlA0MitqNVVDT2tYdHY2eVpjdW1OeC91ZUV0RVJ1VUJPQWVRQ1FKVDEzYW80ZU9xeWdBR1ltVWJtSWVpUUpoUExpZ1V4WjA5M2QrS0JaSlRMNTBHSFkwNzg0ZE82MVJKdndKYTJ6dS9xWXJSZWZRZVZKV01ZU3BKRmowVXBVYU9wd2NQZ08rOTU1cy9ZNkxYQ3BDZlJsVzljLzZhS2RQblhKTkhuYjhiaGdYZzVzMWJmSmx6L3RNaXZrQmZreGpBanM5Kzl0cWZJblpnZ3ZJbm1UUjExbDk0TDA4V21FUUF3QmpUTVdGYVdjWE8xMTVyZnBlMHlCaUFWRlpXbHRVM3RXMTF6azB0NEtXZW1FMWd6ZWNQTngvODl6aTlILytTQThDSG13K3NaNlpOeUI2RDgva3U1a1VtdERjZldWZFZWV1hQWUR1Y1BZWXcyOWF6Qnh2YkhuUGVUOHRyaFBUM0FnTERXNjljL2JIL3l2ZHVIb1NTaWFRb3NGOWxwa0tCeDBEVmV5OS91bnRmUSsyNmRldjRqNmlFL3FNeTMzdndoejlTbFkva05VUnplMStaQ2FQSGxONzI4TU1QaC9uc0VCZG9MWm1HaG4wdkpSS0pIeEJ4b1U2UUFjVDFwVE5YZmZtcmR6d1JLVUZRK01UbzJSb213dnN5dm16YWd5TDZHUkVwRkpjY3M3SFcya2YyN256elY0VlMrRkNMNXZJRmMzL1oyWFhpYWxWTXhxQjJPYkdLT085MWNkM3pQNy9vZ3ZMNWRTMHRMVDNSQXZRc3U3d0Y0Q3NyTHozUHExOG53S2MxYTNsYndKZzJzR2J2N1BNWFhkUFV0Q2NzdExaaGo4bk5XckI0UmZmeHpwZEZKQ2pzTWVxSTJMSXhlMHBLaWo1WHYyL1hiMklCZFNTUHlnMDRLemg3d1lLTGVqcjdmdVJGRnhjNHg1VHpmTEhHK3RKUnhSL1l2My9YSzBNQk9ETU0vTERIajdZMWwwMmNzdHM1VngyQkl4cE1uY09yYUprTDNXZkdqQmtYekpvNS9aVzJ0cmErbUNMd0RoVEJPSG4wVFZhdlhsMXlvay91Nk9ucGU5U0xUSWthdVFXRWg3ZldXaHVZNnh2cjl6NFhNd2hPVndGUjJxdXluY2RlZmIyc2JFcW44KzV5RWZFRmdCSURFRlcxb3FqcTdjdDg0cnl4NDlOTGwxendWbU5qWXlhRzVXeWVBcW5Bd3pHaGN3QklWcTVjV2F4YzlLbUQ5VTAvRHAxYjY3MFlvb0p4UjVFOXoyQnRZTzg0M0hUZyt6akZlZUhUQWFvQmdIRGNwR2xmTldTKzQ3MlhJUUpvcm5scU9IdWpZeWNiODU4bGlhSW5EaDdjdFZQMXpKeUFpTEIwYVdYNTBlUEhyc3BrMHAvM291VXFDa0NHT1RFT0lXSmpMZDNUMnRMdzkzaUhoNlVISWEzejV5Nzhjay9YaVh1ekZmT3dkd1UwcHdoVkNZMnhtNW40bDRtaTVPOU5BcnZPS3lvNnZHWExsczdjRCs2NjZ5NSsvdm5ueHh3NjFESFJBK1hlaFJkbG5Mc0VxaGVKYXFBblQ0Z1BlV2RBQVdPTlJTTGcyNXNiRDN3SHAzbUY1a3hLRlF2QXpadzUvNW9UbWZTajNra3BJQTRZOHJaSS82V0pxTFdiSTU0RlNoMWt1Q01SQkFvQW1UQmtpSTRUbGJGRXhKcnRWMEpWUUVRT3d4NnhWNWU5TmNJOW8wWVYzMWkvZjlkUHppUUluMkd0bHVVT3lzdVhMVHZhZWZ5SDNzbjdSQVUwdERmRXQ0Wm0yZU9UUjl4elYyUm9RR05KUGRCLzQyTzRpMWRlVlptTklXYmFXcEpJWEY5ZnYvZFZuT0hscVRNRUx3Y0ZnRzF2YnoxMHlRY3Uvbkg3MFdPc3Fpc1ZzS3FxVVMrQkN5ZzVzaUJ4ekNwS0JJMDRlODNMTER5TThENEtFc1lhSThsRTR0c1ZTeForN3JYWE50ZmpiZHdjbzNlUW5nUUE1aStxdUxDNzgvamR6c2xxRVlHSWdnaW5jTnN6SGdKQUZMQWMzVUZLV1B2VDBsRWxkKy9ldlgxVC9wck9oUUxpbHZWRVFIbjUwcXFPNDExZmNkNy91U3FNcWlEeUNvOHp1enc1Z0EvUUxHOUhSQXdpU0JDWVp5M1pCeG9iOXo0Zmg4VnZGMnVNUkVlSDQrWHlnZ1dMVjNUMTlGenJ2S3dCY0lIa2JuNE5USVA1OXdkelBYdk9MU3RyYU1vMU1IY2trc0dHa2tUeXYzZnYzcjZsMEh2ZmlSVkhza0RwUDBoVlUxTmpINnQ5K2oyOTNWMnJuTmVWenJsRnFqSVZvUE55Y0MzT1ZwOE1oSHFjUUUxc3pIWnI3TXVqUzRwZXZQYmFUN3lXU3FWY2ZoVTRVaGo3YkpTcG5CK01hbXBxN0pOUFBqbWxxODlOUitpbkhPL3VMU291dHRNQklKTnhUV1BHakFrRjBsUmFaSnZ1dlBQT2xyVnIxL29DYVhnazdpQU5HUDhQd3hTVTZsNUVqMHNBQUFBQVNVVk9SSzVDWUlJPSIvPjwvc3ZnPg==";

// src/css.ts
var done = /* @__PURE__ */ new Set();
function injectCss(id, text) {
  if (typeof document === "undefined" || done.has(id)) return;
  const el = document.createElement("style");
  el.dataset.crew = id;
  el.textContent = text;
  document.head.appendChild(el);
  done.add(id);
}

// src/styles/base.css
var base_default = `/* Ported from scripts/crew_dashboard/tokens.css: the only place a colour is decided. Two inherited inputs (host
   background and foreground); every surface, stroke and text step is the foreground at an alpha. Nothing here may
   reach a host page: the inputs sit on the OUTERMOST .crew-scope (a wrapper that sets --crew-bg / --crew-fg inline,
   Desktop from its theme, wins over them; a nested .crew-scope must not re-declare them) and on :root only when the
   document is our own served shell (#crew-app[data-crew-shell]). The ladder is declared on .crew-scope (and that
   :root), so it is recomputed from whatever colours the wrapper set. */
:root:has(#crew-app[data-crew-shell]),.crew-scope:not(.crew-scope .crew-scope){
  /* The page's own scheme, so an embedded mark (the header logo, the tab icon) picks the ink that reads on
     THIS field, not the one the viewer's OS prefers: a black-ring mark on a dark page is an invisible mark.
     The dashboard's field is dark; a light host sets --crew-scheme:light with its --color-* / --dt-* tokens. */
  color-scheme: var(--crew-scheme, dark);
  --crew-bg: var(--color-background, var(--dt-background, #0f1115));
  --crew-fg: var(--color-foreground, var(--ui-base, #e8eaed));
  --crew-font: var(--dt-font-sans, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif);
  --crew-mono: var(--dt-font-mono, ui-monospace, "JetBrains Mono", SFMono-Regular, Menlo, Consolas, monospace);
}

:root:has(#crew-app[data-crew-shell]),.crew-scope{
  --crew-text-1: color-mix(in srgb, var(--crew-fg) 94%, transparent);
  --crew-text-2: color-mix(in srgb, var(--crew-fg) 74%, transparent);
  --crew-text-3: color-mix(in srgb, var(--crew-fg) 54%, transparent);
  --crew-text-4: color-mix(in srgb, var(--crew-fg) 36%, transparent);
  --crew-stroke-1: color-mix(in srgb, var(--crew-fg) 14%, transparent);
  --crew-stroke-2: color-mix(in srgb, var(--crew-fg) 8%, transparent);
  --crew-fill-1: color-mix(in srgb, var(--crew-fg) 7%, transparent);
  --crew-fill-2: color-mix(in srgb, var(--crew-fg) 4%, transparent);
  --crew-fill-3: color-mix(in srgb, var(--crew-fg) 2.5%, var(--crew-bg));
  --crew-elevated: color-mix(in srgb, var(--crew-fg) 5%, var(--crew-bg));
  --crew-overlay: color-mix(in srgb, var(--crew-elevated) 92%, transparent);
  --crew-shadow: color-mix(in srgb, #000 50%, transparent);

  /* Desktop sets --crew-in-running / -blocked / -review / -ready / -done on its wrapper (theme.ts); a nested .crew-scope
     re-declares the tones below, so the inputs are read here and the browser, which sets none, keeps its fallbacks. */
  /* status tones: running and verified green, blocked/failed red, review/unverified/stale amber, ready
     blue, done teal; todo and pending are neutral. Every state chip on both pages takes one of these. */
  --crew-tone-running: var(--crew-in-running, var(--color-success, #34d399));
  --crew-tone-blocked: var(--crew-in-blocked, var(--color-destructive, #f87171));
  --crew-tone-review:  var(--crew-in-review, var(--color-warning, #fbbf24));
  --crew-tone-ready:   var(--crew-in-ready, #60a5fa);
  --crew-tone-done:    var(--crew-in-done, var(--color-info, #2dd4bf));   /* finished work: its own tone, not the grey of "nothing" */
  --crew-tone-neutral: var(--crew-text-3);

  /* a tone as a tinted box: the wash, its outline, a stronger header wash */
  --crew-running-fill: color-mix(in srgb, var(--crew-tone-running) 8%, var(--crew-bg));
  --crew-running-line: color-mix(in srgb, var(--crew-tone-running) 35%, var(--crew-bg));
  --crew-blocked-fill: color-mix(in srgb, var(--crew-tone-blocked) 8%, var(--crew-bg));
  --crew-blocked-line: color-mix(in srgb, var(--crew-tone-blocked) 35%, var(--crew-bg));
  --crew-review-fill:  color-mix(in srgb, var(--crew-tone-review) 8%, var(--crew-bg));
  --crew-review-head:  color-mix(in srgb, var(--crew-tone-review) 14%, var(--crew-bg));
  --crew-review-line:  color-mix(in srgb, var(--crew-tone-review) 35%, var(--crew-bg));
  --crew-ready-line:   color-mix(in srgb, var(--crew-tone-ready) 35%, var(--crew-bg));
  --crew-running-glow: color-mix(in srgb, var(--crew-tone-running) 55%, transparent);
  --crew-running-halo: color-mix(in srgb, var(--crew-tone-running) 35%, transparent);
}

/* the standalone page: the served shell has only <div id="crew-app"> */
body:has(#crew-app[data-crew-shell]){margin:0;background:var(--crew-bg)}
#crew-app[data-crew-shell]{height:100vh;height:100dvh;display:flex;flex-direction:column}

/* \u2500\u2500 scrollbars, both pages (scoped to the board/card root): a hairline track and a small rounded oval thumb in the theme's own tones \u2500\u2500 */
.crew-scope *{scrollbar-width:thin;scrollbar-color:var(--crew-stroke-1) transparent;}
.crew-scope ::-webkit-scrollbar{width:8px;height:8px;}
.crew-scope ::-webkit-scrollbar-track{background:linear-gradient(to right, transparent 3.5px, var(--crew-stroke-2) 3.5px,
  var(--crew-stroke-2) 4.5px, transparent 4.5px);}
.crew-scope ::-webkit-scrollbar-track:horizontal{background:linear-gradient(to bottom, transparent 3.5px, var(--crew-stroke-2) 3.5px,
  var(--crew-stroke-2) 4.5px, transparent 4.5px);}
.crew-scope ::-webkit-scrollbar-thumb{background:var(--crew-stroke-1);border-radius:999px;border:2px solid transparent;
  background-clip:padding-box;min-height:28px;}
.crew-scope ::-webkit-scrollbar-thumb:hover{background-color:var(--crew-text-4);}
.crew-scope ::-webkit-scrollbar-corner{background:transparent;}
`;

// src/styles/board.css
var board_default = `/* Board styles, ported unchanged from scripts/crew_dashboard/crew.css (the .page-board rules). The only edit: the old
   \`body.page-board\` rule is the root element's \`.page-board\` rule, so the board lays out inside a host page too. */
/* board page (ui-spec section 4): one-line header, crew bar, five fixed lanes, the desktop card */
.page-board *{box-sizing:border-box}
.page-board{margin:0;background:var(--crew-bg);color:var(--crew-text-1);
  font:13px/1.45 var(--crew-font);-webkit-font-smoothing:antialiased;height:100%;display:flex;flex-direction:column;overflow:hidden}
.page-board button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
.page-board header{display:flex;align-items:center;gap:14px;padding:14px 18px 10px;flex:0 0 auto}
.page-board h1{font-size:15px;margin:0;font-weight:600;letter-spacing:-.01em}
/* LIVE: the server answers the poll - a green dot that pulses; amber and still once a poll fails */
.page-board .badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 9px 2px 7px;font-weight:700;
  font-size:10px;letter-spacing:.08em;line-height:1.3;color:var(--crew-tone-running);
  background:color-mix(in srgb, var(--crew-tone-running) 12%, transparent)}
.page-board .badge i{width:7px;height:7px;border-radius:50%;background:var(--crew-tone-running);
  animation:livepulse 1.6s ease-out infinite}
@keyframes livepulse{0%{box-shadow:0 0 0 0 var(--crew-running-glow)}70%{box-shadow:0 0 0 6px transparent}
  100%{box-shadow:0 0 0 0 transparent}}
.page-board .badge.stale{color:var(--crew-tone-review);background:color-mix(in srgb, var(--crew-tone-review) 12%, transparent)}
.page-board .badge.stale i{background:var(--crew-tone-review);animation:none}
@media (prefers-reduced-motion: reduce){ .page-board .badge i{animation:none} }
.page-board .meta{font-size:12px;color:var(--crew-text-3);white-space:nowrap}
.page-board .meta.on{color:var(--crew-tone-running)}
.page-board #when{font-size:11px;color:var(--crew-text-4);font-variant-numeric:tabular-nums}
.page-board .stats{display:flex;gap:6px;font-size:11.5px;color:var(--crew-text-3)}
.page-board .stats span{--tone:var(--crew-text-3);display:inline-flex;align-items:baseline;gap:4px;padding:2px 8px;border-radius:5px;
  background:color-mix(in srgb, var(--tone) 12%, transparent);color:var(--tone)}
.page-board .stats b{font-weight:600;font-variant-numeric:tabular-nums}
.page-board .stats .running{--tone:var(--crew-tone-running)}
.page-board .stats .blocked{--tone:var(--crew-tone-blocked)}
.page-board .stats .done{--tone:var(--crew-tone-done)}
.page-board .stats .none{--tone:var(--crew-text-4)}
.page-board .stale{font-size:11px;color:var(--crew-tone-review)}
.page-board .stale[hidden]{display:none}
.page-board .dispatcher-down{margin:0 18px 8px;padding:7px 12px;border-radius:6px;font-size:12.5px;flex:0 0 auto;
  color:var(--crew-tone-blocked);background:color-mix(in srgb, var(--crew-tone-blocked) 12%, transparent)}
.page-board .dispatcher-down code{font:inherit;font-weight:600}
.page-board .hright{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:11px;color:var(--crew-text-4)}
.page-board .hright .node{white-space:nowrap}
.page-board .hright a{color:var(--crew-text-3)}
.page-board .hright a:hover{color:var(--crew-text-1)}
.page-board header{border-bottom:1px solid var(--crew-stroke-2)}
.page-board .avatar{display:inline-grid;place-items:center;flex:0 0 auto;border-radius:999px;width:18px;height:18px;
  font-size:9px;font-weight:600;background:color-mix(in srgb, var(--hue) 22%, transparent);color:var(--hue)}
.page-board .avatar.face{border-radius:6px;object-fit:cover;background:none;padding:0;}
/* a card's state: a chip tinted in its own tone */
.page-board .schip{display:inline-flex;align-items:center;white-space:nowrap;border-radius:4px;padding:1px 6px;font-size:10px;
  font-weight:500;background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone)}
/* lanes */
.page-board main{flex:1;min-height:0;display:flex;gap:10px;padding:12px 18px 16px;overflow-x:auto;align-items:stretch}
.page-board .lane{display:flex;flex-direction:column;flex:1 1 264px;min-width:264px;max-width:340px;border-radius:8px;
  padding:8px;background:var(--crew-fill-3);min-height:0}
.page-board .lane.rail{flex:0 0 32px;min-width:32px;width:32px;align-items:center;gap:6px}
.page-board .lane.rail .lt{writing-mode:vertical-rl;margin-top:4px}
.page-board .lane.rail .ln{margin-top:2px}
.page-board [data-toggle]{cursor:pointer}
.page-board .lane.togglable:hover,.page-board .lane.togglable:focus-visible{background:var(--crew-fill-2,var(--crew-fill-3));outline:none}
.page-board .lh{display:flex;flex:0 0 auto;align-items:center;gap:6px;height:20px;margin:0 4px 6px}
.page-board .lh i{width:6px;height:6px;border-radius:50%;background:var(--tone)}
.page-board .lt{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:var(--crew-text-3)}
.page-board .ln{font-size:10px;color:var(--crew-text-4);font-variant-numeric:tabular-nums}
.page-board .lbody{display:flex;flex-direction:column;gap:8px;overflow-y:auto;min-height:0;padding:1px}
.page-board .more{font-size:11px;color:var(--crew-text-3);text-align:center;padding:6px;border:1px dashed var(--crew-stroke-1);
  border-radius:6px;width:100%}
.page-board .more:hover{color:var(--crew-text-1)}
.page-board .empty{color:var(--crew-text-4);font-size:11px;padding:2px 4px}
/* the card: the Hermes desktop kanban card anatomy */
.page-board .card{position:relative;display:flex;flex-direction:column;gap:8px;border-radius:6px;padding:10px;
  text-decoration:none;color:inherit;background:var(--crew-elevated);border:1px solid var(--crew-stroke-2);
  border-left:2px solid var(--tone)}
.page-board .card:hover{border-color:var(--crew-stroke-1);border-left-color:var(--tone)}
.page-board .card .ti{font-size:13px;font-weight:500;line-height:1.35;color:var(--crew-text-1);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.page-board .card .su{font-size:11px;line-height:1.4;color:var(--crew-text-3);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.page-board .card .ft{display:flex;align-items:center;gap:6px;white-space:nowrap;font-size:10px;color:var(--crew-text-3)}
.page-board .card .ft .who{font-weight:500}
.page-board .card .ft .r{margin-left:auto;display:flex;align-items:center;gap:8px;min-width:0;font-variant-numeric:tabular-nums}
.page-board .card .ft .id{font-family:var(--crew-mono);color:var(--crew-text-4)}
.page-board .ok{color:var(--crew-tone-running)}
.page-board .bad{color:var(--crew-tone-blocked)}
.page-board .warn{color:var(--crew-tone-review)}
.page-board .dim{color:var(--crew-text-4)}
/* motion means work: an arc sweeps the border of a live card; a quiet one crawls amber; reduced motion = ring */
@property --crew-arc{syntax:"<angle>";inherits:false;initial-value:0deg}
.page-board .card.live::after,.page-board .card.quiet::after{content:"";position:absolute;inset:-1px;border-radius:7px;
  padding:1px;pointer-events:none;
  background:conic-gradient(from var(--crew-arc), transparent 0 70%, var(--arc) 88%, transparent 100%);
  -webkit-mask:linear-gradient(currentColor 0 0) content-box,linear-gradient(currentColor 0 0);-webkit-mask-composite:xor;
  mask:linear-gradient(currentColor 0 0) content-box exclude,linear-gradient(currentColor 0 0);
  animation:crewarc var(--arc-s) linear infinite}
.page-board .card.live{--arc:var(--crew-tone-running);--arc-s:2.2s}
.page-board .card.quiet{--arc:var(--crew-tone-review);--arc-s:6s}
@keyframes crewarc{to{--crew-arc:360deg}}
@media (prefers-reduced-motion: reduce){
  .page-board .card.live::after,.page-board .card.quiet::after{animation:none;background:var(--arc)}
}
.page-board #bellwrap{position:relative;display:inline-flex;align-items:center}
.page-board .bell{position:relative;display:inline-flex;align-items:center;gap:6px;background:var(--crew-fill-1);
  color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);border-radius:6px;padding:3px 7px;font:inherit;
  cursor:pointer;line-height:0}
.page-board .bell:hover{border-color:var(--crew-tone-ready)}
.page-board .bell.waiting{border-color:var(--crew-tone-review);color:var(--crew-text-1)}
.page-board .bell .n{background:var(--crew-stroke-1);color:var(--crew-text-3);border-radius:9px;font-weight:700;font-size:10px;
  padding:0 5px;line-height:14px}
.page-board .bell.waiting .n{background:var(--crew-tone-blocked);color:var(--crew-bg)}
.page-board #notes{position:absolute;right:0;top:27px;z-index:40;width:560px;max-width:86vw;max-height:70vh;
  overflow:auto;background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:8px;
  box-shadow:0 10px 28px var(--crew-shadow);padding:8px 9px}
.page-board #notes[hidden]{display:none}
.page-board .nh{display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--crew-text-3);
  font-size:10px;text-transform:uppercase;letter-spacing:.1em;margin:2px 2px 7px}
.page-board .nh b{color:var(--crew-text-1)}
.page-board .nh button,.page-board #noterows button{background:var(--crew-fill-1);color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);
  border-radius:4px;font:inherit;font-size:10px;padding:1px 8px;cursor:pointer}
.page-board .nh button:hover,.page-board #noterows button:hover{border-color:var(--crew-tone-ready)}
.page-board #notes .empty{color:var(--crew-text-4);font-size:11px;padding:2px}
.page-board .ar{display:flex;align-items:center;gap:10px;background:var(--crew-elevated);border:1px solid var(--crew-stroke-1);
  border-left:3px solid var(--crew-tone-neutral);border-radius:6px;padding:5px 9px;margin-bottom:5px;font-size:11px}
.page-board .ar.stuck{border-left-color:var(--crew-tone-blocked)}
.page-board .ar a.t{color:var(--crew-text-1);text-decoration:none;flex:1;min-width:0;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.page-board .ar a.t:hover{color:var(--crew-tone-ready)}
.page-board .ar .st{font-weight:700;width:56px}
.page-board .ar.stuck .st{color:var(--crew-tone-blocked)}
.page-board .ar .st{color:var(--crew-tone-neutral)}
.page-board .ar .w,.page-board .ar .ag{color:var(--crew-text-3);white-space:nowrap}
.page-board .ar button{background:var(--crew-fill-1);color:var(--crew-text-2);border:1px solid var(--crew-stroke-1);border-radius:4px;
  font:inherit;font-size:10px;padding:1px 8px;cursor:pointer}
.page-board .ar button:hover{border-color:var(--crew-tone-ready)}
.page-board .tailnet{color:var(--crew-tone-ready)}

.page-board header a.brand{display:inline-flex;align-items:center;flex:0 0 auto;border-radius:6px}
.page-board header a.brand img{display:block;width:18px;height:18px}
.page-board header a.brand:hover{background:var(--crew-fill-1)}
.page-board header a.brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}

/* narrow (the Desktop main pane beside the flow pane): the title never wraps or vanishes; the header's least
   important facts step aside by width and stay in the DOM */
.page-board header{container-type:inline-size;container-name:crewhead;}
@container crewhead (max-width:900px){
  .page-board header > *{flex-shrink:0;}
  .page-board header > h1{flex-shrink:1;min-width:5.5em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
}
@container crewhead (max-width:900px){ .page-board #when{display:none;} }
@container crewhead (max-width:760px){ .page-board #cards{display:none;} }
@container crewhead (max-width:620px){ .page-board #live{display:none;} }
@container crewhead (max-width:520px){ .page-board .stats .none{display:none;} }

/* Desktop only: the switch that brings the app's own Kanban row back (Board.tsx, host.kanbanRow). */
.page-board .kswitch{display:inline-flex;align-items:center;gap:7px;cursor:pointer;white-space:nowrap;color:var(--crew-text-3)}
.page-board .kswitch:hover{color:var(--crew-text-1)}
.page-board .kswitch input{position:absolute;opacity:0;width:0;height:0}
.page-board .kswitch i{position:relative;width:24px;height:14px;border-radius:7px;background:var(--crew-stroke-1);transition:background .15s}
.page-board .kswitch i::after{content:"";position:absolute;top:2px;left:2px;width:10px;height:10px;border-radius:50%;background:var(--crew-bg);transition:transform .15s}
.page-board .kswitch input:checked + i{background:var(--crew-tone-running)}
.page-board .kswitch input:checked + i::after{transform:translateX(10px)}
.page-board .kswitch input:focus-visible + i{outline:2px solid var(--crew-tone-ready);outline-offset:2px}

/* Desktop only: the command row under a tile's chips (TileActions draws nothing in the browser) */
.page-board .card .tact{display:flex;flex-direction:column;gap:4px;cursor:default}
.page-board .card .tbtns{display:flex;flex-wrap:wrap;align-items:center;gap:4px}
.page-board .card .tmsg{font-size:10px;line-height:1.4;color:var(--crew-text-2);overflow-wrap:anywhere}
.page-board .card .tmsg.bad{color:var(--crew-tone-blocked)}
`;

// src/components/boardUtil.ts
function fmt(s) {
  if (s === null || s === void 0) return "";
  s = Math.max(0, Math.floor(s));
  if (s < 60) return s + "s";
  if (s < 3600) return Math.floor(s / 60) + "m";
  if (s < 86400) return Math.floor(s / 3600) + "h";
  return Math.floor(s / 86400) + "d";
}
var shortId = (id) => String(id).replace(/^t_/, "").slice(0, 6);
function hhmm(d) {
  const p = (x) => (x < 10 ? "0" : "") + x;
  return p(d.getHours()) + ":" + p(d.getMinutes());
}
function store(k, v) {
  try {
    if (v === void 0) return sessionStorage.getItem("crew." + k);
    if (v === null) sessionStorage.removeItem("crew." + k);
    else sessionStorage.setItem("crew." + k, v);
  } catch {
    return null;
  }
}
var TONE = {
  blocked: "var(--crew-tone-blocked)",
  triage: "var(--crew-tone-blocked)",
  running: "var(--crew-tone-running)",
  review: "var(--crew-tone-review)",
  ready: "var(--crew-tone-ready)",
  todo: "var(--crew-tone-neutral)",
  done: "var(--crew-tone-done)",
  queued: "var(--crew-tone-ready)",
  other: "var(--crew-tone-neutral)"
};
var QUIET_S = 120;

// src/components/Lane.tsx
import { useLayoutEffect, useRef as useRef3 } from "react";

// src/components/ActionBar.tsx
import { useEffect as useEffect3, useRef as useRef2, useState as useState3 } from "react";

// src/card-format.ts
function fmtTokens(n) {
  const v = +n || 0;
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "k";
  return "" + v;
}
var pad = (x) => (x < 10 ? "0" : "") + x;
function fmtTime(sec) {
  if (sec == null) return "";
  const d = new Date(sec * 1e3);
  return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
}
function fmtAgo(sec) {
  if (!sec) return "";
  let d = Date.now() / 1e3 - sec;
  if (d < 0) d = 0;
  if (d < 60) return Math.round(d) + "s ago";
  if (d < 3600) return Math.round(d / 60) + "m ago";
  if (d < 86400) return Math.round(d / 3600) + "h ago";
  return Math.round(d / 86400) + "d ago";
}
function fmtAge(sec) {
  if (sec === null || sec === void 0 || sec === "") return "age unknown";
  const s = Math.max(0, Math.round(+sec || 0));
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m " + s % 60 + "s ago";
  if (s < 86400) return Math.floor(s / 3600) + "h " + Math.floor(s % 3600 / 60) + "m ago";
  return Math.floor(s / 86400) + "d " + Math.floor(s % 86400 / 3600) + "h ago";
}
function fmtExact(n) {
  return Math.round(+n || 0).toLocaleString("en-US");
}
function offLabel(s) {
  return s.sec != null ? "t+" + s.sec + "s" : "";
}
function cap1(s) {
  const t = String(s || "");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
function hhmm2(ts) {
  return ts ? fmtTime(ts).slice(0, 5) : "";
}
var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function dayTime(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1e3);
  return MONTHS[d.getMonth()] + " " + d.getDate() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
}
var ROLE_ICON = { coordinator: "\u25C6", worker: "\u25B2", content: "\u25CF", verifier: "\u2713" };
var roleIcon = (name) => ROLE_ICON[name || ""] || "\u25AA";
var STATUS_TONE = {
  running: "running",
  live: "running",
  pending: "neutral",
  done: "done",
  completed: "done",
  finished: "done",
  blocked: "blocked",
  triage: "blocked",
  failed: "blocked",
  crashed: "blocked",
  timed_out: "blocked",
  gave_up: "blocked",
  review: "review",
  review_requested: "review",
  ready: "ready",
  queued: "ready",
  todo: "neutral",
  PASS: "running",
  verified: "running",
  FAIL: "blocked",
  unverified: "review",
  rate_limited: "review"
};
var toneVar = (word) => "var(--crew-tone-" + (STATUS_TONE[word || ""] || "neutral") + ")";
function budgetTone(pct) {
  const G = "var(--crew-tone-running)", Y = "var(--crew-tone-review)", R = "var(--crew-tone-blocked)";
  if (pct >= 100) return R;
  if (pct >= 80) return "color-mix(in srgb, " + R + " " + Math.round((pct - 80) / 20 * 100) + "%, " + Y + ")";
  if (pct >= 50) return "color-mix(in srgb, " + Y + " " + Math.round((pct - 50) / 30 * 100) + "%, " + G + ")";
  return G;
}
var stepWord = (s) => s.state === "err" ? "failed" : s.state === "pending" ? "still running" : "ok";
function groupParallel(steps) {
  const out = [];
  for (const s of steps || []) {
    const k = (s.tool || "?") + "@" + (s.ts || 0);
    const last = out[out.length - 1];
    if (last && last.k === k) {
      last.args.push(s.args || "");
      last.states.push(s.state);
      if (!last.note) last.note = s.note;
      if (s.out) last.out = s.out;
      if (!last.say) last.say = s.say;
    } else {
      out.push({ k, tool: s.tool, ts: s.ts, sec: s.sec, args: [s.args || ""], states: [s.state], note: s.note, out: s.out, say: s.say, state: "" });
    }
  }
  for (const g of out) g.state = g.states.indexOf("err") >= 0 ? "err" : g.states.indexOf("pending") >= 0 ? "pending" : "ok";
  return out;
}
function stepStatus(g) {
  const note = g.note || "", out = g.out || "";
  let text = "";
  if (note && out) text = out.indexOf(note) === 0 || note.indexOf(out) === 0 ? out.length > note.length ? out : note : note + " - " + out;
  else text = note || out;
  const bits = [stepWord(g)];
  if (text) bits.push(text);
  if (g.ts) bits.push(fmtTime(g.ts));
  return bits.join(" - ");
}
var tickTime = (s) => s.ts ? fmtTime(s.ts) : offLabel(s);
function coordinatorTarget(value) {
  const m = /^([^/]*)\/([^/]*)$/.exec(String(value || ""));
  if (!m || m[2] === "no-session") return null;
  if (!/^[A-Za-z0-9_.-]{1,64}$/.test(m[1]) || !/^[A-Za-z0-9_-]{1,128}$/.test(m[2])) return null;
  return { profile: m[1], session: m[2] };
}
function copyText(text, done2) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => done2(true), () => done2(false));
      return;
    }
  } catch {
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, ta.value.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    done2(ok);
  } catch {
    done2(false);
  }
}
function briefFields(nodes) {
  const b = nodes.find((n) => n.kind === "brief")?.brief || null;
  if (!b || !String(b.text || "").trim()) return null;
  const src = b.source || "owner";
  const when = b.ts ? fmtTime(b.ts) : "";
  const label = src === "owner" ? "the owner's words when /crew was called" : src === "card goal" ? "the card's own GOAL line - no brief was recorded" : "source: " + src;
  return { text: String(b.text).trim(), src: label + (when ? " - " + when : "") };
}

// src/components/ActionBar.tsx
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
var cardSubject = (card) => ({
  status: card.card_status || "",
  proof_ask: card.situation?.proof_ask || "",
  live: !!card.situation?.live_run
});
function actionStates(s) {
  const st = s.status;
  return {
    unstuck: st === "triage" || st === "blocked" || st === "scheduled",
    retry: st === "done" || st === "blocked" || st === "failed" || st === "triage",
    proof: !!s.proof_ask,
    stop: s.live
  };
}
var WHY_NOT = {
  unstuck: "only a blocked, triage or stopped card can be unstuck",
  retry: "only a done, blocked or failed card can be retried",
  proof: "no proof question is waiting for you on this card",
  stop: "no run is alive on this card"
};
var WHAT = {
  unstuck: "lift the block so the card runs again (/crew-unstuck)",
  retry: "raise the budget and run the card again",
  proof: "give the go for the proof the coordinator asked about (/crew-proof)",
  stop: "park the card and stop its run (/crew-stop)"
};
var LABEL = { unstuck: "Unstuck", retry: "Retry", proof: "Proof", stop: "Stop" };
var SHOW_MS = 6e3;
var NAMES = ["unstuck", "retry", "proof", "stop"];
function ActionButtons({ subject, card, compact, only, onResult, onDone }) {
  const { actions } = useCrewHost();
  const [busy, setBusy] = useState3(null);
  if (!actions) return null;
  const { Button: Button2 } = actions;
  const on = actionStates(subject);
  const press = async (name) => {
    if (busy || !on[name]) return;
    const extra = {};
    if (name === "stop") {
      if (!await actions.confirm("Stop this card?", "Its run is killed and the card is parked with its history. /crew-unstuck continues it.")) return;
      extra.confirm = true;
    }
    if (name === "proof") {
      const brave = subject.proof_ask !== "rescope";
      if (brave && !await actions.confirm("Run the flagged proof?", "Hermes flagged this proof command as dangerous. Brave runs it for this card anyway.")) return;
      extra.mode = brave ? "brave" : "yes";
    }
    setBusy(name);
    try {
      onResult(await actions.run(name, card, extra));
    } catch (e) {
      onResult({ ok: false, text: LABEL[name] + " failed: " + (e instanceof Error ? e.message : String(e)) });
    }
    setBusy(null);
    onDone();
  };
  return /* @__PURE__ */ jsx(Fragment, { children: NAMES.filter((n) => (!only || only.includes(n)) && (n !== "proof" || on.proof)).map((n) => /* @__PURE__ */ jsx(
    Button2,
    {
      id: compact ? void 0 : "act-" + n,
      size: "xs",
      variant: n === "stop" ? "destructive" : n === "proof" ? "default" : "outline",
      disabled: !on[n] || !!busy,
      title: on[n] ? WHAT[n] : WHY_NOT[n],
      onClick: () => {
        void press(n);
      },
      children: LABEL[n]
    },
    n
  )) });
}
function useFlash(reset) {
  const [msg, setMsg] = useState3(null);
  const timer = useRef2(null);
  useEffect3(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);
  useEffect3(() => {
    setMsg(null);
  }, [reset]);
  return [msg, (m) => {
    setMsg(m);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), SHOW_MS);
  }];
}
function ActionBar({ card, openChat, onDone }) {
  const { actions } = useCrewHost();
  const [msg, show] = useFlash(card.card_id);
  if (!actions) return null;
  const { Button: Button2 } = actions;
  const target = coordinatorTarget(card.coordinator);
  return /* @__PURE__ */ jsxs("div", { id: "actionbar", className: "actionbar", children: [
    /* @__PURE__ */ jsxs("div", { className: "abtns", children: [
      /* @__PURE__ */ jsx(ActionButtons, { subject: cardSubject(card), card: card.card_id, onResult: show, onDone }),
      target && openChat ? /* @__PURE__ */ jsx(
        Button2,
        {
          id: "act-chat",
          size: "xs",
          variant: "ghost",
          title: "open the chat this card came from",
          onClick: () => openChat(target.profile, target.session),
          children: "Open chat"
        }
      ) : null
    ] }),
    msg ? /* @__PURE__ */ jsx("div", { id: "actionmsg", role: "status", className: "amsg" + (msg.ok ? "" : " bad"), children: msg.text }) : null
  ] });
}
function TileActions({ t, lane }) {
  const { actions } = useCrewHost();
  const [msg, show] = useFlash(t.id);
  if (!actions || lane !== "blocked") return null;
  const subject = { status: t.status, proof_ask: t.proof_ask || "", live: !!t.active };
  return /* @__PURE__ */ jsxs("div", { className: "tact", onClick: (e) => {
    e.preventDefault();
    e.stopPropagation();
  }, children: [
    /* @__PURE__ */ jsx("div", { className: "tbtns", children: /* @__PURE__ */ jsx(ActionButtons, { compact: true, only: ["unstuck", "retry", "proof"], subject, card: t.id, onResult: show, onDone: () => {
    } }) }),
    msg ? /* @__PURE__ */ jsx("div", { role: "status", className: "tmsg" + (msg.ok ? "" : " bad"), children: msg.text }) : null
  ] });
}

// src/components/CardTile.tsx
import { jsx as jsx2, jsxs as jsxs2 } from "react/jsx-runtime";
var tone = (v) => ({ "--tone": v });
function Chip({ text, kind }) {
  return /* @__PURE__ */ jsx2("span", { className: "schip", style: tone("var(--crew-tone-" + kind + ")"), children: text });
}
function State({ t }) {
  const a = t.active;
  if (a) {
    if (a.quiet_s !== null && a.quiet_s !== void 0 && a.quiet_s > QUIET_S) return /* @__PURE__ */ jsx2(Chip, { text: "no heartbeat", kind: "review" });
    let facts = "";
    if (a.steps) facts += " \xB7 step " + (+a.steps || 0);
    if (a.last_tool) facts += " \xB7 last: " + a.last_tool;
    return /* @__PURE__ */ jsx2(Chip, { text: "working \xB7 " + fmt(+a.for_s) + facts, kind: "running" });
  }
  if (t.status === "ready" || t.status === "todo") return /* @__PURE__ */ jsx2(Chip, { text: "queued", kind: "ready" });
  if (t.status === "blocked" || t.status === "triage") return /* @__PURE__ */ jsx2(Chip, { text: t.status === "triage" ? "needs you" : "blocked", kind: "blocked" });
  if (t.status === "review") return /* @__PURE__ */ jsx2(Chip, { text: "in review", kind: "review" });
  if (t.status !== "done") return null;
  if (t.verdict === "PASS") return /* @__PURE__ */ jsx2(Chip, { text: "\u2713 verified", kind: "running" });
  if (t.verdict === "FAIL") return /* @__PURE__ */ jsx2(Chip, { text: "\u2715 verify failed", kind: "blocked" });
  if (t.verdict === "unverified") return /* @__PURE__ */ jsx2(Chip, { text: "\u25CB unverified", kind: "review" });
  return /* @__PURE__ */ jsx2(Chip, { text: "done", kind: "done" });
}
function Avatar({ api, name, hue }) {
  const src = useAvatar(api, name);
  if (name) return /* @__PURE__ */ jsx2("img", { className: "avatar face", src, alt: name, title: name });
  return /* @__PURE__ */ jsx2("span", { className: "avatar", style: { "--hue": hue || "var(--crew-text-3)" }, children: "?" });
}
function CardTile({ t, lane, api, onOpen }) {
  const who = t.active ? t.active.profile : t.role || t.assignee || "unassigned";
  const b = t.budget;
  const quiet = !!t.active && t.active.quiet_s !== null && t.active.quiet_s !== void 0 && t.active.quiet_s > QUIET_S;
  const motion = t.active ? quiet ? " quiet" : " live" : "";
  const open2 = (e) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    onOpen(t.id);
  };
  return /* @__PURE__ */ jsxs2("a", { className: "card" + motion, "data-id": t.id, href: "/card/" + t.id, style: tone(TONE[t.status] || "var(--crew-tone-neutral)"), onClick: open2, children: [
    /* @__PURE__ */ jsx2("div", { className: "ti", children: t.title || "(untitled)" }),
    t.summary ? /* @__PURE__ */ jsx2("div", { className: "su", children: t.summary }) : null,
    /* @__PURE__ */ jsxs2("div", { className: "ft", children: [
      /* @__PURE__ */ jsx2(Avatar, { api, name: who === "unassigned" ? "" : who, hue: t.color }),
      /* @__PURE__ */ jsx2("span", { className: "who", children: who }),
      /* @__PURE__ */ jsx2(State, { t }),
      /* @__PURE__ */ jsxs2("span", { className: "r", children: [
        t.runs !== void 0 && t.runs > 1 ? /* @__PURE__ */ jsxs2("span", { title: "runs", children: [
          "\u21BB ",
          +t.runs || 0
        ] }) : null,
        b && b.pct >= 80 ? /* @__PURE__ */ jsxs2("span", { className: b.pct >= 100 ? "bad" : "warn", title: "token budget: " + (+b.used || 0) + " of " + (+b.ceiling || 0), children: [
          Math.round(b.pct),
          "%"
        ] }) : null,
        /* @__PURE__ */ jsx2("span", { title: "time in this state", children: fmt(t.settled_s !== null && t.settled_s !== void 0 ? t.settled_s : t.age_s) }),
        /* @__PURE__ */ jsx2("span", { className: "id", title: t.id, children: shortId(t.id) })
      ] })
    ] }),
    /* @__PURE__ */ jsx2(TileActions, { t, lane })
  ] });
}

// src/components/Lane.tsx
import { jsx as jsx3, jsxs as jsxs3 } from "react/jsx-runtime";
function LaneBody({ laneKey, children }) {
  const ref = useRef3(null);
  useLayoutEffect(() => {
    const y = +(store("scroll." + laneKey) || 0);
    if (y && ref.current) ref.current.scrollTop = y;
  }, [laneKey]);
  return /* @__PURE__ */ jsx3("div", { className: "lbody", ref, onScroll: (e) => store("scroll." + laneKey, String(e.currentTarget.scrollTop)), children });
}
function Lane({ lane: l, api, archivedOpen, older, onToggleArchived, onOlder, onOpenCard: onOpenCard2 }) {
  const tone4 = { "--tone": TONE[l.key] || "var(--crew-tone-neutral)" };
  const n = l.tiles.length + (l.hidden || 0);
  const key = (fn) => (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
    fn();
  };
  if (l.key === "archived" && n && !archivedOpen)
    return /* @__PURE__ */ jsxs3(
      "section",
      {
        className: "lane rail togglable",
        "data-lane": "archived",
        "data-toggle": "archived",
        role: "button",
        tabIndex: 0,
        "aria-expanded": "false",
        style: tone4,
        title: "Archived: " + n + " - click to open",
        onClick: onToggleArchived,
        onKeyDown: key(onToggleArchived),
        children: [
          /* @__PURE__ */ jsx3("div", { className: "lh", children: /* @__PURE__ */ jsx3("i", {}) }),
          /* @__PURE__ */ jsx3("span", { className: "lt", children: l.label }),
          /* @__PURE__ */ jsx3("span", { className: "ln", children: n })
        ]
      }
    );
  if (!n)
    return /* @__PURE__ */ jsxs3("section", { className: "lane rail", "data-lane": l.key, style: tone4, title: l.label + ": empty", children: [
      /* @__PURE__ */ jsx3("div", { className: "lh", children: /* @__PURE__ */ jsx3("i", {}) }),
      /* @__PURE__ */ jsx3("span", { className: "lt", children: l.label })
    ] });
  const toggle = l.key === "archived";
  return /* @__PURE__ */ jsxs3("section", { className: "lane", "data-lane": l.key, style: tone4, children: [
    /* @__PURE__ */ jsxs3(
      "div",
      {
        className: "lh",
        ...toggle ? { "data-toggle": "archived", role: "button", tabIndex: 0, "aria-expanded": "true", title: "click to collapse", onClick: onToggleArchived, onKeyDown: key(onToggleArchived) } : {},
        children: [
          /* @__PURE__ */ jsx3("i", {}),
          /* @__PURE__ */ jsx3("span", { className: "lt", children: l.label }),
          /* @__PURE__ */ jsx3("span", { className: "ln", children: n })
        ]
      }
    ),
    /* @__PURE__ */ jsxs3(LaneBody, { laneKey: l.key, children: [
      l.tiles.map((t) => /* @__PURE__ */ jsx3(CardTile, { t, lane: l.key, api, onOpen: onOpenCard2 }, t.id)),
      l.hidden && l.key === "done" ? /* @__PURE__ */ jsxs3("button", { className: "more", "data-older": "1", onClick: () => onOlder(true), children: [
        "Show ",
        +l.hidden || 0,
        " older"
      ] }) : l.key === "done" && older ? /* @__PURE__ */ jsx3("button", { className: "more", "data-older": "0", onClick: () => onOlder(false), children: "Show the newest only" }) : null
    ] })
  ] });
}

// src/components/Board.tsx
import { jsx as jsx4, jsxs as jsxs4 } from "react/jsx-runtime";
var HEADER = [["running", "running", ["running"]], ["blocked", "blocked", ["blocked", "triage"]], ["done", "done", ["done"]]];
var BELL = /* @__PURE__ */ jsx4("svg", { width: "15", height: "15", viewBox: "0 0 24 24", "aria-hidden": "true", fill: "currentColor", children: /* @__PURE__ */ jsx4("path", { d: "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" }) });
function Board({ api, onOpenCard: onOpenCard2, flags, onFlags, home }) {
  injectCss("base", base_default);
  injectCss("board", board_default);
  const { kanbanRow } = useCrewHost();
  const all = flags?.all ?? (typeof location !== "undefined" && /[?&]all=1/.test(location.search));
  const [older, setOlder] = useState4(() => flags?.older ?? !!store("older"));
  useEffect4(() => {
    if (flags?.older !== void 0) setOlder(flags.older);
  }, [flags?.older]);
  const [archivedOpen, setArchivedOpen] = useState4(() => {
    if (typeof location !== "undefined" && location.hash === "#archived") store("archived.open", "1");
    return !!store("archived.open");
  });
  const query = [all ? "all=1" : "", older ? "older=1" : ""].filter(Boolean).join("&");
  const { board, error, loading, refresh } = useBoard(api, 2e3, query);
  const setOlderFlag = (on) => {
    store("older", on ? "1" : null);
    setOlder(on);
    onFlags?.({ all, older: on });
  };
  const toggleArchived = () => {
    const next = !archivedOpen;
    store("archived.open", next ? "1" : null);
    setArchivedOpen(next);
  };
  const [staleSince, setStaleSince] = useState4(null);
  useEffect4(() => {
    setStaleSince((s) => error ? s || /* @__PURE__ */ new Date() : null);
  }, [error]);
  const when = useMemo(() => board ? (/* @__PURE__ */ new Date()).toLocaleTimeString() : "", [board]);
  const [cleared, setCleared] = useState4(/* @__PURE__ */ new Set());
  useEffect4(() => {
    setCleared(/* @__PURE__ */ new Set());
  }, [board]);
  const [notesOpen, setNotesOpen] = useState4(false);
  const wrap = useRef4(null);
  useEffect4(() => {
    const away = (e) => {
      if (!wrap.current?.contains(e.target)) setNotesOpen(false);
    };
    const esc = (e) => {
      if (e.key === "Escape" && isCrewKey(e, wrap.current?.closest(".crew-scope") || null)) setNotesOpen(false);
    };
    document.addEventListener("click", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("click", away);
      document.removeEventListener("keydown", esc);
    };
  }, []);
  const ack = (path, ids) => {
    setCleared((c) => /* @__PURE__ */ new Set([...c, ...ids]));
    api.post(path).then(refresh, refresh);
  };
  if (!board) {
    const box = { padding: 16, fontFamily: "var(--crew-font)" };
    return /* @__PURE__ */ jsx4("div", { style: box, children: error ? "Crew could not load: " + error : loading ? "Loading..." : "" });
  }
  const att = board.attention || {};
  const rows = (att.rows || []).filter((r) => !cleared.has(r.id));
  const live = board.live || 0;
  const cards = board.cards || 0;
  const counts = board.counts || {};
  const link = (board.dashboard_url || (typeof location !== "undefined" ? location.origin : "")) + "/";
  const brand = /* @__PURE__ */ jsx4("a", { className: "brand", href: "/", title: "overview", "aria-label": "crew overview", onClick: home ? (e) => {
    e.preventDefault();
    home();
  } : void 0, children: /* @__PURE__ */ jsx4("img", { src: MARK_URI, alt: "", width: 26, height: 26 }) });
  return /* @__PURE__ */ jsxs4("div", { className: "page-board crew-scope", children: [
    /* @__PURE__ */ jsxs4("header", { children: [
      brand,
      /* @__PURE__ */ jsxs4("span", { className: "badge" + (error ? " stale" : ""), id: "badge", title: error ? "the board server is not answering" : "the board server answers", children: [
        /* @__PURE__ */ jsx4("i", {}),
        "LIVE"
      ] }),
      /* @__PURE__ */ jsx4("h1", { children: "crew board" }),
      /* @__PURE__ */ jsx4("span", { className: "meta", id: "cards", children: cards + " card" + (cards === 1 ? "" : "s") }),
      /* @__PURE__ */ jsx4("span", { className: "meta" + (live ? " on" : ""), id: "live", children: live ? live + " working now" : "nothing running" }),
      /* @__PURE__ */ jsx4("div", { className: "stats", id: "counts", children: HEADER.map(([cls, word, statuses]) => {
        const n = statuses.reduce((a, s) => a + (counts[s] || 0), 0);
        return /* @__PURE__ */ jsxs4("span", { className: cls + (n ? "" : " none"), children: [
          /* @__PURE__ */ jsx4("b", { children: n }),
          word
        ] }, cls);
      }) }),
      /* @__PURE__ */ jsx4("span", { className: "meta", id: "when", children: "updated " + when }),
      /* @__PURE__ */ jsx4("span", { className: "stale", id: "stale", hidden: !error, children: staleSince ? "stale since " + hhmm(staleSince) : "" }),
      /* @__PURE__ */ jsxs4("span", { className: "hright", children: [
        kanbanRow ? /* @__PURE__ */ jsxs4("label", { className: "kswitch", title: "Hermes shows its own Kanban row in the sidebar; Crew hides it unless this is on", children: [
          /* @__PURE__ */ jsx4("input", { type: "checkbox", role: "switch", checked: kanbanRow.show, onChange: (e) => kanbanRow.set(e.target.checked) }),
          /* @__PURE__ */ jsx4("i", { "aria-hidden": "true" }),
          "Show Hermes Kanban row"
        ] }) : null,
        /* @__PURE__ */ jsxs4("span", { id: "bellwrap", ref: wrap, children: [
          /* @__PURE__ */ jsxs4(
            "button",
            {
              id: "bell",
              className: "bell" + (rows.length ? " waiting" : ""),
              "aria-label": "notifications",
              title: rows.length ? rows.length + " waiting - click for the list" : "nothing waiting",
              onClick: () => setNotesOpen((o) => !o),
              children: [
                BELL,
                /* @__PURE__ */ jsx4("span", { className: "n", id: "belln", children: rows.length })
              ]
            }
          ),
          /* @__PURE__ */ jsxs4("div", { id: "notes", hidden: !notesOpen, children: [
            /* @__PURE__ */ jsxs4("div", { className: "nh", children: [
              /* @__PURE__ */ jsxs4("span", { id: "notehead", children: [
                "needs you - ",
                /* @__PURE__ */ jsx4("b", { children: +(att.stuck || 0) }),
                " stuck - ",
                /* @__PURE__ */ jsx4("b", { children: +(att.done || 0) }),
                " done"
              ] }),
              /* @__PURE__ */ jsx4("button", { id: "clearall", title: "clear every listed row", onClick: () => ack("/ack/all", rows.map((r) => r.id)), children: "clear all" })
            ] }),
            /* @__PURE__ */ jsx4("div", { id: "noterows", children: rows.length ? rows.map((r) => /* @__PURE__ */ jsxs4("div", { className: "ar" + (r.status !== "done" ? " stuck" : ""), children: [
              /* @__PURE__ */ jsx4("span", { className: "st", children: r.status }),
              /* @__PURE__ */ jsx4("a", { className: "t", href: "/card/" + r.id, onClick: (e) => {
                e.preventDefault();
                setNotesOpen(false);
                onOpenCard2(r.id);
              }, children: r.id + " - " + (r.title || "(untitled)") }),
              /* @__PURE__ */ jsx4("span", { className: "w", children: r.who || "-" }),
              /* @__PURE__ */ jsx4("span", { className: "ag", children: fmt(+r.age_s) }),
              /* @__PURE__ */ jsx4("button", { title: "clear this one", onClick: () => ack("/ack/" + r.id, [r.id]), children: "\u2715" })
            ] }, r.id)) : /* @__PURE__ */ jsx4("div", { className: "empty", children: "nothing waiting" }) })
          ] })
        ] }),
        /* @__PURE__ */ jsxs4("span", { className: "node", children: [
          (board.node || "") + " - kanban" + (board.board && board.board !== "default" ? " " + board.board : "") + " ",
          /* @__PURE__ */ jsx4("a", { className: "tailnet", href: link, children: "link" })
        ] })
      ] })
    ] }),
    board.dispatcher && board.dispatcher.alive === false ? /* @__PURE__ */ jsxs4("div", { className: "dispatcher-down", id: "dispatcher-down", role: "alert", children: [
      /* @__PURE__ */ jsx4("b", { children: "Cards will not start." }),
      " " + (board.dispatcher.detail || "The gateway is not running") + ". Start it with ",
      /* @__PURE__ */ jsx4("code", { children: board.dispatcher.command || "hermes gateway run" })
    ] }) : null,
    /* @__PURE__ */ jsx4("main", { id: "board", children: board.lanes.map((l) => /* @__PURE__ */ jsx4(
      Lane,
      {
        lane: l,
        api,
        archivedOpen,
        older,
        onToggleArchived: toggleArchived,
        onOlder: setOlderFlag,
        onOpenCard: onOpenCard2
      },
      l.key
    )) })
  ] });
}

// src/components/CardPage.tsx
import { useCallback as useCallback3, useEffect as useEffect8, useMemo as useMemo3, useRef as useRef8, useState as useState9 } from "react";

// src/card-ui.ts
import { createContext as createContext2, useContext as useContext2 } from "react";
var CardUiContext = createContext2(null);
function useCardUi() {
  const ui = useContext2(CardUiContext);
  if (!ui) throw new Error("useCardUi: no CardPage above");
  return ui;
}

// src/styles/card.css
var card_default = `/* The card page, ported from scripts/crew_dashboard/crew.css (everything except the flow graph and minimap, which
   graph.css carries). Scoped under .page-card, which is now the page's root element instead of <body>. */
/* The reset skips the Desktop button bar (:where keeps the selector's weight at one class): its Buttons are the app's own,
   styled by utilities in a CSS layer, and an unlayered padding:0 here would strip every one of them. */
.page-card *:where(:not(#actionbar *)){box-sizing:border-box;margin:0;padding:0;}
/* the page root (it was <body>): fills its host. The served page keeps the browser's own 8px body margin, so the
   screenshots match the old page; Desktop's host has no such margin. */
.page-card{height:100%;flex:0 0 auto;min-width:0;}
#crew-app > .page-card{margin:8px;height:calc(100% - 16px);}
/* body.page-card became .page-card */
.page-card{display:flex;flex-direction:column;background:var(--crew-bg);color:var(--crew-text-2);
  font:12px/1.5 var(--crew-font);overflow:hidden;}
.page-card #event{flex:0 0 auto;padding:6px 14px;border-bottom:1px solid var(--crew-stroke-1);
  display:flex;align-items:center;gap:12px;white-space:nowrap;overflow:hidden;font-size:12px;}
.page-card #event .evmain{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;}
.page-card #event .t{color:var(--crew-text-3);margin-right:8px;}
.page-card #event .txt{color:var(--crew-text-1);}
.page-card #main{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}
.page-card #row{flex:1 1 auto;display:flex;min-height:0;}
.page-card #rail{flex:0 0 212px;border-right:1px solid var(--crew-stroke-2);background:var(--crew-elevated);
  padding:10px 9px;display:flex;flex-direction:column;min-height:0;overflow-y:auto;}
.page-card #toksec{flex:0 0 auto;border:1px solid var(--crew-stroke-1);border-radius:5px;background:var(--crew-bg);
  padding:6px 8px;margin-bottom:10px;}
.page-card #toksec .tokrow{display:flex;align-items:baseline;gap:8px;font-size:11px;line-height:1.6;}
.page-card #toksec .tk{color:var(--crew-text-3);}
.page-card #toksec .tv{margin-left:auto;color:var(--crew-text-1);transition:color .3s;font-variant-numeric:tabular-nums;white-space:nowrap;}
.page-card #rail.collapsed #toksec{display:none;}
.page-card #rail.collapsed{flex:0 0 44px;padding:10px 6px;overflow:hidden;}
.page-card #rail.collapsed .rbtnlabel,.page-card #rail.collapsed #briefsec{display:none;}
@keyframes ldot{0%,100%{box-shadow:0 0 0 0 transparent;transform:scale(1);}
  50%{box-shadow:0 0 0 4px var(--crew-running-halo);transform:scale(1.25);}}
.page-card #toparea{flex:0 0 auto;display:grid;width:100%;max-width:100%;
  grid-template-columns:minmax(0,1.15fr) minmax(0,1fr) minmax(0,1fr);gap:8px;padding:6px 12px;
  align-items:stretch;border-bottom:1px solid var(--crew-stroke-1);background:var(--crew-bg);
  max-height:40vh;overflow-y:auto;overflow-x:hidden;}
/* A card that is not looping has nothing to say in the third column, so its cell goes and the two
   live boxes take the width: the reason box stops wrapping into a fourth line and the card box
   keeps its fields on one line. Two tracks, not three with a note in one. */
.page-card #toparea.two{grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);}
/* \u2500\u2500 the card page's top area: the same design language as the step panel (ui-spec sections 3 and 5) \u2500\u2500
   each cell is a quiet elevated box with a small-caps label; state is a tinted pill in its tone; the run
   counts are a key-number grid; the card's own ids are copy chips; the reason boxes are callouts. */
.page-card #toparea .tcell{min-width:0;display:flex;flex-direction:column;gap:6px;padding:7px 10px;
  border:1px solid var(--crew-stroke-2);border-radius:8px;background:var(--crew-elevated);overflow-x:hidden;}
/* .tcell sets display:flex, which would beat the user agent's [hidden] rule: say it here. */
.page-card #toparea .tcell[hidden]{display:none;}
.page-card #toparea .tcell > .tch{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);}
.page-card #toparea .tcell > .tce{color:var(--crew-text-3);font-size:12px;}
.page-card #toparea .tcell > .tce[hidden]{display:none;}
@media (max-width:760px){
  .page-card #toparea{grid-template-columns:minmax(0,1fr);max-height:55vh;}
  .page-card #toparea.two{grid-template-columns:minmax(0,1fr);}
}
/* a state chip anywhere on the card page: tinted in its own tone (set --tone on the element) */
.page-card .chip-tone,.page-card #sit .pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:4px;
  padding:2px 8px;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #sit .pill i{width:6px;height:6px;border-radius:50%;background:var(--tone);}
.page-card #sit{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0;max-width:100%;font-size:12px;}
.page-card #sit > *{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:break-word;}
/* the run counts: one compact strip at the right end of the top event line - "3 runs | 1 done | 2 blocked ..." */
.page-card .sitkpis{display:inline-flex;align-items:stretch;border:1px solid var(--crew-stroke-2);border-radius:5px;
  background:var(--crew-bg);margin-left:auto;flex:0 0 auto;}
.page-card .sitkpis .kpi{display:flex;align-items:baseline;gap:4px;padding:1px 8px;border-left:1px solid var(--crew-stroke-2);}
.page-card .sitkpis .kpi:first-child{border-left:0;}
.page-card .sitkpis .kv{font-size:12px;font-weight:600;color:var(--crew-text-1);font-variant-numeric:tabular-nums;}
.page-card .sitkpis .kv.on{color:var(--tone);}
.page-card .sitkpis .kl{font-size:10px;color:var(--crew-text-4);}
/* The card's own fields: copy chips, the way the panel shows ids - label, mono value, copy */
.page-card #sitfields{display:flex;flex-wrap:wrap;align-items:center;gap:4px 5px;min-width:0;max-width:100%;}
.page-card #sitfields[hidden]{display:none;}
.page-card #sitfields .fp{display:inline-flex;align-items:baseline;gap:5px;font-size:10.5px;min-width:0;max-width:100%;
  border:1px solid var(--crew-stroke-2);border-radius:5px;padding:0 4px 0 7px;line-height:16px;}
.page-card #sitfields .fk{flex:0 0 auto;color:var(--crew-text-3);}
.page-card #sitfields .fv{min-width:0;max-width:34ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-family:var(--crew-mono);color:var(--crew-text-2);}
.page-card #sitfields .fp.act .fv{color:var(--crew-tone-running);}
.page-card #sitfields .copy{flex:0 0 auto;background:none;color:var(--crew-text-4);border:0;border-left:1px solid var(--crew-stroke-2);
  font:inherit;font-size:10px;line-height:14px;padding:0 0 0 5px;cursor:pointer;}
.page-card #sitfields .copy:hover{color:var(--crew-text-1);}
.page-card #sitfields .copy:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:1px;}
/* The open chat button sits on a row of its own, in the copy buttons' quiet style, with no divider before it. */
.page-card #sitfields .brk{flex-basis:100%;height:0;}
.page-card #sitfields .openrow .copy{border-left:0;padding-left:0;}
/* Desktop only: the commands for this card, under its fields (ActionBar draws nothing in the browser) */
.page-card #actionbar{display:flex;flex-direction:column;gap:4px;margin-top:2px;}
.page-card #actionbar .abtns{display:flex;flex-wrap:wrap;align-items:center;gap:5px;}
.page-card #actionbar .amsg{font-size:11px;line-height:1.4;color:var(--crew-text-2);overflow-wrap:anywhere;}
.page-card #actionbar .amsg.bad{color:var(--crew-tone-blocked);}
/* the pending reason and the repeated-stop note: callouts in their tone */
.page-card #sitbox,.page-card #spinbox{--tone:var(--crew-tone-blocked);margin:0;border:1px solid color-mix(in srgb, var(--tone) 22%, transparent);
  border-left:2px solid var(--tone);border-radius:6px;background:color-mix(in srgb, var(--tone) 7%, transparent);
  font-size:12px;overflow-y:auto;overflow-x:hidden;flex:0 0 auto;}
.page-card #sitbox{max-height:none;overflow:visible;}
/* only the text scrolls: the head and its copy button stay put */
.page-card #sitboxWhy{max-height:calc(2.9em + 7px);overflow-y:auto;}
/* 2 lines, so the top area keeps its height */
.page-card #spinbox{--tone:var(--crew-tone-review);max-height:28vh;}
.page-card #sitbox[hidden],.page-card #spinbox[hidden]{display:none;}
.page-card #sitbox.nobody{--tone:var(--crew-tone-review);}
.page-card #sitbox.done{--tone:var(--crew-tone-done);}
.page-card #sitboxHead,.page-card #spinboxHead{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:5px 9px 0;}
.page-card #sitboxHead .sbl{font-size:12px;font-weight:500;color:var(--tone);}
.page-card #sitboxHead .sb{--tone:var(--crew-tone-neutral);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  padding:1px 7px;border-radius:4px;background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #sitboxHead .sb.blocked,.page-card #sitboxHead .sb.failed{--tone:var(--crew-tone-blocked);}
.page-card #sitboxHead .sb.running{--tone:var(--crew-tone-running);}
.page-card #sitboxHead .sb.done{--tone:var(--crew-tone-done);}
.page-card #sitboxWhy,.page-card #spinboxText{padding:3px 9px 4px;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
  color:var(--crew-text-1);font-size:12px;line-height:1.45;}
.page-card #sitboxMeta{padding:0 9px 5px;color:var(--crew-text-3);font-size:10px;}
.page-card #spinboxCount{font-size:12px;font-weight:500;color:var(--tone);}
.page-card #spinboxHead .sbl{font-size:10px;font-weight:600;padding:1px 7px;border-radius:4px;color:var(--tone);
  background:color-mix(in srgb, var(--tone) 15%, transparent);text-transform:uppercase;letter-spacing:.04em;}
.page-card #sitCopy,.page-card #spinCopy{margin-left:auto;font:inherit;font-size:10.5px;padding:1px 7px;border-radius:4px;cursor:pointer;
  border:1px solid var(--crew-stroke-1);background:transparent;color:var(--crew-text-3);}
.page-card #sitCopy:hover,.page-card #spinCopy:hover{color:var(--crew-text-1);border-color:var(--crew-text-3);}
.page-card #spinboxText{padding:8px 10px;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
  color:var(--crew-text-2);line-height:1.45;}
.page-card #briefsec{padding:8px 10px 10px;border-bottom:1px solid var(--crew-stroke-1);}
.page-card #briefText{white-space:pre-wrap;word-break:break-word;font-size:10px;line-height:1.5;color:var(--crew-text-2);max-height:180px;overflow:auto;}
.page-card #briefSrc{color:var(--crew-text-3);font-size:9px;margin-top:4px;}
/* A session-text line that just arrived: animated once, on arrival only (the panel keeps a
   per-node key cache so the 2 s poll never replays it). stepIn is a chip animation - its
   max-height:16px would clip a wrapped line - so a text line gets its own. */
@keyframes sayIn{from{opacity:0;transform:translateY(-6px);}to{opacity:1;transform:translateY(0);}}
.page-card #scrubwrap{flex:0 0 auto;border-top:1px solid var(--crew-stroke-1);padding:8px 14px 4px;}
.page-card #scrubber{position:relative;height:34px;}
.page-card #scrubber .track{position:absolute;top:5px;left:0;right:0;border-top:1px solid var(--crew-stroke-1);}
.page-card #scrubber .tl{position:absolute;top:15px;font-size:9px;color:var(--crew-text-3);white-space:nowrap;}
.page-card #scrubber .tl.left{left:0;}
.page-card #scrubber .tl.right{right:0;}
.page-card #scrubber .tick{position:absolute;top:1px;transform:translateX(-50%);cursor:pointer;}
.page-card #scrubber .diam{width:8px;height:8px;border:1px solid var(--crew-text-3);background:transparent;transform:rotate(45deg);}
.page-card #scrubber .tick.active .diam{border-color:var(--crew-text-1);}
.page-card #scrubber .tick.playhead .diam{border-color:var(--crew-text-1);background:var(--crew-text-1);}
.page-card #statusbar{flex:0 0 auto;display:flex;align-items:center;gap:10px;padding:7px 14px 11px;
  border-top:1px solid var(--crew-stroke-1);background:var(--crew-elevated);font-size:11px;}
.page-card .pill{background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:10px;padding:1px 8px;color:var(--crew-text-2);}
.page-card .pill.btn{cursor:pointer;}
.page-card .pill.on{border-color:var(--crew-tone-running);color:var(--crew-tone-running);}
.page-card .live{background:var(--crew-tone-running);color:var(--crew-bg);border-radius:4px;padding:1px 8px;font-weight:700;
  font-size:10px;letter-spacing:.5px;}
.page-card .live.paused{background:var(--crew-text-3);}
.page-card #cardtitle{color:var(--crew-text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:30%;}
.page-card #statusbar .meta{margin-left:auto;display:flex;align-items:center;gap:14px;color:var(--crew-text-3);}
.page-card #statusbar .meta a{color:var(--crew-tone-ready);text-decoration:none;}
.page-card #statusbar .meta a:hover{text-decoration:underline;}
.page-card .hints{font-size:10px;}
.page-card #help{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--crew-elevated);
  border:1px solid var(--crew-stroke-1);border-radius:8px;padding:16px 20px;z-index:60;display:none;
  font-size:12px;box-shadow:0 10px 30px var(--crew-shadow);}
.page-card #help.open{display:block;}
.page-card #help .h{font-weight:700;margin-bottom:8px;}
.page-card #help .row{margin:3px 0;}
.page-card #help kbd{background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:3px;padding:0 5px;margin-right:6px;}
/* \u2500\u2500 step panel (ui-spec section 5): the third column of #row, below the top area, so it covers nothing.
   One template for every node kind: header - id chips - callout - KPIs - tabs; only the body scrolls. */
.page-card #panel{display:none;flex:0 0 420px;width:420px;min-width:0;flex-direction:column;background:var(--crew-bg);
  border-left:1px solid var(--crew-stroke-1);font:13px/1.45 var(--crew-font);color:var(--crew-text-1);overflow:hidden;}
.page-card #panel.open{display:flex;}
@media (max-width:1100px){
  .page-card #panel.open{position:fixed;top:0;right:0;bottom:0;z-index:50;box-shadow:-6px 0 18px var(--crew-shadow);}
}
.page-card #panel button{font:inherit;color:inherit;background:none;border:0;cursor:pointer;}
.page-card #panel .phead{display:flex;flex-direction:column;gap:10px;padding:14px 16px 12px;flex:0 0 auto;}
.page-card #panel .pnav{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--crew-text-3);}
.page-card #panel .pnav .navback:hover{color:var(--crew-text-1);}
.page-card #panel .pnav .x{margin-left:auto;font-size:14px;line-height:1;color:var(--crew-text-3);}
.page-card #panel .pnav .x:hover{color:var(--crew-text-1);}
.page-card #panel .pid{display:flex;align-items:center;gap:10px;}
.page-card #panel .pidt{min-width:0;}
.page-card #panel .pt{font-size:14px;font-weight:600;line-height:1.2;}
.page-card #panel .ps{font-size:11.5px;color:var(--crew-text-3);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.page-card #panel .pid .pill{margin-left:auto;}
.page-card #panel .avatar{display:inline-grid;place-items:center;flex:0 0 auto;border-radius:999px;width:18px;height:18px;
  font-size:9px;font-weight:600;background:color-mix(in srgb, var(--hue) 22%, transparent);color:var(--hue);}
.page-card #panel .avatar.lg{width:28px;height:28px;font-size:11px;}
.page-card #panel .pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;flex:0 0 auto;border-radius:4px;
  padding:3px 8px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}
.page-card #panel .pill i{width:6px;height:6px;border-radius:50%;background:var(--tone);}
.page-card #panel .ids{display:flex;flex-wrap:wrap;gap:5px;}
.page-card #panel .idc{display:inline-flex;align-items:baseline;gap:5px;max-width:100%;border:1px solid var(--crew-stroke-2);
  border-radius:5px;padding:1px 7px;font-size:10.5px;color:var(--crew-text-3);}
.page-card #panel .idc:hover{border-color:var(--crew-stroke-1);color:var(--crew-text-2);}
.page-card #panel .idc b{font-family:var(--crew-mono);font-weight:400;color:var(--crew-text-2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;max-width:220px;}
.page-card #panel .idc i{font-style:normal;color:var(--crew-text-4);}
.page-card #panel .pcall:empty,.page-card #panel .pkpi:empty{display:none;}
.page-card #panel .callout{display:flex;flex-direction:column;gap:6px;border-radius:6px;padding:10px;
  background:color-mix(in srgb, var(--tone) 7%, transparent);border-left:2px solid var(--tone);}
.page-card #panel .callout .ct{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:500;color:var(--tone);}
.page-card #panel .callout .cb{font-size:12.5px;line-height:1.5;color:var(--crew-text-1);overflow-wrap:anywhere;
  max-height:9.5em;overflow:auto;-webkit-user-select:text;user-select:text;}
.page-card #panel .callout .cm{font-size:10.5px;color:var(--crew-text-3);font-family:var(--crew-mono);overflow-wrap:anywhere;}
.page-card #panel .copy{margin-left:auto;font-size:10.5px;color:var(--crew-text-3);border:1px solid var(--crew-stroke-1);
  border-radius:4px;padding:1px 7px;}
.page-card #panel .kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border:1px solid var(--crew-stroke-2);border-radius:6px;}
.page-card #panel .kpi{padding:7px 10px;border-left:1px solid var(--crew-stroke-2);min-width:0;}
.page-card #panel .kpi:first-child{border-left:0;}
.page-card #panel .kpi .kv{font-size:13px;font-weight:600;color:var(--crew-text-1);font-variant-numeric:tabular-nums;}
.page-card #panel .kpi .kl{font-size:10px;color:var(--crew-text-4);margin-top:1px;}
.page-card #panel .ptabs{display:flex;align-items:center;padding:0 16px 10px;border-bottom:1px solid var(--crew-stroke-2);flex:0 0 auto;}
.page-card #panel .ptabs[hidden]{display:none;}
.page-card #panel .ptabs .hint{margin-left:auto;font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .seg{display:inline-flex;gap:2px;padding:2px;border-radius:7px;background:var(--crew-fill-1);}
.page-card #panel .seg b{font-weight:500;font-size:11.5px;padding:3px 10px;border-radius:5px;color:var(--crew-text-3);cursor:pointer;}
.page-card #panel .seg b:hover{color:var(--crew-text-1);}
.page-card #panel .seg b.on{background:var(--crew-elevated);color:var(--crew-text-1);box-shadow:0 0 0 1px var(--crew-stroke-2);}
.page-card #panel .seg b span{color:var(--crew-text-4);margin-left:4px;}
.page-card #panel .pbody{flex:1 1 auto;min-height:0;overflow-y:auto;padding:4px 16px 16px;}
.page-card #panel .empty{color:var(--crew-text-3);font-size:12px;padding:14px 0;}
.page-card #panel code{font-family:var(--crew-mono);font-size:.92em;padding:0 4px;border-radius:3px;background:var(--crew-fill-1);}
.page-card #panel .mono{font-family:var(--crew-mono);font-size:11.5px;}
.page-card #panel .bad{color:var(--crew-tone-blocked);}
.page-card #panel .ok{color:var(--crew-tone-running);}
.page-card #panel .warn{color:var(--crew-tone-review);}
.page-card #panel .dim{color:var(--crew-text-4);}
/* Transcript: time gutter (mono) + text (sans); the newest row up to 12 lines, older ones 5, click expands */
.page-card #panel .msg{display:grid;grid-template-columns:62px 1fr;gap:0 8px;padding:10px 0;border-bottom:1px solid var(--crew-stroke-2);cursor:pointer;}
.page-card #panel .msg:last-child{border-bottom:0;}
.page-card #panel .msg time{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);padding-top:3px;align-self:start;
  display:flex;align-items:center;gap:5px;}
.page-card #panel .msg p{margin:0;font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;-webkit-user-select:text;user-select:text;cursor:text;}
.page-card #panel .msg.first p{color:var(--crew-text-1);-webkit-line-clamp:12;}
.page-card #panel .msg.ex p{-webkit-line-clamp:unset;display:block;}
.page-card #panel .msg .md{min-width:0;font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;
  max-height:9em;overflow:hidden;-webkit-user-select:text;user-select:text;cursor:text;}
.page-card #panel .msg.first .md{color:var(--crew-text-1);max-height:22em;}
.page-card #panel .msg.ex .md{max-height:none;}
.page-card #panel .msg.new{animation:sayIn .3s ease-out;}
.page-card #panel .livedot{width:6px;height:6px;border-radius:50%;background:var(--crew-tone-running);display:inline-block;
  animation:beat 1.1s ease-in-out infinite;}
@keyframes beat{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.75)}}
/* Calls: the filter on top, a chip row per tool, folded rows newest first; expanded = args then output */
.page-card #panel .calltools{display:flex;align-items:center;gap:8px;padding:10px 0 8px;}
.page-card #panel .calltools .hint{margin-left:auto;font-size:10.5px;color:var(--crew-text-4);text-align:right;}
.page-card #panel .chips{display:flex;flex-wrap:wrap;gap:5px;padding-bottom:8px;}
.page-card #panel .chip{font-size:10.5px;border:1px solid var(--crew-stroke-1);border-radius:999px;padding:1px 8px;color:var(--crew-text-2);
  font-family:var(--crew-mono);}
.page-card #panel .chip b{font-weight:500;color:var(--crew-text-4);margin-left:3px;}
.page-card #panel .nl{font-size:10.5px;color:var(--crew-text-4);padding-bottom:6px;}
.page-card #panel .call{display:grid;grid-template-columns:14px auto 1fr auto;gap:0 8px;align-items:baseline;
  padding:6px 0;border-bottom:1px solid var(--crew-stroke-2);font-size:11.5px;cursor:pointer;}
.page-card #panel .call .st{font-size:11px;}
.page-card #panel .call .tn{font-family:var(--crew-mono);font-weight:600;color:var(--crew-text-1);}
.page-card #panel .call .ar{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-3);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;min-width:0;}
.page-card #panel .call.failed .ar{color:var(--crew-tone-blocked);}
.page-card #panel .call .of{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .call .ex{grid-column:2 / -1;margin-top:5px;padding:7px 9px;border-radius:5px;background:var(--crew-fill-2);
  font-family:var(--crew-mono);font-size:10.5px;line-height:1.5;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;
  cursor:text;-webkit-user-select:text;user-select:text;}
.page-card #panel .call .ex .ea+.ea{margin-top:4px;}
.page-card #panel .call .ex .eo{margin-top:6px;color:var(--crew-text-3);}
.page-card #panel .call .ex .eo.er{color:var(--crew-tone-blocked);}
/* Details / Contract / Proof / Result: a definition list; the leftover evidence sits in a closed "Raw fields" */
.page-card #panel dl{margin:0;}
.page-card #panel .kvr{display:grid;grid-template-columns:96px 1fr;gap:0 10px;align-items:baseline;padding:7px 0;
  border-bottom:1px solid var(--crew-stroke-2);font-size:12px;}
.page-card #panel .kvr dt{color:var(--crew-text-3);}
.page-card #panel .kvr dd{margin:0;color:var(--crew-text-1);overflow-wrap:anywhere;}
.page-card #panel .kvr dd small{display:block;font-size:10.5px;color:var(--crew-text-3);margin-top:2px;line-height:1.45;}
.page-card #panel .sec{margin-top:14px;}
.page-card #panel .label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);margin-bottom:6px;}
.page-card #panel .prose{font-size:12.5px;line-height:1.55;color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;}
.page-card #panel .prose.dimp{margin-top:4px;color:var(--crew-text-3);}
.page-card #panel .cm{font-size:10.5px;color:var(--crew-text-3);margin-top:8px;}
.page-card #panel .cmd{font-family:var(--crew-mono);font-size:11px;line-height:1.5;padding:8px 10px;border-radius:5px;
  background:var(--crew-fill-2);color:var(--crew-text-2);overflow-wrap:anywhere;white-space:pre-wrap;}
.page-card #panel details.raw{margin-top:14px;font-size:12px;}
.page-card #panel details.raw summary{cursor:pointer;color:var(--crew-text-3);font-size:11px;}
/* Route: the model chooser's trail, oldest first; a quota wall in the blocked tone */
.page-card #panel .route{display:flex;flex-direction:column;gap:6px;font-size:11.5px;padding-top:10px;}
.page-card #panel .route .rr{display:grid;grid-template-columns:86px 1fr;gap:8px;}
.page-card #panel .route time{font-family:var(--crew-mono);font-size:10.5px;color:var(--crew-text-4);}
.page-card #panel .route span{color:var(--crew-text-2);line-height:1.45;overflow-wrap:anywhere;}
.page-card #panel .route span.bad{color:var(--crew-tone-blocked);}
/* \u2500\u2500 scrollbars, both pages: a hairline track and a small rounded oval thumb in the theme's own tones \u2500\u2500 */
/* \u2500\u2500 the left rail: narrower, its two buttons in the panel's quiet style \u2500\u2500 */
.page-card #rail .rback{margin-top:10px;display:flex;}
.page-card #rail .rbot{margin-top:auto;display:flex;align-items:center;padding-top:10px;border-top:1px solid var(--crew-stroke-2);}
.page-card .railbtn{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;cursor:pointer;text-decoration:none;
  font:inherit;font-size:12px;line-height:1;padding:6px 11px;border-radius:6px;border:1px solid var(--crew-stroke-2);
  background:var(--crew-fill-2);color:var(--crew-text-2);transition:background .15s,border-color .15s,color .15s;}
.page-card .railbtn:hover{background:var(--crew-fill-1);border-color:var(--crew-stroke-1);color:var(--crew-text-1);}
.page-card .railbtn:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:1px;}
.page-card .railbtn .rbtnlabel{font-size:12px;}
.page-card .railbtn.tog{margin-left:auto;padding:6px 9px;font-size:13px;}
.page-card #rail.collapsed .rback,.page-card #rail.collapsed .rbot{justify-content:center;}
.page-card #rail.collapsed .railbtn{padding:6px 8px;}
.page-card #rail.collapsed .railbtn.tog{margin-left:0;}
/* \u2500\u2500 the role filters: one horizontal strip under the top boxes; a role is a small card that focuses its
   nodes, and its last message opens that lane's newest step \u2500\u2500 */
.page-card #rolestrip{flex:0 0 auto;border-bottom:1px solid var(--crew-stroke-2);background:var(--crew-bg);padding:6px 12px;}
.page-card #roster{display:flex;gap:6px;overflow-x:auto;align-items:stretch;}
.page-card .role{flex:0 1 auto;min-width:0;max-width:340px;display:flex;flex-direction:column;justify-content:center;gap:2px;
  padding:5px 11px 5px 9px;border:1px solid var(--crew-stroke-2);border-radius:8px;background:var(--crew-fill-2);cursor:pointer;
  transition:border-color .15s,background .15s;}
.page-card .role:hover{border-color:var(--crew-stroke-1);}
.page-card .role.on{border-color:var(--crew-text-3);background:var(--crew-elevated);}
.page-card .role.all{flex:0 0 auto;}
.page-card .role.all .rn{color:var(--crew-text-1);}
.page-card .role .rl{display:flex;align-items:center;gap:6px;white-space:nowrap;}
.page-card .role .ricon{font-size:11px;width:auto;flex:0 0 auto;}
.page-card .role .rn{font-weight:600;font-size:12px;}
.page-card .role .rc{color:var(--crew-text-4);font-size:10.5px;margin-left:4px;}
.page-card .role .ra{color:var(--crew-text-3);font-size:10.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.page-card .role .rmsg{font-size:11px;line-height:1.35;color:var(--crew-text-3);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;cursor:pointer;}
.page-card .role .rmsg:hover{color:var(--crew-text-1);}
.page-card .role .rmsg.live{color:var(--crew-text-2);}
.page-card .ldot{width:7px;height:7px;border-radius:50%;flex:0 0 auto;opacity:.45;}
.page-card .ldot.act{opacity:1;animation:ldot 1s ease-in-out infinite;}
.page-card #rail .rh{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.14em;color:var(--crew-text-4);margin-bottom:6px;}
.page-card #rail.collapsed .rh{display:none;}
/* the strip stays thin - the canvas is the page: one line per role, the last message inline and cut */
.page-card #rolestrip{padding:4px 12px;}
.page-card #roster{gap:5px;align-items:center;}
.page-card .role{flex-direction:row;align-items:center;gap:8px;padding:2px 10px 2px 8px;border-radius:999px;max-width:420px;}
.page-card .role .ra{display:none;}
.page-card .role .rn{font-size:11.5px;}
.page-card .role .rc{font-size:10px;margin-left:2px;}
.page-card .role .rmsg{min-width:0;max-width:300px;font-size:10.5px;border-left:1px solid var(--crew-stroke-2);padding-left:8px;}
/* the role strip: symbol, name, node count - nothing else; a symbol pulses while its role has a node running */
.page-card .role .ricon{font-size:12px;line-height:1;display:inline-block;}
.page-card .role .ricon.act{animation:ricpulse 1.2s ease-in-out infinite;text-shadow:0 0 6px currentColor;}
@keyframes ricpulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(1.3)}}
@media (prefers-reduced-motion: reduce){ .page-card .role .ricon.act{animation:none} }
/* the brand mark: our logo with no background, the very top left of the header, linking to the overview */
.page-board header a.brand{display:inline-flex;align-items:center;flex:0 0 auto;border-radius:6px}
.page-board header a.brand img{display:block;width:18px;height:18px}
.page-board header a.brand:hover{background:var(--crew-fill-1)}
.page-board header a.brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}
/* the brand mark on the card (steps) view: the same logo with no background, pinned at the top left of the
   event strip and clearing it with #event's left padding; it links to the overview (/), like the board's. */
.page-card{position:relative}
.page-card .brand{position:absolute;top:10px;left:14px;z-index:5;display:inline-flex;align-items:center;border-radius:4px}
.page-card .brand img{display:block;width:12px;height:12px}
.page-card .brand:hover{background:var(--crew-fill-1)}
.page-card .brand:focus-visible{outline:2px solid var(--crew-tone-ready);outline-offset:2px}
.page-card #event{padding-left:28px}
/* the graph (graph.css) sits in the page's row where #stage used to: it takes the width the rail and panel leave */
.page-card #row > .crew-graph{flex:1 1 auto;}
/* The panel's tool chips also took the graph's base .chips / .chip rules on the old page (graph.css scopes those to
   .crew-graph now), so the two bits they contributed are restated here: the chip row's margin and the chip's field. */
.page-card #panel .chips{margin:4px 0 0 4px;}
.page-card #panel .chip{background:var(--crew-bg);white-space:nowrap;}

/* \u2500\u2500 narrow layout (the Desktop pane beside the flow pane is ~580 px wide): the status bar is ONE line, the
   least important items step aside by width and stay in the DOM; the title shrinks; the role strip and the rail
   scroll by wheel without drawing a bar. Container queries on the bar and the strip, so the wide page is untouched. \u2500\u2500 */
.page-card #statusbar{container-type:inline-size;container-name:crewbar;flex-wrap:nowrap;white-space:nowrap;}
.page-card #statusbar > *,.page-card #statusbar .meta > *{flex:0 0 auto;}
.page-card #statusbar #cardtitle{flex:0 1 auto;min-width:0;}
.page-card #statusbar .meta{min-width:0;flex:0 1 auto;}
.page-card #statusbar .meta .hints{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;}
.page-card #rail{scrollbar-width:none;}
.page-card #rail::-webkit-scrollbar{display:none;}
.page-card #rolestrip{container-type:inline-size;container-name:crewstrip;}
@container crewbar (max-width:900px){ .page-card #statusbar .hints{display:none;} }
@container crewbar (max-width:620px){ .page-card #statusbar #ractive{display:none;} }
@container crewbar (max-width:480px){ .page-card #statusbar #counts{display:none;} }
@container crewbar (max-width:360px){ .page-card #statusbar #followbtn{display:none;} }
@container crewstrip (max-width:700px){
  .page-card #roster{scrollbar-width:none;}
  .page-card #roster::-webkit-scrollbar{display:none;}
  .page-card .role .rmsg{display:none;}
  .page-card .role{flex:0 0 auto;}
}
`;

// src/components/EventLine.tsx
import { Fragment as Fragment2, jsx as jsx5, jsxs as jsxs5 } from "react/jsx-runtime";
var T = ({ children }) => /* @__PURE__ */ jsx5("span", { className: "t", children });
function Event({ card }) {
  const nodes = card.nodes || [];
  let lastRun = null, lastEnd = -1;
  for (const n of nodes) {
    if ((n.kind === "run" || n.kind === "verifier") && (n.t1 || 0) > lastEnd) {
      lastEnd = n.t1 || 0;
      lastRun = n;
    }
  }
  let root = null;
  for (const n of nodes) if (n.kind === "card") root = n;
  const rootEv = root && root.evidence || {};
  if (rootEv.block_reason)
    return /* @__PURE__ */ jsxs5(Fragment2, { children: [
      /* @__PURE__ */ jsx5(T, { children: fmtTime(root.t1 || 0) }),
      /* @__PURE__ */ jsx5(T, { children: "coordinator" }),
      /* @__PURE__ */ jsx5("span", { className: "txt", children: "card " + (card.card_status || "blocked") + ": " + rootEv.block_reason })
    ] });
  let live = null;
  for (const n of nodes) if (n.status === "live" || n.status === "running") live = n;
  if (live) {
    const ls = live.steps || [];
    const s = ls[ls.length - 1];
    return /* @__PURE__ */ jsxs5(Fragment2, { children: [
      /* @__PURE__ */ jsx5(T, { children: fmtTime(s ? s.ts : live.t1) }),
      /* @__PURE__ */ jsx5(T, { children: live.role || "" }),
      /* @__PURE__ */ jsx5("span", { className: "txt", children: "working now" + (s ? ": " + s.tool + (s.args ? " " + s.args : "") : "") })
    ] });
  }
  let best = null, bestTs = -1;
  if (lastRun) {
    for (const s of lastRun.steps || []) if ((s.ts || 0) >= lastEnd - 2 && (s.ts || 0) > bestTs) {
      bestTs = s.ts || 0;
      best = s;
    }
  }
  const st = card.card_status || "";
  const head = /* @__PURE__ */ jsxs5(Fragment2, { children: [
    /* @__PURE__ */ jsx5(T, { children: fmtTime(lastEnd > 0 ? lastEnd : 0) }),
    /* @__PURE__ */ jsx5(T, { children: card.card_role || "coordinator" })
  ] });
  if (best)
    return /* @__PURE__ */ jsxs5(Fragment2, { children: [
      head,
      /* @__PURE__ */ jsx5("span", { className: "txt", children: (lastRun.role || "") + " " + best.tool + (best.args ? " " + best.args : "") + " - card " + st })
    ] });
  return /* @__PURE__ */ jsxs5(Fragment2, { children: [
    head,
    /* @__PURE__ */ jsx5("span", { className: "txt", children: "card " + st + " - " + (card.card_title || "") })
  ] });
}
function Kpis({ card }) {
  const s = card.situation || {}, c = s.counts || {};
  const kpi = (v, label, word) => /* @__PURE__ */ jsxs5("div", { className: "kpi", children: [
    /* @__PURE__ */ jsx5("div", { className: "kv" + (v && word ? " on" : ""), style: { "--tone": toneVar(word || "pending") }, children: +(v || 0) }),
    /* @__PURE__ */ jsx5("div", { className: "kl", children: label })
  ] });
  const title = +(s.runs || 0) + " runs: " + +(c.done || 0) + " done, " + +(c.blocked || 0) + " blocked, " + +(c.failed || 0) + " failed, " + +(c.running || 0) + " running";
  return /* @__PURE__ */ jsxs5("div", { className: "sitkpis", title, children: [
    kpi(s.runs, "runs"),
    kpi(c.done, "done", "done"),
    kpi(c.blocked, "blocked", "blocked"),
    kpi(c.failed, "failed", "failed"),
    kpi(c.running, "running", "running")
  ] });
}
function EventLine({ card }) {
  return /* @__PURE__ */ jsxs5("div", { id: "event", children: [
    /* @__PURE__ */ jsx5("span", { className: "evmain", children: /* @__PURE__ */ jsx5(Event, { card }) }),
    /* @__PURE__ */ jsx5(Kpis, { card })
  ] });
}

// src/components/Graph.tsx
import { Fragment as Fragment3, useCallback as useCallback2, useId, useEffect as useEffect6, useLayoutEffect as useLayoutEffect2, useMemo as useMemo2, useRef as useRef6, useState as useState6 } from "react";

// src/graph-types.ts
var CW = 250;

// src/styles/graph.css
var graph_default = "/* The flow graph and its minimap, ported from scripts/crew_dashboard/crew.css (the .page-card graph rules). Same ids and\n   class names as card.js draws, scoped under .crew-graph instead of body.page-card so the graph can sit in any host\n   (the card page, the Desktop flow pane). Colours come from the --crew-* ladder in base.css only. */\n.crew-graph,.crew-graph *{box-sizing:border-box;margin:0;padding:0}\n.crew-graph{position:relative;display:flex;flex-direction:column;min-height:240px;min-width:0;\n  background:var(--crew-bg);color:var(--crew-text-2);font:12px/1.5 var(--crew-font);outline:none}\n\n.crew-graph .chip-tone{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:4px;\n  padding:2px 8px;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;\n  background:color-mix(in srgb, var(--tone) 15%, transparent);color:var(--tone);}\n.crew-graph .foot .chip-tone{padding:0 6px;font-size:9.5px;}\n.crew-graph .stage{flex:1 1 auto;position:relative;overflow:hidden;background-color:var(--crew-bg);\n  background-image:radial-gradient(circle, var(--crew-stroke-1) 1.3px, transparent 1px);\n  background-size:24px 24px;cursor:grab;}\n.crew-graph .stage{-webkit-user-select:none;user-select:none;}\n.crew-graph .stage.drag{cursor:grabbing;}\n.crew-graph .world{position:absolute;top:0;left:0;transform-origin:0 0;}\n.crew-graph .edges{position:absolute;top:0;left:0;pointer-events:none;overflow:visible;}\n.crew-graph .nodes{position:absolute;top:0;left:0;}\n.crew-graph .node{position:absolute;width:250px;transition:opacity .15s;}\n.crew-graph .node.dim{opacity:.18;}\n.crew-graph .card{position:relative;background:var(--crew-elevated);border:1px solid var(--crew-stroke-1);border-left-width:3px;\n  border-radius:6px;padding:6px 9px 6px 8px;cursor:pointer;}\n.crew-graph .card:hover{border-top-color:var(--crew-text-4);border-right-color:var(--crew-text-4);border-bottom-color:var(--crew-text-4);}\n.crew-graph .node.sel .card{border-top-color:var(--crew-tone-ready);border-right-color:var(--crew-tone-ready);border-bottom-color:var(--crew-tone-ready);}\n.crew-graph .node.alive .card{animation:breathe 1s ease-in-out infinite;}\n@keyframes breathe{0%,100%{box-shadow:0 0 0 0 transparent;}\n  50%{box-shadow:0 0 10px 2px var(--crew-running-glow);}}\n.crew-graph .badge{display:inline-block;border-radius:9px;padding:0 8px;font-size:10px;font-weight:700;\n  color:var(--crew-bg);letter-spacing:.3px;}\n.crew-graph .hdr{display:flex;align-items:center;gap:6px;font-weight:700;font-size:12px;margin-top:2px;}\n.crew-graph .glyph{flex:0 0 auto;width:12px;text-align:center;}\n.crew-graph .node.alive .glyph{animation:glyph 1s steps(1) infinite;}\n@keyframes glyph{50%{opacity:.35;}}\n.crew-graph .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--crew-text-1);}\n.crew-graph .gold{color:var(--crew-text-3);font-size:10px;margin:2px 0 0 0;}\n.crew-graph .desc{color:var(--crew-text-3);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .tools{color:var(--crew-tone-ready);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .foot{display:flex;justify-content:space-between;font-size:10px;}\n.crew-graph .foot .sw{font-weight:700;text-transform:uppercase;}\n.crew-graph .foot .tok{color:var(--crew-text-3);}\n.crew-graph .cellmark{display:none;position:absolute;inset:0;align-items:center;justify-content:center;\n  font-size:34px;font-weight:700;color:var(--crew-bg);}\n.crew-graph .world.cells .card > *:not(.cellmark){visibility:hidden;}\n.crew-graph .world.cells .cellmark{display:flex;}\n.crew-graph .world.cells .chips,.crew-graph .world.cells .steps{visibility:hidden;}\n.crew-graph .chips{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0 0 4px;}\n.crew-graph .chip{font-size:10px;border:1px solid;border-radius:9px;padding:0 7px;background:var(--crew-bg);white-space:nowrap;}\n.crew-graph .chip.done{opacity:.6;}\n.crew-graph .chip.more{color:var(--crew-text-3);border-color:var(--crew-stroke-1);}\n.crew-graph .chip .tk{color:var(--crew-text-3);font-variant-numeric:tabular-nums;}\n.crew-graph .brieftext{margin:3px 0 0 6px;font-size:10px;line-height:1.45;max-height:58px;overflow:hidden;}\n.crew-graph .bline{color:var(--crew-text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}\n.crew-graph .bsrc{color:var(--crew-text-3);font-size:9px;margin:2px 0 0 6px;}\n.crew-graph .node.briefcard .card{border-left-style:dashed;}\n.crew-graph .steps{margin:3px 0 0 6px;font-size:10px;line-height:1.5;max-height:93px;overflow:hidden;}\n.crew-graph .step{color:var(--crew-text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;\n  max-height:16px;will-change:transform,opacity;}\n.crew-graph .step.new{animation:stepIn .32s cubic-bezier(.2,.75,.3,1);}\n.crew-graph .step.out{animation:stepOut .26s ease-in forwards;overflow:hidden;}\n@keyframes stepIn{from{opacity:0;transform:translateY(-7px);max-height:0;}to{opacity:1;transform:translateY(0);max-height:16px;}}\n@keyframes stepOut{from{opacity:.9;transform:translateY(0);max-height:16px;}to{opacity:0;transform:translateY(-5px);max-height:0;}}\n.crew-graph .step:hover{color:var(--crew-text-2);}\n.crew-graph .step .ic{color:var(--crew-text-3);margin-right:4px;}\n.crew-graph .step .tn{font-weight:700;}\n.crew-graph .step .off{color:var(--crew-text-3);margin-left:6px;}\n.crew-graph .step .args{color:var(--crew-text-3);margin-left:6px;opacity:.7;}\n.crew-graph .edge{stroke:var(--crew-stroke-1);stroke-width:1.2;fill:none;}\n.crew-graph .edges .ah{fill:var(--crew-stroke-1);}\n.crew-graph .edges .ah.live{fill:var(--crew-tone-running);}\n.crew-graph .edge.live{stroke:var(--crew-tone-running);stroke-width:1.8;}\n.crew-graph .edge.dim{opacity:.15;}\n.crew-graph .edge.flow{stroke:var(--crew-tone-running);stroke-width:1.4;fill:none;opacity:.45;stroke-dasharray:2 8;\n  animation:flowdash 1.1s linear infinite;pointer-events:none;}\n@keyframes flowdash{to{stroke-dashoffset:-20;}}\n.crew-graph .edge-dot{fill:var(--crew-tone-running);filter:drop-shadow(0 0 3px var(--crew-tone-running));pointer-events:none;}\n.crew-graph .minimap{position:absolute;right:12px;bottom:12px;width:min(200px,34%);height:auto;aspect-ratio:200/130;background:var(--crew-overlay);\n  border:1px solid var(--crew-stroke-1);border-radius:5px;cursor:pointer;}\n.crew-graph .zoomlbl{position:absolute;left:10px;bottom:10px;color:var(--crew-text-3);font-size:10px;}\n/* The follow toggle sat in the card page's status bar; the graph carries its own so the Desktop pane has it too. */\n.crew-graph .gfollow{position:absolute;left:10px;top:10px;z-index:1;font:inherit;font-size:11px;cursor:pointer;\n  background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:10px;padding:1px 8px;color:var(--crew-text-2);}\n.crew-graph .gfollow.on{border-color:var(--crew-tone-running);color:var(--crew-tone-running);}\n.crew-graph .gempty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--crew-text-3);}\n\n/* The Desktop flow pane: a narrow vertical chart of the running card, node boxes joined by straight lines. */\n.crew-flow{display:flex;flex-direction:column;height:100%;min-height:0;overflow:auto;font:12px/1.5 var(--crew-font);color:var(--crew-text-2);}\n.crew-flow .fhead{display:flex;align-items:baseline;gap:8px;min-width:0;padding:10px 12px 4px;}\n.crew-flow .fsel{width:100%;min-width:0;font:inherit;color:var(--crew-text-1);background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:6px;padding:3px 6px;}\n.crew-flow .fid{font-family:var(--crew-mono);color:var(--crew-text-3);font-size:11px;flex:0 0 auto;}\n.crew-flow .ftitle{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--crew-text-1);font-weight:600;}\n.crew-flow .fchart{min-height:0;display:flex;flex-direction:column;align-items:stretch;padding:8px 10px 16px;cursor:pointer;}\n.crew-flow .fchart:focus-visible{outline:1px solid var(--crew-tone-running);}\n.crew-flow .fstepwrap{display:flex;flex-direction:column;align-items:stretch;min-width:0;}\n.crew-flow .fline{align-self:center;display:block;width:20px;height:18px;overflow:visible;}\n.crew-flow .fchart .node{position:relative;width:auto;min-width:0;}\n.crew-flow .fchart .card{cursor:inherit;}\n.crew-flow .fchart:hover .card{border-top-color:var(--crew-text-4);border-right-color:var(--crew-text-4);border-bottom-color:var(--crew-text-4);}\n.crew-flow .fnode.st-failed .card{border-top-color:var(--crew-tone-blocked);border-right-color:var(--crew-tone-blocked);border-bottom-color:var(--crew-tone-blocked);}\n.crew-flow .fnode .tok{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;}\n.crew-flow .fnone{padding:16px 12px;color:var(--crew-text-3);}\n.crew-flow .fboard{color:var(--crew-text-2);}\n\n/* motion means work: no breathing border, glyph blink or travelling dashes for a reader who asked for less */\n@media (prefers-reduced-motion: reduce){\n  .crew-graph .node.alive .card,.crew-graph .node.alive .glyph,.crew-graph .edge.flow{animation:none}\n  .crew-graph .node.alive .card{box-shadow:0 0 0 1px var(--crew-tone-running)}\n  .crew-graph .edge-dot{display:none}\n}\n.crew-flow .fhint{padding:6px 12px 0;font-size:11px;color:var(--crew-text-3);}\n.crew-flow .fcompact{padding:16px 12px;}\n.crew-flow .fhint kbd{font:inherit;background:var(--crew-bg);border:1px solid var(--crew-stroke-1);border-radius:3px;padding:0 4px;}\n";

// src/components/Minimap.tsx
import { useEffect as useEffect5, useRef as useRef5, useState as useState5 } from "react";
import { jsx as jsx6 } from "react/jsx-runtime";
function resolveColour(el, v) {
  el.style.color = v;
  return getComputedStyle(el).color;
}
function Minimap({ nodes, pos, world, cam, stage, focusRole, roleColor, onCenter }) {
  const ref = useRef5(null);
  const map = useRef5(null);
  const [size, setSize] = useState5({ w: 200, h: 130 });
  useEffect5(() => {
    const c = ref.current;
    if (!c || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      const w = Math.round(c.offsetWidth), h = Math.round(c.offsetHeight);
      if (w > 0 && h > 0) setSize((s) => s.w === w && s.h === h ? s : { w, h });
    });
    ro.observe(c);
    return () => ro.disconnect();
  }, []);
  useEffect5(() => {
    const c = ref.current;
    const ctx = c && c.getContext ? c.getContext("2d") : null;
    if (!c || !ctx) return;
    const W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);
    const sc = Math.min((W - 12) / world.w, (H - 12) / world.h);
    const ox = (W - world.w * sc) / 2, oy = (H - world.h * sc) / 2;
    map.current = { sc, ox, oy };
    for (const n of nodes) {
      const it = pos[n.id];
      if (!it) continue;
      ctx.globalAlpha = focusRole && n.role !== focusRole ? 0.25 : 1;
      ctx.fillStyle = resolveColour(c, roleColor(n));
      ctx.fillRect(ox + it.x * sc, oy + it.y * sc, Math.max(4, CW * sc), Math.max(3, it.cardH * sc));
    }
    ctx.globalAlpha = 1;
    const vx = -cam.tx / cam.k, vy = -cam.ty / cam.k, vw = stage.w / cam.k, vh = stage.h / cam.k;
    ctx.strokeStyle = resolveColour(c, "var(--crew-text-1)");
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + vx * sc + 0.5, oy + vy * sc + 0.5, vw * sc, vh * sc);
  }, [nodes, pos, world, cam, stage, focusRole, roleColor, size]);
  return /* @__PURE__ */ jsx6(
    "canvas",
    {
      className: "minimap",
      ref,
      width: size.w,
      height: size.h,
      onMouseDown: (e) => e.stopPropagation(),
      onClick: (e) => {
        e.stopPropagation();
        const m = map.current;
        const c = ref.current;
        if (!m || !c) return;
        const r = c.getBoundingClientRect();
        onCenter((e.clientX - r.left - m.ox) / m.sc, (e.clientY - r.top - m.oy) / m.sc);
      }
    }
  );
}

// src/components/Graph.tsx
import { Fragment as Fragment4, jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
var GX = 40;
var GY = 70;
var PADX = 30;
var PADY = 18;
var CELL_ZOOM = 0.5;
var MAX_CHIPS = 4;
var MAX_STEP_LINES = 6;
var COLOUR = {
  running: "var(--crew-tone-running)",
  done: "var(--crew-tone-done)",
  blocked: "var(--crew-tone-blocked)",
  failed: "var(--crew-tone-blocked)",
  pending: "var(--crew-tone-neutral)"
};
var CHIP = { pending: "var(--crew-tone-review)", ok: "var(--crew-tone-neutral)", err: "var(--crew-tone-blocked)" };
var GLYPH = { running: "\u25CF", done: "\u2713", failed: "\u2717", blocked: "\u2717", pending: "\u25CB" };
var ROLE_ICON2 = { coordinator: "\u25C6", worker: "\u25B2", content: "\u25CF", verifier: "\u2713" };
var roleIcon2 = (name) => name && ROLE_ICON2[name] || "\u25AA";
var shortId2 = (s) => s.length <= 14 ? s : s.slice(0, 7) + ".." + s.slice(-5);
var fmtTokens2 = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : "" + n;
var pad2 = (x) => (x < 10 ? "0" : "") + x;
function fmtTime2(sec) {
  if (sec == null) return "";
  const d = new Date(sec * 1e3);
  return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
}
function nameFor(n) {
  if (n.kind === "card") return n.title || n.label;
  if (n.kind === "run") return "run " + n.label;
  if (n.kind === "verifier" && String(n.label).indexOf("verdict") === 0) return n.label;
  if (n.kind === "brief") return n.title || "owner brief";
  return n.kind + " " + shortId2(String(n.label));
}
function descFor(n) {
  const e = n.evidence || {};
  if (n.kind === "card")
    return "status " + (n.status || "-") + " - coordinator" + (e.writer_role ? " - " + e.writer_role + " did the work" : "") + " - runs " + (e.run_count || 0) + (e.model_override ? "\nworker model: " + e.model_override + (e.provider_override ? " via " + e.provider_override : "") : "");
  if (n.kind === "run") return (e.profile || "-") + " - " + (e.outcome || "-") + " - " + (e.duration || "-");
  if (e.verdict) return e.command || "";
  return (e.model || "-") + " - " + (e.duration || "-");
}
function toolsLine(n) {
  const c = n.tool_count || 0;
  return n.last_tool ? "tools " + c + " - " + n.last_tool : "tools " + c;
}
function tokensFor(n) {
  const e = n.evidence || {};
  if (e.verdict) return "rc=" + e.rc + " - " + (e.duration_s != null ? e.duration_s + "s" : "");
  const t = e.output_tokens || 0;
  return t ? fmtTokens2(t) + " tok" : "";
}
var stepKey = (s) => (s.tool || "?") + "@" + (s.ts || 0) + "|" + String(s.args || "").slice(0, 24);
function unitIds(nodes, id) {
  const n = nodes.find((x) => x.id === id);
  if (!n) return {};
  const out = { [n.id]: 1 };
  const same = (a, b) => a !== void 0 && a !== null && a === b;
  if (n.kind === "run") {
    const rid = (n.evidence || {}).run_id;
    for (const x of nodes) if (x.kind === "session" && same(x.run_id, rid)) out[x.id] = 1;
  } else if (n.kind === "session") {
    const rid = n.run_id;
    for (const x of nodes) if (x.kind === "run" && same((x.evidence || {}).run_id, rid)) out[x.id] = 1;
  }
  return out;
}
function Tk({ ts }) {
  const [now, setNow] = useState6(() => Date.now() / 1e3);
  useEffect6(() => {
    const t = setInterval(() => setNow(Date.now() / 1e3), 500);
    return () => clearInterval(t);
  }, []);
  const el = now - ts;
  if (el < 0 || el > 300) return null;
  return /* @__PURE__ */ jsx7("span", { className: "tk", children: " " + el.toFixed(1) + "s" });
}
function Steps({ n, col, onPick }) {
  const seen = useRef6(null);
  const all = n.steps || [];
  const keys = /* @__PURE__ */ new Set();
  const lines = all.slice(-MAX_STEP_LINES).filter((s) => !keys.has(stepKey(s)) && !!keys.add(stepKey(s)));
  const marks = useRef6(/* @__PURE__ */ new Set());
  const [, redraw] = useState6(0);
  const before = seen.current;
  const added = before ? lines.map(stepKey).filter((k) => !before.has(k)) : [];
  added.forEach((k) => marks.current.add(k));
  useEffect6(() => {
    seen.current = new Set(keys);
    if (!added.length) return;
    setTimeout(() => {
      added.forEach((k) => marks.current.delete(k));
      redraw((x) => x + 1);
    }, 420);
  });
  return /* @__PURE__ */ jsx7("div", { className: "steps", children: lines.map((s) => {
    const k = stepKey(s);
    return /* @__PURE__ */ jsxs6(
      "div",
      {
        "data-k": k,
        className: "step" + (marks.current.has(k) ? " new" : ""),
        onClick: (ev) => {
          ev.stopPropagation();
          const i = all.findIndex((x) => stepKey(x) === k);
          if (i >= 0) onPick(i);
        },
        children: [
          /* @__PURE__ */ jsx7("span", { className: "ic", children: "\u25B8" }),
          /* @__PURE__ */ jsx7("span", { className: "tn", style: { color: col }, children: s.tool }),
          /* @__PURE__ */ jsx7("span", { className: "off", children: s.sec != null ? "t+" + s.sec + "s" : "" }),
          s.args ? /* @__PURE__ */ jsx7("span", { className: "args", children: s.args }) : null
        ]
      },
      k
    );
  }) });
}
function NodeView({ n, pageCard, rc, pos, sel, dim, cells, nodeRef, cardRef, onSelect }) {
  const col = COLOUR[n.status] || "var(--crew-tone-neutral)";
  const runs = n.tool_runs || [];
  const total = n.tool_run_total || runs.length;
  const shown = runs.slice(-MAX_CHIPS);
  const live = n.status === "running" || n.status === "pending" || n.t1 == null;
  const d = n.kind === "brief" ? "" : descFor(n);
  return /* @__PURE__ */ jsxs6(
    "div",
    {
      ref: nodeRef,
      className: "node" + (n.status === "running" ? " alive" : "") + (sel ? " sel" : "") + (dim ? " dim" : "") + (n.kind === "brief" ? " briefcard" : ""),
      "data-id": n.id,
      style: pos ? { left: pos.x + "px", top: pos.y + "px" } : void 0,
      children: [
        /* @__PURE__ */ jsxs6(
          "div",
          {
            ref: cardRef,
            className: "card",
            style: { borderLeftColor: rc, background: cells ? col : void 0 },
            onClick: (ev) => {
              ev.stopPropagation();
              onSelect(n.id);
            },
            children: [
              /* @__PURE__ */ jsx7("span", { className: "badge", style: { background: rc }, children: roleIcon2(n.role) + " " + (n.role || "?") }),
              /* @__PURE__ */ jsx7("div", { className: "gold", children: n.layer + " - " + n.kind + (n.card && n.card !== pageCard ? " - card " + n.card : "") }),
              /* @__PURE__ */ jsxs6("div", { className: "hdr", children: [
                /* @__PURE__ */ jsx7("span", { className: "glyph", style: { color: col }, children: GLYPH[n.status] || "\u25CB" }),
                /* @__PURE__ */ jsx7("span", { className: "name", children: nameFor(n) })
              ] }),
              n.kind === "brief" ? /* @__PURE__ */ jsxs6(Fragment4, { children: [
                /* @__PURE__ */ jsx7("div", { className: "brieftext", children: (n.brief && n.brief.text || "").split(/\n+/).slice(0, 4).map((ln, i) => /* @__PURE__ */ jsx7("div", { className: "bline", children: ln }, i)) }),
                /* @__PURE__ */ jsx7("div", { className: "bsrc", children: "source: " + (n.brief && n.brief.source || "owner") })
              ] }) : d ? /* @__PURE__ */ jsx7("div", { className: "desc", children: d }) : null,
              n.kind !== "card" && n.kind !== "run" ? /* @__PURE__ */ jsx7("div", { className: "tools", children: toolsLine(n) }) : null,
              /* @__PURE__ */ jsxs6("div", { className: "foot", children: [
                /* @__PURE__ */ jsx7("span", { className: "sw chip-tone", style: { ["--tone"]: col }, children: n.status }),
                /* @__PURE__ */ jsx7("span", { className: "tok", children: tokensFor(n) })
              ] }),
              /* @__PURE__ */ jsx7("div", { className: "cellmark", children: (n.role || "?").charAt(0).toUpperCase() })
            ]
          }
        ),
        runs.length ? /* @__PURE__ */ jsxs6("div", { className: "chips", children: [
          total > shown.length ? /* @__PURE__ */ jsx7("span", { className: "chip more", children: "+" + (total - shown.length) + " more" }) : null,
          shown.map((r, ri) => {
            const cc = CHIP[r.state] || "var(--crew-tone-neutral)";
            const mark = r.state === "ok" ? " \u2713" : r.state === "err" ? " \u2717" : "";
            return /* @__PURE__ */ jsxs6(
              "span",
              {
                className: "chip" + (r.state === "pending" ? "" : " done"),
                style: { color: cc, borderColor: cc },
                title: r.state + (r.last_ts ? " - " + fmtTime2(r.last_ts) : ""),
                children: [
                  r.tool + ((r.count || 0) > 1 ? " x" + r.count : "") + mark,
                  live && ri === shown.length - 1 && r.last_ts ? /* @__PURE__ */ jsx7(Tk, { ts: r.last_ts }) : null
                ]
              },
              ri + r.tool
            );
          })
        ] }) : null,
        /* @__PURE__ */ jsx7(Steps, { n, col, onPick: (i) => onSelect(n.id, i) })
      ]
    }
  );
}
var sameLayout = (a, b) => !!a && a.world.w === b.world.w && a.world.h === b.world.h && Object.keys(b.pos).length === Object.keys(a.pos).length && Object.keys(b.pos).every((k) => a.pos[k] && a.pos[k].x === b.pos[k].x && a.pos[k].y === b.pos[k].y && a.pos[k].cardH === b.pos[k].cardH);
function Graph({ card, height, selectedId, onSelect, focusRole: focusProp, standalone, onFollowChange }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const arrowId = "arrow" + uid, arrowLiveId = "arrowlive" + uid;
  injectCss("base", base_default);
  injectCss("graph", graph_default);
  const nodes = useMemo2(() => card.nodes || [], [card.nodes]);
  const edges = useMemo2(() => card.edges || [], [card.edges]);
  const focusRole = focusProp ?? null;
  const [innerSel, setInnerSel] = useState6(null);
  const sel = selectedId !== void 0 ? selectedId : innerSel;
  const select = useCallback2((id, step) => {
    setInnerSel(id);
    if (onSelect) onSelect(id, step);
  }, [onSelect]);
  const [layout, setLayout] = useState6(null);
  const [cam, setCam] = useState6({ k: 1, tx: 0, ty: 0 });
  const [follow, setFollow] = useState6(false);
  const [drag, setDrag] = useState6(false);
  const [stage, setStage] = useState6({ w: 0, h: 0 });
  const nodeEls = useRef6({});
  const cardEls = useRef6({});
  const stageEl = useRef6(null);
  const camRef = useRef6(cam);
  camRef.current = cam;
  const layoutRef = useRef6(layout);
  layoutRef.current = layout;
  const followRef = useRef6(follow);
  followRef.current = follow;
  useEffect6(() => {
    if (onFollowChange) onFollowChange(follow);
  }, [follow]);
  const fitted = useRef6(false);
  const fitLayout = useRef6(null);
  const userCam = useRef6(false);
  const dragRef = useRef6(null);
  const suppressClick = useRef6(false);
  const prevStageW = useRef6(null);
  const world = layout ? layout.world : { w: 400, h: 300 };
  const roleColor = useCallback2((n) => {
    const r = (card.roles || []).find((x) => x.name === n.role);
    return n.role_color || r && r.color || "var(--crew-tone-neutral)";
  }, [card.roles]);
  const stageSize = () => {
    const s = stageEl.current;
    return { w: s ? s.clientWidth : 0, h: s ? s.clientHeight : 0 };
  };
  const fitView = useCallback2(() => {
    const w = layoutRef.current ? layoutRef.current.world : { w: 400, h: 300 };
    const s = stageSize();
    const k = Math.max(0.12, Math.min(Math.min(s.w / w.w, s.h / w.h) * 0.92, 1.2));
    setCam({ k, tx: (s.w - w.w * k) / 2, ty: Math.max(10, (s.h - w.h * k) / 2) });
  }, []);
  const centerOn = useCallback2((id) => {
    const it = layoutRef.current && layoutRef.current.pos[id];
    if (!it) return;
    const s = stageSize(), k = camRef.current.k;
    setCam({ k, tx: s.w / 2 - (it.x + CW / 2) * k, ty: s.h / 2 - (it.y + it.cardH / 2) * k });
  }, []);
  const followTarget = () => {
    let best = null, bt = -1;
    let pool = nodes.filter((n) => n.status === "running");
    if (!pool.length) pool = nodes;
    for (const n of pool) {
      const t = n.last_ts || 0;
      if (t >= bt) {
        bt = t;
        best = n;
      }
    }
    return best;
  };
  const stopFollow = () => {
    if (followRef.current) setFollow(false);
  };
  const cardId = card.card_id;
  useLayoutEffect2(() => {
    fitted.current = false;
    userCam.current = false;
    setInnerSel(null);
  }, [cardId]);
  useLayoutEffect2(() => {
    const layers = {};
    let maxLayer = 0;
    for (const n of nodes) {
      (layers[n.layer] = layers[n.layer] || []).push(n);
      if (n.layer > maxLayer) maxLayer = n.layer;
    }
    const pos = {};
    let y = PADY, totalW = PADX;
    for (let l = 0; l <= maxLayer; l++) {
      const lyr = (layers[l] || []).slice().sort((a, b) => (a.x || 0) - (b.x || 0));
      if (!lyr.length) continue;
      let x = PADX, maxH = 0;
      for (const n of lyr) {
        const el = nodeEls.current[n.id], ce = cardEls.current[n.id];
        pos[n.id] = { x, y, cardH: ce && ce.offsetHeight || 40 };
        maxH = Math.max(maxH, el && el.offsetHeight || 0);
        x += CW + GX;
      }
      totalW = Math.max(totalW, x - GX + PADX);
      y += maxH + GY;
    }
    const next = { pos, world: { w: Math.max(totalW, 300), h: Math.max(y - GY + PADY, 200) } };
    setLayout((prev) => sameLayout(prev, next) ? prev : next);
  }, [nodes]);
  useEffect6(() => {
    if (!layout) return;
    if (!fitted.current) {
      fitted.current = true;
      fitLayout.current = layout;
      fitView();
    } else if (layout !== fitLayout.current && !userCam.current) {
      fitLayout.current = layout;
      fitView();
    }
    if (followRef.current) {
      const t = followTarget();
      if (t) centerOn(t.id);
    }
  }, [layout, follow, nodes]);
  useEffect6(() => {
    const el = stageEl.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      const s = stageSize();
      setStage((p) => p.w === s.w && p.h === s.h ? p : s);
      const prev = prevStageW.current;
      prevStageW.current = s.w;
      if (!layoutRef.current) return;
      if (userCam.current && prev !== null) {
        const d = (s.w - prev) / 2;
        if (d) setCam((c) => ({ ...c, tx: c.tx + d }));
      } else if (!userCam.current) fitView();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fitView]);
  useEffect6(() => {
    const st = stageEl.current;
    if (!st) return;
    const wheel = (e) => {
      e.preventDefault();
      const r = st.getBoundingClientRect(), c = camRef.current;
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      const k2 = Math.max(0.12, Math.min(2.5, c.k * Math.exp(-e.deltaY * 15e-4)));
      const wx = (mx - c.tx) / c.k, wy = (my - c.ty) / c.k;
      userCam.current = true;
      stopFollow();
      setCam({ k: k2, tx: mx - wx * k2, ty: my - wy * k2 });
    };
    st.addEventListener("wheel", wheel, { passive: false });
    const move = (e) => {
      const d = dragRef.current;
      if (!d) return;
      const dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (!d.moved && Math.abs(dx) + Math.abs(dy) > 4) {
        d.moved = true;
        setDrag(true);
        stopFollow();
      }
      if (d.moved) {
        userCam.current = true;
        setCam({ k: camRef.current.k, tx: d.tx + dx, ty: d.ty + dy });
      }
    };
    const up = () => {
      const d = dragRef.current;
      if (d && d.moved) {
        suppressClick.current = true;
        setTimeout(() => {
          suppressClick.current = false;
        }, 0);
      }
      dragRef.current = null;
      setDrag(false);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => {
      st.removeEventListener("wheel", wheel);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
  }, []);
  const onSelectNode = (id, step) => {
    if (!suppressClick.current) select(id, step);
  };
  const units = unitIds(nodes, sel);
  const cells = cam.k < CELL_ZOOM;
  const g = 24 * cam.k;
  const byId = {};
  if (layout) {
    for (const n of nodes) if (layout.pos[n.id]) byId[n.id] = { n, p: layout.pos[n.id] };
  }
  const key = (e) => {
    if (e.key === "f") {
      stopFollow();
      userCam.current = false;
      fitView();
    } else if (e.key === "F") setFollow((f) => !f);
    else if (e.key === "0") {
      stopFollow();
      userCam.current = true;
      setCam({ k: 1, tx: 0, ty: 0 });
    } else if (e.key === "Escape") select(null);
  };
  return /* @__PURE__ */ jsx7("div", { className: "crew-scope crew-graph", style: height ? { height: height + "px" } : void 0, tabIndex: 0, onKeyDown: key, children: /* @__PURE__ */ jsxs6(
    "div",
    {
      ref: stageEl,
      className: "stage" + (drag ? " drag" : ""),
      style: { backgroundSize: g + "px " + g + "px", backgroundPosition: cam.tx + "px " + cam.ty + "px" },
      onClick: () => {
        if (!suppressClick.current && sel) select(null);
      },
      onMouseDown: (e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        dragRef.current = { x: e.clientX, y: e.clientY, tx: camRef.current.tx, ty: camRef.current.ty, moved: false };
        suppressClick.current = false;
      },
      onDoubleClick: () => {
        stopFollow();
        userCam.current = false;
        fitView();
      },
      children: [
        /* @__PURE__ */ jsxs6(
          "div",
          {
            className: "world" + (cells ? " cells" : ""),
            style: { transform: "translate(" + cam.tx + "px," + cam.ty + "px) scale(" + cam.k + ")" },
            children: [
              /* @__PURE__ */ jsxs6("svg", { className: "edges", width: world.w, height: world.h, style: { width: world.w + "px", height: world.h + "px" }, children: [
                /* @__PURE__ */ jsx7("defs", { children: [[arrowId, "ah"], [arrowLiveId, "ah live"]].map(([id, cls]) => /* @__PURE__ */ jsx7("marker", { id, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse", children: /* @__PURE__ */ jsx7("path", { d: "M0,0 L10,5 L0,10 z", className: cls }) }, id)) }),
                edges.map((e, i) => {
                  const a = byId[e.from], b = byId[e.to];
                  if (!a || !b) return null;
                  const x1 = a.p.x + CW / 2, y1 = a.p.y + a.p.cardH, x2 = b.p.x + CW / 2, y2 = b.p.y;
                  const c = Math.max(y2 - y1, 0) * 0.55;
                  const d = "M" + x1 + " " + y1 + " C " + x1 + " " + (y1 + c) + ", " + x2 + " " + (y2 - c) + ", " + x2 + " " + y2;
                  const live = b.n.status === "running";
                  const off = !!focusRole && a.n.role !== focusRole && b.n.role !== focusRole;
                  return /* @__PURE__ */ jsxs6(Fragment3, { children: [
                    /* @__PURE__ */ jsx7("path", { d, className: "edge" + (live ? " live" : "") + (off ? " dim" : ""), markerEnd: "url(#" + (live ? arrowLiveId : arrowId) + ")" }),
                    live && !off ? /* @__PURE__ */ jsxs6(Fragment4, { children: [
                      /* @__PURE__ */ jsx7("path", { d, className: "edge flow" }),
                      /* @__PURE__ */ jsx7("circle", { r: "2.6", className: "edge-dot", children: /* @__PURE__ */ jsx7("animateMotion", { dur: "1.6s", repeatCount: "indefinite", path: d, fill: "freeze" }) })
                    ] }) : null
                  ] }, e.from + ">" + e.to + i);
                })
              ] }),
              /* @__PURE__ */ jsx7("div", { className: "nodes", style: { width: world.w + "px", height: world.h + "px" }, children: nodes.map((n) => /* @__PURE__ */ jsx7(
                NodeView,
                {
                  n,
                  pageCard: card.card_id,
                  rc: roleColor(n),
                  pos: layout ? layout.pos[n.id] : void 0,
                  sel: !!units[n.id],
                  dim: !!focusRole && n.role !== focusRole,
                  cells,
                  nodeRef: (el) => {
                    nodeEls.current[n.id] = el;
                  },
                  cardRef: (el) => {
                    cardEls.current[n.id] = el;
                  },
                  onSelect: onSelectNode
                },
                n.id
              )) })
            ]
          }
        ),
        standalone ? /* @__PURE__ */ jsx7("button", { type: "button", className: "gfollow" + (follow ? " on" : ""), onClick: (e) => {
          e.stopPropagation();
          setFollow((f) => !f);
        }, children: "follow " + (follow ? "on" : "off") }) : null,
        /* @__PURE__ */ jsx7(
          Minimap,
          {
            nodes,
            pos: layout ? layout.pos : {},
            world,
            cam,
            stage,
            focusRole,
            roleColor,
            onCenter: (wx, wy) => {
              const s = stageSize();
              userCam.current = true;
              stopFollow();
              setCam({ k: camRef.current.k, tx: s.w / 2 - wx * camRef.current.k, ty: s.h / 2 - wy * camRef.current.k });
            }
          }
        ),
        /* @__PURE__ */ jsx7("div", { className: "zoomlbl", children: Math.round(cam.k * 100) + "%" + (cells ? " - cells" : "") })
      ]
    }
  ) });
}

// src/components/Panel.tsx
import { useEffect as useEffect7, useLayoutEffect as useLayoutEffect3, useRef as useRef7, useState as useState7 } from "react";

// src/card-model.ts
var TAB_SETS = {
  step: ["Transcript", "Calls", "Details"],
  card: ["Contract", "Route", "Details"],
  verifier: ["Proof", "Runs", "Details"],
  close: ["Result", "Details"],
  brief: []
};
var LATEST_N = 6;
var roleDef = (card, name) => (card.roles || []).find((r) => r.name === name) || null;
var nodeById = (card, id) => (card.nodes || []).find((n) => n.id === id) || null;
function unitOf(card, n) {
  if (!n) return null;
  let run = null, sess = null;
  if (n.kind === "run") {
    run = n;
    const rid = (n.evidence || {}).run_id;
    for (const x of card.nodes || []) if (x.kind === "session" && x.run_id !== void 0 && x.run_id !== null && x.run_id === rid) sess = x;
  } else if (n.kind === "session") {
    sess = n;
    if (n.run_id !== void 0 && n.run_id !== null) run = nodeById(card, "run:" + n.run_id);
  }
  return { run, session: sess, main: n, key: run ? run.id : n.id };
}
function panelKind(n) {
  if (n.kind === "run" || n.kind === "session" || n.kind === "subagent") return "step";
  if (n.kind === "card" || n.kind === "verifier" || n.kind === "close" || n.kind === "brief") return n.kind;
  return "step";
}
function getSelectedNode(card, selected) {
  if (selected) {
    const n = nodeById(card, selected);
    if (n) return n;
  }
  let best = null, bestTs = -1;
  for (const n of card.nodes || []) for (const s of n.steps || []) {
    const t = s.ts || 0;
    if (t > bestTs) {
      bestTs = t;
      best = n;
    }
  }
  return best || card.nodes && card.nodes[0] || null;
}
function modelPick(card, startedAt) {
  let pick = null;
  for (const r of card.route || []) if (r.kind !== "quota_wall" && (!startedAt || (r.ts || 0) <= startedAt + 5)) pick = r;
  return pick;
}
function panelModel(card, n) {
  const ev = n.evidence || {}, kind = panelKind(n), u = unitOf(card, n);
  const m = { kind, tabs: TAB_SETS[kind], kpis: [] };
  const other = n.card && n.card !== card.card_id ? n.card : null;
  if (kind === "step" && u) {
    const run = u.run, sess = u.session || (n.kind === "subagent" ? n : null);
    const re = (run || {}).evidence || {}, se = (sess || {}).evidence || {};
    const lv = (sess || run || n).live || {};
    const live = lv.state === "pending" || (run || n).status === "running";
    m.role = n.role;
    m.unit = u;
    m.title = cap1(n.role) + " \xB7 " + (run ? "run " + (re.run_id !== void 0 ? re.run_id : run.label) : n.kind === "subagent" ? "subagent" : "session");
    m.sub = live ? "running " + fmtAgo((run || n).t0 || 0).replace(/ ago$/, "") + (lv.tool ? " \xB7 " + lv.tool : "") : (re.profile || se.profile_name || "") + (re.ended_at || (sess || {}).t1 ? " \xB7 ended " + hhmm2(re.ended_at || sess.t1) : "");
    if (other) m.sub += " \xB7 card " + other;
    const outcome = re.outcome || (sess || n).status;
    m.pill = [live ? "Running" : cap1(String(outcome || "").replace(/_/g, " ")), live ? "running" : outcome];
    m.chips = [
      ["model", "model", se.model || ev.model, "panelModCopy"],
      ["session_id", "session", se.session_id || ev.session_id, "panelSidCopy"],
      ["kanban id", "card", other || card.card_id, "panelCidCopy"]
    ];
    if (run && !live && outcome && outcome !== "completed" && (re.summary || re.error))
      m.callout = ["Why this run stopped", re.summary || re.error, re.summary && re.error ? re.error : "", outcome, "panelWhyCopy"];
    const tin = +se.input_tokens || 0, tout = +se.output_tokens || 0;
    const calls = +(se.tool_call_count || (sess || n).tool_count || 0) || 0;
    const failed = +(se.calls_failed !== void 0 && se.calls_failed !== null ? se.calls_failed : (sess || n).steps ? (sess || n).steps.filter((s) => s.state === "err").length : 0) || 0;
    m.kpis = [
      { value: re.duration || se.duration || "-", label: "duration" },
      sess ? { value: fmtTokens(tin + tout), label: "tokens \xB7 " + fmtTokens(tout) + " out" } : null,
      sess ? { value: String(calls), label: "tool calls", failed } : null
    ];
    m.src = sess || run || n;
    m.run = run;
    m.sess = sess;
    m.live = live;
    m.failed = failed;
    m.calls = calls;
  } else if (kind === "card") {
    m.role = "coordinator";
    m.title = "Coordinator \xB7 card";
    m.sub = (card.card_title || "") + (ev.run_count ? " \xB7 " + ev.run_count + " run" + (ev.run_count === 1 ? "" : "s") : "");
    m.pill = [cap1(card.card_status || n.status), card.card_status || n.status];
    m.chips = [
      ["model", "model", ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "", "panelModCopy"],
      ["session_id", "session", ev.coordinator || "", "panelSidCopy"],
      ["kanban id", "card", card.card_id, "panelCidCopy"]
    ];
  } else if (kind === "verifier") {
    m.role = "verifier";
    m.title = "Verifier \xB7 verdict";
    const runsV = ev.review_runs || [], lastRun = runsV[runsV.length - 1] || {};
    m.sub = ev.by ? "by " + ev.by + (ev.ts ? " \xB7 " + hhmm2(ev.ts) : "") : runsV.length ? runsV.length + " review run(s)" : "no verdict yet";
    m.pill = [ev.verdict || "unverified", ev.verdict || "unverified"];
    m.chips = [
      ["model", "model", "", "panelModCopy"],
      ["session_id", "session", lastRun.session_id || "", "panelSidCopy"],
      ["kanban id", "card", card.card_id, "panelCidCopy"]
    ];
    if (ev.verdict === "FAIL")
      m.callout = ["Verification failed", ev.output_head || "(no output recorded)", ev.command ? "command: " + ev.command : "", "FAIL", "panelWhyCopy"];
    m.kpis = [
      { value: ev.rc === null || ev.rc === void 0 ? "-" : String(ev.rc), label: "rc" },
      { value: ev.duration_s === null || ev.duration_s === void 0 ? "-" : ev.duration_s + "s", label: "duration" },
      { value: String(ev.verdict_count || 0), label: "verdict lines" }
    ];
  } else if (kind === "close") {
    m.role = "coordinator";
    m.title = "Coordinator \xB7 close";
    m.sub = ev.completed_at ? "completed " + dayTime(ev.completed_at) : "not closed";
    m.pill = [cap1(ev.status || n.status), ev.status || n.status];
    m.chips = [["model", "model", "", "panelModCopy"], ["session_id", "session", "", "panelSidCopy"], ["kanban id", "card", card.card_id, "panelCidCopy"]];
  } else if (kind === "brief") {
    m.role = n.role || "owner";
    m.title = "Owner brief";
    m.sub = ev.source ? "from " + ev.source : "";
    m.chips = [["kanban id", "card", card.card_id, "panelCidCopy"]];
  }
  return m;
}

// src/components/Runs.tsx
import { Fragment as Fragment5, jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
function Md({ text }) {
  const parts = String(text === null || text === void 0 ? "" : text).split(/`([^`\n]+)`/);
  return /* @__PURE__ */ jsx8(Fragment5, { children: parts.map((p, i) => i % 2 ? /* @__PURE__ */ jsx8("code", { children: p }, i) : p) });
}
function transcriptRows(m, expanded, renderMarkdown) {
  const src = m.src || {};
  const lines = (src.text || []).slice().reverse();
  return lines.map((l, i) => {
    const key = String(l.ts || "") + "|" + String(l.text || "").slice(0, 80);
    return {
      key,
      cls: "msg" + (i === 0 ? " first" : "") + (expanded[key] ? " ex" : ""),
      children: /* @__PURE__ */ jsxs7(Fragment5, { children: [
        /* @__PURE__ */ jsxs7("time", { children: [
          i === 0 && m.live ? /* @__PURE__ */ jsx8("i", { className: "livedot" }) : null,
          l.ts ? fmtTime(l.ts) : ""
        ] }),
        renderMarkdown ? /* @__PURE__ */ jsx8("div", { className: "md", children: renderMarkdown(String(l.raw || l.text || "")) }) : /* @__PURE__ */ jsx8("p", { children: /* @__PURE__ */ jsx8(Md, { text: l.text }) })
      ] })
    };
  });
}
function callGroups(m, views) {
  const steps = (m.src || {}).steps || [];
  const view = views[m.unit.key] || ((m.failed || 0) > 0 ? "failed" : "latest");
  const picked = view === "failed" ? steps.filter((s) => s.state === "err") : steps.slice(-LATEST_N);
  return { view, groups: groupParallel(picked).reverse(), steps };
}
function callRows(m, cg, open2) {
  return cg.groups.map((g) => {
    const key = g.k + "|" + (g.args[0] || "").slice(0, 24);
    const isOpen = !!open2[m.unit.key + "|" + key];
    const icon = g.state === "err" ? /* @__PURE__ */ jsx8("span", { className: "st bad", children: "\u2715" }) : g.state === "pending" ? /* @__PURE__ */ jsx8("span", { className: "st warn", children: "\u25CF" }) : /* @__PURE__ */ jsx8("span", { className: "st ok", children: "\u2713" });
    const prev = g.state === "err" && (g.note || g.out) ? g.note || g.out : g.args[0] || "";
    return {
      key,
      cls: "call" + (isOpen ? " open" : "") + (g.state === "err" ? " failed" : ""),
      children: /* @__PURE__ */ jsxs7(Fragment5, { children: [
        icon,
        /* @__PURE__ */ jsx8("span", { className: "tn", children: g.tool + (g.args.length > 1 ? " \xD7" + g.args.length : "") }),
        /* @__PURE__ */ jsx8("span", { className: "ar", children: prev }),
        /* @__PURE__ */ jsx8("span", { className: "of", children: offLabel(g) }),
        isOpen ? /* @__PURE__ */ jsxs7("div", { className: "ex", children: [
          g.args.filter((a) => a).map((a, i) => /* @__PURE__ */ jsx8("div", { className: "ea", children: a }, i)),
          /* @__PURE__ */ jsx8("div", { className: "eo" + (g.state === "err" ? " er" : ""), children: stepStatus(g) })
        ] }) : null
      ] })
    };
  });
}
function CallsHead({ m, cg, onView }) {
  const total = m.calls || cg.steps.length, loaded = cg.steps.length;
  const nf = m.failed || 0, latest = Math.min(LATEST_N, loaded);
  const chips = /* @__PURE__ */ new Map();
  for (const t of (m.src || {}).tool_runs || []) chips.set(t.tool, (chips.get(t.tool) || 0) + t.count);
  const failedLoaded = cg.steps.filter((s) => s.state === "err").length;
  const hint = cg.view === "failed" ? nf + " failed of " + total + " calls" + (nf > failedLoaded ? " (older failures not loaded)" : "") : "latest " + latest + " of " + total + " calls";
  const notLoaded = Math.max(0, total - loaded);
  return /* @__PURE__ */ jsxs7(Fragment5, { children: [
    /* @__PURE__ */ jsxs7("div", { className: "calltools", children: [
      /* @__PURE__ */ jsxs7("div", { className: "seg cbfilter", role: "tablist", children: [
        /* @__PURE__ */ jsxs7("b", { className: cg.view === "failed" ? "on" : "", "data-view": "failed", onClick: () => onView("failed"), children: [
          "Failed",
          /* @__PURE__ */ jsx8("span", { children: nf })
        ] }),
        /* @__PURE__ */ jsxs7("b", { className: cg.view === "latest" ? "on" : "", "data-view": "latest", onClick: () => onView("latest"), children: [
          "Latest",
          /* @__PURE__ */ jsx8("span", { children: latest })
        ] })
      ] }),
      /* @__PURE__ */ jsx8("span", { className: "hint", children: hint })
    ] }),
    chips.size ? /* @__PURE__ */ jsx8("div", { className: "chips", children: [...chips].map(([t, c]) => /* @__PURE__ */ jsxs7("span", { className: "chip", children: [
      t,
      /* @__PURE__ */ jsx8("b", { children: c })
    ] }, t)) }) : null,
    notLoaded ? /* @__PURE__ */ jsx8("div", { className: "nl", children: notLoaded + " earlier ok call" + (notLoaded === 1 ? "" : "s") + " not loaded" }) : null
  ] });
}

// src/components/Panel.tsx
import { Fragment as Fragment6, jsx as jsx9, jsxs as jsxs8 } from "react/jsx-runtime";
var tone2 = (word) => ({ "--tone": toneVar(word) });
function Pill({ text, word }) {
  if (!text) return null;
  return /* @__PURE__ */ jsxs8("span", { className: "pill", style: tone2(word || text), children: [
    /* @__PURE__ */ jsx9("i", {}),
    text
  ] });
}
function Avatar2({ card, role }) {
  const hue = roleDef(card, role)?.color || "var(--crew-tone-neutral)";
  return /* @__PURE__ */ jsx9("span", { className: "avatar lg", style: { "--hue": hue }, children: cap1(role || "?").slice(0, 1) });
}
function kvRow(key, val, sub) {
  if (val === null || val === void 0 || val === "" || val === false) return null;
  return /* @__PURE__ */ jsxs8("div", { className: "kvr", children: [
    /* @__PURE__ */ jsx9("dt", { children: key }),
    /* @__PURE__ */ jsxs8("dd", { children: [
      val,
      sub ? /* @__PURE__ */ jsx9("small", { children: sub }) : null
    ] })
  ] }, key);
}
function rawFields(evs, skip) {
  const rows = [];
  for (const ev of evs) for (const k of Object.keys(ev || {})) {
    const v = ev[k];
    if (skip[k] || v === null || v === void 0 || v === "" || typeof v === "object") continue;
    rows.push(kvRow(k, /at$/.test(k) || k === "ts" ? typeof v === "number" ? fmtTime(v) : String(v) : String(v)));
    skip[k] = 1;
  }
  return rows.length ? /* @__PURE__ */ jsxs8("details", { className: "raw", children: [
    /* @__PURE__ */ jsx9("summary", { children: "Raw fields" }),
    /* @__PURE__ */ jsx9("dl", { children: rows })
  ] }) : null;
}
function RoleAbout({ card, role }) {
  const rd = roleDef(card, role) || { purpose: "", proof: "" };
  if (!rd.purpose && !rd.proof) return null;
  return /* @__PURE__ */ jsxs8("div", { className: "sec", children: [
    /* @__PURE__ */ jsx9("div", { className: "label", children: "About the " + role + " role" }),
    /* @__PURE__ */ jsx9("div", { className: "prose", children: rd.purpose || "" }),
    rd.proof ? /* @__PURE__ */ jsx9("div", { className: "prose dimp", children: "Proof: " + rd.proof }) : null
  ] });
}
function Route({ card }) {
  const rows = card.route || [];
  if (!rows.length) return /* @__PURE__ */ jsx9("div", { className: "empty", children: "No model was routed for this card: its runs used the role profile's own model." });
  return /* @__PURE__ */ jsx9("div", { className: "route", children: rows.map((r, i) => {
    const wall = r.kind === "quota_wall";
    const what = wall ? "quota wall" + (r.wall_number ? " #" + r.wall_number : "") + " on " + (r.model || "?") + " - " + (r.why || "") : (r.kind === "reroute" ? "re-routed to " : "picked ") + (r.provider ? r.provider + "/" : "") + (r.model || "?") + (r.why ? " - " + r.why : "");
    return /* @__PURE__ */ jsxs8("div", { className: "rr", children: [
      /* @__PURE__ */ jsx9("time", { children: dayTime(r.ts) }),
      /* @__PURE__ */ jsx9("span", { className: wall ? "bad" : "", children: what })
    ] }, i);
  }) });
}
function detailsStep(card, m) {
  const re = (m.run || {}).evidence || {}, se = (m.sess || {}).evidence || {};
  const src = m.src || {};
  const pick = modelPick(card, re.started_at || src.t0);
  const skip = {
    model: 1,
    session_id: 1,
    run_id: 1,
    profile: 1,
    profile_name: 1,
    started_at: 1,
    ended_at: 1,
    duration: 1,
    input_tokens: 1,
    output_tokens: 1,
    message_count: 1,
    tool_call_count: 1,
    calls_failed: 1,
    summary: 1,
    error: 1,
    outcome: 1
  };
  return /* @__PURE__ */ jsxs8(Fragment6, { children: [
    /* @__PURE__ */ jsxs8("dl", { children: [
      kvRow("Model pick", pick ? pick.why || pick.model : "", pick ? "routed " + dayTime(pick.ts) + " \xB7 " + (pick.provider || "") + "/" + (pick.model || "") : ""),
      kvRow("Profile", re.profile || se.profile_name || ""),
      kvRow("Started", fmtTime(re.started_at || src.t0), (re.ended_at ? "ended " + fmtTime(re.ended_at) : "") + (re.duration ? " \xB7 " + re.duration : "")),
      kvRow("Tokens", m.sess ? fmtTokens(se.input_tokens) + " in \xB7 " + fmtTokens(se.output_tokens) + " out" : "", se.message_count ? se.message_count + " messages" : ""),
      kvRow("Prompt", src.prompt ? /* @__PURE__ */ jsx9("span", { className: "mono", children: src.prompt }) : "")
    ] }),
    /* @__PURE__ */ jsx9(RoleAbout, { card, role: m.role }),
    rawFields([re, se], skip)
  ] });
}
function tabBody(card, n, m, tab) {
  const ev = n.evidence || {};
  if (m.kind === "card") {
    if (tab === "Contract")
      return { doc: /* @__PURE__ */ jsxs8("dl", { children: [
        kvRow("Done when", ev.done_when ? /* @__PURE__ */ jsx9(Md, { text: ev.done_when }) : ""),
        kvRow("Writer", (ev.writer_role || "") + (ev.assignee ? " \xB7 " + ev.assignee : "")),
        kvRow("Verifier", ev.verifier || ""),
        kvRow("Model pin", ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "none - the role profile's model"),
        kvRow("Budget", ev.ceiling ? fmtTokens(ev.spent) + " of " + fmtTokens(ev.ceiling) + " tokens" : ""),
        kvRow("Result", ev.result ? /* @__PURE__ */ jsx9(Md, { text: ev.result }) : "")
      ] }) };
    if (tab === "Route") return { doc: /* @__PURE__ */ jsx9(Route, { card }) };
    const dec = ev.decisions || [];
    return { doc: /* @__PURE__ */ jsxs8(Fragment6, { children: [
      dec.length ? /* @__PURE__ */ jsxs8("div", { className: "sec", children: [
        /* @__PURE__ */ jsx9("div", { className: "label", children: "Coordinator decisions" }),
        /* @__PURE__ */ jsx9("div", { className: "route", children: dec.map((d, i) => /* @__PURE__ */ jsxs8("div", { className: "rr", children: [
          /* @__PURE__ */ jsx9("time", { children: dayTime(d.ts) }),
          /* @__PURE__ */ jsx9("span", { children: d.label || d.decision || "" })
        ] }, i)) })
      ] }) : null,
      /* @__PURE__ */ jsx9(RoleAbout, { card, role: "coordinator" }),
      rawFields([ev], { done_when: 1, writer_role: 1, assignee: 1, verifier: 1, model_override: 1, provider_override: 1, ceiling: 1, spent: 1, result: 1, block_reason: 1, status: 1, decisions: 1 })
    ] }) };
  }
  if (m.kind === "verifier") {
    if (tab === "Proof")
      return { doc: /* @__PURE__ */ jsxs8(Fragment6, { children: [
        /* @__PURE__ */ jsxs8("dl", { children: [
          kvRow("Done when", ev.done_when ? /* @__PURE__ */ jsx9(Md, { text: ev.done_when }) : ""),
          kvRow("Command", ev.command ? /* @__PURE__ */ jsx9("span", { className: "mono", children: ev.command }) : ""),
          kvRow("Verdict", ev.verdict || "unverified", ev.by ? "by " + ev.by + (ev.ts ? " \xB7 " + dayTime(ev.ts) : "") : "")
        ] }),
        ev.output_head ? /* @__PURE__ */ jsxs8("div", { className: "sec", children: [
          /* @__PURE__ */ jsx9("div", { className: "label", children: "Output" }),
          /* @__PURE__ */ jsx9("div", { className: "cmd", children: ev.output_head })
        ] }) : null
      ] }) };
    if (tab === "Runs") {
      const rs = ev.review_runs || [];
      return { doc: rs.length ? /* @__PURE__ */ jsx9("div", { className: "route", children: rs.map((r, i) => /* @__PURE__ */ jsxs8("div", { className: "rr", children: [
        /* @__PURE__ */ jsx9("time", { children: "run " + r.run_id }),
        /* @__PURE__ */ jsx9("span", { children: (r.profile || "") + " \xB7 " + (r.outcome || "-") + " \xB7 " + (r.duration || "-") + (r.summary ? " - " + r.summary : "") })
      ] }, i)) }) : /* @__PURE__ */ jsx9("div", { className: "empty", children: "No review run: the proof was run without a verifier session." }) };
    }
    return { doc: /* @__PURE__ */ jsxs8(Fragment6, { children: [
      /* @__PURE__ */ jsx9(RoleAbout, { card, role: "verifier" }),
      rawFields([ev], { done_when: 1, command: 1, verdict: 1, by: 1, ts: 1, output_head: 1, rc: 1, duration_s: 1, verdict_count: 1, review_runs: 1 })
    ] }) };
  }
  if (m.kind === "close") {
    if (tab === "Result")
      return { doc: /* @__PURE__ */ jsxs8(Fragment6, { children: [
        /* @__PURE__ */ jsxs8("dl", { children: [
          kvRow("Status", ev.status || ""),
          kvRow("Completed", dayTime(ev.completed_at))
        ] }),
        ev.result ? /* @__PURE__ */ jsx9("div", { className: "prose", children: /* @__PURE__ */ jsx9(Md, { text: ev.result }) }) : /* @__PURE__ */ jsx9("div", { className: "empty", children: "No result recorded yet." })
      ] }) };
    return { doc: rawFields([ev], { status: 1, completed_at: 1, result: 1 }) };
  }
  if (m.kind === "brief")
    return { doc: /* @__PURE__ */ jsxs8(Fragment6, { children: [
      /* @__PURE__ */ jsx9("div", { className: "prose", children: /* @__PURE__ */ jsx9(Md, { text: ev.text || ev.brief || n.brief || "" }) }),
      ev.source || ev.by ? /* @__PURE__ */ jsx9("div", { className: "cm", children: [ev.source, ev.by, ev.origin].filter((x) => x).join(" \xB7 ") }) : null
    ] }) };
  if (tab === "Details") return { doc: detailsStep(card, m) };
  return null;
}
function readTab(kind) {
  try {
    return window.localStorage.getItem("crewTab." + kind);
  } catch {
    return null;
  }
}
function storeTab(kind, tab) {
  try {
    window.localStorage.setItem("crewTab." + kind, tab);
  } catch {
  }
}
function Panel({ hash, askedTab, onTabApplied }) {
  const ui = useCardUi();
  const { card } = ui;
  const { renderMarkdown } = useCrewHost();
  const [tabs, setTabs] = useState7({});
  const [views, setViews] = useState7({});
  const [openCalls, setOpenCalls] = useState7({});
  const [expanded, setExpanded] = useState7({});
  const [flash, setFlash] = useState7({});
  const seen = useRef7({});
  const bodyRef = useRef7(null);
  const open2 = ui.panelOpen;
  const n = open2 ? getSelectedNode(card, ui.selected) : null;
  const m = n ? panelModel(card, n) : null;
  const ukey = n ? m.unit && m.unit.key || n.id : "";
  let tab = null;
  if (m && m.tabs.length) {
    const asked = askedTab && n && askedTab.node === n.id ? m.tabs.find((t) => t.toLowerCase() === String(askedTab.tab).toLowerCase()) : void 0;
    const want = asked || tabs[m.kind] || readTab(m.kind);
    tab = m.tabs.indexOf(want || "") >= 0 ? want : m.tabs[0];
  }
  useEffect7(() => {
    if (m && askedTab && n && askedTab.node === n.id) {
      const t = m.tabs.find((x) => x.toLowerCase() === String(askedTab.tab).toLowerCase());
      if (t) {
        storeTab(m.kind, t);
        setTabs((s) => ({ ...s, [m.kind]: t }));
      }
      onTabApplied();
    }
  });
  useLayoutEffect3(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = 0;
  }, [ukey, tab, open2]);
  useEffect7(() => {
    if (!hash || typeof window === "undefined") return;
    const parts = [];
    for (const kv of (window.location.hash || "").replace(/^#/, "").split("&")) if (kv && !/^(node|tab)=/.test(kv)) parts.push(kv);
    if (open2 && n) {
      parts.push("node=" + encodeURIComponent(n.id));
      if (tab) parts.push("tab=" + tab.toLowerCase());
    }
    const h = parts.length ? "#" + parts.join("&") : "";
    if (h !== window.location.hash) {
      try {
        window.history.replaceState(null, "", window.location.pathname + window.location.search + h);
      } catch {
      }
    }
  }, [hash, open2, n && n.id, ukey, tab]);
  const rowsT = open2 && m && tab === "Transcript" ? transcriptRows(m, expanded, renderMarkdown) : null;
  const seenNow = rowsT ? seen.current[ukey] : void 0;
  useEffect7(() => {
    if (!rowsT) return;
    const s = seen.current[ukey] = seen.current[ukey] || /* @__PURE__ */ new Set();
    for (const r of rowsT) s.add(r.key);
  });
  if (!open2 || !n || !m) return /* @__PURE__ */ jsx9("div", { id: "panel", className: open2 ? "open" : "" });
  const copy = (id, text) => {
    copyText(text, (ok) => {
      setFlash((f) => ({ ...f, [id]: { until: Date.now() + 1600, label: ok ? "copied" : "select + copy" } }));
      setTimeout(() => setFlash((f) => ({ ...f })), 1700);
    });
  };
  const flashLabel = (id, dflt) => flash[id] && flash[id].until > Date.now() ? flash[id].label : dflt;
  const chip = (c) => {
    const [key, label, value, copyId] = c;
    return /* @__PURE__ */ jsxs8(
      "button",
      {
        type: "button",
        className: "idc",
        id: copyId,
        "data-k": key,
        "data-v": value || "",
        title: "copy " + key,
        "aria-label": "copy " + key,
        onClick: (e) => {
          e.stopPropagation();
          copy(copyId, key + ": " + (value || ""));
        },
        children: [
          label,
          /* @__PURE__ */ jsx9("b", { className: "idv", children: value || "none" }),
          /* @__PURE__ */ jsx9("i", { children: flash[copyId] && flash[copyId].until > Date.now() ? flash[copyId].label : "\u29C9" })
        ]
      },
      copyId
    );
  };
  let rows = [];
  let top = null;
  let doc = null;
  let listCls = "plist";
  const body = tabBody(card, n, m, tab);
  if (body) doc = body.doc;
  else if (tab === "Transcript") {
    rows = rowsT || [];
    listCls = "plist transcript";
    if (!rows.length) doc = /* @__PURE__ */ jsx9("div", { className: "empty", children: "No text yet, this run has only made tool calls." });
  } else {
    const cg = callGroups(m, views);
    top = /* @__PURE__ */ jsx9(CallsHead, { m, cg, onView: (v) => setViews((s) => ({ ...s, [ukey]: v })) });
    listCls = "plist calls";
    rows = callRows(m, cg, openCalls);
    if (!cg.steps.length) doc = /* @__PURE__ */ jsx9("div", { className: "empty", children: "No tool call recorded for this run." });
    else if (!cg.groups.length) doc = /* @__PURE__ */ jsx9("div", { className: "empty", children: cg.view === "failed" ? "No failed call." : "No call." });
  }
  const noSel = () => !String(window.getSelection ? window.getSelection() || "" : "");
  const dedup = /* @__PURE__ */ new Map();
  const kpis = m.kpis.filter((k) => k);
  return /* @__PURE__ */ jsxs8("div", { id: "panel", className: "open", children: [
    /* @__PURE__ */ jsxs8("div", { className: "phead", children: [
      /* @__PURE__ */ jsxs8("div", { className: "pnav", children: [
        n.kind === "card" ? /* @__PURE__ */ jsx9("span", { children: "Card" }) : /* @__PURE__ */ jsx9("button", { type: "button", className: "navback", "data-node": "card:" + card.card_id, onClick: () => ui.select("card:" + card.card_id), children: "\u2039 Card" }),
        /* @__PURE__ */ jsx9("span", { className: "dim", children: "/" }),
        /* @__PURE__ */ jsx9("span", { children: m.role || n.kind }),
        /* @__PURE__ */ jsx9("button", { type: "button", className: "x", title: "close (esc)", onClick: () => ui.closePanel(), children: "\u2715" })
      ] }),
      /* @__PURE__ */ jsxs8("div", { className: "pid", children: [
        /* @__PURE__ */ jsx9(Avatar2, { card, role: m.role }),
        /* @__PURE__ */ jsxs8("div", { className: "pidt", children: [
          /* @__PURE__ */ jsx9("div", { className: "pt", children: m.title }),
          m.sub ? /* @__PURE__ */ jsx9("div", { className: "ps", children: m.sub }) : null
        ] }),
        m.pill ? /* @__PURE__ */ jsx9(Pill, { text: m.pill[0], word: m.pill[1] }) : null
      ] }),
      /* @__PURE__ */ jsx9("div", { className: "ids", children: (m.chips || []).map(chip) }),
      /* @__PURE__ */ jsx9("div", { className: "pcall", children: m.callout ? /* @__PURE__ */ jsxs8("div", { className: "callout", style: tone2(m.callout[3] || "blocked"), children: [
        /* @__PURE__ */ jsxs8("div", { className: "ct", children: [
          m.callout[0],
          /* @__PURE__ */ jsx9(
            "button",
            {
              type: "button",
              className: "copy",
              id: m.callout[4],
              "data-copytext": m.callout[1],
              onClick: (e) => {
                e.stopPropagation();
                copy(m.callout[4], m.callout[1]);
              },
              children: flashLabel(m.callout[4], "copy")
            }
          )
        ] }),
        /* @__PURE__ */ jsx9("div", { className: "cb", children: /* @__PURE__ */ jsx9(Md, { text: m.callout[1] }) }),
        m.callout[2] ? /* @__PURE__ */ jsx9("div", { className: "cm", children: m.callout[2] }) : null
      ] }) : null }),
      /* @__PURE__ */ jsx9("div", { className: "pkpi", children: kpis.length ? /* @__PURE__ */ jsx9("div", { className: "kpis", children: kpis.map((k, i) => /* @__PURE__ */ jsxs8("div", { className: "kpi", children: [
        /* @__PURE__ */ jsx9("div", { className: "kv", children: k.value }),
        /* @__PURE__ */ jsxs8("div", { className: "kl", children: [
          k.label,
          k.failed ? /* @__PURE__ */ jsxs8(Fragment6, { children: [
            " ",
            "\xB7",
            " ",
            /* @__PURE__ */ jsx9("span", { className: "bad", children: k.failed + " failed" })
          ] }) : null
        ] })
      ] }, i)) }) : null })
    ] }),
    /* @__PURE__ */ jsx9("div", { className: "ptabs", hidden: !m.tabs.length, children: m.tabs.length ? /* @__PURE__ */ jsxs8(Fragment6, { children: [
      /* @__PURE__ */ jsx9("div", { className: "seg", role: "tablist", children: m.tabs.map((t) => /* @__PURE__ */ jsxs8(
        "b",
        {
          className: t === tab ? "on" : "",
          "data-tab": t,
          onClick: () => {
            storeTab(m.kind, t);
            setTabs((s) => ({ ...s, [m.kind]: t }));
          },
          children: [
            t,
            t === "Calls" ? /* @__PURE__ */ jsx9("span", { children: m.calls || 0 }) : t === "Route" ? /* @__PURE__ */ jsx9("span", { children: (card.route || []).length }) : null
          ]
        },
        t
      )) }),
      tab === "Transcript" ? /* @__PURE__ */ jsx9("span", { className: "hint", children: "newest first" }) : null
    ] }) : null }),
    /* @__PURE__ */ jsxs8("div", { className: "pbody", ref: bodyRef, children: [
      /* @__PURE__ */ jsx9("div", { className: "ptop", children: top }),
      /* @__PURE__ */ jsx9("div", { className: listCls, children: rows.map((r) => {
        const c = dedup.get(r.key) || 0;
        dedup.set(r.key, c + 1);
        const isNew = tab === "Transcript" && seenNow && !seenNow.has(r.key);
        return /* @__PURE__ */ jsx9(
          "div",
          {
            "data-key": r.key,
            className: r.cls + (isNew ? " new" : ""),
            onClick: (e) => {
              if (!noSel()) return;
              if (tab === "Calls") {
                if (e.target.closest(".ex")) return;
                const k = ukey + "|" + r.key;
                setOpenCalls((s) => ({ ...s, [k]: !s[k] }));
              } else setExpanded((s) => ({ ...s, [r.key]: !s[r.key] }));
            },
            children: r.children
          },
          r.key + (c ? "#" + c : "")
        );
      }) }),
      /* @__PURE__ */ jsx9("div", { className: "pdoc", children: doc })
    ] })
  ] });
}

// src/components/Brief.tsx
import { jsx as jsx10, jsxs as jsxs9 } from "react/jsx-runtime";
function Brief({ card }) {
  const b = briefFields(card.nodes || []);
  return /* @__PURE__ */ jsxs9("div", { id: "briefsec", hidden: !b, children: [
    /* @__PURE__ */ jsx10("div", { className: "rh", children: "brief" }),
    /* @__PURE__ */ jsx10("div", { id: "briefText", children: b ? b.text : "" }),
    /* @__PURE__ */ jsx10("div", { id: "briefSrc", children: b ? b.src : "" })
  ] });
}

// src/components/Tokens.tsx
import { jsx as jsx11, jsxs as jsxs10 } from "react/jsx-runtime";
function Tokens({ card }) {
  const t = card.tokens || {};
  const ceil = +(t.ceiling || 0), used = +(t.used || 0);
  const pct = ceil ? Math.round(1e3 * used / ceil) / 10 : 0;
  const row = (id, label, value, color) => /* @__PURE__ */ jsxs10("div", { className: "tokrow", id, children: [
    /* @__PURE__ */ jsx11("span", { className: "tk", children: label }),
    /* @__PURE__ */ jsx11("span", { className: "tv", style: color ? { color } : void 0, children: value })
  ] });
  return /* @__PURE__ */ jsxs10("div", { id: "toksec", children: [
    /* @__PURE__ */ jsx11("div", { className: "rh", children: "tokens" }),
    row("tokCeiling", "ceiling", fmtExact(ceil)),
    row("tokUsed", "used (billed)", fmtExact(used)),
    row("tokRaw", "raw total", fmtExact(t.raw_total)),
    row("tokCalls", "api calls", fmtExact(t.calls)),
    row("tokPct", "of ceiling", pct.toFixed(1) + "%", ceil ? budgetTone(pct) : void 0)
  ] });
}

// src/components/Rail.tsx
import { jsx as jsx12, jsxs as jsxs11 } from "react/jsx-runtime";
function Rail({ card, collapsed, onToggle, onBack, href = "/" }) {
  const arrow = collapsed ? "\u203A" : "\u2039";
  return /* @__PURE__ */ jsxs11("div", { id: "rail", className: collapsed ? "collapsed" : "", children: [
    /* @__PURE__ */ jsx12(Tokens, { card }),
    /* @__PURE__ */ jsx12(Brief, { card }),
    /* @__PURE__ */ jsx12("div", { className: "rback", children: /* @__PURE__ */ jsxs11("a", { className: "railbtn", href, title: "back to the board", onClick: (e) => {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      onBack();
    }, children: [
      "\u2039",
      /* @__PURE__ */ jsx12("span", { className: "rbtnlabel", children: " board" })
    ] }) }),
    /* @__PURE__ */ jsx12("div", { className: "rbot", children: /* @__PURE__ */ jsx12("button", { className: "railbtn tog", id: "railBot", type: "button", title: collapsed ? "expand the sidebar" : "collapse the sidebar", onClick: onToggle, children: arrow }) })
  ] });
}

// src/components/Roster.tsx
import { jsx as jsx13, jsxs as jsxs12 } from "react/jsx-runtime";
function Roster() {
  const { card, focusRole, setFocusRole } = useCardUi();
  const colour = (c) => ({ color: c });
  return /* @__PURE__ */ jsx13("div", { id: "rolestrip", children: /* @__PURE__ */ jsxs12("div", { id: "roster", children: [
    /* @__PURE__ */ jsx13("div", { className: "role all" + (focusRole ? "" : " on"), onClick: () => setFocusRole(null), children: /* @__PURE__ */ jsxs12("div", { className: "rl", children: [
      /* @__PURE__ */ jsx13("span", { className: "ricon", children: "\u25A6" }),
      /* @__PURE__ */ jsx13("span", { className: "rn", children: focusRole ? "\u2190 show all roles" : "all roles" }),
      /* @__PURE__ */ jsx13("span", { className: "rc", children: (card.node_count || 0) + " nodes" })
    ] }) }),
    (card.roles || []).map((r) => /* @__PURE__ */ jsx13(
      "div",
      {
        className: "role" + (focusRole === r.name ? " on" : ""),
        title: (r.purpose || "") + (r.active ? " - working now" : ""),
        onClick: () => setFocusRole(focusRole === r.name ? null : r.name),
        children: /* @__PURE__ */ jsxs12("div", { className: "rl", children: [
          /* @__PURE__ */ jsx13("span", { className: "ricon" + (r.active ? " act" : ""), style: colour(r.color), children: roleIcon(r.name) }),
          /* @__PURE__ */ jsx13("span", { className: "rn", style: colour(r.color), children: r.name }),
          /* @__PURE__ */ jsx13("span", { className: "rc", children: r.nodes + (r.nodes === 1 ? " node" : " nodes") })
        ] })
      },
      r.name
    ))
  ] }) });
}

// src/components/Scrubber.tsx
import { Fragment as Fragment7, jsx as jsx14, jsxs as jsxs13 } from "react/jsx-runtime";
function Scrubber() {
  const { card, selected, selStep, selectStep } = useCardUi();
  const sel = getSelectedNode(card, selected);
  const steps = sel ? sel.steps || [] : [];
  return /* @__PURE__ */ jsx14("div", { id: "scrubwrap", children: /* @__PURE__ */ jsxs13("div", { id: "scrubber", children: [
    /* @__PURE__ */ jsx14("div", { className: "track" }),
    !steps.length ? /* @__PURE__ */ jsx14("span", { className: "tl left", children: "no steps" }) : /* @__PURE__ */ jsxs13(Fragment7, { children: [
      /* @__PURE__ */ jsx14("span", { className: "tl left", children: tickTime(steps[0]) }),
      /* @__PURE__ */ jsx14("span", { className: "tl right", children: tickTime(steps[steps.length - 1]) }),
      steps.map((_s, i) => /* @__PURE__ */ jsx14(
        "div",
        {
          className: "tick" + (i === selStep ? " active" : "") + (i === steps.length - 1 ? " playhead" : ""),
          style: { left: (steps.length === 1 ? 50 : i / (steps.length - 1) * 100) + "%" },
          onClick: () => selectStep(sel.id, i),
          children: /* @__PURE__ */ jsx14("div", { className: "diam" })
        },
        i
      ))
    ] })
  ] }) });
}

// src/components/StatusBar.tsx
import { jsx as jsx15, jsxs as jsxs14 } from "react/jsx-runtime";
function StatusBar({ card, paused, follow, onFollow, onBack, href = "/" }) {
  const act = (card.roles || []).filter((r) => r.active).map((r) => r.name);
  return /* @__PURE__ */ jsxs14("div", { id: "statusbar", children: [
    /* @__PURE__ */ jsx15("span", { className: "pill", children: "crew" }),
    /* @__PURE__ */ jsx15("span", { className: "live" + (paused ? " paused" : ""), id: "live", children: paused ? "PAUSED" : "LIVE" }),
    /* @__PURE__ */ jsx15("span", { className: "cardtitle", id: "cardtitle", children: card.card_title || card.card_id || "" }),
    /* @__PURE__ */ jsx15("span", { className: "pill", id: "ractive", children: "roles active: " + (act.length ? act.join(", ") : "none") }),
    /* @__PURE__ */ jsx15("span", { className: "pill btn" + (follow ? " on" : ""), id: "followbtn", onClick: onFollow, children: "follow " + (follow ? "on" : "off") }),
    /* @__PURE__ */ jsxs14("span", { className: "meta", children: [
      /* @__PURE__ */ jsx15("span", { id: "counts", children: (card.node_count || 0) + " nodes - " + (card.edge_count || 0) + " edges" }),
      /* @__PURE__ */ jsx15("a", { href, onClick: (e) => {
        if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();
        onBack();
      }, children: "overview" }),
      /* @__PURE__ */ jsx15("span", { className: "hints", children: "space pause - r refresh - f or double-click fit - 0 zoom - F follow - ? help - o overview" })
    ] })
  ] });
}

// src/components/TopArea.tsx
import { useState as useState8 } from "react";
import { Fragment as Fragment8, jsx as jsx16, jsxs as jsxs15 } from "react/jsx-runtime";
var tone3 = (word) => ({ "--tone": toneVar(word) });
function CopyButton({ id, title, text, className = "copy", label = "copy", stop = true }) {
  const [shown, setShown] = useState8(label);
  return /* @__PURE__ */ jsx16(
    "button",
    {
      type: "button",
      className,
      id,
      title,
      "aria-label": title,
      onClick: (e) => {
        if (stop) e.stopPropagation();
        copyText(text(), (ok) => {
          setShown(ok ? "copied" : "select + copy");
          setTimeout(() => setShown(label), 1600);
        });
      },
      children: shown
    }
  );
}
function Field({ label, value, copy }) {
  if (value === null || value === void 0 || value === "") return null;
  return /* @__PURE__ */ jsxs15("span", { className: "fp", children: [
    /* @__PURE__ */ jsx16("span", { className: "fk", children: label }),
    /* @__PURE__ */ jsx16("span", { className: "fv", title: value, children: value }),
    copy ? /* @__PURE__ */ jsx16(CopyButton, { id: copy.id, title: copy.title, text: () => value }) : null
  ] });
}
function TopArea({ card, openChat, onAction }) {
  const { actions } = useCrewHost();
  const s = card.situation || {};
  const cls = s.headline && s.headline.indexOf("stopped") === 0 ? "blocked" : s.headline === "finished" ? "done" : s.headline && s.headline.indexOf("working") === 0 ? "running" : "";
  const st = card.card_status || "-";
  const fp = s.first_pass || {};
  const un = s.units || {};
  const kids = (s.children || []).length;
  const target = coordinatorTarget(card.coordinator);
  const report = card.card_status === "done" ? card.report || "" : "";
  const reason = report || s.reason || s.why || "";
  const you = (s.reason_actor || (s.reason ? "nobody" : "")) === "you" || cls === "blocked";
  const age = s.reason_age_s;
  const spinText = s.repeat_text || "";
  const quiet = !s.repeat || !spinText;
  return /* @__PURE__ */ jsxs15("div", { id: "toparea", className: quiet ? "two" : "", children: [
    /* @__PURE__ */ jsxs15("div", { className: "tcell", id: "topSit", children: [
      /* @__PURE__ */ jsx16("div", { className: "tch", children: "card" }),
      /* @__PURE__ */ jsxs15("div", { id: "sit", className: "sit", children: [
        /* @__PURE__ */ jsxs15("span", { className: "pill sh", style: tone3(st), children: [
          /* @__PURE__ */ jsx16("i", {}),
          st
        ] }),
        /* @__PURE__ */ jsx16("span", { className: "pill sb " + cls, style: tone3(cls || "pending"), children: s.headline || "-" }),
        fp.rounds ? /* @__PURE__ */ jsx16("span", { className: "pill sb " + (fp.first_pass ? "done" : "blocked"), style: tone3(fp.first_pass ? "PASS" : "FAIL"), children: fp.first_pass ? "passed first try" : +(fp.passes || 0) ? +(fp.fails || 0) + " fail(s) before pass" : "check failed" }) : null,
        un.total ? /* @__PURE__ */ jsx16("span", { className: "pill sd", style: tone3((un.passed || 0) >= un.total ? "PASS" : "pending"), children: "units " + +(un.passed || 0) + " of " + +un.total + " passed" }) : null,
        kids ? /* @__PURE__ */ jsx16("span", { className: "pill sd", style: tone3("pending"), children: "children " + kids }) : null
      ] }),
      /* @__PURE__ */ jsxs15("div", { id: "sitfields", className: "fields", children: [
        /* @__PURE__ */ jsx16(Field, { label: "model", value: card.card_model || "" }),
        card.card_created_at ? /* @__PURE__ */ jsx16(Field, { label: "started", value: fmtAge(Date.now() / 1e3 - card.card_created_at) }) : null,
        /* @__PURE__ */ jsx16(Field, { label: "kanban id", value: card.card_id || "", copy: { id: "cardIdCopy", title: "copy the kanban id" } }),
        /* @__PURE__ */ jsx16(Field, { label: "coordinator", value: card.coordinator || "", copy: { id: "cardCoCopy", title: "copy the coordinator session" } }),
        target && openChat && !actions ? /* @__PURE__ */ jsxs15(Fragment8, { children: [
          /* @__PURE__ */ jsx16("span", { className: "brk" }),
          /* @__PURE__ */ jsx16("span", { className: "fp openrow", children: /* @__PURE__ */ jsx16(
            "button",
            {
              type: "button",
              className: "copy",
              id: "cardCoOpen",
              title: "open the chat this card came from",
              "aria-label": "open the chat this card came from",
              onClick: (e) => {
                e.stopPropagation();
                openChat(target.profile, target.session);
              },
              children: "open chat \u2197"
            }
          ) })
        ] }) : null
      ] }),
      /* @__PURE__ */ jsx16(ActionBar, { card, openChat, onDone: onAction || (() => {
      }) })
    ] }),
    /* @__PURE__ */ jsxs15("div", { className: "tcell", id: "topWhy", children: [
      /* @__PURE__ */ jsx16("div", { className: "tch", id: "whyHead", children: report ? "done report" : "pending reason" }),
      /* @__PURE__ */ jsx16("div", { className: "tce", id: "sitboxNone", hidden: !!reason, children: "nothing pending" }),
      /* @__PURE__ */ jsxs15("div", { id: "sitbox", hidden: !reason, className: !reason ? void 0 : report ? "done" : you ? "you" : "nobody", children: [
        /* @__PURE__ */ jsxs15("div", { id: "sitboxHead", children: [
          /* @__PURE__ */ jsx16("span", { className: "sbl", children: report ? "delivered" : you ? "needs you" : "waiting - nobody has to act" }),
          /* @__PURE__ */ jsx16("span", { className: report ? "sb done" : "sb " + cls, children: report ? "done" : (card.card_status || "-") + (s.headline ? " - " + s.headline : "") }),
          /* @__PURE__ */ jsx16(CopyButton, { id: "sitCopy", title: "copy the pending reason", text: () => (card.card_id ? card.card_id + "\n\n" : "") + reason })
        ] }),
        /* @__PURE__ */ jsx16("div", { id: "sitboxWhy", children: reason }),
        /* @__PURE__ */ jsx16("div", { id: "sitboxMeta", children: report ? "what the owner is sent when the card ends" : "source: " + (s.reason_source || "task") + " - recorded " + fmtAge(age) + (age !== null && age !== void 0 ? " (" + age + "s)" : "") })
      ] })
    ] }),
    /* @__PURE__ */ jsxs15("div", { className: "tcell", id: "topSpin", hidden: quiet, children: [
      /* @__PURE__ */ jsx16("div", { className: "tch", children: "repeated stops" }),
      /* @__PURE__ */ jsx16("div", { className: "tce", id: "spinboxNone", hidden: !quiet, children: "not spinning" }),
      /* @__PURE__ */ jsxs15("div", { id: "spinbox", hidden: quiet, children: [
        /* @__PURE__ */ jsxs15("div", { id: "spinboxHead", children: [
          /* @__PURE__ */ jsx16("span", { id: "spinboxCount", children: (s.repeat_stops || 0) + " of " + (s.runs || 0) + " runs stopped on the same reason" }),
          /* @__PURE__ */ jsx16("span", { className: "sbl", children: "spinning" }),
          /* @__PURE__ */ jsx16(CopyButton, { id: "spinCopy", title: "copy the repeated reason", text: () => spinText })
        ] }),
        /* @__PURE__ */ jsx16("div", { id: "spinboxText", children: spinText })
      ] })
    ] })
  ] });
}

// src/components/CardPage.tsx
import { jsx as jsx17, jsxs as jsxs16 } from "react/jsx-runtime";
function readRail() {
  try {
    return window.localStorage.getItem("crewRailCollapsed") === "1";
  } catch {
    return false;
  }
}
function CardPage({ api, id, onBack, openChat, hash = false, boardHref = "/" }) {
  injectCss("base", base_default);
  injectCss("card", card_default);
  const [paused, setPaused] = useState9(false);
  const { card, error, loading, reload } = useCard(api, id, 2e3, paused);
  const [selected, setSelected] = useState9(null);
  const [selStep, setSelStep] = useState9(-1);
  const [panelOpen, setPanelOpen] = useState9(false);
  const [focusRole, setFocusRole] = useState9(null);
  const [railCollapsed, setRailCollapsed] = useState9(() => readRail() || hash && /rail=collapsed/.test(window.location.hash));
  const [help, setHelp] = useState9(false);
  const [askedTab, setAskedTab] = useState9(null);
  const root = useRef8(null);
  const suppressClick = useRef8(false);
  useEffect8(() => {
    setSelected(null);
    setSelStep(-1);
    setPanelOpen(false);
    setFocusRole(null);
  }, [id]);
  useEffect8(() => {
    if (!hash) return;
    const apply = () => {
      let node = null, tab = null;
      for (const kv of (window.location.hash || "").replace(/^#/, "").split("&")) {
        const i = kv.indexOf("=");
        if (i < 0) continue;
        const k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
        if (k === "role") setFocusRole(v || null);
        if (k === "node" && v) node = v;
        if (k === "tab" && v) tab = v;
      }
      if (node) {
        setSelected((prev) => prev === node ? prev : node);
        setPanelOpen(true);
      }
      if (node && tab) setAskedTab({ node, tab });
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, [hash]);
  const select = useCallback3((nodeId) => {
    setSelected(nodeId);
    setSelStep(-1);
    setPanelOpen(true);
  }, []);
  const selectStep = useCallback3((nodeId, i) => {
    setSelected(nodeId);
    setSelStep(i);
    setPanelOpen(true);
  }, []);
  const closePanel = useCallback3(() => {
    setSelected(null);
    setPanelOpen(false);
  }, []);
  const toggleRail = useCallback3(() => {
    setRailCollapsed((c) => {
      try {
        window.localStorage.setItem("crewRailCollapsed", c ? "0" : "1");
      } catch {
      }
      return !c;
    });
  }, []);
  const keyRef = useRef8({ paused, selected, reload, onBack, closePanel });
  keyRef.current = { paused, selected, reload, onBack, closePanel };
  useEffect8(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || !isCrewKey(e, root.current)) return;
      const k = keyRef.current;
      if (e.code === "Space") {
        e.preventDefault();
        setPaused((p) => !p);
      } else if (e.key === "r" || e.key === "R") k.reload();
      else if (e.key === "?") setHelp((h) => !h);
      else if (e.key === "o" || e.key === "O") k.onBack();
      else if (e.key === "f" || e.key === "F" || e.key === "0") toGraph(root.current, e.key);
      else if (e.key === "Escape") {
        setHelp(false);
        if (k.selected) k.closePanel();
        else setFocusRole(null);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  const [follow, setFollow] = useState9(false);
  const ui = useMemo3(
    () => card && {
      card,
      api,
      selected,
      selStep,
      focusRole,
      follow,
      paused,
      panelOpen,
      select,
      selectStep,
      closePanel,
      setFocusRole,
      setFollow: () => toGraph(root.current, "F"),
      suppressClick
    },
    [card, api, selected, selStep, focusRole, follow, paused, panelOpen, select, selectStep, closePanel]
  );
  if (!card || !ui)
    return /* @__PURE__ */ jsx17("div", { className: "page-card crew-scope", ref: root, "data-card": id, children: /* @__PURE__ */ jsx17("div", { style: { padding: 16 }, children: error ? "Crew could not load: " + error : loading ? "Loading..." : "" }) });
  return /* @__PURE__ */ jsx17(CardUiContext.Provider, { value: ui, children: /* @__PURE__ */ jsxs16("div", { className: "page-card crew-scope", ref: root, "data-card": card.card_id, children: [
    /* @__PURE__ */ jsx17("a", { className: "brand", href: boardHref, title: "overview", "aria-label": "crew overview", onClick: (e) => {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      onBack();
    }, children: /* @__PURE__ */ jsx17("img", { src: MARK_URI, alt: "", width: 26, height: 26 }) }),
    /* @__PURE__ */ jsx17(EventLine, { card }),
    /* @__PURE__ */ jsxs16("div", { id: "main", children: [
      /* @__PURE__ */ jsx17(TopArea, { card, openChat, onAction: reload }),
      /* @__PURE__ */ jsx17(Roster, {}),
      /* @__PURE__ */ jsxs16("div", { id: "row", children: [
        /* @__PURE__ */ jsx17(Rail, { card, collapsed: railCollapsed, onToggle: toggleRail, onBack, href: boardHref }),
        /* @__PURE__ */ jsx17(
          Graph,
          {
            card,
            api,
            selectedId: panelOpen ? selected : null,
            focusRole,
            onFollowChange: setFollow,
            onSelect: (nodeId, step) => {
              if (nodeId === null) closePanel();
              else if (step !== void 0) selectStep(nodeId, step);
              else select(nodeId);
            }
          }
        ),
        /* @__PURE__ */ jsx17(Panel, { hash, askedTab, onTabApplied: () => setAskedTab(null) })
      ] })
    ] }),
    /* @__PURE__ */ jsx17(Scrubber, {}),
    /* @__PURE__ */ jsx17(StatusBar, { card, paused, follow, onFollow: () => toGraph(root.current, "F"), onBack, href: boardHref }),
    /* @__PURE__ */ jsx17(Help, { open: help })
  ] }) });
}
function toGraph(root, key) {
  const g = root && root.querySelector(".crew-graph");
  if (g) g.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
}
function Help({ open: open2 }) {
  const row = (k, text) => /* @__PURE__ */ jsxs16("div", { className: "row", children: [
    /* @__PURE__ */ jsx17("kbd", { children: k }),
    text
  ] });
  return /* @__PURE__ */ jsxs16("div", { id: "help", className: open2 ? "open" : "", children: [
    /* @__PURE__ */ jsx17("div", { className: "h", children: "keys" }),
    row("space", "pause / resume polling"),
    row("r", "refresh once"),
    row("f", "fit view"),
    row("0", "reset zoom"),
    row("F", "follow the newest active node"),
    /* @__PURE__ */ jsxs16("div", { className: "row", children: [
      /* @__PURE__ */ jsx17("kbd", { children: "wheel" }),
      "zoom - ",
      /* @__PURE__ */ jsx17("kbd", { children: "drag" }),
      "pan - zoomed out, cards become status blocks"
    ] }),
    row("?", "toggle this help"),
    row("o", "open overview"),
    row("esc", "close help, clear role focus")
  ] });
}

// src/components/Splash.tsx
import { useEffect as useEffect9, useState as useState10 } from "react";

// ../assets/fonts/archivo-900-subset.woff2
var archivo_900_subset_default = "data:font/woff2;base64,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";

// ../assets/fonts/jetbrains-mono-500-subset.woff2
var jetbrains_mono_500_subset_default = "data:font/woff2;base64,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";

// src/fonts.ts
var FONT_FACE_CSS = `@font-face{font-family:CrewArchivo;font-weight:900;font-style:normal;font-display:block;src:url(${archivo_900_subset_default}) format('woff2')}@font-face{font-family:CrewMono;font-weight:500;font-style:normal;font-display:block;src:url(${jetbrains_mono_500_subset_default}) format('woff2')}`;

// src/styles/splash.css
var splash_default = `/* Desktop splash: the crew mark, an eyebrow and one headline in the landing page's faces, over the page area.
   Colours are the --crew-* ladder, so a light and a dark host both read. The overlay is the page root's own box
   (position:absolute; inset:0 on the relative .crew-scope), so it fills exactly the route area, and the block sits in
   its middle on both axes.
   Motion: CSS keyframes only (transform and opacity), the landing page's easings (.3,.9,.2,1 settle; .3,1.6,.4,1 overshoot),
   under prefers-reduced-motion: no-preference and the sp-anim class. Timeline: mark 0-.55 s, rule .25-.6, eyebrow text
   .55-.85, words You .6, ask .75, once. .9 (each .4 s, the last overshoots), hold, overlay fade .3 s (Splash.tsx MIN_MS). */
.crew-splash{position:absolute; inset:0; z-index:50; display:flex; align-items:center; justify-content:center;
  background:var(--crew-bg); color:var(--crew-fg); opacity:1; container-type:size}
.crew-splash[data-out="1"]{opacity:0; pointer-events:none}
.crew-splash .sp-in{display:flex; flex-direction:column; align-items:flex-start; gap:18px; padding:0 32px; max-width:100%}
.crew-splash .sp-mark{width:44px; height:44px; display:block}
.crew-splash .sp-eyebrow{display:flex; align-items:center; gap:12px; font-family:CrewMono,var(--crew-mono); font-weight:500; font-size:11px;
  letter-spacing:.07em; text-transform:uppercase; color:var(--crew-tone-running)}
.crew-splash .sp-eyebrow s{width:36px; height:1px; flex:0 0 36px; background:var(--crew-tone-running); text-decoration:none}
.crew-splash .sp-foot{position:absolute; left:0; right:0; bottom:88px; text-align:center; font-family:CrewMono,var(--crew-mono); font-weight:500;
  font-size:13px; letter-spacing:.07em; color:var(--crew-text-3)}
.crew-splash .sp-title{margin:0; font-family:CrewArchivo,var(--crew-font); font-weight:900; font-size:clamp(32px,10cqw,96px);
  letter-spacing:-.055em; line-height:.9; white-space:nowrap; color:var(--crew-fg)}
.crew-splash .sp-title em{font-style:normal; color:var(--crew-tone-running)}
.crew-splash .sp-w{display:inline-block}
@media (prefers-reduced-motion: no-preference){
  .crew-splash.sp-anim{transition:opacity .3s ease}
  .crew-splash.sp-anim .sp-mark{animation:crew-sp-mark .55s cubic-bezier(.3,.9,.2,1) both}
  .crew-splash.sp-anim .sp-eyebrow s{transform-origin:0 50%; animation:crew-sp-rule .35s cubic-bezier(.3,.9,.2,1) .25s both}
  .crew-splash.sp-anim .sp-eb{animation:crew-sp-fade .3s ease .55s both}
  /* the footer comes last, after 'once.' has landed (.9s + .4s), inside the same 1.3 s window: nothing gets longer */
  .crew-splash.sp-anim .sp-foot{animation:crew-sp-fade .25s ease 1.05s both}
  .crew-splash.sp-anim .sp-w1{animation:crew-sp-word .4s cubic-bezier(.3,.9,.2,1) .6s both}
  .crew-splash.sp-anim .sp-w2{animation:crew-sp-word .4s cubic-bezier(.3,.9,.2,1) .75s both}
  .crew-splash.sp-anim .sp-w3{animation:crew-sp-last .4s cubic-bezier(.3,1.6,.4,1) .9s both}
}
@keyframes crew-sp-mark{from{opacity:0; transform:scale(.6)} 60%{opacity:1; transform:scale(1.06)} to{opacity:1; transform:scale(1)}}
@keyframes crew-sp-rule{from{transform:scaleX(0)} to{transform:scaleX(1)}}
@keyframes crew-sp-fade{from{opacity:0} to{opacity:1}}
@keyframes crew-sp-word{from{opacity:0; transform:translateY(.4em)} to{opacity:1; transform:none}}
@keyframes crew-sp-last{from{opacity:0; transform:translateY(.5em)} to{opacity:1; transform:none}}
`;

// src/components/Splash.tsx
import { jsx as jsx18, jsxs as jsxs17 } from "react/jsx-runtime";
var MIN_MS = 1300;
var MIN_REDUCED_MS = 500;
var MAX_MS = 5e3;
var FADE_MS = 300;
var prefersReduced = () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
function Splash({ api }) {
  const [out, setOut] = useState10(false);
  const [gone, setGone] = useState10(false);
  const [reduced] = useState10(prefersReduced);
  injectCss("splash-fonts", FONT_FACE_CSS);
  injectCss("splash", splash_default);
  useEffect9(() => {
    const t0 = Date.now();
    let live = true;
    const timers = [];
    let started = false;
    const leave = () => {
      if (!live || started) return;
      started = true;
      timers.push(setTimeout(() => {
        if (!live) return;
        setOut(true);
        timers.push(setTimeout(() => live && setGone(true), reduced ? 0 : FADE_MS));
      }, Math.max(0, (reduced ? MIN_REDUCED_MS : MIN_MS) - (Date.now() - t0))));
    };
    api.get("/board.json").then(leave, leave);
    timers.push(setTimeout(leave, MAX_MS));
    return () => {
      live = false;
      timers.forEach(clearTimeout);
    };
  }, [api, reduced]);
  if (gone) return null;
  return /* @__PURE__ */ jsxs17("div", { className: "crew-splash" + (reduced ? "" : " sp-anim"), "data-out": out ? "1" : "0", role: "status", "aria-label": "Hermes.Crew", children: [
    /* @__PURE__ */ jsxs17("div", { className: "sp-in", children: [
      /* @__PURE__ */ jsx18("img", { className: "sp-mark", src: MARK_URI, alt: "" }),
      /* @__PURE__ */ jsxs17("div", { className: "sp-eyebrow", children: [
        /* @__PURE__ */ jsx18("s", {}),
        /* @__PURE__ */ jsx18("span", { className: "sp-eb", children: "Hermes.Crew \xB7 the agent company for Hermes" })
      ] }),
      /* @__PURE__ */ jsxs17("h1", { className: "sp-title", children: [
        /* @__PURE__ */ jsx18("span", { className: "sp-w sp-w1", children: "You" }),
        " ",
        /* @__PURE__ */ jsx18("span", { className: "sp-w sp-w2", children: "ask" }),
        " ",
        /* @__PURE__ */ jsx18("em", { className: "sp-w sp-w3", children: "once." })
      ] })
    ] }),
    /* @__PURE__ */ jsxs17("div", { className: "sp-foot", children: [
      "crew.forgecoreai.com \xB7 v",
      "0.10.4"
    ] })
  ] });
}

// src/components/CrewPage.tsx
import { jsx as jsx19, jsxs as jsxs18 } from "react/jsx-runtime";
var splashShown = false;
function CrewPage({ api }) {
  const { theme, renderedMode } = useTheme();
  const [route, setRoute] = useState11({ page: "board", all: false });
  useEffect10(() => {
    const open2 = (id) => setRoute({ page: "card", id });
    const go = () => {
      const id = cardFromHash(window.location.hash);
      if (id) open2(id);
    };
    const first = takePendingCard() || cardFromHash(window.location.hash) || cardFromSearch(window.location.search);
    if (first) open2(first);
    const off = onOpenCard((id) => {
      takePendingCard();
      open2(id);
    });
    window.addEventListener("hashchange", go);
    return () => {
      off();
      window.removeEventListener("hashchange", go);
    };
  }, []);
  const back = () => setRoute({ page: "board", all: false });
  const host3 = sdk.host;
  const openSession = host3?.openSession;
  const openChat = typeof openSession === "function" ? (profile, session) => {
    void openSession.call(host3, session, { profile });
  } : void 0;
  const [splash] = useState11(() => !splashShown);
  useEffect10(() => {
    splashShown = true;
  }, []);
  const card = route.page === "card";
  useEffect10(() => {
    setCardPageOpen(card);
    return () => setCardPageOpen(false);
  }, [card]);
  return /* @__PURE__ */ jsxs18(
    "div",
    {
      className: "crew-scope",
      style: { ...crewVarsFromTheme(theme, renderedMode), background: "var(--crew-bg)", color: "var(--crew-fg)", height: "100%", minHeight: "100%", width: "100%", minWidth: 0, flex: "1 1 auto", alignSelf: "stretch", boxSizing: "border-box", position: "relative", overflow: card ? "hidden" : "auto" },
      children: [
        splash ? /* @__PURE__ */ jsx19(Splash, { api }) : null,
        route.page === "card" ? /* @__PURE__ */ jsx19(CardPage, { api, id: route.id, onBack: back, openChat }) : /* @__PURE__ */ jsx19(Board, { api, onOpenCard: (id) => setRoute({ page: "card", id }), home: back })
      ]
    }
  );
}

// src/components/FlowPane.tsx
import { useEffect as useEffect11, useId as useId2, useState as useState12, useSyncExternalStore } from "react";
import { Fragment as Fragment9, jsx as jsx20, jsxs as jsxs19 } from "react/jsx-runtime";
function useLiveCard(api, id, intervalMs = 2e3) {
  const [card, setCard] = useState12(null);
  const [error, setError] = useState12(null);
  useEffect11(() => {
    setCard(null);
    setError(null);
    if (!id) return;
    let live = true;
    const load = () => api.get("/card/" + id + ".json").then((c) => {
      if (live) {
        setCard(c);
        setError(null);
      }
    }).catch((e) => {
      if (live) setError(String(e && e.message || e));
    });
    load();
    const timer = setInterval(load, intervalMs);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [api, id, intervalMs]);
  return { card, error };
}
var KIND_LABEL = { brief: "Owner brief", close: "Close", verifier: "Verifier" };
function flowSteps(card) {
  return card.nodes.filter((n) => n.kind !== "session" && n.kind !== "subagent").sort((a, b) => a.layer - b.layer || (a.x ?? 0) - (b.x ?? 0)).map((n) => ({
    id: n.id,
    role: n.kind === "brief" ? "owner" : n.role || n.kind,
    label: KIND_LABEL[n.kind] ?? (n.kind === "run" ? "Run " + n.label : n.title || "Coordinator"),
    status: n.status,
    color: n.role_color || "var(--crew-tone-neutral)"
  }));
}
function Link({ live, arrow, arrowLive }) {
  return /* @__PURE__ */ jsxs19("svg", { className: "fline", viewBox: "0 0 20 18", preserveAspectRatio: "xMidYMid meet", "aria-hidden": "true", children: [
    /* @__PURE__ */ jsx20("path", { d: "M10 0 L10 17", className: "edge" + (live ? " live" : ""), markerEnd: "url(#" + (live ? arrowLive : arrow) + ")" }),
    live ? /* @__PURE__ */ jsxs19(Fragment9, { children: [
      /* @__PURE__ */ jsx20("path", { d: "M10 0 L10 17", className: "edge flow" }),
      /* @__PURE__ */ jsx20("circle", { r: "2.2", className: "edge-dot", children: /* @__PURE__ */ jsx20("animateMotion", { dur: "1.6s", repeatCount: "indefinite", path: "M10 0 L10 17", fill: "freeze" }) })
    ] }) : null
  ] });
}
function Chart({ card, go }) {
  const steps = flowSteps(card);
  const uid = useId2().replace(/:/g, "");
  const arrow = "farrow" + uid, arrowLive = "farrowlive" + uid;
  return /* @__PURE__ */ jsxs19(
    "div",
    {
      className: "crew-graph fchart",
      role: "button",
      tabIndex: 0,
      title: "Open the full flow",
      onClick: go,
      onKeyDown: (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          go();
        }
      },
      children: [
        /* @__PURE__ */ jsx20("svg", { width: "0", height: "0", style: { position: "absolute" }, "aria-hidden": "true", children: /* @__PURE__ */ jsx20("defs", { children: [[arrow, "ah"], [arrowLive, "ah live"]].map(([id, cls]) => /* @__PURE__ */ jsx20("marker", { id, viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse", children: /* @__PURE__ */ jsx20("path", { d: "M0,0 L10,5 L0,10 z", className: cls }) }, id)) }) }),
        steps.map((s, i) => {
          const col = COLOUR[s.status] || "var(--crew-tone-neutral)";
          return /* @__PURE__ */ jsxs19("div", { className: "fstepwrap", children: [
            i ? /* @__PURE__ */ jsx20(Link, { live: s.status === "running", arrow, arrowLive }) : null,
            /* @__PURE__ */ jsx20("div", { className: "node fnode st-" + s.status + (s.status === "running" ? " alive on" : ""), "data-id": s.id, children: /* @__PURE__ */ jsxs19("div", { className: "card", style: { borderLeftColor: s.color }, children: [
              /* @__PURE__ */ jsxs19("div", { className: "hdr", children: [
                /* @__PURE__ */ jsx20("span", { className: "glyph", style: { color: col }, children: GLYPH[s.status] || "\u25CB" }),
                /* @__PURE__ */ jsx20("span", { className: "name", children: s.label })
              ] }),
              /* @__PURE__ */ jsxs19("div", { className: "foot", children: [
                /* @__PURE__ */ jsx20("span", { className: "sw chip-tone fstatus", style: { ["--tone"]: col }, children: s.status }),
                /* @__PURE__ */ jsxs19("span", { className: "tok frole", children: [
                  roleIcon(s.role),
                  " ",
                  s.role
                ] })
              ] })
            ] }) })
          ] }, s.id);
        })
      ]
    }
  );
}
function FlowPane({ api, navigate, cardLink: cardLink2, boardLink }) {
  injectCss("base", base_default);
  injectCss("graph", graph_default);
  const { board, error: boardError } = useBoard(api);
  const cards = [];
  const seen = /* @__PURE__ */ new Set();
  for (const want of [false, true])
    for (const lane of board?.lanes ?? [])
      for (const t of lane.tiles) {
        const needs = lane.key === "blocked" && t.status === "blocked";
        if (needs === want && (needs || t.active) && !seen.has(t.id)) {
          seen.add(t.id);
          cards.push(t);
        }
      }
  const [pick, setPick] = useState12(null);
  const picked = pick ? cards.find((t) => t.id === pick) : void 0;
  useEffect11(() => {
    if (pick && !picked) setPick(null);
  }, [pick, picked]);
  const cur = picked ?? cards[0] ?? null;
  const onCardPage = useSyncExternalStore(subscribeCardPage, cardPageOpen, cardPageOpen);
  const { card, error } = useLiveCard(api, cur && !onCardPage ? cur.id : null);
  if (onCardPage)
    return /* @__PURE__ */ jsx20("div", { className: "crew-scope crew-flow", children: /* @__PURE__ */ jsxs19("div", { className: "fhint fcompact", children: [
      "Full flow is open on the left - ",
      /* @__PURE__ */ jsx20("kbd", { children: "Ctrl+J" }),
      " hides this pane"
    ] }) });
  return /* @__PURE__ */ jsxs19("div", { className: "crew-scope crew-flow", children: [
    /* @__PURE__ */ jsxs19("div", { className: "fhint", children: [
      /* @__PURE__ */ jsx20("kbd", { children: "Ctrl+J" }),
      " hides this pane"
    ] }),
    cur ? /* @__PURE__ */ jsxs19(Fragment9, { children: [
      /* @__PURE__ */ jsx20("div", { className: "fhead", children: cards.length > 1 ? /* @__PURE__ */ jsx20("select", { className: "fsel", "aria-label": "Card", value: cur.id, onChange: (e) => setPick(e.target.value), children: cards.map((t) => /* @__PURE__ */ jsx20("option", { value: t.id, children: shortId(t.id) + "  " + t.title }, t.id)) }) : /* @__PURE__ */ jsxs19(Fragment9, { children: [
        /* @__PURE__ */ jsx20("span", { className: "fid", children: shortId(cur.id) }),
        /* @__PURE__ */ jsx20("span", { className: "ftitle", children: cur.title })
      ] }) }),
      card && card.card_id === cur.id ? /* @__PURE__ */ jsx20(Chart, { card, go: () => navigate?.(cardLink2(cur.id)) }) : /* @__PURE__ */ jsx20("div", { className: "fnone", children: error ? "Crew could not load the flow: " + error : "Loading the flow..." })
    ] }) : /* @__PURE__ */ jsxs19("div", { className: "fnone", children: [
      boardError && !board ? "Crew could not load: " + boardError : "Nothing running",
      " ",
      /* @__PURE__ */ jsx20("a", { href: "#", className: "fboard", onClick: (e) => {
        e.preventDefault();
        navigate?.(boardLink);
      }, children: "Open the board" })
    ] })
  ] });
}

// src/desktop.tsx
import { jsx as jsx21, jsxs as jsxs20 } from "react/jsx-runtime";
var hostNavigate = (path) => {
  openCardRoute(path, (p) => sdk2.host?.navigate?.(p));
};
function Pane({ api }) {
  const { theme, renderedMode } = useTheme2();
  return /* @__PURE__ */ jsx21("div", { style: { ...crewVarsFromTheme(theme, renderedMode), background: "var(--crew-bg)", color: "var(--crew-fg)", height: "100%" }, children: /* @__PURE__ */ jsx21(FlowPane, { api, navigate: hostNavigate, cardLink, boardLink: CREW_ROUTE }) });
}
function Host({ api, kanban, children }) {
  const [ask, setAsk] = useState13(null);
  const [showKanban, setShowKanban] = useState13(kanban ? kanban.show : false);
  const host3 = useMemo4(() => {
    const h = {};
    const Md2 = sdk2.MessageTextContent, Sd = sdk2.Streamdown;
    if (Md2) h.renderMarkdown = (text) => /* @__PURE__ */ jsx21(Md2, { text, media: false });
    else if (Sd) h.renderMarkdown = (text) => /* @__PURE__ */ jsx21(Sd, { children: text });
    if (sdk2.Button && sdk2.ConfirmDialog)
      h.actions = {
        // the route is POST /action/<name> {card, ...extra}; the backend allowlists the names again
        run: (name, card, extra) => api.post("/action/" + name, { ...extra, card }),
        confirm: (title, body) => new Promise((resolve) => setAsk({ title, body, done: resolve })),
        Button: sdk2.Button
      };
    if (kanban) h.kanbanRow = { show: showKanban, set: (v) => {
      kanban.set(v);
      setShowKanban(v);
    } };
    return h;
  }, [api, kanban, showKanban]);
  const Dialog = sdk2.ConfirmDialog;
  const close = (ok) => {
    if (ask) ask.done(ok);
    setAsk(null);
  };
  return /* @__PURE__ */ jsxs20(CrewHostContext.Provider, { value: host3, children: [
    children,
    Dialog && ask ? /* @__PURE__ */ jsx21(Dialog, { open: true, title: ask.title, description: ask.body, confirmLabel: "Confirm", destructive: true, onClose: () => close(false), onConfirm: () => close(true) }) : null
  ] });
}
var KANBAN_ROW_ID = "kanban:nav";
var HIDE_KEY = "hideKanbanRow";
function kanbanRowSwitch(ctx) {
  const area = sdk2.SIDEBAR_NAV_PREFS_AREA;
  if (!area || typeof ctx.register !== "function") return null;
  let drop;
  const apply = (show) => {
    if (drop) {
      drop();
      drop = void 0;
    }
    if (!show) drop = ctx.register({ id: "nav-prefs", area, data: { hide: [KANBAN_ROW_ID] } });
  };
  const row = {
    show: ctx.storage ? ctx.storage.get(HIDE_KEY, true) === false : false,
    set(show) {
      row.show = show;
      try {
        ctx.storage?.set(HIDE_KEY, !show);
      } catch {
      }
      apply(show);
    }
  };
  apply(row.show);
  return row;
}
var WATCH_MS = 5e3;
function watchBlocked(ctx, api) {
  const host3 = sdk2.host;
  if (!host3?.notify || typeof ctx.setInterval !== "function") return;
  const tick = blockedWatch(() => api.get("/board.json"), (t) => {
    host3.notify({
      id: "crew-blocked-" + t.id,
      kind: "warning",
      title: "Crew: a card needs you",
      message: t.message,
      detail: t.detail,
      action: { label: "Open in Crew", onClick: () => hostNavigate(cardLink(t.id)) }
    });
    try {
      ctx.os?.notify({ title: "Crew: a card needs you", body: t.message + "\n" + t.detail });
    } catch {
    }
  });
  void tick();
  ctx.setInterval(() => {
    void tick();
  }, WATCH_MS);
}
var CARD_LINKS = "__crewCardLinks";
var MD_BLOCK = ".aui-md, .stub-md, .md";
function watchCardLinks(doc = document) {
  const slot = doc;
  slot[CARD_LINKS]?.();
  const onClick = (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const navigate = sdk2.host?.navigate;
    if (typeof navigate !== "function") return;
    const t = e.target;
    const a = t && typeof t.closest === "function" ? t.closest("a[href]") : null;
    if (!a) return;
    if (a.closest(".crew-scope") && !a.closest(MD_BLOCK)) return;
    const id = cardFromHref(a.getAttribute("href") || "");
    if (!id) return;
    e.preventDefault();
    openCardRoute(cardLink(id), (p) => sdk2.host?.navigate?.(p));
  };
  doc.addEventListener("click", onClick, true);
  const off = () => {
    doc.removeEventListener("click", onClick, true);
    if (slot[CARD_LINKS] === off) slot[CARD_LINKS] = void 0;
  };
  slot[CARD_LINKS] = off;
  return off;
}
var desktop_default = {
  id: "crew",
  name: "Crew",
  register(ctx) {
    const api = restApi(ctx);
    const kanban = kanbanRowSwitch(ctx);
    ctx.registerMany([
      { id: "page", area: ROUTES_AREA, data: { path: "/crew" }, render: () => /* @__PURE__ */ jsx21(Host, { api, kanban, children: /* @__PURE__ */ jsx21(CrewPage, { api }) }) },
      { id: "nav", area: SIDEBAR_NAV_AREA, data: { path: "/crew", label: "Crew", codicon: "organization" } },
      {
        id: "flow",
        area: PANES_AREA,
        title: "Crew flow",
        data: { placement: "right", width: "260px", hideOnly: true, collapsible: true },
        render: () => /* @__PURE__ */ jsx21(Pane, { api })
      }
    ]);
    watchBlocked(ctx, api);
    if (typeof sdk2.host?.navigate === "function" && typeof document !== "undefined") {
      const off = watchCardLinks(document);
      if (typeof ctx.onDispose === "function") ctx.onDispose(off);
    }
  }
};
export {
  KANBAN_ROW_ID,
  cardFromHref,
  desktop_default as default,
  kanbanRowSwitch,
  onOpenCard,
  openCardRoute,
  takePendingCard,
  watchCardLinks
};
