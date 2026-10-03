---
name: crew-role-content
description: "Crew content pass: posts, reports, video, pages and social on a crew card; rendered artifact plus source."
version: 0.2.0
---

# Crew content pass

Loaded on a crew card whose role is content (posts, reports, video, pages, every social channel).

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line, target channel and format.
2. Produce the artifact and keep its raw source next to it. Read every entry of the card's `Inputs`
   (paths, URLs, quoted text) before you start; the result is checked against them as well as `Done when`. A proof
   script the proof command names (`<folder>/.crew/<card folder>/verify.py`) belongs to the verifier: you never create, edit or
   delete anything under `.crew/` (the plugin refuses it; reading is fine), and the script may not exist yet. Fix the
   work, not the proof.
3. Render it the way the reader will see it (image, page, preview) and check the render yourself.
4. A card whose proof command runs a `.crew/` script is `Verify: independent` and its script is the verifier's to
   write: skip the verdict and go to step 5 (`kanban_request_review`). Otherwise run the card's proof through the
   tool, never by hand, so the PASS/FAIL line lands in the verdict log:
   `python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" verdict --card <card id>` (the proof command the card was
   opened with; editing the line on the card changes nothing). Exit 5 means Hermes safety refused the proof and
   nothing ran (no verdict line): `kanban_block` with kind `needs_input` and the printed reason.
5. Finish with the rendered artifact path, the source path and any figures with their source, by the `Verify:`
   line: `proof` - `kanban_complete` after the PASS (no verifier session; `kanban_request_review` is refused; the
   coordinator runs the proof once more afterwards); `independent` - `kanban_request_review`, never
   `kanban_complete`; `closeout` (a part of a split, no proof of its own) - `kanban_complete` with the paths.

## Never
- Publish or send without the owner's approval on the card.
- Use a number that is not computed or cited.
- Put internal data in anything outward-facing.
- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `python3 "$HERMES_HOME/plugins/crew/scripts/crew_card.py" lesson --role <role> --text "..."` (role = who it applies to: worker, content, verifier, coordinator or all).
