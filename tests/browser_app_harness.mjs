// Node harness for the GENERATED scripts/crew_dashboard/app.js (built from ui/src/browser.tsx): the app the standalone
// server's shell loads, and the one the Hermes web dashboard tab mounts. It is evaluated for real in a jsdom window
// with a stub fetch that answers the JSON fixtures, so the markup asserted below is what React drew from them.
// Also loads the dashboard tab (dashboard/dist/index.js) against a stub of the Hermes plugin SDK and checks it mounts the
// same app with the SDK's authedFetch as the transport.
// Usage: node browser_app_harness.mjs <app.js> <dashboard/dist/index.js>   (exit 0 and "OK n checks" when all pass)
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const [, , appPath, tabPath] = process.argv
const here = path.dirname(fileURLToPath(import.meta.url))
const req = createRequire(path.join(here, '..', 'ui', 'package.json'))
const { JSDOM, VirtualConsole } = req('jsdom')
const React = req('react')
const { createRoot } = req('react-dom/client')
const src = fs.readFileSync(appPath, 'utf8')
const board = JSON.parse(fs.readFileSync(path.join(here, 'fixtures', 'board.live.json'), 'utf8'))
const card = JSON.parse(fs.readFileSync(path.join(here, 'fixtures', 'card.live.json'), 'utf8'))
let checks = 0
const ok = (cond, msg) => { assert.ok(cond, msg); checks++ }
const eq = (a, b, msg) => { assert.deepEqual(a, b, msg); checks++ }
const settle = ms => new Promise(r => setTimeout(r, ms))
// Waits (up to 4 s) until `sel` matches in `root`; the first paint of a big page takes a moment under jsdom.
async function until(root, sel) {
  for (let i = 0; i < 80 && !root.querySelector(sel); i++) await settle(50)
  return root.querySelector(sel)
}

// A page with the app loaded into it. `url` is the address bar; `fetchLog` records what the app asked for.
function page(url, body, setup = () => {}) {
  const dom = new JSDOM('<!doctype html><html><head></head><body>' + body + '</body></html>', {
    url, runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: new VirtualConsole()
  })
  const w = dom.window
  const fetchLog = []
  w.fetch = async (u, init) => {
    fetchLog.push([String(u), (init && init.method) || 'GET'])
    const p = String(u).replace(/^\/api\/plugins\/crew/, '')
    const payload = p.startsWith('/card/') ? card : board
    return { ok: true, status: 200, json: async () => payload, text: async () => 'cleared\n' }
  }
  setup(w)
  w.eval(src)
  return { w, fetchLog, doc: w.document }
}

// --- the served shell: the route comes from location.pathname
{
  const { doc, fetchLog, w } = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  ok(await until(doc, '#crew-app .page-board'), '/ draws the board')
  ok(fetchLog.some(f => f[0] === '/board.json'), '/ polls /board.json with no flags')
  ok(typeof w.__crewMount === 'function', 'the app exposes __crewMount for a host page')
}
{
  const { doc, fetchLog } = page('http://127.0.0.1:8799/?all=1&older=1', '<div id=crew-app></div>')
  await until(doc, '.page-board')
  ok(fetchLog.some(f => f[0] === '/board.json?all=1&older=1'), '/?all=1&older=1 reaches the route as both flags')
  ok(doc.querySelector('.page-board'), 'the flags still draw the board')
}
{
  const { doc, fetchLog } = page('http://127.0.0.1:8799/card/' + card.card_id, '<div id=crew-app></div>')
  ok(await until(doc, '#crew-app .page-card .crew-graph .node'), '/card/<id> draws the card page')
  ok(fetchLog.some(f => f[0] === '/card/' + card.card_id + '.json'), '/card/<id> polls /card/<id>.json')
  ok(doc.querySelectorAll('.crew-graph .node').length === card.nodes.length, 'the card page drew every node of the fixture')
}

// --- the shareable card link crew sends out (crew_card.card_url): /crew?card=<id> opens that card; /crew alone is the board
{
  const { doc, fetchLog } = page('http://127.0.0.1:8799/crew?card=' + card.card_id, '<div id=crew-app></div>')
  ok(await until(doc, '#crew-app .page-card .crew-graph .node'), '/crew?card=<id> draws the card page')
  ok(fetchLog.some(f => f[0] === '/card/' + card.card_id + '.json'), '/crew?card=<id> polls that card')
  const bare = page('http://127.0.0.1:8799/crew', '<div id=crew-app></div>')
  ok(await until(bare.doc, '#crew-app .page-board'), '/crew with no card is the board')
  const bad = page('http://127.0.0.1:8799/crew?card=a%20b', '<div id=crew-app></div>')
  ok(await until(bad.doc, '#crew-app .page-board'), 'a card id outside [A-Za-z0-9_-] lands on the board')
}

