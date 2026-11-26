"""A stand-in for `hermes -p <profile> config get/set`, shared by the installer tests (a test never starts the real launcher).

It keeps one dict per profile and prints what Hermes prints: a scalar as text, a list as `  - item` lines (a mapping
item as `  - k: v` with its other keys indented under it), `[]` for an empty list, exit 1 for a key that is not set. `set` coerces a `[a,b]` literal to a list the way `hermes config set` does; `set --force` replaces a whole
section (a JSON mapping is stored as its text and printed back as JSON by `get`).
"""
import json


class Proc:
    returncode = 0
    stdout = ""
    stderr = ""


def _items(text):
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x) for x in data]
    except ValueError:
        pass
    return [x.strip() for x in text[1:-1].split(",") if x.strip()]


def _mappings(text):
    """A JSON list of mappings (`[{"provider":"p","model":"m"}]`) as that list, else None."""
    try:
        data = json.loads(text.strip())
    except ValueError:
        return None
    return data if isinstance(data, list) and data and all(isinstance(x, dict) for x in data) else None


def _block_item(mapping):
    """One list item the way Hermes prints a mapping: `  - k: v` and the other keys indented under it."""
    lines = ["%s: %s" % (k, v) for k, v in mapping.items()]
    return "  - %s\n" % lines[0] + "".join("    %s\n" % l for l in lines[1:])


class FakeConfig:
    def __init__(self):
        self.store = {}          # profile -> {dotted key: text as stored ('[a,b]' for a list)}
        self.calls = []
        self.forced = []         # (profile, key) of every `config set --force`
        self.refuse_unforced = set()   # keys a set without --force is refused for, as Hermes refuses a whole section

    def seed(self, profile, **keys):
        self.store.setdefault(profile or "default", {}).update({k.replace("__", "."): v for k, v in keys.items()})

    def __call__(self, profile, *args):
        self.calls.append((profile or "default",) + args)
        r, conf = Proc(), self.store.setdefault(profile or "default", {})
        if args[:2] == ("config", "get"):
            val = conf.get(args[2])
            if val is None:
                r.returncode = 1
            elif _mappings(val) is not None:
                r.stdout = "".join(_block_item(m) for m in _mappings(val))
            elif val.startswith("[") and val != "[]":
                r.stdout = "\n".join("  - %s" % i for i in _items(val)) + "\n"
            else:
                r.stdout = val + "\n"
        elif args[:2] == ("config", "set"):
            rest = list(args[2:])
            force = rest[:1] == ["--force"]
            key, val = rest[1:] if force else rest
            if key in self.refuse_unforced and not force:
                # what Hermes's section guard does: a whole section of another shape needs --force
                r.returncode, r.stderr = 1, "Cannot set '%s': use --force to replace the entire section" % key
                return r
            if force:
                self.forced.append((profile or "default", key))
            if _mappings(val) is not None:
                conf[key] = json.dumps(_mappings(val))
            else:
                conf[key] = "[%s]" % ",".join(_items(val)) if val.startswith("[") else val
        else:
            r.returncode = 1
        return r
