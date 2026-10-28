// Opening a card from outside the page (the blocked-card toast): Desktop's router owns the address, so the card id rides
// the route's query, "#/crew?card=<id>". A fresh stamp per link makes a second link to the same card a changed hash, so
// the page sees it again after the owner went back to the board.
export const CREW_ROUTE = '/crew'

export const cardLink = (id: string, stamp: number = Date.now()): string =>
  CREW_ROUTE + '?card=' + encodeURIComponent(id) + '&n=' + stamp

const CARD_ID = /^[A-Za-z0-9_-]+$/

// The card id of a location hash ("#/crew?card=t_x&n=1"), or '' when the hash opens no card.
export function cardFromHash(hash: string): string {
  const m = /^#?\/crew\?(.*)$/.exec(hash || '')
  const id = m ? new URLSearchParams(m[1]).get('card') || '' : ''
  return CARD_ID.test(id) ? id : ''
}

// The card id of a location query ("?card=t_x"), or '' when the query opens no card: what a freshly loaded shareable
// card link ("<dashboard>/crew?card=<id>", crew_card.card_url) carries when it lands on a hosted Crew tab.
export function cardFromSearch(search: string): string {
  const id = new URLSearchParams((search || '').replace(/^\?/, '')).get('card') || ''
  return CARD_ID.test(id) ? id : ''
}

// The card id of any link that is a shareable Crew card link, or '' when it is not one: what a chat message's
// "[<id>](<dashboard>/crew?card=<id>)" (crew_card.card_md_link) renders to. A full http(s) URL, a path-relative
// "/crew?card=<id>" or the hash route "#/crew?card=<id>"; the path must BE the Crew tab ("/crew", or a mount ending in
// "/crew", a trailing slash allowed) so another site's "?card=" is never taken for a Crew card.
export function cardFromHref(href: string): string {
  const raw = (href || '').trim()
  if (!raw) return ''
  if (raw.startsWith('#')) return cardFromHash(raw)
  let url: URL
  try { url = new URL(raw, 'http://crew.invalid') } catch { return '' }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return ''
  const p = url.pathname.replace(/\/+$/, '')
  if (p !== CREW_ROUTE && !p.endsWith(CREW_ROUTE)) return ''
  return cardFromSearch(url.search)
}

// The card bus: how a click outside the page (a chat link, the toast, the flow pane) reaches the Crew page without the
// address bar. openCardRoute tells every mounted page (onOpenCard) and parks the id for a page that mounts later
// (takePendingCard: a Crew tab Desktop opens only now), then hands the route to the host router.
let pendingCard = ''
const openListeners = new Set<(id: string) => void>()

export function openCardRoute(path: string, navigate?: (p: string) => void): void {
  const id = cardFromHash(path) || cardFromHref(path)
  if (id) {
    pendingCard = id
    openListeners.forEach(fn => { try { fn(id) } catch { /* one bad listener must not stop the rest */ } })
  }
  navigate?.(path)
}

export function takePendingCard(): string {
  const id = pendingCard
  pendingCard = ''
  return id
}

export function onOpenCard(fn: (id: string) => void): () => void {
  openListeners.add(fn)
  return () => { openListeners.delete(fn) }
}
