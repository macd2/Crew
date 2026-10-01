#!/usr/bin/env python3
"""One delegate-fit model pick for a crew card, from the box's own router.

A crew card runs an autonomous agent (terminal, file, web tools), so the pick has to come from the
router's own delegate menu - the free HTTP hosts that can hold an agent's context (gateway, gemini,
openrouter) - not from `worker_route.py plan`, whose pool includes hosts that cannot serve an agent
at all (groq's 8k ceiling, CLI/web workers). This asks the free_first_router plugin's own decider
(`_decide(text, delegate=True)`, Jev first, the rule table on a Jev error) and prints:

  {"label": "gateway:x/y", "provider": "ai-gateway", "model": "x/y", "why": "...", "decider": "jev",
   "floor": {"min_context": 64000, "tools": "verified", "menu_size": 2}, "menu_size": 2}

`label` is "parent" when the router says the main model should take the task: then the crew card
keeps the role profile's own model and no pin is written.

A crew card runs an autonomous agent, so the menu is the router's agent-floor menu (free_first_router's
agent_floor.py: verified tool calling and a stated 64k window). When no live model clears the floor the
answer is "parent" without asking the chooser - a card is never pinned to a model that cannot carry it.
`floor` and `menu_size` travel with every answer so the card's route event can say why a model was allowed.

Privacy: the text is passed to the decider only, never logged. Run:
  python3 crew_route_pick.py --text "commit and push the package"
"""
import argparse
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_card  # noqa: E402 - router_plugin_path(): the one lookup for the optional router plugin


def plugin_dir():
    """The optional free_first_router plugin (CREW_ROUTER_PLUGIN, this profile, the owner profile), or None."""
    return crew_card.router_plugin_path()


