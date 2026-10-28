import { useMemo, useState, type ReactNode } from 'react'
import * as sdk from '@hermes/plugin-sdk'
import { PANES_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA, useTheme } from '@hermes/plugin-sdk'
import { restApi, type CrewApi, type RestCtx } from './api'
import type { Board } from './types'
import { blockedWatch } from './blocked-watch'
import { CrewPage } from './components/CrewPage'
import { FlowPane } from './components/FlowPane'
import { CrewHostContext, type CrewHost, type KanbanRow } from './host'
import { CREW_ROUTE, cardFromHref, cardLink, openCardRoute } from './open-card'
import { crewVarsFromTheme } from './theme'

export { cardFromHref, onOpenCard, openCardRoute, takePendingCard } from './open-card'

// Every in-app open of a card goes through the card bus first (open-card.openCardRoute), then Desktop's router.
const hostNavigate = (path: string) => { openCardRoute(path, p => sdk.host?.navigate?.(p)) }

function Pane({ api }: { api: ReturnType<typeof restApi> }) {
  const { theme, renderedMode } = useTheme()
  return (
    <div style={{ ...crewVarsFromTheme(theme, renderedMode), background: 'var(--crew-bg)', color: 'var(--crew-fg)', height: '100%' }}>
      <FlowPane api={api} navigate={hostNavigate} cardLink={cardLink} boardLink={CREW_ROUTE} />
    </div>
  )
}

interface Ask { title: string; body: string; done(ok: boolean): void }

// What only Desktop can bring to the shared components (host.ts): the app's own markdown renderer, Button and
// ConfirmDialog, each feature-detected (an older shell lacks some; the page then falls back to what the browser draws).
// MessageTextContent is the chat's own renderer (the same Streamdown pipeline: code cards, lists, links, inline code);
// bare Streamdown is the fallback. media={false}: a transcript is not a chat turn, a MEDIA: line stays prose.
function Host({ api, kanban, children }: { api: CrewApi; kanban: KanbanRow | null; children: ReactNode }) {
  const [ask, setAsk] = useState<Ask | null>(null)
  const [showKanban, setShowKanban] = useState(kanban ? kanban.show : false)   // the switch re-renders from this
  const host = useMemo<CrewHost>(() => {
    const h: CrewHost = {}
    const Md = sdk.MessageTextContent, Sd = sdk.Streamdown
    if (Md) h.renderMarkdown = text => <Md text={text} media={false} />
    else if (Sd) h.renderMarkdown = text => <Sd>{text}</Sd>
    if (sdk.Button && sdk.ConfirmDialog)
      h.actions = {
        // the route is POST /action/<name> {card, ...extra}; the backend allowlists the names again
        run: (name, card, extra) => api.post('/action/' + name, { ...extra, card }),
        confirm: (title, body) => new Promise<boolean>(resolve => setAsk({ title, body, done: resolve })),
        Button: sdk.Button as NonNullable<CrewHost['actions']>['Button']
      }
    if (kanban) h.kanbanRow = { show: showKanban, set: v => { kanban.set(v); setShowKanban(v) } }
    return h
  }, [api, kanban, showKanban])
  const Dialog = sdk.ConfirmDialog
  const close = (ok: boolean) => { if (ask) ask.done(ok); setAsk(null) }
  return (
    <CrewHostContext.Provider value={host}>
      {children}
      {Dialog && ask ? (
        <Dialog open title={ask.title} description={ask.body} confirmLabel="Confirm" destructive onClose={() => close(false)} onConfirm={() => close(true)} />
      ) : null}
    </CrewHostContext.Provider>
  )
}

// The app's own "Kanban" sidebar row is the in-tree kanban plugin's nav contribution: plugin id 'kanban' + register id
// 'nav' (apps/desktop/src/plugins/kanban/plugin.tsx), which ctx.register namespaces to 'kanban:nav'. Hiding it is a
// sidebarNav.prefs contribution (store/sidebar-nav.ts), which the loader drops with Crew when Crew is disabled, so the row
// comes back by itself. The owner's choice persists in ctx.storage (default: hide) and is re-contributed on register.
export const KANBAN_ROW_ID = 'kanban:nav'
const HIDE_KEY = 'hideKanbanRow'   // true (the default) = Crew hides the row; false = the owner brought it back

type PrefsCtx = {
  register?(c: unknown): (() => void) | void
  storage?: { get<T>(key: string, fallback: T): T; set(key: string, value: unknown): void }
}

