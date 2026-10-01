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

Edit a template, then run the installer:

    python3 install.py --profile NAME            # creates + updates the role profiles
    python3 install.py --check --profile NAME    # what would change
    python3 install.py --profile-prefix crew- ...            # different profile name prefix

Re-running never overwrites an edit made in the profile: the installer records what it shipped
and skips a file that changed, reporting it as `kept your edit`.

Profile names default to `<prefix><role>`: `crew-worker`, `crew-verifier`, and so on. A card is
assigned to its role's profile by scripts/crew_card.py, and falls back to the installing profile
when that role profile does not exist.
