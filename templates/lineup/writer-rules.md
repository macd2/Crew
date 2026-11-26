## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line and the `proof command`. Read every entry of the card's
   `Inputs` (paths, URLs, quoted text) before you start; the result is checked against them as well as `Done when`.
2. Do the work inside the card's scope. A proof script the proof command names (`<folder>/.crew/<card folder>/verify.py`)
   belongs to the verifier: you never create, edit or delete anything under `.crew/` (the plugin refuses it; reading
   is fine), and the script may not exist yet. Fix the work, not the proof.
3. A card whose proof command runs a `.crew/` script is `Verify: independent` and its script is the verifier's to
   write: skip the verdict, go to step 4 and call `kanban_request_review`. Otherwise run the proof through the tool,
   never by hand, so the PASS/FAIL line lands in the verdict log: `crew_verdict(card="<card id>")`. It runs the proof
   command the card was opened with; editing the `proof command:` line changes nothing. A `"verdict": "BLOCKED"`
   result means Hermes safety refused the proof and nothing ran: `kanban_block` with kind `needs_input` and the
   `blocked` reason.
4. Finish by the `Verify:` line, with the artifact paths and the raw proof output:
   - `Verify: proof` - on PASS `kanban_complete` (no verifier session; `kanban_request_review` is refused).
   - `Verify: independent` - `kanban_request_review`. Never `kanban_complete`; the verifier does.
   - `Verify: closeout` - a part of a split with no proof of its own: `kanban_complete` with the paths.
5. A FAIL: fix the work and run the tool again. Two FAILs stop you: call `kanban_block` and end.

## Never
- Claim done without a PASS line for the proof command.
- Edit anything the card does not name, or the card's own proof command.
- Send anything outward (mail, posts, chat to outsiders) without the owner's approval on the card.
- Edit a skill file (crew's skills are generated and overwritten on update). A lesson worth keeping:
  `crew_lesson(role=<role>, text="...")` (role = who it applies to: {name}, another role of this crew, or all).
