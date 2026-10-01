---
name: crew-role-content
description: "Crew content pass: posts, reports, video, pages and social on a crew card; rendered artifact plus source."
version: 0.2.0
---

# Crew content pass

Loaded on a crew card whose role is content (posts, reports, video, pages, every social channel).

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line, target channel and format.
2. Produce the artifact and keep its raw source next to it.
3. Render it the way the reader will see it (image, page, preview) and check the render yourself.
4. Run the card's proof through the tool, never by hand, so the PASS/FAIL line lands in the verdict log:
   `python3 "$HERMES_HOME/scripts/crew_card.py" verdict --card <card id>` (the proof command the card was
   opened with; editing the line on the card changes nothing).
5. Finish with the rendered artifact path, the source path and any figures with their source, by the `Verify:`
   line: `proof` - `kanban_complete` after the PASS (no verifier session; `kanban_request_review` is refused; the
   coordinator runs the proof once more afterwards); `independent` - `kanban_request_review`, never
   `kanban_complete`.

## Never
- Publish or send without the owner's approval on the card.
- Use a number that is not computed or cited.
- Put internal data in anything outward-facing.
