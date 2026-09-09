"""Build yajna-reader.html from decks.json + config.json + template.html. No network, no model.

    python build.py            # writes config["output"] next to this file
    python build.py --out X    # elsewhere (tests)

The template carries three placeholders: __PAYLOAD_JSON__ (decks), __CONFIG_JSON__ (config),
__THEME_CSS__ (colour + type tokens rendered from config["theme"] / config["type"]). Leaving any
of them behind is a build failure, never a warning. Word counts are recomputed from the card
text so the reference strip cannot drift from what is on the card.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a single curly quote must not exit 1
REQUIRED = ("title", "md", "book")
PLACEHOLDERS = ("__PAYLOAD_JSON__", "__CONFIG_JSON__", "__THEME_CSS__")


def theme_css(cfg: dict) -> str:
    th, ty = cfg.get("theme") or {}, cfg.get("type") or {}

    def block(tokens: dict) -> str:
        return ";".join(f"--{k}:{v}" for k, v in tokens.items())

    light = block(th.get("light") or {})
    if ty.get("readSize"):
        light += f";--read:{ty['readSize']}"
    if ty.get("leading"):
        light += f";--lead:{ty['leading']}"
    if ty.get("measureEm"):
        light += f";--measure:{ty['measureEm']}"
    if ty.get("roomSize"):
        light += f";--room:{ty['roomSize']}"
    dark = block(th.get("dark") or {})
    return ('<style id="theme">:root{' + light + "}"
            '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){' + dark + "}}"
            ':root[data-theme="dark"]{' + dark + "}</style>")


def _js(obj) -> str:
    # "</" inside a JSON string must not be able to close the <script> tag.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")



def build_stamp(here: pathlib.Path) -> dict:
    """Commit date + short hash of HEAD, so a reader can say which build they are looking at.

    Derived from git, never from the clock: two builds of the same commit are byte-identical.
    No git (a tarball, a CI checkout without history) -> {} and the page hides the stamp.
    """
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h\t%cd", "--date=format:%Y-%m-%d %H:%M"],
                             cwd=here, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return {}
    if out.returncode != 0 or "\t" not in out.stdout:
        return {}
    commit, when = out.stdout.strip().split("\t", 1)
    return {"commit": commit, "when": when + " (NST)"}

def build(out: pathlib.Path | None = None, here: pathlib.Path = HERE) -> pathlib.Path:
    decks = json.loads((here / "decks.json").read_text("utf-8"))
    cfg = json.loads((here / "config.json").read_text("utf-8"))
    tpl = (here / "template.html").read_text("utf-8")
    # an exporter building outside the repo pre-seeds the stamp; git is unreachable there (#302)
    cfg["build"] = cfg.get("build") or build_stamp(here)
    expose_path = bool((cfg.get("features") or {}).get("showSourceFile"))   # #299: internal paths stay out of the page
    for d in decks["decks"]:
        for it in d["items"]:
            if not expose_path:
                it.pop("source_file", None)
            missing = [k for k in REQUIRED if not it.get(k)]
            if missing:
                raise SystemExit(f"build: deck {d['id']!r} card {it.get('title')!r} lacks {missing}")
            it["words"] = len(it["md"].split())
    html = (tpl.replace("__PAYLOAD_JSON__", _js(decks))
               .replace("__CONFIG_JSON__", _js(cfg))
               .replace("__THEME_CSS__", theme_css(cfg)))
    left = [p for p in PLACEHOLDERS if p in html]
    if left:
        raise SystemExit(f"build: placeholder(s) survived: {left}")
    target = out or (here / cfg.get("output", "yajna-reader.html"))
    target.write_text(html, "utf-8", newline="\n")
    n = sum(len(d["items"]) for d in decks["decks"])
    print(f"built {target} - {len(decks['decks'])} decks, {n} cards, {target.stat().st_size:,} bytes")
    return target


EDIT_FIELDS = ("title", "speaker", "theme", "why", "note", "md")


def _check_header(patch: dict, here: pathlib.Path) -> None:
    cfg = json.loads((here / "config.json").read_text("utf-8"))
    for k in ("repo", "project"):
        if patch.get(k) and cfg.get(k) and patch[k] != cfg[k]:
            raise SystemExit(f"refused: this JSON is for {patch.get('repo')} {patch.get('project')}, "
                             f"not {cfg.get('repo')} {cfg.get('project')} (mispaste?)")


def apply_patch(patch_path: pathlib.Path, here: pathlib.Path = HERE) -> None:
    """Write an edit-mode patch (order / hidden / edits) permanently into decks.json.
    Text edits ("md") are applied but printed loudly: run validate.py before building."""
    patch = json.loads(patch_path.read_text("utf-8")); _check_header(patch, here)
    dp = here / "decks.json"; decks = json.loads(dp.read_text("utf-8"))
    n_order = n_hidden = n_edit = 0; text_edits = []
    hidden = set(patch.get("hidden") or []); edits = patch.get("edits") or {}
    for d in decks["decks"]:
        order = (patch.get("order") or {}).get(d["id"])
        if order:
            by = {it["id"]: it for it in d["items"]}
            d["items"] = [by[i] for i in order if i in by] + [it for it in d["items"] if it["id"] not in order]; n_order += 1
        for it in d["items"]:
            if it["id"] in hidden and not it.get("hidden"):
                it["hidden"] = True; n_hidden += 1
            e = edits.get(it["id"])
            if e:
                for k in EDIT_FIELDS:
                    if k in e and e[k] != it.get(k):
                        it[k] = e[k]; n_edit += 1
                        if k == "md":
                            text_edits.append(it["title"])
    dp.write_text(json.dumps(decks, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"applied: {n_order} deck orders, {n_hidden} cards hidden, {n_edit} field edits")
    if text_edits:
        print("TEXT EDITED — run validate.py before build:", "; ".join(text_edits))


def build_selection(sel_path: pathlib.Path, out: pathlib.Path, here: pathlib.Path = HERE) -> pathlib.Path:
    """One hostable page holding only the selected cards, in that order (#282). The selection's
    deck.title / occasion / audio override the config; everything else is inherited."""
    sel = json.loads(sel_path.read_text("utf-8")); _check_header(sel, here)
    decks = json.loads((here / "decks.json").read_text("utf-8")); cfg = json.loads((here / "config.json").read_text("utf-8"))
    kinds = {}
    for t in cfg.get("tabs", []):
        for k in t.get("kinds", []):
            kinds[k] = t["id"]
    by = {}
    for d in decks["decks"]:
        for it in d["items"]:
            it = dict(it); it["kind"] = kinds.get(d["kind"], d["kind"]); it["deck_label"] = d.get("label") or d.get("short"); by[it["id"]] = it
    ids = sel.get("selection") or []
    if not ids:
        raise SystemExit("selection is empty — tick cards in Edit mode and copy the selection JSON")
    missing = [i for i in ids if i not in by]
    if missing:
        raise SystemExit(f"unknown card ids (decks.json changed since the selection?): {missing}")
    items = []
    for i in ids:
        it = by[i]; e = (sel.get("edits") or {}).get(i) or {}
        for k in EDIT_FIELDS:
            if k in e:
                it[k] = e[k]
        if not it.get("theme"):
            it["theme"] = it.pop("deck_label", "")
        it.pop("deck_label", None); it.pop("hidden", None); items.append(it)
    dk = sel.get("deck") or {}
    title = dk.get("title") or cfg.get("title", "Deck")
    decks_out = {"decks": [{"id": "deck", "kind": "deck", "short": title, "label": title, "attributed": "", "items": items}]}
    cfg_out = dict(cfg); cfg_out["tabs"] = [{"id": "deck", "label": title, "kinds": ["deck"]}]
    if dk.get("title"): cfg_out["title"] = dk["title"]
    if dk.get("occasion"): cfg_out["occasion"] = dk["occasion"]
    if dk.get("dates"): cfg_out["dates"] = dk["dates"]
    if (dk.get("audio") or {}).get("src"): cfg_out["audio"] = dk["audio"]
    tmp = pathlib.Path(str(out) + ".build"); tmp.mkdir(exist_ok=True)
    (tmp / "decks.json").write_text(json.dumps(decks_out, ensure_ascii=False), "utf-8")
    (tmp / "config.json").write_text(json.dumps(cfg_out, ensure_ascii=False), "utf-8")
    (tmp / "template.html").write_text((here / "template.html").read_text("utf-8"), "utf-8")
    try:
        return build(out, here=tmp)
    finally:
        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--apply", type=pathlib.Path, help="edit-mode patch JSON to write into decks.json, then build")
    ap.add_argument("--select", type=pathlib.Path, help="selection JSON -> one hostable deck page (needs --out)")
    a = ap.parse_args()
    if a.apply:
        apply_patch(a.apply)
    if a.select:
        if not a.out:
            raise SystemExit("--select needs --out <file.html>")
        build_selection(a.select, a.out)
    else:
        build(a.out)
