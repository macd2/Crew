/**
 * Hermes.Crew Desktop runtime plugin — autonomous proof-gated coordination board.
 *
 * Registers /crew route + sidebar nav entry below OpenSpec under the TOOLS group.
 * Provides live flow graph, multi-agent kanban view, and attention task monitoring.
 *
 * Packaging: single uncompiled ESM file. Runtime loader scans
 * ~/.hermes/plugins/crew/desktop/plugin.js or desktop-plugins/crew/plugin.js.
 */

import {
  Button, Codicon, ROUTES_AREA, SIDEBAR_NAV_AREA
} from '@hermes/plugin-sdk'
import React from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function getThemeTokens() {
  if (typeof document === 'undefined') return { bg: '#041c1c', fg: '#ffffff', mode: 'dark' }
  var root = window.getComputedStyle(document.documentElement)
  var mode = document.documentElement.dataset.hermesMode || (root.getPropertyValue('color-scheme').trim()) || 'dark'
  var bg = root.getPropertyValue('--dt-background').trim() || root.getPropertyValue('--ui-bg-editor').trim() || root.getPropertyValue('--background').trim() || (mode === 'light' ? '#ffffff' : '#041c1c')
  var fg = root.getPropertyValue('--ui-text-primary').trim() || root.getPropertyValue('--dt-foreground').trim() || root.getPropertyValue('--foreground').trim() || (mode === 'light' ? '#17171a' : '#ffffff')
  return { bg: bg, fg: fg, mode: mode }
}

function withThemeQuery(url) {
  var t = getThemeTokens()
  var sep = url.indexOf('?') === -1 ? '?' : '&'
  return url + sep + 'theme=' + encodeURIComponent(t.mode) + '&bg=' + encodeURIComponent(t.bg) + '&fg=' + encodeURIComponent(t.fg)
}

var LOCAL_BOARD_URL = 'http://127.0.0.1:8799/'
var LOCAL_HEALTH_URL = 'http://127.0.0.1:8799/healthz'
var AUTH_REQUIRED_MESSAGE = 'Authentication required: please log in to Hermes Gateway or ensure local Crew daemon is running'

// True when the local crew_graph_serve daemon answers. no-cors: the daemon sends no CORS headers, so the
// response is opaque, but a resolved fetch proves the port is serving and a network error rejects.
async function probeLocalDaemon(timeoutMs) {
  if (typeof fetch !== 'function') return false
  var ctrl = typeof AbortController === 'function' ? new AbortController() : null
  var timer = ctrl ? setTimeout(function () { ctrl.abort() }, timeoutMs || 1500) : null
  try {
    await fetch(LOCAL_HEALTH_URL, { mode: 'no-cors', cache: 'no-store', signal: ctrl ? ctrl.signal : undefined })
    return true
  } catch (probeErr) {
    return false
  } finally {
    if (timer) clearTimeout(timer)
  }
}