def load_plugin():
    d = plugin_dir()
    if not d:
        return None
    spec = importlib.util.spec_from_file_location("free_first_router_pick",
                                                  os.path.join(d, "__init__.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PAID_ROWS = {"anthropic": True}     # the role profile's own paid model is always on Jev's menu


def profile_default_model(profile=None):
    """(provider, model) the role profile itself runs - the paid row Jev may choose."""
    prof = profile or os.environ.get("CREW_ROLE_PROFILE") or ""
    if not prof:
        return None, None
    cfg = os.path.expanduser("~/.hermes/profiles/%s/config.yaml" % prof)
    if not os.path.isfile(cfg):
        return None, None
    prov = model = None
    block = False
    for line in open(cfg):
        if line.startswith("model:"):
            block = True
            continue
        if block:
            if line[:1] not in (" ", "\t"):
                break
            k, _, v = line.strip().partition(":")
            if k == "provider":
                prov = v.strip()
            elif k == "default":
                model = v.strip()
    return prov, model


def refresh_stale(wr, mod):
    """Re-check the delegate hosts whose own evidence is past its freshness bound, before reading the menu.

    The router's own CLI re-checks stale ids before every decision (`plan`), but the plugin's
    ``_live_menu`` deliberately does not - it also serves the latency-bound delegate_task hook. A crew
    card's pick is not on a 30s hook path, and it must not read a menu the box has stopped checking:
    the free HTTP hosts are only evidence-backed for ``POOL[...]["fresh_s"]`` (gateway/gemini/groq 30
    minutes), so a box whose last probe is older than that puts NO free host on the delegate menu, the
    pick comes back empty, the card is never pinned and a quota wall can never be routed around. Only
    hosts that could serve a delegated child are re-checked, in parallel, once per stale window.
    """
    try:
        targets = [t for t in wr.due_ids(wr.load_state(), wr.load_exhaustion())
                   if t[0] in mod.DELEGATE_PROVIDERS]
        if targets:
            wr.refresh(targets)
        return len(targets)
    except Exception:          # noqa: BLE001 - a refresh that cannot run must not decide anything
        return 0


def pick(text, target_profile=None):
    """Jev's pick over the floor-clearing free delegate hosts AND the paid rows. Returns a dict or a reason."""
    mod = load_plugin()
    if mod is None:
        return {"label": None, "why": "no free_first_router plugin on this box"}
    wr = mod._wr()
    refresh_stale(wr, mod)
    try:
        menu, dropped, or_left, _ledger = mod._live_menu(wr, delegate=True, floor=True)
        floor = mod._floor().spec()
    except Exception as exc:  # noqa: BLE001
        return {"label": None, "why": "router menu error: %s" % exc}
    free = {p: ids for p, ids in menu.items() if p != "claude-cli"}
    floor["menu_size"] = mod._floor().size(free)
    task_class, tier = mod._task_class(text)
    if not free:                                       # nothing can carry an agent: no chooser call, no pin
        return {"label": "parent", "provider": None, "model": None, "decider": "floor", "floor": floor,
                "menu_size": 0, "task_class": task_class, "tier": tier,
                "why": "no live free model clears the agent floor (tool calling VERIFIED, context >= %d "
                       "tokens): the card runs on the role profile's own model" % floor["min_context"]}
    paid_prov, paid_model = profile_default_model(target_profile)
    if paid_prov and paid_model:                       # the paid row: quality when Jev wants it
        menu.setdefault(paid_prov, [])
        if paid_model not in menu[paid_prov]:
            menu[paid_prov].append(paid_model)
    needs = mod._needs(text)
    j = wr.jev_pick((mod.CHILD_FACTS + "\n\n" + text)[:6000], needs, tier, menu, or_left,
                    timeout=mod.JEV_TIMEOUT_S, excluded=dropped, units=1, tokens=0, child=True)
    base = {"floor": floor, "menu_size": floor["menu_size"]}
    if not (j.get("model") and j.get("provider") not in (None, "unknown")):
        d = mod._decide(text[:4000], delegate=True, floor=True)     # Jev unavailable: the router's rule table
        return dict(base, provider=mod.HERMES_PROVIDER.get(d.get("provider")),
                    model=None if mod._label(d) == mod.PARENT else d.get("model"),
                    label=mod._label(d), router_provider=d.get("provider"), decider="rules",
                    task_class=d.get("task_class"), tier=d.get("tier"), why=d.get("why"))
    prov, model = j["provider"], j["model"]
    if prov in ("claude-cli", "web") and paid_prov and paid_model:
        # Jev escalated to the paid ladder: pin the role profile's own model explicitly, so the card
        # records that this card was deliberately run on the paid model (and not left implicit).
        return dict(base, provider=paid_prov, model=paid_model, label="%s:%s" % (paid_prov, paid_model),
                    router_provider=prov, decider="jev", paid=True,
                    task_class=j.get("class") or task_class, tier=j.get("tier") or tier,
                    why="Jev gate (conf %s, %ss) escalated to %s: this card runs on the paid model "
                        "%s/%s" % (j.get("confidence"), j.get("latency_s"), j.get("label"),
                                   paid_prov, paid_model))
    # Paid is a fact of the row: the profile's own model (PAID_ROWS) or a router host whose POOL row says
    # paid=True (deepseek) - the card's route event must say so either way.
    paid = prov in PAID_ROWS or bool((wr.POOL.get(prov) or {}).get("paid"))
    if prov in PAID_ROWS:                               # the profile's paid model: keep the Hermes provider id
        hermes, label = prov, "%s:%s" % (prov, model)
    else:
        hermes = mod.HERMES_PROVIDER.get(prov)
        label = mod._label({"provider": prov, "model": model}) if hermes else None
    return dict(base, provider=hermes, model=model if hermes else None, label=label,
                router_provider=prov, decider="jev",
                task_class=j.get("class") or task_class, tier=j.get("tier") or tier,
                paid=paid,
                why="Jev gate (conf %s, %ss) picked %s; host %s%s"
                    % (j.get("confidence"), j.get("latency_s"), j.get("label"), prov,
                       " (the paid model)" if paid else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", required=True, help="the card's brief/goal text")
    ap.add_argument("--profile", default=None,
                    help="the role profile whose own (paid) model goes on Jev's menu")
    a = ap.parse_args()
    out = pick(a.text, target_profile=a.profile)
    print(json.dumps(out))
    return 0 if out.get("provider") and out.get("model") else 1


if __name__ == "__main__":
    raise SystemExit(main())
