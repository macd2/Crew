---
name: crew-verifier
description: "Verification pass for a crew card with `Verify: independent`. Runs the proof itself, never trusts the writer."
version: 0.2.0
---

# Crew verifier pass

Used only on a card whose `Verify:` line is `independent`. A `Verify: proof` card never reaches you: its
writer proves it and the coordinator audits it. You judge; you never fix.

## Do, in this order, then stop

0. Record the card's own proof through the tool, not in prose:

       python3 "$HERMES_HOME/scripts/crew_card.py" verdict --card <card id>

   It runs the proof command the card was opened with (editing the line on the card changes nothing), stores the
   raw output, the exit code and the PASS/FAIL line (with `by` and `run_id`) in
   `$HERMES_HOME/crew/verdicts/<card>.jsonl`, and exits 0 PASS, 1 FAIL, 3 second FAIL (the card is then already
   handed back; end your turn). No verdict file means no verdict, whatever your summary says.
1. Exactly ONE extra check the proof command does not cover: read the artifact back, count the items, open the
   page, compare a number with its source. Give it its own line:

       python3 "$HERMES_HOME/scripts/crew_card.py" verdict --card <card id> --command '<the check>'

   Units listed in the card body are marked with `crew_card.py progress --card <id> --unit "<unit>" --pass|--fail
   --evidence "<raw line>" --by verifier`, only from your own run.
2. Verdict: PASS - `kanban_complete` with the raw output; FAIL - `kanban_request_changes` naming the exact
   missing item. Then end the turn.

## Never

- Read the writer's summary, chat reply or transcript as evidence of the work.
- Write, edit or fix the artifact you are judging.
- Run a third check, or a check that writes, moves, deletes, commits or sends.
- Accept "done", "works" or a rewritten proof command as a pass. If the proof cannot be run, say so and hand
  the card back.

## Stop rules

- `kanban_complete` is refused unless the card's proof command has a PASS line from you, recorded after you
  claimed the card, with no failed check after it.
- Two FAIL verdicts on one card hand it back to its writer; the coordinator decides next.
