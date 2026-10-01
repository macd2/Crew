# crew - reference

**Purpose:** the crew system for the kanban board. You type the ask, the coordinator turns it into
a card contract ("Done when:", proof command, token budget, role) - or asks you what is missing and
opens nothing. Then exactly one writer per card, an independent verifier profile that runs the proof
itself. There is no
mode switch: `/crew <ask>` is always available and normal chat stays untouched otherwise.

## Fresh install (3 commands)

```sh
# 1. install into a profile (copies plugin, scripts, roles, enables the plugin,
#    sets config, writes the feed unit + the graph http unit, retires the old heal and observer crons)
python3 install.py --profile NAME

# 2. publish the live graph over the tailnet (adds an https mapping for this node's MagicDNS name)
python3 install.py --profile NAME --publish

# 3. verify it (run from any shell; prints a readiness report)
hermes -p NAME plugins doctor crew
```

The graph service listens on `http://127.0.0.1:8799/` (change with `--graph-port`); `--publish`
maps it to `https://<node>.<tailnet>.ts.net:8445/` (change with `--https-port`). Take the mapping
down again with `tailscale serve --https=8445 off`.

Run from anywhere inside this repo checkout. Running it twice is safe: every step is idempotent
and an existing plugin dir is backed up to `<profile>/backups/crew-<stamp>/` before it is replaced.

## What `--check` does

`python3 install.py --check --profile NAME` changes nothing. It compares the profile against this
package and prints exactly what would change (including the feed unit content), then exits 0 when
the install is complete and 1 when something is missing or a role profile's first-call prompt is over
`prompt_budget_tokens`; it also prints each role profile's skills size and measured first call. Safe to
run at any time.

## Flags

- `--profile NAME`  target profile (default: `HERMES_HOME`, then `~/.hermes`)
- `--check`         dry run; change nothing, exit 0/1
- `--no-service`    do not write/enable the `kanban-zulip-feed.service` and `crew-graph-http.service` user units
- `--no-cron`       do not register the nightly proofs cron or retire the old heal and observer crons
- `--graph-port N`  local port for the graph http service (default 8799)
- `--https-port N`  tailnet https port used by `--publish` (default 8445)
- `--publish`       publish the graph over the tailnet with `tailscale serve`
- `--no-profiles`   do not create/update the role profiles from `templates/`
- `--profile-prefix P`  name prefix for the role profiles (default `crew-`, so `crew-worker`)

## Commands

Five entries. `/crew` and `/crew-diagnose` are agent turns (the `crew` and `crew-diagnose` skills): a plugin
command's handler can only return text and cannot start a turn, so a pass that needs the model is a
skill. `/crew-status`, `/crew-graph` and `/crew-stop` are plugin commands, deterministic and free of any model
call: the option is in the command name, so `/help` and the platform command menus list exactly these five.
Everything else the owner once typed is gone: the coordinator loop heals, retries and asks, and the install
and role checks are `python3 install.py --check [--profile NAME]` (`hermes plugins doctor crew` only validates
that the plugin loads and registers; it reports nothing about roles, crons or profile drift).

- `/crew <ask>`            coordinator intake: critical check, the questions in one `clarify` form (up
                           to five, recommended option first; prose only when no UI), no card opened
                           until every field is the owner's own. The turn opens a 30-minute intake
                           window on that session, so the owner's answer turn opens the card without
                           a second `/crew`; the window closes on the first card out of it. The card is
                           opened with the kernel's `kanban_create` tool (the installer turns the kanban
                           toolset on for the chat platforms); a pre_tool_call guard refuses it outside a
                           `/crew` turn or an incomplete contract, rebuilds the body (Coordinator, Origin,
                           budget floor, assignee, skill, route pin) and a post_tool_call hook records the
                           origin, the brief, the units and the route. The turn ends at the card id;
                           the coordinator loop owns the card and the feed reports its ending
- `/crew-status`           the crew cards in flight (newest eight), each as Title / ID / status / assignee,
                           the coordinator's last decision, and `Needs you: <question>` when the card
                           is blocked on an `ask_owner` decision
- `/crew-graph <card id|latest> [--watch N | --html [PATH]]`  one card's flow graph (layered box
                           nodes); `--watch N` renders two frames N seconds apart, `--html [PATH]` writes
                           the self-contained HTML plus its JSON and prints the absolute paths
- `/crew-stop [<card id>] [--dry-run]`  stop one card, or every open card, and keep it down: kill each
                           live run's worker process, close the session row it left open, archive the
                           card. A bare `stop` does the whole board; `--dry-run` only reports. The open
                           cards linked to the one it stopped are named, never followed silently
