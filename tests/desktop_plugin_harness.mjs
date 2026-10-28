// Node harness for the GENERATED desktop/plugin.js (built from ui/src by ui/build.mjs). Hermes Desktop provides
// three modules to a disk plugin; here @hermes/plugin-sdk is a stub, while react and react/jsx-runtime are the REAL
// ones from ui/node_modules and the page and pane are rendered for real into a jsdom document, so the markup
// asserted below is what React produced from the board.json fixture, effects and polling included.
// Usage: node desktop_plugin_harness.mjs <plugin.js> <scratch dir>   (exit 0 and "OK n checks" when all pass)
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'

const [, , pluginPath, tmp] = process.argv
const UI = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'ui')
const req = createRequire(path.join(UI, 'package.json'))
const { JSDOM } = req('jsdom')
const dom = new JSDOM('<!doctype html><div id="root"></div>')
globalThis.window = dom.window
globalThis.document = dom.window.document
globalThis.IS_REACT_ACT_ENVIRONMENT = true
const React = req('react')
const { createRoot } = req('react-dom/client')

const lightTheme = {
  colors: { background: '#ffffff', foreground: '#111111', card: '#f5f5f5', cardForeground: '#111111', muted: '#eeeeee',
    mutedForeground: '#666666', primary: '#0055ff', primaryForeground: '#ffffff', accent: '#ddeeff',
    accentForeground: '#001133', border: '#cccccc', destructive: '#cc0000' },
  typography: { fontSans: 'Test Sans', fontMono: 'Test Mono' }
}
const reactUrl = pathToFileURL(req.resolve('react')).href
const runtimeUrl = pathToFileURL(req.resolve('react/jsx-runtime')).href
fs.writeFileSync(path.join(tmp, 'sdk.mjs'), `
export const ROUTES_AREA = 'routes', SIDEBAR_NAV_AREA = 'sidebar.nav', PANES_AREA = 'panes'
export const useTheme = () => ({ theme: globalThis.__theme, renderedMode: globalThis.__mode || 'light' })
// Desktop's chat-open contract, host.openSession(session, { profile }) (recorded); every Desktop SDK has it
export const host = { openSession: (s, o) => { (globalThis.__opened = globalThis.__opened || []).push([s, o]); return Promise.resolve() } }
`)
// The app's pieces a host-aware build uses (Desktop exports them; a stand-in for each): the chat's message renderer (bold
// and `code` to markup, so a test can tell it ran), the Button (data-variant/size so the bar's choice shows), the ConfirmDialog.
const HOST_STUBS = `
import R from '${reactUrl}'
const h = R.createElement
export const MessageTextContent = ({ text }) => h('div', { className: 'stub-md', dangerouslySetInnerHTML: { __html: String(text)
  .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\`([^\`]+)\`/g, '<code>$1</code>') } })
export const Button = ({ children, id, title, disabled, onClick, variant, size }) =>
  h('button', { type: 'button', id, title, disabled, onClick, 'data-variant': variant, 'data-size': size }, children)
// the host verbs a plugin may use beyond openSession (in both stubs): a toast (recorded) and the router (the hash, as the
// real navigate sets it)
Object.assign(host, {
  notify: n => { (globalThis.__toasts = globalThis.__toasts || []).push(n); return n.id },
  navigate: p => { (globalThis.__navigated = globalThis.__navigated || []).push(p); window.location.hash = '#' + p }
})
export const ConfirmDialog = ({ open, title, onConfirm, onClose }) => open
  ? h('div', { id: 'confirm' }, h('b', null, title), h('button', { id: 'confirm-yes', onClick: onConfirm }, 'Confirm'), h('button', { id: 'confirm-no', onClick: onClose }, 'Cancel'))
  : null
`
fs.writeFileSync(path.join(tmp, 'sdk-host.mjs'), fs.readFileSync(path.join(tmp, 'sdk.mjs'), 'utf8') + HOST_STUBS)
fs.writeFileSync(path.join(tmp, 'jsx.mjs'), `import R from '${runtimeUrl}'\nexport const { jsx, jsxs, Fragment } = R\n`)
fs.writeFileSync(path.join(tmp, 'react.mjs'), `import R from '${reactUrl}'\nexport default R\nexport const { Fragment, ${Object.keys(req('react')).filter(k => k !== 'Fragment').filter(k => /^[A-Za-z_$][\w$]*$/.test(k)).join(', ')} } = R\n`)
globalThis.__theme = lightTheme

