#!/usr/bin/env python3
"""Add the Raider.IO "main" of every character you rated to MPPPR_DB.

For each character with the chosen flag (Avoid by default) this asks Raider.IO
which character its owner declared as their main ("Alt of ..." on the profile).
If there is one, the main is added to your ratings with the same flag, both
characters are linked to one person, and the new character gets a note saying
who it was linked to originally.

Limits, so nothing here is a surprise:
  * Raider.IO only exposes the declared main of a character, not a list of all
    alts, and only when its owner set one. Unclaimed profiles give nothing.
  * It uses the website's own JSON (the public API has no alt data). That is
    unofficial and may change; failures are reported, never fatal.
  * WoW rewrites the saved variables on logout and /reload, so the game must
    be closed. A dry run is the default; pass --apply to write.

Usage:
    python3 link_alts.py                 # dry run: show what would change
    python3 link_alts.py --apply         # write it (a backup is kept)
"""

import argparse
import glob
import json
import os
import re
import subprocess
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WTF = os.path.normpath(os.path.join(HERE, "..", "..", "..", "WTF"))
VAR = "MPPPR_DB"
FILE = "MythicPlusPersonalPlayerRatings.lua"  # WoW names the file after the addon, not the variable
SITE = "https://raider.io/api/characters/{region}/{realm}/{name}"
UA = "MPPPR-link-alts/1.0 (personal use; +https://github.com/wkerstiens/MythicPlusPersonalPlayerRatings)"


# -- Lua saved-variables parsing and writing ----------------------------------
# Only the subset WoW writes: one `NAME = <table>` assignment of tables,
# strings, numbers, booleans and nil.

class LuaError(ValueError):
    pass