- `/crew-diagnose [state]`  the read-only pass (a skill, so it runs in this session's own turn): every
                           card sitting in that state (`blocked` when none is named) with its id, kind,
                           wait and reason, then how each would resume and who takes that step. It
                           diagnoses only - no retry, no unblock, no stop, no comment, no card

Why two names: a plugin slash command is always dispatched before skills and its handler can only
return text (it cannot start an agent turn), so the plugin registers `crew-<option>` and never
`crew`. The intake needs an agent turn, so it is a skill.

## Flow graph
- The step lines under a card are a six-line terminal window: a new line slides in at the bottom, the oldest slides out, and a tool call in flight ticks a stopwatch on its chip
- An edge into a node that is working carries a dot travelling along the path, over a dashed flow line; it settles to a plain line when the node finishes

`/crew graph` projects one card into a live flow graph modelled on zoetrope: one node per card,
worker run, worker session and subagent session, edges parent -> child, node status read from
colour alone (green alive, gold done, red failed), Sugiyama layered layout, steps in timestamp
order. It reads the shared kanban board (`kanban.db`) and the per-profile session store
(`state.db`, `sessions` + `messages`), both read-only; the worker session is the card's
`tasks.session_id` when set, else matched by run time window. Run the script directly for the
extra modes: `python3 scripts/crew_graph.py --card ID [--watch N|--json PATH|--html PATH]`.
Always-on: `crew_graph_serve.py` (unit `crew-graph-http.service`) serves the index at `/`,
the live page at `/card/<id>`, its data at `/card/<id>.json` and `/healthz`, rebuild per request.

## Roles in the graph

Every node carries the role doing the work. The card node is the coordinator; run, session and
subagent nodes carry the card's writer role, read from the `Role:` line of the card contract
(the intake's `Role:` row is worker or content). Each run of `crew_card.py verdict`
appends a verdict line (`by`, `run_id`, PASS only on rc 0) to `$HERMES_HOME/crew/verdicts/<card>.jsonl`,
the only verdict record; the verifier node and its chip read the newest line since the card's newest claim.
`kanban_complete` on a crew card is refused, in every profile, unless the card's proof command has a PASS
line there and no check failed after it (`crew_card.close_check`). "The card's proof command" is the one
snapshotted in the card's `origin` event when it opened (or the one an applied coordinator `rescope` set), so
a rewritten `proof command:` line can never produce a PASS. The `Verify:` contract line picks who runs it:
`proof` (default when a proof command is named: the writer runs `crew_card.py verdict` and closes the card, no
verifier session, `kanban_request_review` is refused) or `independent` (the writer requests review, the card's
model pin is swapped for the router's `review` pick, the verifier runs the proof plus one extra check and
closes it). Either way the coordinator loop re-runs the proof once after the card is done (`by=coordinator`,
an `audit` decision); a FAIL comments on the done card and opens one follow-up card under it. The owner's override is
`hermes kanban complete --force` from the CLI, which the coordinator loop records as an `owner_close`
decision. Two failed verifications go back to the writer (`request-changes`) or block the card as
`transient`; the coordinator decides, the owner is not asked. The page draws a
role roster on the left (click to focus), role badges and borders on cards, tool-call chips
(`write_file x3`, yellow pending, green ok, red failed), green edges into running nodes, wheel
zoom with a status-block view when zoomed out, a minimap, and `f` fit, `0` reset, `F` follow.

## Role profiles

`install.py` creates one profile per role from `templates/profiles/<role>/` (see
`templates/README.md`): `crew-coordinator`, `crew-worker`, `crew-content`, `crew-verifier`. Each gets the persona (`SOUL.md`), the model for the role, the toolsets the role
has (`platform_toolsets.cli`: a kanban worker is a `chat` run, so this list is exactly its tools) and
must not have, its own copy of the plugin, scripts and roles file, and the plugin enabled.
A file you edit in a profile is never overwritten: the installer records the hash of what it
shipped and only replaces a file still equal to that record.

A role profile is slim. `hermes profile create --clone-from` copies the installing profile's whole
skills tree (47 MB here); the installer then cuts `<profile>/skills/` down to `skills/crew/` (the role
skills this package ships) plus what the role's `settings.conf` names in `skills_extra = [category/skill]`
(paths under the installing profile's skills dir), and writes `.no-bundled-skills` so `hermes update`
does not re-seed the rest. A role with no `skills` toolset gets no skills index in its system prompt
either (`agent/system_prompt.py` adds it only when a skills tool exists). `install.py --check` prints,
per role profile, the skills size and the first-call prompt measured from the newest kanban sessions in
that profile's `state.db` (the smallest per-call average of input + cache read + cache write, an upper
bound on the first call), and fails when it is above `prompt_budget_tokens` in `roles/roles.json`.
The installing profile's own skills are never touched.

`crew.role` is what activates the guards: a per-card token budget hard stop, an iteration cap per run
(`agent.max_turns` in the role's settings: 60 writers, 30 verifier), a thrash stop (after
`max_consecutive_failures` in roles.json failed tool calls in a row, or `max_window_failures` of the last
`failure_window_calls` (8 of 25: the failures scattered between ok results that a streak never sees), every
tool but the `kanban_*` ones a blocked card may use is refused and the run ends with a `transient` block for
the coordinator), and for
`crew-verifier` no write / patch / send / delegate / code-execute tools plus a terminal that
refuses commands which write, move, delete, commit or send. `crew_card.py open` assigns the card to
the role's profile (`crew-worker`, `crew-content`) and falls back to the installing profile when
that profile is absent.

## Layout

```
plugin.yaml            manifest v2 (five hooks: pre_tool_call, post_tool_call, pre_llm_call,
                       post_api_request, api_request_error)
__init__.py            the plugin: one command per plugin option (/crew-status, /crew-graph, /crew-stop),
                       role guards (budget, verifier read-only)
templates/profiles/    one editable directory per role: SOUL.md + settings.conf
roles/roles.json       the roles: coordinator, worker, content, verifier
roles/briefs/*.md      one short contract brief per role
skills/crew/           the intake skill behind /crew
skills/crew-verifier/  verification checklist skill
skills/crew-role-worker/ + crew-role-content/  what a writer card is forced to load
scripts/crew_card.py   open a card from a contract, plan a parent with child cards, run a verdict
scripts/crew_coordinator.py    the coordinator loop: one pass per dispatch tick over the board's events (heal, decide, ask the owner)
scripts/crew_heal.py           the mechanical remedies the loop calls first (a library; no command of its own)
scripts/kanban_zulip_feed.py   live kanban->Zulip feed (run by the user unit)
scripts/crew_graph.py          live flow graph (terminal + --watch + self-contained HTML)
scripts/crew_graph_serve.py    always-on HTTP surface for the graph (/ , /card/<id>, /card/<id>.json, /healthz)
scripts/crew_option_commands_proof.py  proof that every option is its own command in the live registry
scripts/crew_proofs.py         runs every proof, each on the crew-proofs board (see "Proofs" below)
scripts/crew_proof_board.py    the proofs board: its env, the exit-2 guard, scratch boards, a dashboard for a proof
install.py             the installer
install.sh             thin wrapper
pyproject.toml         entry point crew = crew:register
```

## Proofs

Every proof seeds its cards on the kernel's own `crew-proofs` board (`~/.hermes/kanban/boards/crew-proofs/`), never
on the live one. `install.py` creates it (`hermes kanban boards create crew-proofs`, step `proofs-board`);
`crew_proofs.py` creates it too if it is missing and runs each proof with the env that pins it
(`crew_proof_board.proofs_env`: `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_DB`, `KANBAN_DB`, workspaces and attachments
roots). A proof that seeds cards calls `crew_proof_board.proof_db()` first: a pin on the live default board, no pin at
all, or a pinned file that does not exist exits 2 before anything is created. Run one by hand with
`crew_proofs.py --only <word>`. A proof that reads the dashboard over HTTP starts its own server on the proofs board
(`crew_proof_board.graph_base()`), and its cleared-notification file lives beside the board, not in the owner's home.

Four held-back proofs are live-service proofs on purpose, because their subject is the live feed, gateway or Zulip
adapter (`LIVE_BOARD` in `crew_proofs.py`: `crew_notify_proof`, `crew_zulip_route_proof`, `crew_live_walk`,
`crew_graph_flow_check`). They run only with `--all` or `--card` and unpinned. Three of them seed PROBE cards on the
live board; `crew_live_walk` does not: it posts to Zulip, opens no card, and only counts the live board read-only.
Its kernel-only leg (a card opened from a topic records that topic as its origin) runs on a scratch board in
`crew_origin_open_proof.py`, and the walks of one `Verify: proof` and one `independent` card to done are
`crew_two_stage_proof.py`.

**PROBE filters stay for now.** The spec removes them after one clean nightly run; that run has not happened, and the
three live-board proofs above that seed cards still seed PROBE cards on the live board. Remove these, in one commit, once a nightly run
left no `PROBE%` title on the default board (`select count(*) from tasks where title like 'PROBE%'` is 0) and the
proofs have a feed/gateway of their own on the proofs board:

- `scripts/crew_graph_serve.py`: `PROBE_RX` and `is_probe_card` (lines ~54-61), the `"test"` tile key (~137), the
  `test_cards` filter and its `?all=1` reveal (~145-149), the attention-list filter (~295-299).
- `scripts/crew_card.py`: `PROBE_OWNER`, `probe_card`, and its use in the card list filter (~201-227);
  `scripts/crew_coordinator.py` (~704, the `ctx.probe` skip).
- `__init__.py`: `PROBE_TITLE_RX` and its two uses in `_open_guard` and `crew_open_hook` (~861, 915, 1362).
- `scripts/kanban_zulip_feed.py` has no PROBE filter to remove.

## Uninstall

```sh
hermes -p NAME plugins disable crew
systemctl --user disable --now kanban-zulip-feed.service
rm -rf ~/.hermes/profiles/NAME/plugins/crew ~/.hermes/profiles/NAME/roles/crew
rm -f ~/.hermes/profiles/NAME/scripts/kanban_zulip_feed.py \
      ~/.hermes/profiles/NAME/scripts/crew_graph.py
```

(or `hermes -p NAME config unset crew.roles_path crew.source_dir` to drop the recorded keys; for the default
profile use `~/.hermes/` in place of `~/.hermes/profiles/NAME/`).

## Repo conventions

- Private repository, `main` as default branch; topics per `TOPICS.md`.
- Commits: `type: summary` (`feat` / `fix` / `chore` / `docs`).
- No secrets (the pre-push hook scans for them), no binaries. Credentials by Bitwarden item name only.
