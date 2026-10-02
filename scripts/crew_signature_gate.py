#!/usr/bin/env python3
"""Gate: a function handed to a dispatcher must fit the call the dispatcher makes.

The heal pass hands `safely` a helper and `safely` calls it as fn(card, dry). A helper declared
with a third parameter cannot bind that call: it raises TypeError before its own guards run, every
run, and the pass reports "could not heal" forever. That is a signature defect, so it is checked
statically, here, and not only by whichever proof happens to walk that route.

Two passes over each module's AST, in any module of the plugin:

  1. find the dispatchers - a function whose first positional parameter is CALLED inside its own
     body (fn(card, dry) is the pattern), recording how many arguments that call passes
  2. at every call site of such a dispatcher, take the first argument; when it names a function of
     the same module (or a sibling module's function, resolved through `import x` /
     `from x import y`), check that the function accepts exactly that many positional arguments -
     no more required than are passed, and no more accepted than are passed either

Also flagged: a helper passed to a dispatcher with *args or **kwargs, whose arity cannot be checked
- reported as UNCLEAR, not as a pass, so the gap is visible.

Run:  python3 crew_signature_gate.py [--json]
Exit: 0 when no helper is called with the wrong number of arguments, 1 otherwise.
"""
import argparse
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
def package_root():
    """The plugin package: the nearest ancestor carrying plugin.yaml, else the parent of this file."""
    env = os.environ.get("CREW_PKG")
    if env and os.path.isfile(os.path.join(env, "plugin.yaml")):
        return env
    d = HERE
    while True:
        if os.path.isfile(os.path.join(d, "plugin.yaml")):
            return d
        parent = os.path.dirname(d)
        if parent == d:   # an installed copy in <profile>/scripts: the package install.py ran from
            sys.path.insert(0, HERE)
            import crew_card
            return crew_card.package_dir() or os.path.dirname(HERE)
        d = parent


def modules():
    root = package_root()
    out = []
    entry = os.path.join(root, "__init__.py")
    if os.path.isfile(entry):
        out.append(entry)
    scripts = os.path.join(root, "scripts")
    for name in sorted(os.listdir(scripts if os.path.isdir(scripts) else HERE)):
        d = scripts if os.path.isdir(scripts) else HERE
        if name.endswith(".py") and name != os.path.basename(__file__):
            out.append(os.path.join(d, name))
    return out


def params_of(fn):
    """(required positional, accepted positional, has *args)."""
    a = fn.args
    pos = list(a.posonlyargs) + list(a.args)
    required = len(pos) - len(a.defaults)
    return required, len(pos), bool(a.vararg)


def collect(tree):
    """module-level functions by name, plus the aliases imported from sibling modules."""
    funcs, aliases = {}, {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
        elif isinstance(node, ast.Import):
            for al in node.names:
                aliases[al.asname or al.name.split(".")[0]] = al.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[-1]
            for al in node.names:
                aliases[al.asname or al.name] = "%s:%s" % (mod, al.name)
    return funcs, aliases


def called_with(fn, first_param):
    """The argument count of the first call to `first_param` inside fn, or None."""
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name) and f.id == first_param:
            n = len([a for a in node.args if not isinstance(a, ast.Starred)])
            return n
    return None


def dispatchers(funcs):
    out = {}
    for name, fn in funcs.items():
        pos = list(fn.args.posonlyargs) + list(fn.args.args)
        if not pos:
            continue
        n = called_with(fn, pos[0].arg)
        if n is not None:
            out[name] = n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    problems, unclear, checked = [], [], 0
    for path in modules():
        try:
            tree = ast.parse(open(path).read(), path)
        except SyntaxError as exc:
            problems.append({"file": path, "line": exc.lineno, "code": "syntax error: %s" % exc})
            continue
        funcs, aliases = collect(tree)
        disp = dispatchers(funcs)
        if not disp:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in disp or not node.args:
                continue
            target = node.args[0]
            if not isinstance(target, ast.Name):
                continue                      # a lambda or a construction site: nothing to check
            # a helper of this module, or one imported from a sibling
            if target.id not in funcs and target.id not in aliases:
                continue
            checked += 1
            label = "%s -> %s" % (node.func.id, target.id)
            if target.id in aliases and ":" in aliases[target.id]:
                unclear.append({"module": path, "line": node.lineno, "call": label,
                                "why": "imported from %s" % aliases[target.id].split(":")[0]})
                continue
            required, accepted, star = params_of(funcs[target.id])
            want = disp[node.func.id]
            if star:
                unclear.append({"module": path, "line": node.lineno, "call": label,
                                "why": "takes *args, arity unchecked"})
                continue
            if required > want or accepted < want:
                problems.append({"module": os.path.relpath(path, HERE), "line": node.lineno,
                                 "call": label,
                                 "why": "%s takes %d-%d positional argument(s), the dispatcher calls "
                                        "it with %d" % (target.id, required, accepted, want)})

    if a.json:
        print(json.dumps({"checked": checked, "problems": problems, "unclear": unclear}, indent=1))
    else:
        print("checked %d helper(s) handed to a dispatcher in %d module(s)"
              % (checked, len(modules())))
        for p in problems:
            print("  SIGNATURE MISMATCH  %s:%s  %s\n    %s"
                  % (p["module"], p["line"], p.get("call", ""), p["why"]))
        for u in unclear:
            print("  UNCLEAR             %s:%s  %s (%s)"
                  % (os.path.relpath(u["module"], HERE), u["line"], u["call"], u["why"]))
    if problems:
        print("GATE FAIL: %d call(s) would raise TypeError when the dispatcher binds them"
              % len(problems))
        return 1
    print("GATE OK: every helper handed to a dispatcher takes the call the dispatcher makes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