function CrewPage() {
  var iframeRef = React.useRef(null)
  var [loading, setLoading] = React.useState(true)
  var [boardUrl, setBoardUrl] = React.useState('http://127.0.0.1:8799/')
  // Set instead of a board URL when no authenticated route and no local daemon exist: never iframe a raw 401.
  var [authError, setAuthError] = React.useState('')
  var [resolveNonce, setResolveNonce] = React.useState(0)
  // No board name is baked in: the generic 'Board' shows until the board page posts its live name.
  var [boardTitle, setBoardTitle] = React.useState('Board')

  React.useEffect(function () {
    // The active board's display name, posted by board.js from /board.json (board_name, else board), shown as written.
    function onMsg(e) {
      if (e && e.data && e.data.type === 'hermes:board-info') {
        var name = String(e.data.board_name || e.data.board || '').trim()
        if (name) setBoardTitle(name)
      }
    }
    window.addEventListener('message', onMsg)
    return function () { window.removeEventListener('message', onMsg) }
  }, [])

  React.useEffect(function () {
    var isMounted = true
    function applyUrl(url) {
      if (!isMounted) return
      setAuthError('')
      setBoardUrl(withThemeQuery(url))
    }
    async function resolveBoardUrl() {
      var conn = null
      try {
        if (window.hermesDesktop && window.hermesDesktop.getConnection) {
          conn = await window.hermesDesktop.getConnection()
        }
      } catch (connErr) {
        conn = null
      }
      var base = conn && conn.baseUrl ? String(conn.baseUrl).replace(/\/+$/, '') : ''
      if (conn && conn.mode === 'remote' && base) {
        if (conn.token) {
          return applyUrl(base + '/api/plugins/crew/board?token=' + encodeURIComponent(conn.token))
        }
        if (window.hermesDesktop && window.hermesDesktop.api) {
          try {
            var ticketResp = await window.hermesDesktop.api({ path: '/api/auth/ws-ticket', method: 'POST' })
            if (ticketResp && ticketResp.ticket) {
              return applyUrl(base + '/api/plugins/crew/board?ticket=' + encodeURIComponent(ticketResp.ticket))
            }
          } catch (ticketErr) {
            // Not authenticated with the remote gateway: fall through to the local daemon.
          }
        }
        // No token and no ticket: the gateway URL would only render {"error":"unauthenticated",...}.
        if (await probeLocalDaemon(1500)) {
          return applyUrl(LOCAL_BOARD_URL)
        }
        if (isMounted) setAuthError(AUTH_REQUIRED_MESSAGE)
        return
      }
      // Local backend (or no connection info): the daemon directly when it is up; otherwise the
      // local backend's crew proxy, which starts the daemon on demand.
      if (await probeLocalDaemon(1500)) {
        return applyUrl(LOCAL_BOARD_URL)
      }
      if (base && conn && conn.token) {
        return applyUrl(base + '/api/plugins/crew/board?token=' + encodeURIComponent(conn.token))
      }
      applyUrl(LOCAL_BOARD_URL)
    }
    resolveBoardUrl()
    return function () {
      isMounted = false
    }
  }, [resolveNonce])

  React.useEffect(function () {
    function syncTheme() {
      setLoading(false)
      var el = iframeRef.current
      if (!el) return
      var t = getThemeTokens()
      try {
        if (el.contentWindow) {
          el.contentWindow.postMessage({ type: 'hermes:theme', bg: t.bg, fg: t.fg, theme: t.mode }, '*')
        }
      } catch (postErr) {}
      try {
        var doc = el.contentDocument || (el.contentWindow && el.contentWindow.document)
        if (!doc) return
        var existing = doc.getElementById('hermes-theme-sync')
        if (!existing) {
          var s = doc.createElement('style')
          s.id = 'hermes-theme-sync'
          doc.head.appendChild(s)
          existing = s
        }
        existing.textContent =
          ':root { color-scheme: ' + t.mode + ' !important; --crew-scheme: ' + t.mode + ' !important; --crew-bg: ' + t.bg + ' !important; --color-background: ' + t.bg + ' !important; --crew-fg: ' + t.fg + ' !important; } ' +
          'html, body, main#board, main, #main, .page-card { background-color: ' + t.bg + ' !important; ' + (t.fg ? 'color: ' + t.fg + ' !important;' : '') + '}'
      } catch (err) {
        // Cross-origin fallback
      }
    }

    var el = iframeRef.current
    if (el) {
      el.addEventListener('load', syncTheme)
    }
    var obs = null
    try {
      obs = new MutationObserver(syncTheme)
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-hermes-mode', 'class', 'style'] })
    } catch (obsErr) {}

    return function () {
      if (el) {
        el.removeEventListener('load', syncTheme)
      }
      if (obs) {
        obs.disconnect()
      }
    }
  }, [boardUrl])

  var reloadBoard = function () {
    if (authError) {
      // Nothing loaded yet: re-run the resolution (login may have happened, or the daemon started).
      setResolveNonce(function (n) { return n + 1 })
      return
    }
    if (iframeRef.current) {
      setLoading(true)
      iframeRef.current.src = boardUrl
    }
  }

  var openStandalone = function () {
    if (window.hermesDesktop && window.hermesDesktop.openExternal) {
      window.hermesDesktop.openExternal(boardUrl)
    } else {
      window.open(boardUrl, '_blank')
    }
  }

  return jsxs('div', {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      backgroundColor: 'var(--background, #041c1c)'
    },
    children: [
      jsxs('header', {
        style: {
          height: '36px',
          minHeight: '36px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          borderBottom: '1px solid var(--border, rgba(255, 255, 255, 0.08))',
          backgroundColor: 'var(--card, rgba(0, 0, 0, 0.2))'
        },
        children: [
          jsxs('div', {
            style: { display: 'flex', alignItems: 'center', gap: '8px' },
            children: [
              jsx(Codicon, { name: 'organization', style: { fontSize: '14px', color: 'var(--primary, #34d399)' } }),
              jsx('span', {
                style: { fontSize: '12px', fontWeight: 600, letterSpacing: '0.02em', color: 'var(--foreground, #ffffff)' },
                children: boardTitle
              }),
            ]
          }),
          jsxs('div', {
            style: { display: 'flex', alignItems: 'center', gap: '6px' },
            children: [
              jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                onClick: reloadBoard,
                style: { height: '24px', padding: '0 6px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' },
                children: jsxs(React.Fragment, {
                  children: [
                    jsx(Codicon, { name: 'refresh', style: { fontSize: '12px' } }),
                    jsx('span', { children: 'Refresh' })
                  ]
                })
              }),
              jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                onClick: openStandalone,
                style: { height: '24px', padding: '0 6px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' },
                children: jsxs(React.Fragment, {
                  children: [
                    jsx(Codicon, { name: 'link-external', style: { fontSize: '12px' } }),
                    jsx('span', { children: 'Standalone' })
                  ]
                })
              })
            ]
          })
        ]
      }),
      jsx('div', {
        style: { flex: 1, width: '100%', position: 'relative', overflow: 'hidden' },
        children: authError
          ? jsxs('div', {
              role: 'alert',
              style: {
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                padding: '24px',
                textAlign: 'center',
                color: 'var(--foreground, #ffffff)'
              },
              children: [
                jsx(Codicon, { name: 'lock', style: { fontSize: '28px', color: 'var(--primary, #34d399)' } }),
                jsx('div', { style: { fontSize: '13px', fontWeight: 600 }, children: authError }),
                jsx('div', {
                  style: { fontSize: '11px', opacity: 0.7 },
                  children: 'Start the crew dashboard service (crew_graph_serve.py, set up by install.py), or sign in to the gateway, then press Refresh.'
                }),
                jsx(Button, { size: 'sm', variant: 'outline', onClick: reloadBoard, children: 'Retry' })
              ]
            })
          : jsx('iframe', {
              ref: iframeRef,
              src: boardUrl,
              style: {
                width: '100%',
                height: '100%',
                border: 'none',
                display: 'block',
                backgroundColor: 'var(--background, #041c1c)'
              },
              title: boardTitle
            })
      })
    ]
  })
}

var plugin = {
  id: 'crew',
  name: 'Crew',
  description: 'Autonomous proof-gated coordination board and live flow graph',
  register: function(ctx) {
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: '/crew' },
        render: function() { return jsx(CrewPage, {}) }
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        order: 55,
        data: { codicon: 'organization', label: 'Crew', path: '/crew', asTile: true }
      }
    ])
  }
}

export default plugin