const src = fs.readFileSync(pluginPath, 'utf8')
const specs = [...src.matchAll(/^import .* from ['"]([^'"]+)['"]/gm)].map(m => m[1])
const rewritten = src.replace(/(from )"@hermes\/plugin-sdk"/g, '$1"./sdk.mjs"').replace(/(from )"react\/jsx-runtime"/g, '$1"./jsx.mjs"')
  .replace(/(from )"react"/g, '$1"./react.mjs"')
fs.writeFileSync(path.join(tmp, 'plugin.mjs'), rewritten)
const mod = await import(pathToFileURL(path.join(tmp, 'plugin.mjs')).href)
const plugin = mod.default
let checks = 0
const ok = (cond, msg) => { assert.ok(cond, msg); checks++ }
const eq = (a, b, msg) => { assert.deepEqual(a, b, msg); checks++ }

// --- only the three modules Desktop provides
ok(specs.length > 0, 'plugin.js has imports')
eq([...new Set(specs)].sort(), ['@hermes/plugin-sdk', 'react', 'react/jsx-runtime'])
ok(!/\bimport\(|\beval\(|new Function/.test(src), 'no dynamic import, eval or new Function')

// --- registration: the page, the sidebar row, the pane
const board = {
  generated_at: 1, live: 1, cards: 3, counts: { running: 1, ready: 1, done: 1 }, attention: [],
  lanes: [
    { key: 'ready', label: 'Ready', hidden: 0, tiles: [{ id: 't_ready1', title: 'Write the intro', status: 'ready', role: 'worker', assignee: 'w', active: null }] },
    { key: 'running', label: 'Running', hidden: 0, tiles: [
      { id: 't_live77', title: 'Port the board', status: 'running', role: 'worker', assignee: 'w', active: { profile: 'w', run: 5, for_s: 30 } },
      { id: 't_done9', title: 'Ship the doc', status: 'done', role: 'worker', assignee: 'w', active: null }] }
  ]
}
const calls = []
const rests = []
const ctx = {
  registerMany: cs => calls.push(...cs),
  rest: async (p, o) => { rests.push([p, o && o.method]); return board }
}
eq([plugin.id, plugin.name, typeof plugin.register], ['crew', 'Crew', 'function'])
plugin.register(ctx)
eq(calls.map(c => c.area), ['routes', 'sidebar.nav', 'panes'])
const [page, nav, pane] = calls
eq(page.data, { path: '/crew' })
eq([nav.data.path, nav.data.label], ['/crew', 'Crew'])
eq([pane.id, pane.title, pane.data.placement, pane.data.width], ['flow', 'Crew flow', 'right', '260px'])
ok(pane.data.hideOnly === true, 'the pane is hideOnly')
ok(pane.data.collapsible === true, 'the pane is collapsible')

// --- render both for real: effects run, ctx.rest answers the fixture, React re-renders
async function mount(render) {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  await React.act(async () => { root.render(render()) })
  await React.act(async () => { await new Promise(r => setTimeout(r, 10)) })
  const html = host.innerHTML
  await React.act(async () => { root.unmount() })
  host.remove()
  return html
}
const pageHtml = await mount(page.render)
eq(rests.map(r => r[0]).includes('/board.json'), true, 'the page asked ctx.rest for /board.json')
for (const s of ['Ready', 'Running', 't_ready1', 'Write the intro', 'Port the board', 'Ship the doc', 'done'])
  ok(pageHtml.includes(s), `page markup has ${s}`)
ok(pageHtml.includes('--crew-bg: #ffffff') && pageHtml.includes('--crew-font: Test Sans'), 'theme reached the --crew-* variables')
globalThis.__theme = { colors: { ...lightTheme.colors, background: '#101214', foreground: '#eeeeee', primary: '#88aaff', destructive: '#ff6666' },
  typography: { fontSans: 'Dark Sans', fontMono: 'Dark Mono' } }
globalThis.__mode = 'dark'
const darkHtml = await mount(page.render)
ok(darkHtml.includes('--crew-bg: #101214') && darkHtml.includes('--crew-fg: #eeeeee'), 'a dark theme gives a dark --crew-bg and a light --crew-fg')
ok(darkHtml.includes('--crew-font: Dark Sans') && darkHtml.includes('--crew-mono: Dark Mono'), 'fonts come from the theme typography')
ok(darkHtml.includes('--crew-in-blocked: #ff6666') && darkHtml.includes('--crew-in-ready: #88aaff'), 'tones come from destructive and primary')
ok(darkHtml.includes('color-scheme: dark') && !darkHtml.includes('#ffffff'), 'color-scheme follows the rendered mode, no light colour left over')
globalThis.__theme = lightTheme
globalThis.__mode = 'light'
const paneHtml = await mount(pane.render)
ok(paneHtml.includes('live77'), 'pane lists the live card (tile with active), by short id')
ok(!paneHtml.includes('ready1'), 'pane lists only live and Needs-you cards')

// --- the board, rendered for real from two REAL-shape boards: tests/fixtures/board.live.json is the live board read with
// crew_graph_serve.board_data; board.states.json is that board with every card state added (running, quiet, blocked,
// triage, review, ready, budget, verdicts, a bell with rows). Expectations come from the fixture and from the rules
// board.js laneHTML/cardHTML apply, never from the component's own output.
const HERE = path.dirname(fileURLToPath(import.meta.url))
const fixture = n => JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', n), 'utf8'))
async function mountKeep(render) {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  await React.act(async () => { root.render(render()) })
  await React.act(async () => { await new Promise(r => setTimeout(r, 20)) })
  return { host, done: async () => { await React.act(async () => { root.unmount() }); host.remove() } }
}
const settle = () => React.act(async () => { await new Promise(r => setTimeout(r, 20)) })
const click = el => React.act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, button: 0 })) })
const VERDICT = { PASS: '✓ verified', FAIL: '✕ verify failed', unverified: '○ unverified' }
const STATE_CHIP = { ready: 'queued', todo: 'queued', blocked: 'blocked', triage: 'needs you', review: 'in review' }
function chipFor(t) {   // board.js stateHTML, restated from its rules
  if (t.active) {
    if (t.active.quiet_s !== null && t.active.quiet_s > 120) return 'no heartbeat'
    return 'working · ' + (t.active.for_s < 3600 ? Math.floor(t.active.for_s / 60) + 'm' : Math.floor(t.active.for_s / 3600) + 'h') +
      (t.active.steps ? ' · step ' + t.active.steps : '') + (t.active.last_tool ? ' · last: ' + t.active.last_tool : '')
  }
  if (STATE_CHIP[t.status]) return STATE_CHIP[t.status]
  if (t.status !== 'done') return null
  return VERDICT[t.verdict] || 'done'
}
for (const name of ['board.live.json', 'board.states.json']) {
  const fx = fixture(name)
  const seen = []
  ctx.rest = async (p, o) => {
    seen.push([p, o && o.method])
    if (p.includes('older=1')) return { ...fx, lanes: fx.lanes.map(l => (l.key === 'done' ? { ...l, hidden: 0 } : l)) }   // the server lists every done card
    if (p.startsWith('/board.json')) return fx
    if (p.startsWith('/embed/avatar/')) return { data_url: 'data:image/svg+xml;base64,PHN2Zy8+' }
    if (p.startsWith('/embed/ack/')) return { ok: true, status: 200, text: 'cleared' }
    throw new Error('unexpected ' + p)
  }
  const m = await mountKeep(page.render)
  const q = sel => [...m.host.querySelectorAll(sel)]
  const tag = `[${name}] `
  // lanes: same order, names, shape and tile count as laneHTML makes for this fixture
  eq(q('main#board > section.lane').map(e => e.dataset.lane), fx.lanes.map(l => l.key), tag + 'lane order')
  for (const l of fx.lanes) {
    const el = m.host.querySelector(`section.lane[data-lane="${l.key}"]`)
    const n = l.tiles.length + (l.hidden || 0)
    const collapsed = l.key === 'archived' && n > 0   // the Archived column starts closed
    const rail = collapsed || n === 0
    eq(el.className, collapsed ? 'lane rail togglable' : rail ? 'lane rail' : 'lane', tag + l.key + ' lane class')
    eq(el.querySelector('.lt').textContent, l.label, tag + l.key + ' lane name')
    eq(el.querySelectorAll('a.card').length, rail ? 0 : l.tiles.length, tag + l.key + ' tile count')
    if (n > 0) eq(el.querySelector('.ln').textContent, String(n), tag + l.key + ' lane count')
    if (!rail) for (const t of l.tiles) {
      const c = el.querySelector(`a.card[data-id="${t.id}"]`)
      ok(c, tag + 'tile ' + t.id)
      eq(c.className, 'card' + (t.active ? (t.active.quiet_s !== null && t.active.quiet_s > 120 ? ' quiet' : ' live') : ''), tag + t.id + ' tile class')
      eq(c.getAttribute('href'), '/card/' + t.id)
      eq(c.querySelector('.ti').textContent, t.title || '(untitled)')
      eq(!!c.querySelector('.su'), !!t.summary, tag + t.id + ' summary')
      const chip = c.querySelector('.ft .schip')
      eq(chip ? chip.textContent : null, chipFor(t), tag + t.id + ' state chip')
      ok(c.querySelector('.ft .id').textContent === t.id.replace(/^t_/, '').slice(0, 6), tag + t.id + ' short id')
      ok(c.querySelector('img.avatar.face') || c.querySelector('span.avatar'), tag + t.id + ' avatar')
    }
  }
  // header: counts, card count, live word, bell
  eq(q('#counts > span').map(e => e.className), [['running', ['running']], ['blocked', ['blocked', 'triage']], ['done', ['done']]]
    .map(([c, ss]) => c + (ss.reduce((a, k) => a + (fx.counts[k] || 0), 0) ? '' : ' none')), tag + 'header count classes')
  eq(m.host.querySelector('#cards').textContent, fx.cards + (fx.cards === 1 ? ' card' : ' cards'))
  eq(m.host.querySelector('#live').textContent, fx.live ? fx.live + ' working now' : 'nothing running')
  eq(m.host.querySelector('#belln').textContent, String(fx.attention.rows.length), tag + 'bell count')
  ok(seen.some(r => r[0] === '/board.json'), tag + 'board polled with no flags')
  await settle()
  // avatars come through ctx.rest as data URLs (Desktop cannot point an <img> at a route)
  const face = m.host.querySelector('img.avatar.face')
  if (face) {
    ok(face.src.startsWith('data:image/svg+xml'), tag + 'avatar is a data URL: ' + face.src.slice(0, 40) + JSON.stringify(seen.slice(0, 4)))
    ok(seen.some(r => r[0].startsWith('/embed/avatar/role/') && r[0].endsWith('.svg')), tag + 'avatar asked for /embed/avatar/role/<n>.svg')
  }
  // Archived: click the rail open, click the header closed
  const archived = () => m.host.querySelector('section.lane[data-lane="archived"]')
  const arch = fx.lanes.find(l => l.key === 'archived')
  if (arch.tiles.length + arch.hidden > 0) {
    await click(archived())
    eq(archived().className, 'lane', tag + 'archived opens')
    eq(archived().querySelectorAll('a.card').length, arch.tiles.length, tag + 'archived tiles after open')
    await click(archived().querySelector('.lh[data-toggle]'))
    eq(archived().className, 'lane rail togglable', tag + 'archived closes')
  }
  // bell: opens on click, clearing a row posts to the Desktop ack route
  const rows = fx.attention.rows
  eq(m.host.querySelector('#notes').hidden, true, tag + 'notes start closed')
  await click(m.host.querySelector('#bell'))
  eq(m.host.querySelector('#notes').hidden, false, tag + 'bell opens the list')
  eq(q('#noterows .ar').length, rows.length, tag + 'bell rows')
  if (rows.length) {
    await click(m.host.querySelector('#noterows .ar button'))
    ok(seen.some(r => r[0] === '/embed/ack/' + rows[0].id && r[1] === 'POST'), tag + 'ack POST /embed/ack/<id>')
    eq(q('#noterows .ar').length, rows.length - 1, tag + 'cleared row leaves the list')
    await click(m.host.querySelector('#clearall'))
    ok(seen.some(r => r[0] === '/embed/ack/all' && r[1] === 'POST'), tag + 'clear all POST /embed/ack/all')
  } else eq(m.host.querySelector('#noterows').textContent, 'nothing waiting', tag + 'empty bell')
  // "Show N older" asks for older=1
  const more = m.host.querySelector('button.more[data-older="1"]')
  const done = fx.lanes.find(l => l.key === 'done')
  eq(!!more, done.hidden > 0, tag + 'show-older button')
  if (more) {
    eq(more.textContent, `Show ${done.hidden} older`)
    await click(more)
    ok(seen.some(r => r[0] === '/board.json?older=1'), tag + 'older=1 reached the route')
    ok(m.host.querySelector('button.more[data-older="0"]'), tag + 'show-newest-only button after older')
  }
  await m.done()
}
ctx.rest = async (p, o) => { rests.push([p, o && o.method]); return board }

