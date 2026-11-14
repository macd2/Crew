![Hermes.Crew](assets/logo.png)

# Hermes.Crew

**You ask once. A coordinator owns the card until its proof passes.**

[![Hermes plugin](https://img.shields.io/badge/Hermes-plugin-3fb950?style=flat-square)](https://github.com/NousResearch/hermes-agent)
[![Version](https://img.shields.io/badge/version-0.10.8-3fb950?style=flat-square)](plugin.yaml)
[![tests](https://github.com/macd2/Crew/actions/workflows/tests.yml/badge.svg)](https://github.com/macd2/Crew/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/badge/website-crew.forgecoreai.com-0a0e14?style=flat-square)](https://crew.forgecoreai.com)
![Kanban](https://img.shields.io/badge/-kanban-161b22?style=flat-square)
![Multi-agent](https://img.shields.io/badge/-multi--agent-161b22?style=flat-square)
![Verified results](https://img.shields.io/badge/-verified%20results-161b22?style=flat-square)
![Self-hosted](https://img.shields.io/badge/-self--hosted-161b22?style=flat-square)

[Website](https://crew.forgecoreai.com) · [Watch the 53 s film](https://crew.forgecoreai.com/#board) · [Install](#install) · [Windows](WINDOWS.md) · [Hermes Desktop](#crew-in-hermes-desktop) · [Commercial](#commercial-services) · [Reference](REFERENCE.md)

---

**The smart kanban replacement for [Hermes Agent](https://github.com/NousResearch/hermes-agent).** Hermes
hides its own Kanban row while Crew is on, and what stands there is a board that finishes its own cards: one
chat message becomes verified work.

```
/crew launch the Pro plan: pricing page, Stripe checkout, launch post and email
```

Crew asks only what it needs to deliver a good result (five questions at most, often none), writes a
**card contract** - goal, artifact, where it lands, *done when*, a **proof command**, a token budget - and
hands the card to a **coordinator** that owns it until the proof command exits 0. You get the verified
result back in the same chat, or one concrete question when it truly needs you.

[![The crew dashboard: a card's graph with its running worker selected and the live transcript](assets/dashboard.webp)](https://crew.forgecoreai.com)

## What's new in 0.10.8

- **The nightly proves what GitHub ships, nothing else.** Parity compares every crew home against the release
  checkout's `origin/main`, and the nightly fetches and fast-forwards that checkout before it installs - an
  unpushed local commit is never treated as a release.
- **Proofs follow Hermes's owner-admission dispatch.** A card's model pin is now checked where Hermes decides the
  worker's model (`build_kanban_policy`), not on the old spawn line, so the pin proof holds on current Hermes and
  still runs on older ones.
- **Fewer false reds.** The situation-box proof waits for the box to fill in instead of reading it once, and the
  intake proof no longer counts a `tool_search` for the clarify tool as research.
- **Tests use real Hermes output.** The installer's fake Hermes must match captured real `hermes config get` output
  (`tests/test_hermes_fake_contract.py`), so a list-of-mappings setting can no longer re-apply on every install.

## What's new in 0.10.7

- **Your role settings survive an update.** Each role's `settings.conf` and `SOUL.md` can be overridden from Crew's
  own templates folder, outside the package, so updating Crew no longer resets your model, provider, extra skills or
  persona. Overrides apply key by key, duplicates are refused, and anything you leave out keeps the shipped value
  (#24, thanks @keyz182).
- **A failed button no longer prints a Python error.** When a dashboard action fails, the page answers with a short,
  stable line and the detail goes to the log. The two test regexps that strip and count `<script>` tags now match any
  case, which clears the repository's four code-scanning alerts.
- **Docs:** a role ships no fallback model, and an owner override may name one.

## What's new in 0.10.6

- **The nightly shim never reinstalls on its own.** It re-installs a release checkout before the proofs only when
  `CREW_RELEASE` names one; the sibling-`release` default is gone, so a catalog or clone install proves the copy it has.
- **The chat ticket-id click is gone.** Crew no longer listens for clicks in Desktop's own chat; the card link
  `<dashboard>/crew?card=<id>` is a plain link that opens the dashboard.

## What's new in 0.10.5

- **One link to a card, and the ticket id in a chat message is that link.** A card now has one shareable address,
  `<dashboard>/crew?card=<id>`, that opens the card on the standalone page, in the Hermes web dashboard's Crew tab and
  in Hermes Desktop. The notifications and endings Crew writes link the ticket id to it (#23, thanks @phuongvm; the
  in-chat click that opened it in-app was removed in 0.10.6).
- **Windows: the right `hermes.exe`.** Crew's own scheduled steps now start Hermes from the checkout's own launcher
  and never from a package-manager venv's `hermes.exe`, which belongs to a build snapshot and registers as a different
  install (#18, thanks @phuongvm).
- **Longer, clearer reports.** A rescope question shows what changed in a long proof command, questions to you carry
  more of the text, the coordinator's reason is labelled after the command, the endings say how far the card got, and a
  multi-line summary keeps its lines (#22, thanks @phuongvm).

## What's new in 0.10.4

- **The board and card pages poll lighter.** Desktop and every dashboard tab ask for the board and the open card every
  2 s, and each answer rebuilt the whole graph, opening a database connection for every query (64 for the board,
  108-118 for a card). A render now shares one read-only connection and closes it when it ends, and repeated
  identical reads within 3 s are served from one build (a write through the dashboard clears the cache). On a
  26-card board a card render went from 467 ms to 242 ms. The connection never outlives the render, so it cannot
  block deleting or replacing the database on Windows (#20, #21, thanks @g0GobliN).

## What's new in 0.10.3

- **Space and Escape stay with the chat.** With a chat beside a crew card (a split tile or a stacked tab), typing a
  space in the chat no longer got swallowed by the card page or the board. The card and board keys now act only
  when the focus is inside crew (issue #19).

## What's new in 0.10.2

- **The board is Crew's.** Positioning, copy only: the README and the site now say what the UI already does -
  Hermes hides its own Kanban row while Crew is on, so Crew is the smart kanban replacement for Hermes, not a
  view on top of it.
- **Parity compares against the release**, not the package working tree, so a dev edit after a release no longer
  reddens the nightly with nothing wrong (10-20 and 10-24 both did). The nightly shim installs the release tree
  first when `CREW_RELEASE` names one (0.10.6: opt-in only).
- **The attention proof waits for the board** instead of reading once, so a slow poll no longer trips "the
  cleared row is gone from the board data too" (it failed 1 run in 6 under load).

## What's new in 0.10.1

- **The installer asks, it never approves.** It no longer writes Hermes's hook allowlist at all (`--approve-hooks` is
  gone): for a profile with a hook waiting it asks (y/N) whether to open that profile's Hermes, so Hermes asks you at
  its own prompt, and a hook whose script changed is revoked first. Answer no, and it prints the commands to run.
- **Desktop "Open chat"** opens the chat through the app's own session (`host.openSession`) rather than a window.
- The README's hook text, the permission proof and the hook-consent tests describe that flow.

## What's new in 0.10.0

- **Native Desktop UI.** Crew is a page of Hermes Desktop itself, not a frame around a web page: board, card page and
  flow graph in the app's colours, light and dark.
- **The Crew flow pane**, following the live card, with a selector when several cards run.
- **A button bar on every card**: Unstuck, Retry, Stop and Open chat, the same commands as the slash commands; **Proof** appears only when the card has a proof question waiting.
- **Chat-style transcripts** in the Desktop card page: lists and code fences keep their shape.
- **One UI in three places.** The browser dashboard, the Hermes web UI tab and Desktop run the same app, built from
  one source (`ui/`).
- Since 0.9.13: the roles use native tools (`crew_verdict`, `crew_progress`, ...) instead of shell lines.

See [Crew in Hermes Desktop](#crew-in-hermes-desktop).

## Why

| | |
|---|---|
| **One ask** | `/crew <ask>` is the only thing you type. Normal chat stays untouched. |
| **Up to six cards in parallel** | One ask fans out into independent cards, one writer each. |
| **Done means proven** | A card cannot be marked done until its proof command passes - enforced by a tool guard, in every profile. |
| **An owner for every card** | The coordinator heals, retries, rescopes or splits a stuck card, and asks you only when it needs you. |
| **Hard budgets** | Every card carries a token budget; a run that reaches it stops instead of burning on. |
| **See everything** | A local dashboard shows every card, run, session, tool call and verdict, live. |
| **Self-hosted** | Runs inside your own Hermes, on your own machine. No telemetry. |

## Commercial Services

Crew is free and open source, Apache-2.0. If you use it in an enterprise and would benefit from
commercial support, additional tooling, or managed model spending, write to
[crew@forgecoreai.com](mailto:crew@forgecoreai.com).

## Install

Requires Hermes Agent **0.21.5 or newer** with the kanban board, and Python 3.11+. The plugin declares
`requires_hermes: ">=0.21.5"`, so an older Hermes refuses to load it instead of failing half-way. From 0.8.0 crew
runs on Hermes's package-manager dependency layout (the gateway's bare interpreter plus a committed venv) as well
as the older in-tree venv; 0.7.x only knew the latter, and a `hermes update` onto the new layout broke its proofs.

```sh
# 1. get the plugin
hermes plugins install macd2/Crew

# 2. set it up for your chat profile (role profiles, the dashboard service)
python3 ~/.hermes/plugins/crew/install.py --profile NAME

# 3. check it
python3 ~/.hermes/plugins/crew/install.py --check --profile NAME
hermes -p NAME plugins doctor crew
```

`NAME` is the profile you chat with (`default` if you do not use profiles). Running the installer twice
changes nothing; `--check` is a dry run that prints exactly what would change. The installer never approves
a shell hook for you and never writes Hermes's hook allowlist: if a profile has a hook waiting, it asks (y/N)
whether to open that profile's Hermes so Hermes itself asks you.

> **On Windows?** Native Windows is supported with [Git for Windows](https://git-scm.com/download/win)
> installed (proofs run in Git Bash). It has no systemd or cron, so the graph-http service and
> `--nightly-proofs` are skipped there. Use WSL if you want both unchanged. See **[WINDOWS.md](WINDOWS.md)**.

### What `install.py` changes

By default:

- **Role profiles.** Creates `crew-coordinator`, `crew-worker`, `crew-content` and `crew-verifier` with
  `hermes profile create --clone-from NAME`. Hermes has no partial clone, so each role profile gets a copy of
  your profile's `config.yaml` (including its `hooks:`), its whole `.env` (provider keys), `SOUL.md`, skills
  and memories (`MEMORY.md`, `USER.md`); Hermes strips the messaging channels. Then, in each role profile:
  - sets the keys from `templates/profiles/<role>/settings.conf` with `hermes config set`. Models are
    Anthropic's, and `model.base_url` is pinned to `https://api.anthropic.com`: to use your own, put the
    keys you change in `<Hermes home>/crew/templates/<role>/settings.conf`, which an update never touches
    (see [templates/README.md](templates/README.md));
  - replaces `SOUL.md` with the role's persona (only while it is still the shipped one);
  - deletes every skill that is not crew's, printing each path. This only happens in a role profile crew
    created (it carries `crew/template-shipped.json`);
  - installs the plugin, skills and roles file, and runs `plugins enable crew --no-allow-tool-override`.
- **Your profile.** Copies the plugin (with its `scripts/`) to `<profile>/plugins/crew/`, the skills to
  `skills/crew/` and the roles file to `roles/crew/`; sets `crew.roles_path` and `crew.source_dir`; records
  the owner profile in `~/.hermes/crew/owner.json`.
- **Other profiles that already have crew.** Each is updated to the same version (plugin, skills, roles), and
  every update is printed. Profiles without crew are not touched.
- **Old copies.** Deletes the crew scripts earlier versions put in `<profile>/scripts/`, only the files crew
  shipped, printing each one, and retires the old self-heal and observer cron jobs.
- **Dashboard.** Writes and starts the user service `crew-graph-http` (`Restart=always`), bound to
  `127.0.0.1:8799` (`--graph-port N`). `--no-service` skips it.

Only when you ask for it:

| Flag | What it adds |
|---|---|
| `--nightly-proofs` | A Hermes cron job at 03:00 that runs the proof suite and speaks only on a failure, plus the shim `<profile>/scripts/crew_proofs_nightly.py` (Hermes cron runs scripts from there only, and runs a `.py` one with Hermes's own interpreter, which the proofs need; an older `crew_proofs.sh` shim is migrated and removed). Output stays local unless `--proofs-deliver TARGET`. |
| `--chat-kanban` | Enables the kanban toolset on the zulip and telegram platforms of your profile. |
| `--telegram-menu` | Puts the crew commands first in your Telegram command menu. |
| `--spill-cap` | Sets `hooks.output_spill.max_chars` on your profile, so the `/crew` intake reads its brief in one tool call. |
| `--publish` | Serves the dashboard on your tailnet with `tailscale serve` (tailnet only, never the internet). Only one tailnet login gets in (`--publish-user LOGIN`, or the tailnet's single human login; otherwise it refuses), plus devices with a tag from `--publish-tag` (a tagged device carries no login). |

The installer reports shell hooks your profiles declare but you have not approved. It never approves them
and never copies one profile's approvals into another. On a terminal it asks per profile, y/N, whether to start
`hermes -p P chat` now: Hermes then asks you about each hook at its own prompt (a hook whose script changed since
you approved it is revoked first with `hermes -p P hooks revoke`), and you leave with `/exit`. Answer no, or run
without a terminal, and it prints the commands instead: review with `hermes -p P hooks list`, confirm at Hermes's
prompt (or type `--accept-hooks` yourself), check with `hermes -p P hooks doctor`.

## Crew in Hermes Desktop

![Crew in Hermes Desktop, dark: the Crew sidebar entry, a card page with its flow graph and button bar, and the Crew flow pane with its live-card selector](assets/desktop-dark.png)

Hermes Desktop gets a **Crew** page in its sidebar, built from the same app as the browser dashboard and drawn with
the app's own colours. It needs no separate server and no systemd, so it works on Windows too.

**What you get**

- **The native board.** Every card by lane, the counts, the notes bell with its acknowledge buttons.
- **The card page with its flow graph.** Steps, findings, proof and verdict, and the graph of the card's runs,
  sessions and subagents, live. No iframe: it is part of the app.
- **The Crew flow pane.** A pane on the right that shows the graph of the card the crew is working on right now and
  follows it from card to card. When several cards run at once the pane header shows a selector (short id and title);
  your pick is kept until that card stops, then the pane falls back to the first live one.
- **The card's button bar.** **Unstuck**, **Retry** and **Stop** act on the card (Stop asks first, in the
  app's own confirm dialog); each is on only when the card's state allows it. **Proof** is drawn only when the card has a
  proof question waiting, and then it is on. **Open chat** opens the coordinator's session in its own window. On the
  board, the cards in the Needs-you lane carry **Unstuck** and **Retry** too (and **Proof** under the same rule); no
  other lane's tiles have buttons.
- **A popup when a card needs you.** When a card newly lands in Needs you, Crew shows a Desktop toast (and the OS
  notification while you are away) with an **Open in Crew** button that opens that card's page. Desktop's own Kanban
  toast, if you enabled the Kanban plugin, still opens the Kanban board; a plugin cannot redirect it.
- **Chat-style transcripts.** A run's own words are drawn by the app's chat renderer: lists, code blocks, links and
  inline code look as they do in a chat.
- **Light and dark follow the app.** Switch the app's mode and Crew switches with it.
- **One Kanban row.** Crew hides the app's Kanban row while it is enabled; the switch in the Crew header brings it back.

**Set it up**

1. Install crew into the profile Desktop starts with, as in [Install](#install) (on Windows see
   [WINDOWS.md](WINDOWS.md)); with one profile that is `default`. Desktop mounts the Crew page's data from the profile it
   was launched with, not the one you switch to inside the app: if you use another profile, either install crew there
   too or start Desktop with the profile crew is in (point `HERMES_HOME` at that profile's folder when you launch it).
   Desktop remembers the profile you last picked in its profile rail and uses it from the next launch, so restart
   Desktop after switching.
2. Enable the plugin: the installer already runs `hermes plugins enable crew`, which puts `crew` in `plugins.enabled`
   of the profile's `config.yaml` (check with `hermes -p NAME plugins list`).
3. In Desktop open **Capabilities > Plugins** and press **Rescan**. Desktop plugins are opt-in, so switch on crew's
   desktop half there too (switching the agent half on also switches its Desktop half on).
4. **Crew** appears in the sidebar.

**If the page says `Crew could not load: 404 Not Found`**, Desktop is running a profile that has no crew (or an
older crew without the Desktop half): the plugin's data routes are mounted from the launch profile only. Install crew
into that profile, or relaunch Desktop with the profile crew is in, then Rescan.

**Setting this up with an agent?** Run `hermes profile list` to see the profiles, then read the Hermes docs on
[Desktop profiles](https://hermes-agent.nousresearch.com/docs/user-guide/desktop#sessions--profiles) and
[profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles).

### Two modes

Crew has one interface and two ways to run it, in plain words:

- **Terminal (no Desktop).** Install as usual and keep the browser dashboard: same URL (`http://127.0.0.1:8799`),
  same `crew-graph-http` unit, same look. What changed is that it now serves one React app instead of three scripts.
- **Hermes Desktop.** The same app, native in the sidebar, with the flow pane and the button bar. It needs no daemon:
  Desktop's own backend serves crew's data.

Both read the same kanban board and the same session store, so a card looks the same in either, and you can use both
at once. The **Hermes web UI** dashboard tab runs the same app too.

## Use

| Command | What it does |
|---|---|
| `/crew <ask>` | The intake: asks what is missing, writes the contract, opens the card(s). |
| *(reply to a crew report)* | Answer the card-ended message crew posts into your chat with "rework it" and the intake runs for a follow-up card, no `/crew` retyped (your next message only, within 30 min). |
| `/crew-status` | Cards in flight, the coordinator's last decision, any question for you. No model call. |
| `/crew-graph <card\|latest>` | One card's flow graph in the terminal (`--watch N`, `--html`). No model call. |
| `/crew-stop [<card>]` | Park one card, or every open crew card: worker killed, card held with its history, nothing archived. `--archive <card>` drops one for good. No model call. |
| `/crew-unstuck <card>` | Put a card the coordinator gave up on, or one you parked with `/crew-stop`, back in the queue (out of triage unchanged, or unblocked). No model call. |
| `/crew-safety [brave\|safe]` | Show or set how careful unattended proof commands are (see below). No model call. |
| `/crew-proof <card> <yes\|brave>` | Answer a card's proof question: `yes` accepts a proposed proof command, `brave` runs a blocked one. No model call. |
| `/crew-diagnose [state]` | Read-only: every card in that state, why it is there and how it would resume. |

Or paste this into an agent and let it set crew up for you:

```
Set up Hermes.Crew for my Hermes profile NAME: from the Hermes.Crew package run python3 install.py --profile NAME,
then hermes -p NAME plugins doctor crew and fix anything it reports. Finish by sending /crew-status in my chat
and tell me what it answered.
```

## The roles' tools

The roles do not shell out to `crew_card.py`. The plugin registers six tools in the `crew` toolset and the role
skills name them: `crew_verdict` (run the card's confirmed proof), `crew_progress` (mark a unit pass or fail),
`crew_proof_check` (screen a proof command and read the safety mode), `crew_lesson` (record a lesson), `crew_plan`
(open a parent with children) and `crew_diagnose` (the read-only list of stuck cards). `watch` and the owner's CLI
stay as they are. The idea of native tools instead of shell lines came from @phuongvm (PR #16).

## Self-improvement

What agents learn on a card lives in `<base home>/crew/lessons.md`, one dated line per lesson with the roles it
applies to. It is never shipped and the installer and `crew_parity_check` leave it alone. Agents record a lesson
with the `crew_lesson` tool (`role`, `text`; for example role `content,verifier`)
(identical lessons are stored once; the newest 50 entries / 8 KB are kept); editing a crew skill with
`skill_manage` is refused in every profile, because an installed skill is overwritten by the next install.
The plugin adds a role's lessons (and the `all` ones) to that role's turn, and the `all` ones to `/crew`'s intake.
An agent may not write `--role all` lessons (that is the owner's intake channel); it tags its own role and the
owner promotes it. To make a lesson permanent, move it into the matching `skills/*/SKILL.md` in a release and delete it from the file.

## Proof safety

A proof command is a shell command, and crew runs it unattended. When the intake shows you the proof, it asks
once:

```
Proof commands run unattended. How careful should crew be?

  1) Hermes safety (default): a flagged command (rm, chmod, a download piped into a shell, ...)
     stops the card and asks you.
  2) Be brave 🫡 (YOLO): nothing stops a proof except Hermes's hardline list
     (wiping the root, formatting a disk, fork bombs). Crew will happily rm what the proof says.
     Your call, your disk.
```

- **The command you confirm is the only one that runs.** It is saved when the card opens. Editing the card,
  or a coordinator rescope, cannot change it; a new proof needs your yes again.
- **Hermes decides what is dangerous.** Crew uses Hermes's own checks: the hardline list and your
  `approvals.deny` rules always block; in safe mode Hermes's dangerous-command and tirith checks block too.
  If the proof you are confirming would be flagged, the card opens in safe mode and the coordinator asks you;
  answer `/crew-proof <card> brave` to run it for that card. The intake's own `Proof mode` / `Proof approved`
  body lines are ignored for a flagged command, so a model cannot approve it on your behalf.
- **Proofs run with a clean environment.** Provider and tool keys are stripped, the same way Hermes's
  terminal tool does it.
- **`/crew-safety brave` stops the question for good.** It sets Hermes's `approvals.mode: off` in the crew
  role profiles, which also lets the workers' own terminal commands run unprompted. `/crew-safety safe` puts
  back the value each profile had before.

Proof scripts are model-written (by the verifier role, never by the writer). The command that runs them is
owner-confirmed; the script runs with a scrubbed environment, is bound by hash after its first run, and changes only
through a coordinator decision carried out by the verifier. Hermes's command checks see the command, not the script's
content.

## Reports

Crew reports back into the chat a card came from, through Hermes's own `hermes send` (any platform Hermes is
connected to), and only when there is something to say: one report when a card is done, one message per new
question for you, one line if a card is abandoned. Blocks, retries and heals the coordinator is handling stay
silent.

## How a card travels

```
you ──/crew──▶ intake ──contract──▶ coordinator ──▶ writer (worker | content) ──▶ proof ──▶ verifier ──▶ you
                (asks what is        (owns the card,    (one per card,            (exit 0 is    (runs the proof
                 missing, once)       every stop gets    inside the scope)         the only      itself, never
                                      one decision)                                pass)         trusts a summary)
```

The full design - the contract fields, the close rule, verification modes, the coordinator's decisions,
the dashboard and the role profiles - is in [REFERENCE.md](REFERENCE.md).

## Configuration

Everything works with no configuration. Optional environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `CREW_OWNER_PROFILE` | the profile `install.py` was run for | the chat profile cards are opened from and reported to |
| `CREW_DASHBOARD_URL` | `http://127.0.0.1:8799` (or the `--publish` URL) | the board link used in messages |

## Uninstall

```sh
hermes plugins disable crew && hermes plugins remove crew
systemctl --user disable --now crew-graph-http.service
```

The role profiles stay until you remove them (`hermes profile delete crew-worker`, ...). With
`--nightly-proofs`, also remove the cron job (`hermes cron list`, `hermes cron remove <id>`) and
`<profile>/scripts/crew_proofs_nightly.py`.

## Contributing

Pull requests run the test suite in GitHub Actions (Python 3.11 and 3.12). Please keep `python -m pytest tests -q` green; a first-time contributor's run starts after a maintainer approves it.

The interface lives in `ui/`: TSX source, built with esbuild into two generated files that are committed, `desktop/plugin.js`
(Hermes Desktop) and `scripts/crew_dashboard/app.js` (the browser dashboard and the Hermes web UI tab). Never edit
those two by hand. After changing `ui/src`, run `npm ci --prefix ui` once, then `node ui/build.mjs` to regenerate them;
`node ui/build.mjs --check` fails when a generated file is stale (the plugin version from `plugin.yaml` is embedded, so a version bump needs a rebuild), and it runs in CI and in the publish gate (the old
`board.js`, `card.js` and `crew.css` are gone). `ui/node_modules/.bin/tsc -p ui` type-checks the source.

## License

[Apache-2.0](LICENSE) © macd2