// --- the dispatcher strip: drawn only when the board says the gateway is not running; an old server (no field) draws none
{
  const { doc } = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  await until(doc, '.page-board')
  ok(!doc.querySelector('#dispatcher-down'), 'a board with no dispatcher field draws no strip')
}
{
  board.dispatcher = { alive: true, detail: 'the gateway is running (pid 7)', command: '' }
  const { doc } = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  await until(doc, '.page-board')
  ok(!doc.querySelector('#dispatcher-down'), 'a live dispatcher draws no strip')
  board.dispatcher = { alive: false, detail: 'the gateway is not running (no gateway.pid in /h)', command: 'hermes gateway run' }
  const down = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  const strip = await until(down.doc, '#dispatcher-down')
  ok(strip && /Cards will not start/.test(strip.textContent) && /hermes gateway run/.test(strip.textContent), 'a dead dispatcher draws the strip with the command')
  delete board.dispatcher
}

// Every selector in the app's injected <style data-crew> sheets that targets body, html or :root without the shell key.
function hostRules(doc) {
  const css = [...doc.querySelectorAll('style[data-crew]')].map(e => e.textContent).join('\n').replace(/\/\*[\s\S]*?\*\//g, '')
  const out = []
  for (const m of css.matchAll(/(^|\})\s*([^{}@][^{}]*)\{/g))
    for (const sel of m[2].split(',')) if (/(^|\s)(body|html|:root)\b/.test(sel.trim()) && !sel.includes('data-crew-shell')) out.push(sel.trim())
  return out
}
// the served shell marks itself, so its body rule and :root inputs apply there and only there
{
  const { doc } = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  ok(await until(doc, '.page-board'), 'the standalone page draws the board')
  ok(doc.getElementById('crew-app').hasAttribute('data-crew-shell'), 'the standalone mount marks #crew-app data-crew-shell')
  ok([...doc.querySelectorAll('style[data-crew]')].some(e => /body:has\(#crew-app\[data-crew-shell\]\)/.test(e.textContent)), 'the body rule is keyed on the shell marker')
}

// --- navigation pushes history, the back button follows it
{
  const { doc, w } = page('http://127.0.0.1:8799/', '<div id=crew-app></div>')
  const tile = await until(doc, 'a.card[data-id]')
  ok(tile, 'the fixture board has a tile')
  tile.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }))
  eq(w.location.pathname, '/card/' + tile.getAttribute('data-id'), 'a tile click pushes /card/<id>')
  ok(await until(doc, '.page-card'), 'and shows the card')
  w.history.back()
  await until(doc, '.page-board')
  await settle(50)
  ok(doc.querySelector('.page-board') && !doc.querySelector('.page-card'), 'the back button returns to the board')
}

// --- hosted by the dashboard tab: a base, the tab's own fetch, the address bar left alone
{
  const { doc, w, fetchLog } = page('http://127.0.0.1:9119/crew', '<div id=crew-app data-manual=1 data-base=/api/plugins/crew></div>')
  const host = doc.getElementById('crew-app')
  ok(!host.firstChild, 'data-manual: the app does not start by itself')
  const opened = []
  const tabFetch = (u, init) => w.fetch(u, init)
  const unmount = w.__crewMount(host, { base: '/api/plugins/crew', fetch: tabFetch, openChat: (p, s) => opened.push([p, s]) })
  ok(await until(host, '.page-board'), 'the hosted app draws the board')
  // a hosted mount must not restyle the host page: no shell marker, and no injected rule that selects body or :root
  // unless it is keyed on #crew-app[data-crew-shell] (which only our own served shell carries)
  ok(!host.hasAttribute('data-crew-shell'), 'a hosted mount does not mark the host as the crew shell')
  eq(hostRules(doc), [], 'a hosted mount adds no body or :root rule that is not keyed on data-crew-shell')
  ok(fetchLog.some(f => f[0] === '/api/plugins/crew/board.json'), 'its calls go through the given fetch under the base')
  ok(!fetchLog.some(f => f[0] === '/board.json'), 'no call leaves the base')
  const tile = await until(host, 'a.card[data-id]')
  tile.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true }))
  ok(await until(host, '.page-card'), 'a tile opens its card inside the host')
  eq(w.location.pathname, '/crew', 'the host owns the address bar: the route is state only')
  ok(fetchLog.some(f => f[0].startsWith('/api/plugins/crew/card/') && f[0].endsWith('.json')), 'the card is read under the base')
  unmount()
  ok(host.childNodes.length === 0, 'unmount removes the app from the host')
  const before = fetchLog.length
  await settle(2300)
  eq(fetchLog.length, before, 'and the polling stops with it')
}