// Returns null on a shell without the sidebar-prefs area or without ctx.register/ctx.storage (the row then stays).
export function kanbanRowSwitch(ctx: PrefsCtx): KanbanRow | null {
  const area = sdk.SIDEBAR_NAV_PREFS_AREA
  if (!area || typeof ctx.register !== 'function') return null
  let drop: (() => void) | void
  const apply = (show: boolean) => {
    if (drop) { drop(); drop = undefined }
    if (!show) drop = ctx.register!({ id: 'nav-prefs', area, data: { hide: [KANBAN_ROW_ID] } })
  }
  const row: KanbanRow = {
    show: ctx.storage ? ctx.storage.get<boolean>(HIDE_KEY, true) === false : false,
    set(show) {
      row.show = show
      try { ctx.storage?.set(HIDE_KEY, !show) } catch { /* storage full or blocked: the switch still works this session */ }
      apply(show)
    }
  }
  apply(row.show)
  return row
}

const WATCH_MS = 5000

// A card newly blocked (Needs you): Crew's own toast with an "Open in Crew" button, plus the OS notification when the owner
// is away (Desktop fires ctx.os.notify only then). Hermes Desktop's stock Kanban toast cannot be redirected by a plugin
// (docs/desktop/v2/build.md "Blocked-card popup"), so this one stands next to it. Each door is feature-detected.
function watchBlocked(ctx: WatchCtx, api: CrewApi) {
  const host = sdk.host
  if (!host?.notify || typeof ctx.setInterval !== 'function') return
  const tick = blockedWatch(() => api.get<Board>('/board.json'), t => {
    host.notify!({
      id: 'crew-blocked-' + t.id,
      kind: 'warning',
      title: 'Crew: a card needs you',
      message: t.message,
      detail: t.detail,
      action: { label: 'Open in Crew', onClick: () => hostNavigate(cardLink(t.id)) }
    })
    try { ctx.os?.notify({ title: 'Crew: a card needs you', body: t.message + '\n' + t.detail }) } catch { /* no OS door: the toast stands */ }
  })
  void tick()
  ctx.setInterval(() => { void tick() }, WATCH_MS)
}

// Shareable ticket links in chat ("[t_x](<dashboard>/crew?card=t_x)", crew_card.card_md_link) open in-app. Desktop's
// chat renders an http(s) link as ExternalLink, whose onClick returns early when the event is already defaultPrevented
// (apps/desktop/src/lib/external-link.tsx); this capture-phase listener on the document runs before it, takes only an
// unmodified primary click on a Crew card link, and routes it through the card bus to the Crew tab. Ctrl/Cmd/Shift/Alt,
// middle and right clicks (Copy Link) stay the app's, and so does any link that is not a Crew card. Links inside Crew's
// own page are Crew's (its board and card controls), except a markdown block it renders (a transcript).
const CARD_LINKS = '__crewCardLinks'   // the live listener's remover, on the document: a hot reload re-imports this module
const MD_BLOCK = '.aui-md, .stub-md, .md'

export function watchCardLinks(doc: Document = document): () => void {
  const slot = doc as unknown as Record<string, (() => void) | undefined>
  slot[CARD_LINKS]?.()
  const onClick = (e: MouseEvent) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    const navigate = sdk.host?.navigate
    if (typeof navigate !== 'function') return
    const t = e.target as Element | null
    const a = t && typeof t.closest === 'function' ? t.closest('a[href]') : null
    if (!a) return
    if (a.closest('.crew-scope') && !a.closest(MD_BLOCK)) return
    const id = cardFromHref(a.getAttribute('href') || '')
    if (!id) return
    e.preventDefault()
    openCardRoute(cardLink(id), p => sdk.host?.navigate?.(p))
  }
  doc.addEventListener('click', onClick, true)
  const off = () => {
    doc.removeEventListener('click', onClick, true)
    if (slot[CARD_LINKS] === off) slot[CARD_LINKS] = undefined
  }
  slot[CARD_LINKS] = off
  return off
}

// Hermes Desktop loads the generated desktop/plugin.js: a page at /crew, a sidebar row, and the right-hand flow pane.
// hideOnly keeps a close verb off the pane (closing the only plugin pane disables the plugin; track-model.ts:76-80).
type WatchCtx = {
  setInterval?(fn: () => void, ms: number): () => void
  onDispose?(fn: () => void): void
  os?: { notify(n: { title: string; body: string }): unknown }
}

export default {
  id: 'crew',
  name: 'Crew',
  register(ctx: RestCtx & PrefsCtx & WatchCtx & { registerMany(items: unknown[]): void }) {
    const api = restApi(ctx)
    const kanban = kanbanRowSwitch(ctx)
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/crew' }, render: () => <Host api={api} kanban={kanban}><CrewPage api={api} /></Host> },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/crew', label: 'Crew', codicon: 'organization' } },
      {
        id: 'flow',
        area: PANES_AREA,
        title: 'Crew flow',
        data: { placement: 'right', width: '260px', hideOnly: true, collapsible: true },
        render: () => <Pane api={api} />
      }
    ])
    watchBlocked(ctx, api)
    if (typeof sdk.host?.navigate === 'function' && typeof document !== 'undefined') {
      const off = watchCardLinks(document)
      if (typeof ctx.onDispose === 'function') ctx.onDispose(off)
    }
  }
}
