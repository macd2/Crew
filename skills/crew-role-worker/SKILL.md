---
name: crew-role-worker
description: "Crew worker pass: code, config, infra and web work on a crew card; one writer, proof on disk."
version: 0.2.0
---

# Crew worker pass

Loaded on a crew card whose role is worker. You are the only writer on this card.

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line and the `proof command`.
2. Do the work: files, config, services, pages. Stay inside the card's scope.
3. Run the proof through the tool, never by hand, so the PASS/FAIL line lands in the verdict log:

       python3 "$HERMES_HOME/scripts/crew_card.py" verdict --card <card id>

   The tool runs the proof command the card was opened with. Editing the `proof command:` line on the card
   changes nothing: only the opening one counts.
4. Finish by the `Verify:` line:
   - `Verify: proof` - on PASS call `kanban_complete` with the artifact paths and the raw proof output. No
     verifier session runs; `kanban_request_review` is refused. The coordinator runs the proof once more
     after you finish.
   - `Verify: independent` - call `kanban_request_review` with the artifact paths and the raw proof output.
     Never `kanban_complete`; the verifier does.
5. A FAIL: fix the work and run the tool again. Two FAILs stop you: call `kanban_block` and end.

## Never
- Claim done without a PASS line for the proof command.
- Edit anything the card does not name, or the card's own proof command.
- Send anything outward (mail, posts, chat to outsiders).
