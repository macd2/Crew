// Shareable ticket-link checks (ui/src/open-card.ts cardFromHref + the card bus, desktop.tsx watchCardLinks, CrewPage),
// called by desktop_plugin_harness.mjs. A chat message's "[t_x](<dashboard>/crew?card=t_x)" is an <a> OUTSIDE the Crew
// page: a plain left-click on it is taken in the capture phase (defaultPrevented, so Desktop's ExternalLink opens no
// browser) and opens that card in the mounted Crew page through host.navigate; Ctrl/Cmd/Shift/Alt, middle and right
// clicks, and links that are not a Crew card, pass through untouched (Copy Link keeps the full shareable href).
export async function cardLinkChecks({ React, createRoot, window, document, ok, eq, board, makePlugin }) {
  const wait = ms => React.act(async () => { await new Promise(r => setTimeout(r, ms)) })
  const withHost = await makePlugin(true), noHost = await makePlugin(false)

  // --- cardFromHref: the shareable URL in its three spellings; anything else is ''
  const { cardFromHref } = withHost.mod
  ok(typeof cardFromHref === 'function', 'the bundle exports cardFromHref')
  eq(cardFromHref('https://crew.example.test/crew?card=t_d8403bb8'), 't_d8403bb8', 'a full https shareable link')
  eq(cardFromHref('http://127.0.0.1:8799/crew?card=t_1&n=5'), 't_1', 'the local service, extra query kept apart')
  eq(cardFromHref('https://h.example:9119/api/plugins/crew?card=t_2'), 't_2', 'a path that ends in /crew')
  eq(cardFromHref('https://h.example/crew/?card=t_3'), 't_3', 'a trailing slash on /crew')
  eq(cardFromHref('/crew?card=t_4'), 't_4', 'path-relative')
  eq(cardFromHref('#/crew?card=t_5&n=1'), 't_5', 'the hash route')
  eq(cardFromHref('https://example.com/checkout?card=t_d8403bb8'), '', 'a card query on another path is no Crew card')
  eq(cardFromHref('https://example.com/crewmate?card=t_6'), '', 'a path merely starting with crew is not /crew')
  eq(cardFromHref('https://h.example/crew?card=a%20b'), '', 'an id outside [A-Za-z0-9_-] is refused')
  eq(cardFromHref('https://h.example/crew'), '', 'no card query')
  eq(cardFromHref('mailto:x@y.z'), '', 'not a web link')
  eq(cardFromHref(''), '', 'empty')

  // --- the card bus: openCardRoute hands the id to a listener and parks it for a page that mounts later
  const { openCardRoute, takePendingCard, onOpenCard } = withHost.mod
  const heard = [], navs = []
  const off = onOpenCard(id => heard.push(id))
  openCardRoute('/crew?card=t_bus1&n=1', p => navs.push(p))
  eq([heard, navs], [['t_bus1'], ['/crew?card=t_bus1&n=1']], 'listeners hear the id, then navigate gets the path')
  eq(takePendingCard(), 't_bus1', 'the id is parked for a page that mounts after the click')
  eq(takePendingCard(), '', 'and taken once')
  off()
  openCardRoute('/crew?card=t_bus2&n=2')
  eq(heard, ['t_bus1'], 'an unsubscribed listener hears nothing')
  takePendingCard()
  openCardRoute('/crew', p => navs.push(p))
  eq([takePendingCard(), navs.at(-1)], ['', '/crew'], 'a path with no card parks nothing but still navigates')

  // --- mount the real page with the capture listener registered; chat lives outside .crew-scope
  const navigated = []
  const page = { current: null }
  const rests = []
  const ctx = {
    registerMany: cs => { page.current = cs[0] },
    rest: async p => { rests.push(p); return p.startsWith('/card/') ? { card_id: p.slice(6).replace(/\.json.*$/, ''), card_status: 'running', title: 'Linked card', nodes: [], situation: {} } : board },
    onDispose: fn => { ctx.disposers.push(fn) },
    disposers: []
  }
  globalThis.__navigated = navigated
  withHost.mod.default.register(ctx)
  const host = document.createElement('div')
  document.body.appendChild(host)
  const root = createRoot(host)
  await React.act(async () => { root.render(page.current.render()) })
  await wait(20)
  ok(host.querySelector('.page-board'), 'the Crew page starts on the board')

  const chat = document.createElement('div')
  chat.className = 'aui-md'
  // static test fixture markup (no untrusted input): what Desktop's markdown renderer makes of the card-open lead
  chat.innerHTML = '<p><strong>Card open</strong> · <a id="tl" href="https://crew.example.test/crew?card=t_new1"><span id="tl-in">t_new1</span></a> · Port</p>' +
    '<a id="other" href="https://example.com/checkout?card=t_new1">Checkout</a>'
  document.body.appendChild(chat)
  // what Desktop's ExternalLink does in its own (bubble) onClick: bail when a capture listener already took the click
  const external = []
  chat.addEventListener('click', e => { if (!e.defaultPrevented) { e.preventDefault(); external.push(e.target.closest('a').getAttribute('href')) } })
  const fire = async (el, init) => {
    const ev = new window.MouseEvent(init.type || 'click', { bubbles: true, cancelable: true, button: 0, ...init })
    await React.act(async () => { el.dispatchEvent(ev) })
    await wait(30)
    return ev
  }

  // modified and non-primary clicks pass through: native browser / Copy Link behaviour is the app's
  rests.length = 0
  for (const [init, what] of [[{ ctrlKey: true }, 'Ctrl-click'], [{ metaKey: true }, 'Cmd-click'], [{ shiftKey: true }, 'Shift-click'],
    [{ altKey: true }, 'Alt-click'], [{ button: 1, type: 'auxclick' }, 'middle-click'], [{ button: 2, type: 'contextmenu' }, 'right-click (Copy Link)']]) {
    const before = navigated.length
    const ev = await fire(document.getElementById('tl-in'), init)
    if (init.type) ok(!ev.defaultPrevented, what + ' is not taken')
    else ok(external.length > 0 && external.at(-1) === 'https://crew.example.test/crew?card=t_new1', what + ' reaches ExternalLink with the full shareable href')
    eq(navigated.length, before, what + ' does not navigate in-app')
  }
  ok(host.querySelector('.page-board') && !rests.some(p => p.startsWith('/card/t_new1')), 'no modified click opened the card in-app')
  eq(document.getElementById('tl').getAttribute('href'), 'https://crew.example.test/crew?card=t_new1', 'the anchor keeps its full shareable href for copying')

  // an unrelated link with a card query is left alone
  external.length = 0
  const evOther = await fire(document.getElementById('other'), {})
  eq([evOther.defaultPrevented, external], [true, ['https://example.com/checkout?card=t_new1']], 'a non-Crew link is not intercepted: ExternalLink handles it')

  // the plain left-click: taken in capture, ExternalLink bails, host.navigate gets the card route, the page opens the card
  external.length = 0
  const ev = await fire(document.getElementById('tl-in'), {})
  ok(ev.defaultPrevented, 'a plain left-click on the ticket link is defaultPrevented')
  eq(external, [], 'ExternalLink saw defaultPrevented and opened no browser')
  ok(/^\/crew\?card=t_new1&n=\d+$/.test(navigated.at(-1) || ''), 'host.navigate got the in-app card route: ' + navigated.at(-1))
  ok(host.querySelector('.page-card') && !host.querySelector('.page-board'), 'the mounted Crew page shows the card page')
  ok(rests.some(p => p.startsWith('/card/t_new1')), 'the page opened that card (fetched /card/t_new1)')

  // a click INSIDE Crew's own page is Crew's business: the listener never touches it
  const inner = document.createElement('a')
  inner.setAttribute('href', 'https://x.example/crew?card=t_inner')
  host.querySelector('.crew-scope').appendChild(inner)
  const before = navigated.length
  const evIn = await fire(inner, {})
  eq([navigated.length, evIn.defaultPrevented], [before, false], 'an anchor inside .crew-scope is left to Crew')
  inner.remove()
  // ...except a markdown block Crew renders (a transcript inside the card page): its ticket links open in-app too
  const md = document.createElement('div')
  md.className = 'stub-md'
  const mdLink = document.createElement('a')
  mdLink.setAttribute('href', 'https://x.example/crew?card=t_md2')
  md.appendChild(mdLink)
  host.querySelector('.crew-scope').appendChild(md)
  const evMd = await fire(mdLink, {})
  ok(evMd.defaultPrevented && /card=t_md2/.test(navigated.at(-1) || ''), 'a ticket link inside a Crew-rendered markdown block opens in-app')
  ok(rests.some(p => p.startsWith('/card/t_md2')), 'and the page switched to that card')
  md.remove()

  await React.act(async () => { root.unmount() })
  host.remove()

  // a card link clicked while the Crew page is not mounted: parked, and the page that mounts next opens it
  await fire(document.getElementById('tl-in'), {})
  const host2 = document.createElement('div')
  document.body.appendChild(host2)
  const root2 = createRoot(host2)
  rests.length = 0
  window.location.hash = ''
  await React.act(async () => { root2.render(page.current.render()) })
  await wait(30)
  ok(host2.querySelector('.page-card') && rests.some(p => p.startsWith('/card/t_new1')), 'a page mounted after the click opens the parked card')
  await React.act(async () => { root2.unmount() })
  host2.remove()

  // a second register (hot reload) keeps ONE listener; disposing the plugin removes it
  withHost.mod.default.register(ctx)
  const n0 = navigated.length
  await fire(document.getElementById('tl-in'), {})
  eq(navigated.length - n0, 1, 'one click, one navigate after a re-register (no duplicate listener)')
  ctx.disposers.splice(0).forEach(d => d())
  external.length = 0
  const n1 = navigated.length
  const evOff = await fire(document.getElementById('tl-in'), {})
  eq([navigated.length - n1, external.length, evOff.defaultPrevented], [0, 1, true], 'after dispose the click is the app\'s again')

  // no host.navigate (a browser, an older shell): nothing is intercepted
  noHost.mod.default.register({ registerMany: () => {}, rest: async () => board })
  external.length = 0
  const evNo = await fire(document.getElementById('tl-in'), {})
  eq(external.length, 1, 'without host.navigate the link opens as a normal link')
  void evNo
  chat.remove()
  window.location.hash = ''
}