class _Parser:
    def __init__(self, text):
        self.s, self.i = text, 0

    def ws(self):
        while self.i < len(self.s):
            c = self.s[self.i]
            if c.isspace():
                self.i += 1
            elif self.s.startswith("--", self.i):
                j = self.s.find("\n", self.i)
                self.i = len(self.s) if j < 0 else j + 1
            else:
                break

    def expect(self, ch):
        self.ws()
        if self.s[self.i:self.i + 1] != ch:
            raise LuaError("expected %r at offset %d" % (ch, self.i))
        self.i += 1

    def value(self):
        self.ws()
        c = self.s[self.i:self.i + 1]
        if c == "{":
            return self.table()
        if c in "\"'":
            return self.string()
        m = re.compile(r"-?(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+)").match(self.s, self.i)
        if m:
            self.i = m.end()
            t = m.group(0)
            if t.lower().lstrip("-").startswith("0x"):
                return int(t, 16)
            return int(t) if re.fullmatch(r"-?\d+", t) else float(t)
        for word, val in (("true", True), ("false", False), ("nil", None)):
            if self.s.startswith(word, self.i):
                self.i += len(word)
                return val
        raise LuaError("unexpected %r at offset %d" % (c, self.i))

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        esc = {"n": "\n", "r": "\r", "t": "\t", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == q:
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                c = self.s[self.i]
                m = re.compile(r"\d{1,3}").match(self.s, self.i)
                if m:
                    out.append(chr(int(m.group(0))))
                    self.i = m.end()
                    continue
                out.append(esc.get(c, c))
            else:
                out.append(c)
            self.i += 1
        raise LuaError("unterminated string")

    def table(self):
        self.expect("{")
        result, n = {}, 1
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return result
            if self.s[self.i] == "[":
                self.i += 1
                key = self.value()
                self.expect("]")
                self.expect("=")
                result[key] = self.value()
            else:
                m = re.compile(r"([A-Za-z_]\w*)\s*=(?!=)").match(self.s, self.i)
                if m:
                    self.i = m.end()
                    result[m.group(1)] = self.value()
                else:
                    result[n] = self.value()
                    n += 1
            self.ws()
            if self.s[self.i] in ",;":
                self.i += 1


def parse_savedvars(text, var=VAR):
    m = re.search(r"^\s*%s\s*=" % re.escape(var), text, re.M)
    if not m:
        raise LuaError("no %s assignment found" % var)
    p = _Parser(text)
    p.i = m.end()
    return p.value()


def _lua_str(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return '"%s"' % s.replace("|", "\\124")


def _lua_value(v, depth):
    if isinstance(v, dict):
        if not v:
            return "{}"
        pad, inner = "\t" * depth, "\t" * (depth + 1)
        # Integer keys 1..n are written positionally; everything else as ["k"].
        seq = [k for k in v if isinstance(k, int) and not isinstance(k, bool)]
        is_seq = len(seq) == len(v) and sorted(seq) == list(range(1, len(v) + 1))
        lines = []
        keys = list(range(1, len(v) + 1)) if is_seq else sorted(v, key=lambda k: (isinstance(k, str), str(k)))
        for k in keys:
            val = _lua_value(v[k], depth + 1)
            if is_seq:
                lines.append("%s%s," % (inner, val))
            else:
                ks = _lua_str(k) if isinstance(k, str) else repr(k)
                lines.append("%s[%s] = %s," % (inner, ks, val))
        return "{\n" + "\n".join(lines) + "\n" + pad + "}"
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(v)
    return _lua_str(str(v))


def dump_savedvars(data, var=VAR):
    return "%s = %s\n" % (var, _lua_value(data, 0))


# -- Names, keys and Raider.IO ------------------------------------------------

def normalize_realm(realm):
    """The addon's realm form: no spaces, apostrophes, hyphens or dots."""
    return re.sub(r"[\s\-'.]", "", realm or "")


def split_key(key):
    name, _, realm = key.partition("-")
    return name, realm


def slug_candidates(realm, overrides):
    """Raider.IO realm slugs to try for a normalized realm name."""
    if realm in overrides:
        return [overrides[realm]]
    low = realm.lower()
    return [low]


def fetch_profile(region, realm_slug, name, timeout=20):
    """Raider.IO's profile JSON for a character, or None if it does not exist."""
    url = SITE.format(region=region, realm=urllib.parse.quote(realm_slug),
                      name=urllib.parse.quote(name))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            return None
        raise


def declared_main(profile):
    """(name, normalized realm, class token) of the declared main, or None."""
    try:
        main = profile["characterDetails"]["characterCustomizations"]["main_character"]
    except (KeyError, TypeError):
        return None
    if not main:
        return None
    # The site suffixes the name with an internal id ("Yuntao-63621923").
    name = re.sub(r"-\d+$", "", main.get("name") or "")
    realm = normalize_realm((main.get("realm") or {}).get("name") or "")
    if not name or not realm:
        return None
    cls = ((main.get("class") or {}).get("slug") or "").upper().replace("-", "")
    return name, realm, cls or None


# -- Applying -----------------------------------------------------------------

def link_main(db, key, main, now):
    """Rate and link the main of `key`. Returns a list of change descriptions."""
    name, realm, cls = main
    mkey = "%s-%s" % (name, realm)
    if mkey == key:
        return []
    chars, players = db.setdefault("chars", {}), db.setdefault("players", {})
    c = chars[key]
    flag = c.get("f")
    changes = []

    pid = c.get("p") or (chars.get(mkey) or {}).get("p")
    if not pid:
        pid = db.get("nextPid", 1)
        db["nextPid"] = pid + 1
        players[pid] = {"name": name}
        changes.append("created person %r" % name)
    if c.get("p") != pid:
        c["p"] = pid
        changes.append("linked %s to person %d" % (key, pid))

    m = chars.get(mkey)
    if m is None:
        m = chars[mkey] = {"f": flag, "p": pid, "first": now, "rated": now, "rio": now,
                           "n": "Added from Raider.IO: main of %s" % key}
        if cls:
            m["cls"] = cls
        changes.append("added %s (%s), note: linked to %s" % (mkey, flag, key))
    else:
        if m.get("p") != pid:
            m["p"] = pid
            changes.append("linked existing %s to person %d" % (mkey, pid))
        if not m.get("f"):
            m["f"] = flag
            m["rated"] = now
            changes.append("rated existing %s %s" % (mkey, flag))
    return changes


def find_savedvars(path):
    if path:
        return path
    found = sorted(glob.glob(os.path.join(WTF, "Account", "*", "SavedVariables", FILE)))
    if not found:
        sys.exit("No %s found under %s.\nLog in once and log out (or /reload) so the "
                 "game writes it, or pass --file." % (FILE, WTF))
    if len(found) > 1:
        sys.exit("Several accounts have ratings; pass one with --file:\n  " + "\n  ".join(found))
    return found[0]


def wow_running():
    try:
        out = subprocess.run(["pgrep", "-f", "World of Warcraft.app/Contents/MacOS/World of Warcraft"],
                             capture_output=True, text=True).stdout
    except OSError:
        return False
    return bool(out.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", help="path to MythicPlusPersonalPlayerRatings.lua (default: found under ../../../WTF)")
    ap.add_argument("--region", default="us", help="Raider.IO region (default: us)")
    ap.add_argument("--flag", default="avoid", choices=["good", "neutral", "avoid"],
                    help="which rating to look up mains for (default: avoid)")
    ap.add_argument("--realm-map", help='extra JSON file {"Area52": "area-52"} on top of the bundled realms.json')
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default: 1)")
    ap.add_argument("--resync", action="store_true",
                    help="also look up characters already marked as checked (the flag set here and in the addon's editor)")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--force", action="store_true", help="write even if WoW looks like it is running")
    args = ap.parse_args(argv)

    path = find_savedvars(args.file)
    with open(path, encoding="utf-8") as fh:
        db = parse_savedvars(fh.read())
    # realms.json (next to this script) maps realm names to Raider.IO slugs; a
    # --realm-map file is optional and overrides it.
    overrides = {}
    for mp in (os.path.join(HERE, "realms.json"), args.realm_map):
        if mp and os.path.exists(mp):
            with open(mp, encoding="utf-8") as fh:
                overrides.update(json.load(fh))

    if args.apply and wow_running() and not args.force:
        sys.exit("World of Warcraft is running; it would overwrite the change at logout. "
                 "Close it first (or use --force).")

    now = int(time.time())
    rated = sorted(k for k, c in db.get("chars", {}).items() if c.get("f") == args.flag)
    targets = rated if args.resync else [k for k in rated if not db["chars"][k].get("rio")]
    print("%d %s character(s) in %s, %d to look up (%d already checked)"
          % (len(rated), args.flag, path, len(targets), len(rated) - len(targets)))
    total, unresolved, failed = 0, [], []
    for key in targets:
        name, realm = split_key(key)
        profile = None
        for slug in slug_candidates(realm, overrides):
            try:
                profile = fetch_profile(args.region, slug, name)
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                print("  %s: lookup failed (%s)" % (key, e))
                failed.append(key)
                break
            time.sleep(args.delay)
            if profile:
                break
        if not profile:
            if key not in failed:
                unresolved.append(key)
            continue
        # Looked up: remember it so the next run skips this character.
        changes = []
        if not db["chars"][key].get("rio"):
            db["chars"][key]["rio"] = now
            changes.append("marked %s as checked" % key)
        main_char = declared_main(profile)
        if not main_char:
            print("  %s: no declared main" % key)
            total += len(changes)
            continue
        changes += link_main(db, key, main_char, now)
        for line in changes:
            print("  %s: %s" % (key, line))
        total += len(changes)

    if unresolved:
        print("Not found on Raider.IO (wrong region, or a realm missing from "
              "realms.json; see --realm-map): " + ", ".join(unresolved))
    if not total:
        print("Nothing to change.")
        return 0
    if not args.apply:
        print("Dry run: %d change(s) not written. Re-run with --apply." % total)
        return 0

    # One backup only: the state before this run, replacing any earlier one
    # (including the timestamped copies older versions of this script left).
    backup = path + ".link_alts.bak"
    for old in glob.glob(path + ".bak.*"):
        if re.fullmatch(r"\d+", old[len(path) + 5:]):
            os.remove(old)
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dump_savedvars(db))
    print("Wrote %d change(s). Backup: %s" % (total, backup))
    return 0


if __name__ == "__main__":
    sys.exit(main())
