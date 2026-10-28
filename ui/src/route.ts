// The browser shell's routes, by location.pathname: "/" is the board (?all=1 shows every lane, ?older=1 the older done
// cards), "/crew?card=<id>" a card (the link crew sends out, crew_card.card_url); "/card/<id>" is the older card address.
export type Route = { page: 'board'; all: boolean; older?: boolean } | { page: 'card'; id: string }

export function parseLocation(pathname: string, search: string): Route {
  const m = /^\/card\/([A-Za-z0-9_-]+)\/?$/.exec(pathname)
  if (m) return { page: 'card', id: m[1] }
  if (/^\/crew\/?$/.test(pathname)) {
    const id = new URLSearchParams((search || '').replace(/^\?/, '')).get('card') || ''
    if (/^[A-Za-z0-9_-]+$/.test(id)) return { page: 'card', id }
  }
  return { page: 'board', all: /[?&]all=1/.test(search), ...(/[?&]older=1/.test(search) ? { older: true } : {}) }
}
export function hrefFor(r: Route): string {
  if (r.page === 'card') return '/card/' + r.id
  const q = [r.all ? 'all=1' : '', r.older ? 'older=1' : ''].filter(Boolean).join('&')
  return q ? '/?' + q : '/'
}
