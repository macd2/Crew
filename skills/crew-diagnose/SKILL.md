---
name: crew-diagnose
description: "Crew read-only pass: /crew-diagnose [state] - every card sitting in that state with its id and reason, then how each would resume. Plans only, it touches nothing."
version: 0.1.0
---

# /crew-diagnose [state] - a diagnosis per card, and how each would resume

Only the literal slash starts this pass: `/crew-diagnose [state]`. An ordinary message, a reaction, a
follow-up or a message that merely talks about blocked cards starts nothing - answer those as normal
chat.

**Read-only.** This turn looks and reports. It opens no card, retries nothing, lifts nothing, decides
nothing, posts nothing, changes no assignee and writes no file. `/crew-stop` and the coordinator loop
(`scripts/crew_coordinator.py`) are what act on the board; neither runs here, not even their scripts. The
owner picks from your plan and starts the acting pass himself.

## 1. The list comes from one command - the reader

    python3 "$HERMES_HOME/plugins/crew/scripts/crew_diagnose.py" [--state STATE]

The state is whatever the owner named after the slash: `blocked`, `triage`, `todo`, `ready`,
`running`, `done`, `archived`. With no state named, it is `blocked`. Never widen the state the owner
named because the list came back short, and never guess one he did not name.

That reader call is the only tool call in this turn. No `kanban_list`, no `kanban_show`, no session
store, no grep, no terminal command to "just check one card", no file write.

Every id, state, assignee, kind, wait and reason in your answer is copied from the reader's output. A
card the reader did not return is left out; a reason is never retyped from memory, never shortened
into a summary of your own and never softened. If the reader cannot read the board, or answers an
unknown state, say that in one line and stop - do not fall back to another tool to reconstruct the list.

If the reader answers zero cards: one line, "no cards in state STATE", and stop. Do not query anything
else to double-check.

## 2. What you add: the resume path for each card

Work from the reader's lines and the card's own title, nothing else. Per card, two short lines:

- `RESUME:` the smallest concrete step that would move this card - a decision only the owner can make,
  a dependency that is still open (name the parent card), a missing credential or access, a fix plus
  the command that would prove it, or a plain re-run.
- `WHO:` who takes that step - owner, coordinator, a named role, a named service.

Order the cards by the reader's wait, oldest first. When the reason is enough to name the resume path
with certainty, say it plainly. When it is not, say in one line exactly what is missing to decide -
never a guess dressed up as a plan, and never a plausible-sounding cause that the reader did not return.

## 3. Shape of the answer

1. One heading line: the state and the count, as the reader printed them.
2. One block per card: the id, state, assignee, kind, wait and reason exactly as read, then `RESUME:`
   and `WHO:`.
3. One closing line: how many cards wait on the owner, how many on another card, how many need a code fix.

Nothing else: no preamble, no "here is what I checked", no offer to run the acting passes, no card
opened, no comment posted, no retry, no unblock, no dispatch, no board write of any kind in this turn.
Ending your turn with the plan is the whole deliverable.