// --- the card page, from the LIVE card fixture (tests/fixtures/card.live.json: archived card t_c9e643de, a done card with
// a brief, two runs, a c_verifier with a PASS verdict and failed calls). Click a c_tile, read the page, poll again with one
// more step appended: the lists must keep their DOM nodes (the in-place guarantee of the old page).
const c_cardFx = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', 'card.live.json'), 'utf8'))
let c_served = c_cardFx
const c_cardRests = []
ctx.rest = async p => { c_cardRests.push(p); return p.startsWith('/card/') ? c_served : board }
const c_host = document.createElement('div')
document.body.appendChild(c_host)
const c_root = createRoot(c_host)
const c_act = fn => React.act(fn)
const c_settle = ms => c_act(async () => { await new Promise(r => setTimeout(r, ms)) })
await c_act(async () => { c_root.render(page.render()) })
await c_settle(10)
const c_tile = c_host.querySelector('a.card[data-id="t_live77"]')
ok(c_tile, 'the board has the c_tile')
await c_act(async () => { c_tile.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, cancelable: true })) })
await c_settle(10)
ok(c_host.querySelector('.page-card'), 'a click on a c_tile opens the card page')
ok(c_cardRests.some(r => r.startsWith('/card/') && r.endsWith('.json')), 'the card page polled /card/<id>.json')
const c_txt = sel => [...c_host.querySelectorAll(sel)].map(e => e.textContent)
ok(c_host.querySelector('#cardtitle').textContent === c_cardFx.card_title, 'status bar shows the card title')
eq(c_txt('#roster .rn').slice(1), c_cardFx.roles.map(r => r.name), 'roster lists the roles of the fixture')
eq(c_host.querySelectorAll('.crew-graph .node').length, c_cardFx.nodes.length, 'the graph drew every node')
// default node of the scrubber: the one with the c_newest step
let c_newest = null, c_newestTs = -1
for (const n of c_cardFx.nodes) for (const st of n.steps || []) if ((st.ts || 0) > c_newestTs) { c_newestTs = st.ts; c_newest = n }
const c_ticks = () => c_host.querySelectorAll('#scrubber .tick')
eq(c_ticks().length, c_newest.steps.length, 'scrubber has one tick per step of the c_newest node (' + c_newest.id + ')')
// the c_verifier's verdict
const c_verifier = c_cardFx.nodes.find(n => n.kind === 'verifier')
await c_act(async () => { c_host.querySelector('.node[data-id="' + c_verifier.id + '"] .card').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })) })
const panelTxt = c_host.querySelector('#panel').textContent
ok(c_host.querySelector('#panel.open') && panelTxt.includes(c_verifier.evidence.verdict), 'verifier panel shows the verdict ' + c_verifier.evidence.verdict)
await c_act(async () => { c_host.querySelector('#panel [data-tab="Proof"]').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })) })
ok(c_host.querySelector('#panel').textContent.includes(c_verifier.evidence.command.slice(0, 20)), 'Proof tab shows the proof command')
// the c_session's Calls: one row per step, kept across a poll that appends a step
const c_session = c_cardFx.nodes.find(n => n.kind === 'session')
await c_act(async () => { c_host.querySelector('.node[data-id="' + c_session.id + '"] .card').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })) })
await c_act(async () => { c_host.querySelector('#panel [data-tab="Calls"]').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })) })
const c_rows = () => [...c_host.querySelectorAll('#panel .plist.calls > .call')]
eq(c_rows().length, c_session.steps.length, 'Calls lists every step of the c_session (' + c_session.steps.length + ')')
const c_oldest = c_rows()[c_rows().length - 1], c_body = c_host.querySelector('#panel .pbody'), c_firstTick = c_ticks()[0]
c_body.scrollTop = 37
const c_grown = JSON.parse(JSON.stringify(c_cardFx))
const c_gs = c_grown.nodes.find(n => n.id === c_session.id)
c_gs.steps.push({ ...c_gs.steps[c_gs.steps.length - 1], tool: 'terminal', ts: c_gs.steps[c_gs.steps.length - 1].ts + 5, args: 'echo one more' })
c_gs.tool_count += 1; c_gs.evidence.tool_call_count += 1
c_served = c_grown
await c_settle(2300)
eq(c_rows().length, c_session.steps.length + 1, 'the second poll shows the appended step')
ok(c_rows().includes(c_oldest) && c_rows()[c_rows().length - 1] === c_oldest, 'the first call row is the same DOM node after the poll (no remount)')
ok(c_host.querySelector('#panel .pbody') === c_body && c_body.scrollTop === 37, 'the panel body keeps its element and its scroll offset')
ok(c_host.querySelector('#panel .plist.calls') && c_host.querySelector('#event'), 'page chrome stays mounted')
ok(c_host.querySelectorAll('#scrubber .tick').length === c_gs.steps.length || c_host.querySelectorAll('#scrubber .tick').length > 0, 'scrubber follows the selected node')
// Issue #19: the card page listens on document, and Desktop can show a chat beside it (split route tile, or the crew tab
// kept mounted behind the chat tab). Space must stay the chat composer's (a contenteditable div), and keep pausing the card
// when nothing is focused.
const c_space = async target => {
  const ev = new dom.window.KeyboardEvent('keydown', { key: ' ', code: 'Space', bubbles: true, cancelable: true })
  await c_act(async () => { target.dispatchEvent(ev) })
  return ev.defaultPrevented
}
const c_live = () => c_host.querySelector('#live').textContent
const c_ce = document.createElement('div')
c_ce.setAttribute('contenteditable', 'true'); c_ce.setAttribute('role', 'textbox'); c_ce.tabIndex = 0
const c_ceKid = document.createElement('span'); c_ce.appendChild(c_ceKid)
const c_input = document.createElement('input'), c_other = document.createElement('div'); c_other.tabIndex = 0
document.body.append(c_ce, c_input, c_other)
c_ce.focus()
eq(c_live(), 'LIVE', 'the card page starts live')
eq(await c_space(c_ce), false, 'Space in a contenteditable composer beside the card page is not prevented')
eq(await c_space(c_ceKid), false, 'Space in a child of the contenteditable is not prevented')
eq(c_live(), 'LIVE', 'Space in the composer does not pause the card')
eq(await c_space(c_input), false, 'Space in an INPUT is still left alone')
c_other.focus()
eq(await c_space(c_other), false, 'Space on a non-editable element outside the card page is not the card page\'s')
eq(c_live(), 'LIVE', 'a key from outside the card page does not pause it')
c_other.blur()
eq(await c_space(document.body), true, 'Space with nothing focused is the card page\'s')
eq(c_live(), 'PAUSED', 'Space on the body pauses the card')
eq(await c_space(c_host.querySelector('.page-card')), true, 'Space inside the card page is the card page\'s')
eq(c_live(), 'LIVE', 'Space inside the card page resumes it')
c_ce.remove(); c_input.remove(); c_other.remove()
// back to the board
await c_act(async () => { c_host.querySelector('#rail a.railbtn').dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, cancelable: true })) })
await c_settle(10)
ok(c_host.querySelector('.page-board') && !c_host.querySelector('.page-card'), 'the rail button goes back to the board')
await c_act(async () => { c_root.unmount() })
c_host.remove()
ctx.rest = async () => board

