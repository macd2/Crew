# Lineups

A lineup decides which **writer** roles a crew has. Every crew always keeps its `coordinator` and its
`verifier`; a lineup replaces the default writers (`worker` and `content`) with 1 to 12 roles of its own.
Each role becomes its own Hermes profile, `<prefix><name>` (`crew-auditor` with the default prefix).

Crew ships three lineups. The installer copies them into `<Hermes home>/crew/lineups/`, the same place a
lineup you download or write lands, so they are yours to read and edit:

| Lineup | Roles |
|---|---|
| `security` | `auditor` finds vulnerabilities and never fixes them, `remediator` fixes findings in scope, `hardener` hardens config and dependencies |
| `design` | `researcher` gathers evidence about users and competitors, `designer` draws screens as HTML/CSS or SVG with tokens, `prototyper` makes them clickable |
| `pentest` | `recon` maps in-scope targets, `tester` confirms vulnerabilities with safe proofs of concept, `reporter` writes the report. Every card needs a written authorization and a scope list, or the role stops and asks |

Edit them there. An update never overwrites a lineup you changed; an unchanged one is kept in step with the
package. Delete one and the next install puts it back.

## Use one

    /crew --lineup security <ask>     switch to the lineup in the background, then run the intake as usual
    /crew-lineup                      the active lineup, its status, and the lineups you can use
    /crew-lineup use NAME             switch (background install), no ask
    /crew-lineup show NAME            every role, model, toolset and text in full
    /crew-lineup add <url|path>       fetch a lineup and show everything in it; nothing is saved yet
    /crew-lineup save NAME            save the lineup `add` showed you
    /crew-lineup default              back to the default crew (worker + content)
    /crew-lineup uninstall NAME       what uninstalling would remove; add --yes to do it

    python3 install.py --profile NAME --lineup security              the same from the installer
    python3 install.py --profile NAME --uninstall-lineup security

## Uninstall one

Uninstalling is the reverse of installing: the lineup's role profiles are removed entirely (with their role
skills in the other crew profiles), its generated build folder goes, and if it was the crew's lineup the crew
is the default one again. The lineup file and any text files it uses stay: they are the recipe, and
`/crew-lineup use NAME` installs it again. It is refused while a card assigned to one of its roles is still open.

Without `--lineup` the installer keeps the lineup recorded in config (`crew.lineup`), so an update never
switches you back. `--lineup default` is the shipped crew.

