# Role profile templates

One directory per crew role. The installer copies these into the profile it creates.

    coordinator  intake, contract, split decision, budget, the Needs-you gate
    worker       code, config, infra, web
    content      posts, reports, video, pages, social
    verifier     runs the proof itself, read-only, never fixes

Each directory holds:

    SOUL.md         the role's persona and non-negotiables. Copied to the profile as SOUL.md.
    settings.conf   key = value lines the installer applies into the profile config.
                    `[a,b,c]` is a YAML list. Edit these before installing: `crew.role` (the
                    guard reads it), the model for the role, `platform_toolsets.cli` (the tools a
                    card run has: kernel toolset names such as `file`, `terminal`, `web`, `kanban`),
                    and the toolsets the role must not have.
                    `skills_extra = [category/skill, ...]` is read by the installer, not written to
                    config.yaml: skills (paths under the installing profile's skills dir) the role
                    keeps besides skills/crew/, which is all a role profile's skills dir holds.
                    `inherit.env`, `inherit.hooks`, `inherit.skills`, `inherit.mcp` are read by the
                    installer too: what the bare role profile takes from which profile (a profile
                    name, `owner` or `false`; skills and mcp also `[name, profile/name]` or
                    `{"from": ..., "add": [...], "drop": [...]}` as JSON). The shipped roles say
                    env and hooks from the owner, no extra skills, no MCP servers; a lineup's
                    `inherit` block writes the same lines (crew-home/lineups/README.md).

Edit a template, then run the installer:

    python3 install.py --profile NAME            # creates + updates the role profiles
    python3 install.py --check --profile NAME    # what would change
    python3 install.py --profile-prefix crew- ...            # different profile name prefix

Re-running never overwrites an edit made in the profile: the installer records what it shipped
and skips a file that changed, reporting it as `kept your edit`.

## Your own overrides

An edit to a file here is lost or conflicts when crew updates. To keep your own values, put them in
`<Hermes home>/crew/templates/<role>/` instead (`~/.hermes/crew/templates/worker/` on Linux and macOS,
`%LOCALAPPDATA%\hermes\crew\templates\worker\` on Windows). An update never touches that folder.

    settings.conf   only the keys you change. Each one replaces the shipped value; a key the
                    template does not have is added. A list such as `skills_extra` replaces the
                    whole shipped list. Only owner keys are taken: every `model.*` key,
                    `fallback_providers`, `agent.max_turns` and `skills_extra`. Any other key is
                    a gate the card contract relies on (`crew.role`, the toolsets, Slack off, the
                    orchestrator profile, MCP servers): it is skipped and reported. A key written
                    more than once in the file is refused (the shipped value applies) and reported.
                    `--check` and the install output list every skipped or refused line.
    SOUL.md         replaces the shipped persona.

For example, to give the worker another model:

    # ~/.hermes/crew/templates/worker/settings.conf
    model.default = your-model
    model.provider = your-provider

Then run the installer as above. `--check` compares the profiles with the same merged values.
`CREW_TEMPLATE_OVERRIDES` names another folder in place of `<Hermes home>/crew/templates`.

Profile names default to `<prefix><role>`: `crew-worker`, `crew-verifier`, and so on. A card is
assigned to its role's profile by scripts/crew_card.py, and falls back to the installing profile
when that role profile does not exist.

## Lineup roles

A lineup (see [../crew-home/lineups/README.md](../crew-home/lineups/README.md)) has no directory here: the installer generates each
lineup role's `SOUL.md` and `settings.conf` from the lineup (the settings start from `worker/settings.conf`;
the generic texts for a role without its own are in `lineup/`). Owner overrides still apply the same way:
`<Hermes home>/crew/templates/<role>/` (for example `~/.hermes/crew/templates/auditor/`) wins over the
generated values with the same owner-key rules as above.
