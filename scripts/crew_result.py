#!/usr/bin/env python3
"""Reading a tool result: ok or err, the short reason, the last line of output.

One reader for every consumer of a tool result row: crew_graph.py (the step panel and the chip runs) and the
plugin's thrash stop (consecutive failed tool calls). A second copy would let the stop and the dashboard
disagree about what a failure is.

Stdlib only. A tool result is a JSON object carrying 'success', 'error' and/or 'exit_code'.
"""
import json

# The words a thrash stop puts in its block reason ("crew: repeated tool failure: <last note>"). crew_heal keys
# the failure signature on them, so two blocks of this kind count as one repeat whatever the last note said.
THRASH_REASON = "repeated tool failure"


def result_row(content):
    """(ok|err, note, out) from a tool result message. Our tool results are JSON objects that carry
    'success', 'error' and/or 'exit_code'; anything unparseable counts as ok. `note` is the short
    reason for a failure - "" when the result has nothing to say. `out` is the last text the step's own
    output produced, which is what a reader wants when the step never said it in words."""
    if isinstance(content, dict):      # a post_tool_call hook can hand the result over already parsed
        obj = content
    else:
        try:
            obj = json.loads(content or "")
        except Exception:
            return "ok", "", short_reason(content, 160)
    if not isinstance(obj, dict):
        return "ok", "", short_reason(obj, 160)
    out = result_out(obj)
    if obj.get("success") is False:
        return "err", short_reason(obj.get("error") or obj.get("message")), out
    if obj.get("error") not in (None, "", False):
        return "err", short_reason(obj.get("error")), out
    ec = obj.get("exit_code")
    if isinstance(ec, int) and not isinstance(ec, bool) and ec != 0:
        return "err", "exit %d" % ec, out
    return "ok", "", out


def leaf_text(v, limit=160):
    """One readable line out of any value a tool result carries.

    A string is its own text; a dict is named by its path and line when it has them, else by the text
    it holds; a list is its length and its first item. This is what keeps a result like search_files'
    {"total_count": 2, "matches": [...]} from reading as nothing at all.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return " ".join(v.split())[:limit]
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "" if not v else "%d item(s): %s" % (len(v), leaf_text(v[0], limit - 12))
    if isinstance(v, dict):
        if isinstance(v.get("path"), str):
            return v["path"] + (":%s" % v["line"] if v.get("line") is not None else "")
        for k in ("content", "text", "message", "summary", "title", "error", "result"):
            if isinstance(v.get(k), str) and v[k].strip():
                return leaf_text(v[k], limit)
        scalars = [(k, vv) for k, vv in v.items() if not isinstance(vv, (list, dict))]
        if scalars:
            return " ".join("%s=%s" % (k, leaf_text(vv, 40)) for k, vv in scalars)[:limit]
        for k, vv in v.items():
            if isinstance(vv, list) and vv:
                return "%d %s: %s" % (len(vv), k, leaf_text(vv[0], limit - len(k) - 6))
        return ""
    return str(v)[:limit]


def result_out(obj, limit=160):
    """The last text a tool result produced, one line.

    A failure's reason wins; otherwise the tool's own output - terminals carry it under 'output', other
    tools under content/text/message/result. A result that carries no such key is summarised from its
    own shape: the first list it holds (a search's matches, a listing's items) or its scalars
    ("2 matches: .../kanban_zulip_feed.py:551"), so a step never reads as having printed nothing. The
    LAST non-empty line is the tail of the run, which is what went wrong or last happened.
    """
    if not isinstance(obj, dict):
        return leaf_text(obj, limit)
    text = ""
    err = obj.get("error")
    if isinstance(err, str) and err.strip():
        text = err
    else:
        for key in ("output", "stdout", "content", "text", "message", "result", "summary"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                text = v
                break
    if not text:
        lists = [(k, v) for k, v in obj.items() if isinstance(v, list) and v]
        if lists:
            k, v = lists[0]
            text = "%d %s: %s" % (len(v), k, leaf_text(v[0], max(24, limit - len(k) - 6)))
        else:
            text = " ".join("%s=%s" % (k, leaf_text(v, 40)) for k, v in obj.items()) or leaf_text(obj)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return (lines[-1] if lines else "")[:limit]


def short_reason(value, limit=70):
    """One line out of whatever the result put in 'error' - a string, a dict or a list."""
    if isinstance(value, dict):
        value = value.get("message") or value.get("error") or value.get("detail") or ""
    elif isinstance(value, (list, tuple)):
        value = " ".join(str(v) for v in value[:2])
    return " ".join(str(value or "").split())[:limit]


def result_state(content):
    """ok/err from a tool result message (see result_row)."""
    return result_row(content)[0]
