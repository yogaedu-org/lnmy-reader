"""Ground every card in decks.json against the source text it claims; show the diff when it
is not verbatim.

    python validate.py                 # all cards -> validation.md + validation.html; exit 1 on any failure
    python validate.py --deck <id>     # one deck
    python validate.py --resolve       # first fill/repair each card's source_file by CONTENT, then validate

A card PASSES when its text is a contiguous substring of the source at the EXACT or NORMALISED
tier of scripts/_common/grounding.py (typesetting-neutral: whitespace, hyphen line-breaks,
quotes, case). Page-number-only lines are removed from the source first, because a reading that
crosses a printed page is still verbatim. Anything else is reported with a standard side-by-side
diff (difflib.HtmlDiff) between the card and the closest window of the source, so an edit is
visible word by word. A card whose source text is absent on this machine is UNCHECKED, never
passed. A deck with "kind": "parked" is not shown on any tab; its cards are reported as PARKED
<tier> (with the diff) and do not fail the run. The build does not depend on this; run it before
committing a content change.

--resolve exists because a book title is not a file name (#278): "Yajna" is served by an
edition-stemmed file, magazines by a month stem, and a same-titled file can be another edition.
It searches kb/corpus/fulltext for files that contain a phrase from the card, keeps the first
file where the WHOLE card passes, and writes that path into the card's source_file. A card no
file passes for keeps its old value and is reported, never silently reassigned.
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import pathlib
import re
import subprocess
import sys
import textwrap
from difflib import SequenceMatcher

HERE = pathlib.Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a single curly quote must not exit 1
REPO = HERE.parents[2]
FULLTEXT = REPO / "kb" / "corpus" / "fulltext"
sys.path.insert(0, str(REPO / "scripts" / "_common"))
from grounding import TIER_EXACT, TIER_NORMALISED, SourceIndex, normalise, tokens  # noqa: E402

PAGE_LINE = re.compile(r"^[ \t]*\d{1,4}[ \t]*\r?\n", re.M)
MD_STRIP = re.compile(r"(\*\*|__|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)|`|^>[ \t]?|^#{1,6}[ \t]+)", re.M)
_cache: dict[str, SourceIndex | None] = {}


def plain(md: str) -> str:
    return re.sub(r"[ \t]+", " ", MD_STRIP.sub("", md)).strip()


def index_for(rel: str) -> SourceIndex | None:
    if rel not in _cache:
        p = REPO / rel
        _cache[rel] = (SourceIndex(PAGE_LINE.sub("", p.read_text("utf-8", errors="replace")))
                       if p.is_file() else None)
    return _cache[rel]


def passes(rel: str, q: str) -> bool:
    idx = index_for(rel)
    return bool(idx) and idx.locate(q).tier in (TIER_EXACT, TIER_NORMALISED)


def closest_window(src_text: str, quote: str, pad: int = 12) -> str:
    s, q = tokens(src_text), tokens(quote)
    if not s or not q:
        return ""
    m = SequenceMatcher(None, s, q, autojunk=False).find_longest_match(0, len(s), 0, len(q))
    start = max(0, m.a - m.b - pad)
    end = min(len(s), start + len(q) + 2 * pad)
    return " ".join(s[start:end])


def wrap(text: str) -> list[str]:
    return textwrap.wrap(text, 72) or [""]


# ----------------------------------------------------------------------------- resolve
def _phrases(q: str, n: int = 5) -> list[str]:
    """Two short, line-safe phrases: from the start and from the middle of the card."""
    w = q.split()
    out = []
    for at in (0, len(w) // 2):
        seg = w[at:at + n]
        if len(seg) == n:
            out.append(" ".join(seg))
    return out


def candidates_for(q: str, book: str) -> list[str]:
    found: list[str] = []
    for ph in _phrases(q):
        try:
            r = subprocess.run(["rg", "-l", "-F", "--", ph, str(FULLTEXT)], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            found += [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass
    words = [w for w in re.findall(r"\w+", book.lower()) if len(w) > 3][:3]
    by_title = [str(p) for p in FULLTEXT.glob("*.txt") if words and all(w in p.name.lower() for w in words)]
    seen, rels = set(), []
    for p in found + by_title:
        rel = pathlib.Path(p).resolve().relative_to(REPO.resolve()).as_posix()
        if rel not in seen:
            seen.add(rel); rels.append(rel)
    return rels


def resolve(decks: dict) -> tuple[int, list[str]]:
    fixed, unresolved = 0, []
    for d in decks["decks"]:
        for it in d["items"]:
            q = plain(it["md"])
            cur = it.get("source_file") or ""
            if cur and passes(cur, q):
                continue
            hit = next((rel for rel in candidates_for(q, it.get("book", "")) if passes(rel, q)), None)
            if hit:
                it["source_file"] = hit; fixed += 1
            else:
                unresolved.append(f"{d['id']} | {it['title']}")
    return fixed, unresolved


# ----------------------------------------------------------------------------- check
def check(deck_filter: str | None, decks: dict):
    rows, diffs = [], []
    for d in decks["decks"]:
        if deck_filter and d["id"] != deck_filter:
            continue
        for it in d["items"]:
            rel = it.get("source_file") or ""
            idx = index_for(rel) if rel else None
            if idx is None:
                rows.append((d["id"], it["title"], "UNCHECKED", 0.0, rel or "no source_file"))
                continue
            q = plain(it["md"])
            v = idx.locate(q)
            ok = v.tier in (TIER_EXACT, TIER_NORMALISED)
            # a "parked" deck is not shown on any tab: report its state, never fail the run on it
            verdict = "PASS" if ok else ("PARKED " + v.tier if d.get("kind") == "parked" else v.tier)
            rows.append((d["id"], it["title"], verdict, v.score, v.reason))
            if not ok:
                win = closest_window(idx.norm, normalise(q))
                a, b = wrap(win), wrap(" ".join(tokens(normalise(q))))
                table = difflib.HtmlDiff(wrapcolumn=72).make_table(
                    a, b, "source (closest window)", "card", context=True, numlines=2)
                diffs.append((d["id"], it["title"], v.tier, v.score, table))
    return rows, diffs


def write_reports(rows, diffs, here: pathlib.Path = HERE) -> None:
    md = ["# Card validation", "", "| deck | card | verdict | score | reason |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {s:.2f} | {r} |" for a, b, c, s, r in rows]
    (here / "validation.md").write_text("\n".join(md) + "\n", "utf-8", newline="\n")
    style = ("<style>body{font:14px system-ui;margin:24px}table.diff{font-family:ui-monospace,monospace;"
             "font-size:12px;border:1px solid #ccc;width:100%}.diff_add{background:#dfd}.diff_chg{background:#ffd}"
             ".diff_sub{background:#fdd}td{vertical-align:top;padding:1px 4px}h2{margin-top:32px}</style>")
    n_pass = sum(1 for r in rows if r[2] == "PASS")
    n_unc = sum(1 for r in rows if r[2] == "UNCHECKED")
    body = [f"<h1>Card validation</h1><p>{n_pass} pass / {len(rows) - n_pass - n_unc} fail / {n_unc} unchecked</p>"]
    for deck_id, title, tier, score, table in diffs:
        body.append(f"<h2>{html.escape(deck_id)} - {html.escape(title)} <small>{tier} {score:.2f}</small></h2>{table}")
    (here / "validation.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Card validation</title>" + style + "".join(body),
        "utf-8", newline="\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deck")
    ap.add_argument("--resolve", action="store_true", help="fill/repair source_file by content first")
    args = ap.parse_args()
    decks_path = HERE / "decks.json"
    decks = json.loads(decks_path.read_text("utf-8"))
    if args.resolve:
        fixed, unresolved = resolve(decks)
        decks_path.write_text(json.dumps(decks, ensure_ascii=False, indent=1), "utf-8", newline="\n")
        print(f"resolve: {fixed} source_file values set/repaired, {len(unresolved)} cards no file passes")
        for u in unresolved:
            print("  UNRESOLVED", u)
    rows, diffs = check(args.deck, decks)
    write_reports(rows, diffs)
    fails = [r for r in rows if r[2] not in ("PASS", "UNCHECKED") and not r[2].startswith("PARKED")]
    unchecked = [r for r in rows if r[2] == "UNCHECKED"]
    parked = [r for r in rows if r[2].startswith("PARKED")]
    print(f"{len(rows)} cards: {len(rows) - len(fails) - len(unchecked) - len(parked)} pass, {len(fails)} fail, "
          f"{len(unchecked)} unchecked, {len(parked)} parked -> validation.md, validation.html")
    for r in fails:
        print(f"  FAIL {r[0]} | {r[1]} | {r[2]} {r[3]:.2f} {r[4]}")
    sys.exit(1 if fails else 0)
