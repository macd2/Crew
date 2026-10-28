import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { fetchApi, type CrewApi } from './api'
import { Board } from './components/Board'
import { CardPage } from './components/CardPage'
import type { OpenChat } from './components/TopArea'
import { hrefFor, parseLocation, type Route } from './route'
import { cardFromSearch } from './open-card'

// How a host page wires the app in. The served shell passes nothing (same origin, the address bar is the route).
// The Hermes web dashboard tab passes `base` (its plugin API prefix), the SDK's authed `fetch` and an `openChat`.
export interface MountOptions {
  base?: string
  fetch?: typeof fetch
  openChat?: OpenChat
}

// An exported card file (`/crew-graph --html`) carries the card it shows, so it needs no server.
function snapshotApi(snap: any): CrewApi {
  return {
    get: async path => {
      if (path === '/card/' + encodeURIComponent(snap.card_id) + '.json') return snap
      throw new Error(path + ': this file shows one card as it was when it was written')
    },
    post: async () => ({ ok: false, status: 405, text: 'this file is a snapshot\n' }) as any
  }
}

// Terminal mode: the served page has <div id="crew-app">. The route comes from location.pathname; moving between the
// board and a card pushes history, so the back button and a reload land where the owner was. Inside a host page
// (`base` set) the address bar belongs to the host, so the route is state only. A snapshot file shows its one card.
function App({ opts }: { opts: MountOptions }) {
  const snap = (window as any).__CREW_SNAPSHOT
  const hosted = !!opts.base
  const api = useMemo(() => snap ? snapshotApi(snap) : fetchApi(opts.base || '', opts.fetch, !hosted), [snap, opts.base, opts.fetch, hosted])
  const start = (): Route => {
    if (snap) return { page: 'card', id: snap.card_id }
    if (!hosted) return parseLocation(window.location.pathname, window.location.search)
    // hosted: a shareable card link to the tab ("<dashboard>/crew?card=<id>", crew_card.card_url) opens that card
    const shared = cardFromSearch(window.location.search)
    return shared ? { page: 'card', id: shared } : { page: 'board', all: false }
  }
  const [route, setRoute] = useState<Route>(start)
  useEffect(() => {
    if (snap || hosted) return
    const pop = () => setRoute(parseLocation(window.location.pathname, window.location.search))
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [snap, hosted])
  const go = (r: Route) => {
    if (snap) return
    if (!hosted) try { window.history.pushState(null, '', hrefFor(r)) } catch { /* a sandboxed page keeps the route in state only */ }
    setRoute(r)
  }
  const home = () => go({ page: 'board', all: false })
  const openChat = opts.openChat ?? (typeof (window as any).__crewOpenChat === 'function'
    ? (profile: string, session: string) => (window as any).__crewOpenChat(profile, session) : undefined)
  return route.page === 'card'
    ? <CardPage api={api} id={route.id} onBack={home} openChat={openChat} hash={!hosted && !snap} />
    : <Board api={api} onOpenCard={id => go({ page: 'card', id })} home={home}
        flags={hosted ? { all: false } : { all: route.all, ...(route.older ? { older: true } : {}) }} />
}

// Mounts the app into `el` and returns the function that removes it again (the tab calls it when its page closes).
export function mount(el: HTMLElement, opts: MountOptions = {}): () => void {
  const root = createRoot(el)
  root.render(<App opts={opts} />)
  return () => root.unmount()
}

;(window as any).__crewMount = mount
const el = document.getElementById('crew-app')
if (el && !el.hasAttribute('data-manual')) {
  el.setAttribute('data-crew-shell', '')
  mount(el, { base: el.getAttribute('data-base') || '' })
}
