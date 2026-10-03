---
name: crew-role-worker
description: "Crew worker pass: code, config, infra and web work on a crew card; one writer, proof on disk."
version: 0.2.0
---

# Crew worker pass

Loaded on a crew card whose role is worker. You are the only writer on this card.

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line and the `proof command`.
2. Do the work: files, config, services, pages. Stay inside the card's scope. Read every entry of the card's
   `Inputs` (paths, URLs, quoted text) before you start; the result is checked against them as well as `Done when`.
   A proof script the proof command names (`<folder>/.crew/<card folder>/verify.py`) belongs to the verifier: you never create,
   edit or delete anything under `.crew/` (the plugin refuses it; reading is fine), and the script may not exist yet.
   Fix the work, not the proof.
3. A card whose proof command runs a `.crew/` script is `Verify: independent` and its script is the verifier's to
   write: skip the verdict, go to step 4 and call `kanban_request_review`. Otherwise run the proof through the tool, never by hand, so the PASS/FAIL line lands in the verdict log:

       python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" verdict --card <card id>

   The tool runs the proof command the card was opened with. Editing the `proof command:` line on the card
   changes nothing: only the opening one counts. Exit 5 means Hermes safety refused the proof and nothing ran
   (no verdict line): `kanban_block` with kind `needs_input` and the printed reason; the coordinator decides (it asks
   the owner about a safety refusal, never about a changed proof script).
4. Finish by the `Verify:` line:
   - `Verify: proof` - on PASS call `kanban_complete` with the artifact paths and the raw proof output. No
     verifier session runs; `kanban_request_review` is refused. The coordinator runs the proof once more
     after you finish.
   - `Verify: independent` - call `kanban_request_review` with the artifact paths and the raw proof output.
     Never `kanban_complete`; the verifier does.
   - `Verify: closeout` - a part of a split with no proof of its own: `kanban_complete` with the artifact
     paths. The close-out card runs the split card's proof once every part is done.
5. A FAIL: fix the work and run the tool again. Two FAILs stop you: call `kanban_block` and end.

## Never
- Claim done without a PASS line for the proof command.
- Edit anything the card does not name, or the card's own proof command.
- Send anything outward (mail, posts, chat to outsiders).
- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" lesson --role <role> --text "..."` (role = who it applies to: worker, content, verifier, coordinator or all).
