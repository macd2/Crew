"""A stand-in for `hermes -p <profile> config get/set`, shared by the installer tests (a test never starts the real launcher).

It keeps one dict per profile and prints what Hermes prints: a scalar as text, a list as `  - item` lines, `[]` for an
empty list, exit 1 for a key that is not set. `set` coerces a `[a,b]` literal to a list the way `hermes config set` does.
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


class FakeConfig:
    def __init__(self):
        self.store = {}          # profile -> {dotted key: text as stored ('[a,b]' for a list)}
        self.calls = []

    def seed(self, profile, **keys):
        self.store.setdefault(profile or "default", {}).update({k.replace("__", "."): v for k, v in keys.items()})

    def __call__(self, profile, *args):
        self.calls.append((profile or "default",) + args)
        r, conf = Proc(), self.store.setdefault(profile or "default", {})
        if args[:2] == ("config", "get"):
            val = conf.get(args[2])
            if val is None:
                r.returncode = 1
            elif val.startswith("[") and val != "[]":
                r.stdout = "\n".join("  - %s" % i for i in _items(val)) + "\n"
            else:
                r.stdout = val + "\n"
        elif args[:2] == ("config", "set"):
            val = args[3]
            conf[args[2]] = "[%s]" % ",".join(_items(val)) if val.startswith("[") else val
        else:
            r.returncode = 1
        return r