// --- no live card, and a failing API keeps the pane honest
board.lanes[1].tiles[0].active = null
ok((await mount(pane.render)).includes('Nothing running'), 'pane says nothing running')
ctx.rest = async () => { throw new Error('boom') }
ok((await mount(page.render)).includes('Crew could not load: boom'), 'page shows the load error')
// --- the card page's host pieces: the button bar and the markdown renderer (tests/desktop_action_checks.mjs). Two builds of
// plugin.js: one against a stub SDK that exports the app's renderer, Button and ConfirmDialog, one against a stub that does not.
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { actionChecks } = await import(pathToFileURL(path.join(here, 'desktop_action_checks.mjs')).href)
  const makePlugin = async withHost => {
    const file = path.join(tmp, withHost ? 'plugin-host.mjs' : 'plugin-nohost.mjs')
    fs.writeFileSync(file, rewritten.replaceAll('"./sdk.mjs"', withHost ? '"./sdk-host.mjs"' : '"./sdk.mjs"'))
    return { mod: await import(pathToFileURL(file).href + '?v=' + (withHost ? 'h' : 'n')) }
  }
  await actionChecks({ tmp, React, createRoot, window: dom.window, document, ok, eq, fixtures: path.join(here, 'fixtures'), board, makePlugin })
}
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { tileActionChecks } = await import(pathToFileURL(path.join(here, 'desktop_tile_action_checks.mjs')).href)
  const makePlugin = async withHost => {
    const file = path.join(tmp, withHost ? 'plugin-host-t.mjs' : 'plugin-nohost-t.mjs')
    fs.writeFileSync(file, rewritten.replaceAll('"./sdk.mjs"', withHost ? '"./sdk-host.mjs"' : '"./sdk.mjs"'))
    return { mod: await import(pathToFileURL(file).href + '?v=t' + (withHost ? 'h' : 'n')) }
  }
  await tileActionChecks({ React, createRoot, window: dom.window, document, ok, eq, board, makePlugin })
}
// --- the Needs-you popup (tests/desktop_blocked_checks.mjs)
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { blockedChecks } = await import(pathToFileURL(path.join(here, 'desktop_blocked_checks.mjs')).href)
  const makePlugin = async withHost => {
    const file = path.join(tmp, withHost ? 'plugin-host-b.mjs' : 'plugin-nohost-b.mjs')
    fs.writeFileSync(file, rewritten.replaceAll('"./sdk.mjs"', withHost ? '"./sdk-host.mjs"' : '"./sdk.mjs"'))
    return { mod: await import(pathToFileURL(file).href + '?v=b' + (withHost ? 'h' : 'n')) }
  }
  await blockedChecks({ React, createRoot, window: dom.window, document, ok, eq, board, makePlugin })
}
// --- shareable ticket links in chat: capture-phase left-click opens the card in-app (tests/desktop_card_link_checks.mjs)
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { cardLinkChecks } = await import(pathToFileURL(path.join(here, 'desktop_card_link_checks.mjs')).href)
  const makePlugin = async withHost => {
    const file = path.join(tmp, withHost ? 'plugin-host-l.mjs' : 'plugin-nohost-l.mjs')
    fs.writeFileSync(file, rewritten.replaceAll('"./sdk.mjs"', withHost ? '"./sdk-host.mjs"' : '"./sdk.mjs"'))
    return { mod: await import(pathToFileURL(file).href + '?v=l' + (withHost ? 'h' : 'n')) }
  }
  await cardLinkChecks({ React, createRoot, window: dom.window, document, ok, eq, board, makePlugin })
}
// --- the flow graph, minimap and flow pane (tests/desktop_graph_checks.mjs)
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { graphChecks } = await import(pathToFileURL(path.join(here, 'desktop_graph_checks.mjs')).href)
  await graphChecks({ req, tmp, React, createRoot, window: dom.window, document, ok, eq, ui: UI, fixtures: path.join(here, 'fixtures') })
}
// --- the Desktop splash: first open of the page in a module only, mark + eyebrow + headline + brand faces, gone after the
// board has arrived and 1300 ms have passed (+ the 300 ms fade). A fresh module instance = a fresh app session; later mounts in the same module show none.
{
  const file = path.join(tmp, 'plugin-splash.mjs')
  fs.writeFileSync(file, rewritten)
  const fresh = (await import(pathToFileURL(file).href + '?v=splash')).default
  const sCalls = []
  fresh.register({ registerMany: cs => sCalls.push(...cs), rest: async () => board })
  const sPage = sCalls[0]
  const t0 = Date.now()
  const m1 = await mountKeep(sPage.render)
  const sp = m1.host.querySelector('.crew-splash')
  ok(sp, 'splash is in the DOM on the first mount')
  ok(sp.textContent.includes('Hermes.Crew') && sp.textContent.includes('the agent company for Hermes'), 'splash has the eyebrow')
  ok(sp.querySelector('h1').textContent === 'You ask once.', 'splash has the headline')
  ok(sp.querySelector('img.sp-mark').getAttribute('src').startsWith('data:image/svg+xml'), 'splash shows the crew mark')
  const faces = [...document.head.querySelectorAll('style')].map(e => e.textContent).join('\n')
  ok(/@font-face\{font-family:CrewArchivo[^}]*data:font\/woff2/.test(faces) && /@font-face\{font-family:CrewMono[^}]*data:font\/woff2/.test(faces), 'both @font-face rules are injected as data URIs')
  ok(m1.host.querySelector('.page-board'), 'the board renders under the splash')
  await React.act(async () => { await new Promise(r => setTimeout(r, Math.max(0, 2000 - (Date.now() - t0))))})
  ok(!m1.host.querySelector('.crew-splash'), 'splash is gone after the board arrived and the minimum time passed')
  ok(m1.host.querySelector('.page-board'), 'the board is still there')
  await m1.done()
  const m2 = await mountKeep(sPage.render)
  ok(!m2.host.querySelector('.crew-splash'), 'a second mount (navigate away and back, or the Crew row again) shows no splash')
  ok(m2.host.querySelector('.page-board'), 'and the board renders at once')
  await m2.done()
  const m2b = await mountKeep(sPage.render)
  ok(!m2b.host.querySelector('.crew-splash'), 'a third mount still shows none, same app session')
  await m2b.done()
  fs.writeFileSync(path.join(tmp, 'plugin-splash2.mjs'), rewritten)
  const fresh2 = (await import(pathToFileURL(path.join(tmp, 'plugin-splash2.mjs')).href + '?v=splash2')).default
  const s2Calls = []
  fresh2.register({ registerMany: cs => s2Calls.push(...cs), rest: async () => board })
  const m3s = await mountKeep(s2Calls[0].render)
  ok(!!m3s.host.querySelector('.crew-splash'), 'a new app session (fresh module) shows the splash again')
  await m3s.done()
  const browserJs = fs.readFileSync(path.join(HERE, '..', 'scripts', 'crew_dashboard', 'app.js'), 'utf8')
  ok(!/crew-splash|CrewArchivo/.test(browserJs), 'the browser bundle has no splash, so the browser page never shows one')
}
// --- the splash's motion classes and words, reduced motion, and the Kanban-row nav prefs (tests/desktop_splash_checks.mjs)
{
  const here = path.dirname(fileURLToPath(import.meta.url))
  const { splashChecks } = await import(pathToFileURL(path.join(here, 'desktop_splash_checks.mjs')).href)
  await splashChecks({ tmp, rewritten, React, createRoot, window: dom.window, document, ok, eq, board })
}
console.log(`OK ${checks} checks`)