// --- hosted, arriving on a shareable card link ("<dashboard>/crew?card=<id>"): the tab opens that card
{
  const { doc, w, fetchLog } = page('http://127.0.0.1:9119/crew?card=' + card.card_id, '<div id=crew-app data-manual=1 data-base=/api/plugins/crew></div>')
  const host = doc.getElementById('crew-app')
  const unmount = w.__crewMount(host, { base: '/api/plugins/crew', fetch: (u, init) => w.fetch(u, init) })
  ok(await until(host, '.page-card'), 'a hosted tab opened at /crew?card=<id> shows that card')
  ok(fetchLog.some(f => f[0] === '/api/plugins/crew/card/' + card.card_id + '.json'), 'and reads it under the base')
  unmount()
}

// --- an exported file: one card from the embedded snapshot, no server
{
  const { doc, fetchLog } = page('file:///tmp/x.graph.html', '<div id=crew-app></div>', w => { w.__CREW_SNAPSHOT = card })
  ok(await until(doc, '.page-card .crew-graph .node'), 'a snapshot file draws the card page')
  ok(fetchLog.length === 0, 'and asks no server for anything')
  eq(doc.querySelectorAll('.crew-graph .node').length, card.nodes.length, 'with every node of the snapshot')
}

// --- the Hermes web dashboard tab: index.js mounts the app, fetched and run through the SDK's authedFetch
if (tabPath) {
  const tab = fs.readFileSync(tabPath, 'utf8')
  const open = async (appStatus) => {
    const dom = new JSDOM('<!doctype html><html><head></head><body><div id="root"></div></body></html>', {
      url: 'http://127.0.0.1:9119/crew', runScripts: 'dangerously', pretendToBeVisual: true   // dangerously: the tab runs the app as an inline script element, as a browser does, virtualConsole: new VirtualConsole()
    })
    const w = dom.window
    const log = []
    let Page = null
    w.__HERMES_PLUGIN_SDK__ = {
      React,
      authedFetch: async (u, init) => {
        log.push([String(u), (init && init.method) || 'GET'])
        if (u === '/api/plugins/crew/app.js') return { ok: appStatus === 200, status: appStatus, text: async () => src }
        const payload = u.startsWith('/api/plugins/crew/card/') ? card : board
        return { ok: true, status: 200, json: async () => payload, text: async () => 'cleared\n' }
      }
    }
    w.__HERMES_PLUGINS__ = { register: (id, c) => { if (id === 'crew') Page = c } }
    w.eval(tab)
    globalThis.window = w
    globalThis.document = w.document
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    const root = createRoot(w.document.getElementById('root'))
    await React.act(async () => { root.render(React.createElement(Page)) })
    return { w, log, root, doc: w.document, page: Page }
  }
  {
    const { w, log, root, doc, page } = await open(200)
    ok(typeof page === 'function', 'the tab registers a Crew page')
    ok(await until(doc, '#crew-app .page-board'), 'the tab draws the board inside the dashboard page')
    eq(log[0], ['/api/plugins/crew/app.js', 'GET'], 'the first request is the app script, through authedFetch')
    ok(log.some(l => l[0] === '/api/plugins/crew/board.json'), 'the board is read through authedFetch under /api/plugins/crew')
    ok(!log.some(l => !l[0].startsWith('/api/plugins/crew/')), 'no request leaves the plugin API')
    ok(!doc.querySelector('iframe') && !doc.querySelector('script'), 'no iframe, and the injected script element is gone again')
    ok(w.location.pathname === '/crew' && w.location.hash === '', 'the address bar of the host is untouched')
    await React.act(async () => { root.unmount() })
    await settle(100)
    const before = log.length
    await settle(2300)
    eq(log.length, before, 'closing the tab unmounts the app: polling stops')
  }
  {
    const { doc, log, root } = await open(500)
    await settle(300)
    ok(doc.body.textContent.includes('Crew Dashboard Unavailable') && doc.body.textContent.includes('HTTP 500'), 'a failing app.js shows the unavailable card with the status')
    ok(doc.querySelector('button') && doc.querySelector('button').textContent === 'Retry', 'with a Retry button')
    await React.act(async () => { root.unmount() })
  }
}
console.log('OK ' + checks + ' checks')
process.exit(0)   // the polling timers of the pages above would keep node alive
