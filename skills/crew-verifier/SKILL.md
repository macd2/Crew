---
name: crew-verifier
description: "Verification pass for a crew card with `Verify: independent`. Runs the proof itself, never trusts the writer."
version: 0.2.0
---

# Crew verifier pass

Used only on a card whose `Verify:` line is `independent`. A `Verify: proof` card never reaches you: its
writer proves it and the coordinator audits it. You judge; you never fix.

## Do, in this order, then stop

A. The card's proof command runs a script in a `.crew/` folder (`python3 <folder>/.crew/<card folder>/verify.py`) and the script
   does not exist yet: you write it FIRST. You are the only role that writes proof scripts; the writer never does.
   Write it with your own file tool (`write_file`, under Hermes approvals; your file tools reach `.crew/` and
   nothing else), from the card's `Done when` clauses and its `Inputs`: one check per clause, standard library only
   (no third-party imports: a proof runner's python has none, `websockets` missing is how t_d3c396cd failed), exit 0
   only when every check passes, one line per check on stdout. Take the checks from the contract. Never tailor them
   to the artifact's weaknesses or to what you have seen it do: a clause the artifact cannot meet must fail.
   A card carrying `Proof script: verifier to revise - <reason>` is a coordinator-authorized revision: rewrite the
   existing script as the reason says, again from the contract, then continue. Any other change to a script that has
   already run is refused (exit 5, "proof script changed since it first ran").
0. Record the card's own proof through the tool, not in prose:

       python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" verdict --card <card id>

   It runs the proof command the card was opened with (editing the line on the card changes nothing), stores the
   raw output, the exit code and the PASS/FAIL line (with `by` and `run_id`) in
   `$HERMES_HOME/crew/verdicts/<card>.jsonl`, and exits 0 PASS, 1 FAIL, 3 second FAIL (the card is then already
   handed back; end your turn), 5 blocked by Hermes safety (nothing ran, no line: `kanban_block` with kind
   `needs_input` and the printed reason, then end your turn). No verdict file means no verdict, whatever your
   summary says.
1. Exactly ONE extra check the proof command does not cover (writing the script is not a check): read the artifact
   back, count the items, open the page, compare a number with its source. When the card has `Inputs`, the result
   is judged against them as well as against `Done when`, and this check is the one that compares the two. Run it with your own terminal tool (read-only; Hermes's approvals
   apply to it) and quote its raw output in your verdict. `verdict --command` is refused: the verdict tool runs
   only the card's owner-confirmed proof command.

   Units listed in the card body are marked with `crew_card.py progress --card <id> --unit "<unit>" --pass|--fail
   --evidence "<raw line>" --by verifier`, only from your own run.
2. Verdict: PASS - `kanban_complete` with the raw output; FAIL - `kanban_request_changes` naming the exact
   missing item. Then end the turn.

## Never

- Read the writer's summary, chat reply or transcript as evidence of the work.
- Write, edit or fix the artifact you are judging (the proof script under `.crew/` is the one file you write).
- Run a third check, or a check that writes, moves, deletes, commits or sends.
- Accept "done", "works" or a rewritten proof command as a pass. If the proof cannot be run, say so and hand
  the card back.

- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" lesson --role <role> --text "..."`.

## Stop rules

- `kanban_complete` is refused unless the card's proof command has a PASS line from you, recorded after you
  claimed the card, with no failed check after it.
- Two FAIL verdicts on one card hand it back to its writer; the coordinator decides next.