Your own lineups live in `<Hermes home>/crew/lineups/<name>.json` (`~/.hermes/crew/lineups/` on Linux and
macOS, `%LOCALAPPDATA%\hermes\crew\lineups\` on Windows). A name is looked up there first, then here.
An update never touches that folder.

**Only use lineups you trust.** A lineup's roles run with the same access as any Hermes profile: its texts
become the role's persona and skill, its toolsets are the role's tools. `add` shows everything before you save.

## Format

```json
{
  "name": "security",
  "description": "Audit, fix, harden",
  "inherit": {"env": "owner", "hooks": "owner", "skills": false, "mcp": false},
  "roles": [
    {"name": "auditor", "purpose": "Finds vulnerabilities, never fixes them.", "task_class": "review",
     "soul": "...", "brief": "...", "skill": "..."}
  ]
}
```

Lineup keys:

    name          optional, defaults to the file name; lowercase letters, digits and `-`, up to 32;
                  `default` is reserved
    description   optional, one line
    inherit       optional, what every role profile gets from an existing profile (see Inherit)
    roles         required, 1 to 12 roles

Role keys (any other key is an error naming the role and the key):

    name          required, 2 to 24 lowercase letters only; not coordinator, verifier or all; unique
    purpose       required, one line: what the role is for
    description   the Hermes profile description (default "Crew <name>: <purpose>")
    artifact      what the role delivers (default: the worker's)
    proof         what proves it (default: the worker's)
    task_class    code | write | review (default code)
    model         the role's model (model.default); also provider, base_url
    toolsets      toolsets added to the default terminal, file, web, kanban, crew
    no_toolsets   toolsets removed from that default; kanban and crew can never be removed
    budget_tokens the per-card token budget (default from roles/roles.json)
    max_turns     the iteration cap per run (agent.max_turns)
    skills_extra  extra skills the role keeps, as in a template's settings.conf
    inherit       optional, overrides the lineup's inherit for this role, key by key (see Inherit)
    soul          the persona            soul_file    the same, read from a file
    brief         the role's brief       brief_file
    skill         how it works a card    skill_file

## Inherit: what a role profile gets from another profile

Role profiles are created bare (`hermes profile create --no-skills`, no clone of the owner's config). A role
gets exactly what `inherit` says and nothing else. `inherit` is an optional object at the top of the lineup
(every role) and optionally on a role. A role's `inherit` overrides the top one key by key; a key a role does
not name keeps the top value, and a key neither names uses its default.

Keys, all optional:

    env     a profile name, "owner" or false. Whose credentials the role gets: that profile's `.env` plus
            the credential sections of its config.yaml (`secrets`, `vault`, `providers`). false = none,
            the role keeps Hermes's empty placeholder `.env`.                                  default "owner"
    hooks   a profile name, "owner" or false. The shell hooks (config.yaml `hooks:`) copied from that
            profile; false = no hooks. Hooks still need consent per profile in Hermes's own allowlist:
            the installer reports them and never approves for you.                             default "owner"
    skills  a set, in one of the four forms below. Skills beyond crew's own; crew's role skills are always
            installed whatever this says. `skills_extra` still works and adds to the result.  default false
    mcp     a set, in one of the four forms below. The role's `mcp_servers`.                 default false

"owner" is the crew's owner profile, the one the crew was installed from. Any other profile name must be an
existing Hermes profile (`default` is the default profile).

### The four forms of a set (skills, mcp)

A skill is matched by its name: the folder `skills/<category>/<name>/` holding a `SKILL.md` in the source
profile (crew's own `skills/crew/` is never part of a set). An MCP server is a key of the source profile's
config.yaml `mcp_servers`.

1. **A profile name**: everything that profile has.

       "skills": "crew-worker"          every skill of the profile crew-worker
       "mcp": "owner"                   every MCP server of the owner profile

2. **A list**: exactly this list, nothing inherited. A bare name comes from the owner profile,
   `profile/name` from that profile. `[]` is the same as false.

       "skills": ["seo-search", "crew-worker/github"]
       "mcp": ["github", "ops/jira"]

3. **An object**: a profile's set, plus items, minus names. `from` is required: a profile name, "owner",
   or false to start empty. `add` items follow the list rules (bare = owner, `profile/name`); `drop` takes
   bare names. Any other key is refused.

       "skills": {"from": "crew-worker", "add": ["owner/seo-search", "x"], "drop": ["github"]}
       "mcp":    {"from": false, "add": ["ops/jira"]}

   Merge order: the `from` set, then each `add` (an added name replaces an inherited one of the same name,
   and the first add of a name wins), then each `drop`. A name that appears twice ends up once.

4. **false**: none.

The installer writes the merged MCP servers to the role with `hermes config set --force mcp_servers`, so the
role holds exactly that mapping, and copies each resolved skill folder into its `skills/`.

### Top level and roles

```json
{
  "name": "review",
  "inherit": {"env": "owner", "hooks": "owner", "skills": false, "mcp": false},
  "roles": [
    {"name": "coder",    "inherit": {"skills": "crew-worker"}},
    {"name": "triager",  "inherit": {"skills": ["github-pr-workflow", "crew-worker/code-review"]}},
    {"name": "releaser", "inherit": {"mcp": {"from": "owner", "add": ["ops/jira"], "drop": ["slack"]}}},
    {"name": "offline",  "inherit": {"env": false, "hooks": false}}
  ]
}
```

(Role fields such as `purpose` are left out above.) `coder` gets every skill of the profile `crew-worker`;
`triager` gets exactly two skills, one from the owner and one from `crew-worker`; `releaser` gets the owner's
MCP servers except `slack`, plus `jira` from the profile `ops`; `offline` has no credentials and no hooks. A
role's value for a key replaces the top value whole: a role object is not merged into a top list.

The shipped lineups use the empty forms (`"skills": []`, `"mcp": {"from": false, "add": [], "drop": []}`),
so they install on any owner profile; fill them in to give a role more.

### Validation

Refused when the lineup is validated (`crew_lineup.py validate`, and before the installer changes anything),
with a message naming the role (or "top level") and the key: unknown keys, wrong types, a profile that does
not exist, a named skill or MCP server that its source profile does not have, and a `drop` of a name that is
not in the set. A role template's `settings.conf` `inherit.*` lines follow the same rules; there a set is
written `false`, a profile name, `[a,b]` or the object as JSON.

## The texts: soul, brief, skill

- Inline (`soul`) or from a file (`soul_file`). Only one given: that one. Both: the file text, a blank line,
  then the string. Neither: generated from the role's name and purpose.
- A `_file` path is relative to the crew folder (`<Hermes home>/crew/`) and nothing else. Refused, with the
  role, key and path named: an absolute path, `~`, a drive letter, a path that leaves the crew folder
  (symlinks resolved), a missing file, a file that is not UTF-8, a file over 64 KB.
- A shipped lineup uses inline texts only, because the package cannot put files in your crew folder.
- Crew's own rules (one writer per card, never write under `.crew/`, how to ask for review and record a
  verdict) are always part of the role's skill. Your `skill` text adds to them and cannot remove them.

Check a lineup before you use it:

    python3 scripts/crew_lineup.py validate security
    python3 scripts/crew_lineup.py show security
