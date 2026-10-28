import { useEffect, useState } from 'react'
import * as sdk from '@hermes/plugin-sdk'
import { useTheme } from '@hermes/plugin-sdk'
import type { CrewApi } from '../api'
import { crewVarsFromTheme } from '../theme'
import { cardFromHash, cardFromSearch } from '../open-card'
import { setCardPageOpen } from '../card-open'
import type { Route } from '../route'
import { Board } from './Board'
import { CardPage } from './CardPage'
import { Splash } from './Splash'

let splashShown = false

// Desktop page root (fills its route area whatever the parent is: a sized block, or a flex row or column; the splash
// overlay is absolute inset:0 on it): puts the host theme on the --crew-* variables, then the shared board or card page. Navigation is
// state (Desktop owns the address bar): a tile opens its card, the card's back button returns to the board.
export function CrewPage({ api }: { api: CrewApi }) {
  const { theme, renderedMode } = useTheme()
  const [route, setRoute] = useState<Route>({ page: 'board', all: false })
  // A link from outside opens that card: the blocked-card toast ("#/crew?card=<id>") on arrival and while the page is
  // open; a shareable card link ("<dashboard>/crew?card=<id>", crew_card.card_url) on arrival.
  useEffect(() => {
    const go = () => { const id = cardFromHash(window.location.hash); if (id) setRoute({ page: 'card', id }) }
    const shared = cardFromSearch(window.location.search)
    if (shared) setRoute({ page: 'card', id: shared })
    go()
    window.addEventListener('hashchange', go)
    return () => window.removeEventListener('hashchange', go)
  }, [])
  const back = () => setRoute({ page: 'board', all: false })
  // Desktop opens a chat through the plugin SDK's host contract: host.openSession(session, { profile }).
  const host = sdk.host
  const openSession = host?.openSession
  const openChat = typeof openSession === 'function'
    ? (profile: string, session: string) => { void openSession.call(host, session, { profile }) }
    : undefined
  // Once per app session: the flag lives in this module, so it survives the page remounting on every route change
  // (Desktop unmounts /crew when you leave it) and resets when the app restarts. It is set in an effect, not in the
  // initializer, so a double-invoked initializer cannot swallow the splash.
  const [splash] = useState(() => !splashShown)
  useEffect(() => { splashShown = true }, [])
  const card = route.page === 'card'
  // the flow pane steps aside while the card page shows the full flow; leaving /crew unmounts this, which clears it
  useEffect(() => { setCardPageOpen(card); return () => setCardPageOpen(false) }, [card])
  return (
    <div
      className="crew-scope"
      style={{ ...crewVarsFromTheme(theme, renderedMode), background: 'var(--crew-bg)', color: 'var(--crew-fg)', height: '100%', minHeight: '100%', width: '100%', minWidth: 0, flex: '1 1 auto', alignSelf: 'stretch', boxSizing: 'border-box', position: 'relative', overflow: card ? 'hidden' : 'auto' }}
    >
      {splash ? <Splash api={api} /> : null}
      {route.page === 'card'
        ? <CardPage api={api} id={route.id} onBack={back} openChat={openChat} />
        : <Board api={api} onOpenCard={id => setRoute({ page: 'card', id })} home={back} />}
    </div>
  )
}
