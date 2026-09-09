"""Yajna Reader (events/.../reader) — guards for the named failures of #279.

Each test names the failure it catches:
  * a build that leaves a placeholder behind ships a page with no content / no config;
  * a card whose text begins with a corpus path or a "Narrator / occasion" bullet
    puts metadata on the readable card (KA, 2026-09-09 — the file path and the satsang-frame
    remark were both read out loud);
  * a speaker line carrying "satsang frame" is the internal meta-reference KA asked to be moved
    into the notes;
  * a story deck without a `label` loses "Remembrance of <swami>" on the card.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re

import pytest

def _reader_dir() -> pathlib.Path:
    """Where the reader's sources live.

    Two layouts, one test file: inside the working repo they sit under events/<occasion>/reader;
    in the exported public repo they sit at the root beside these tests (#302). Resolving this
    here is what lets the same guards ship with the public project instead of being ajna-only.
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    nested = root / "events" / "lakshmi-narayana-mahayajna-2026-09" / "reader"
    return nested if (nested / "build.py").is_file() else root


READER = _reader_dir()
DECKS = json.loads((READER / "decks.json").read_text("utf-8"))
CARDS = [(d, it) for d in DECKS["decks"] for it in d["items"]]



def _corpus_prefix() -> str:
    """The first two segments of a card's source_file, e.g. "<root>/<sub>".

    Read from the data so this published file never spells out the private tree (#302).
    """
    for d in DECKS["decks"]:
        for it in d["items"]:
            sf = it.get("source_file")
            if sf:
                return "/".join(sf.replace("\\", "/").split("/")[:2])
    raise AssertionError("no card carries a source_file -- the guard cannot derive the prefix")

def _load_build():
    spec = importlib.util.spec_from_file_location("yr_build", READER / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_fills_every_placeholder(tmp_path):
    out = _load_build().build(tmp_path / "reader.html")
    html = out.read_text("utf-8")
    for ph in ("__PAYLOAD_JSON__", "__CONFIG_JSON__", "__THEME_CSS__"):
        assert ph not in html
    assert '<script id="config" type="application/json">{' in html
    assert '<style id="theme">:root{--ash:' in html
    assert "drag the bar" in html  # the scrub hint


@pytest.mark.parametrize("deck,card", CARDS, ids=[f"{d['id']}:{it['title'][:30]}" for d, it in CARDS])
def test_card_text_carries_no_metadata(deck, card):
    head = card["md"].lstrip()[:120]
    assert not head.startswith("`" + _corpus_prefix()), "source path leaked onto the card"
    assert not re.match(r"-\s*\*\*Narrator", head, re.I), "narrator/occasion bullet leaked onto the card"
    assert "satsang frame" not in (card.get("speaker") or ""), "meta-reference on the credit line"


def test_story_decks_carry_a_remembrance_label():
    for d in DECKS["decks"]:
        if d["kind"] == "stories":
            assert d.get("label", "").startswith("Remembrance of "), d["id"]


def test_shown_cards_all_have_a_source_file():
    shown = [(d, it) for d, it in CARDS if d["kind"] != "parked"]
    missing = [it["title"] for d, it in shown if not it.get("source_file")]
    assert not missing, missing


OFFICIAL = ["Swami Sivananda", "Swami Satyananda", "Swami Niranjanananda", "Swami Satyasangananda"]


def test_swami_decks_follow_the_official_order_on_every_tab():
    """#299: a deck appended to decks.json lands LAST in its tab, which is how the Quotes tab came
    to show Swami Satyananda before Swami Sivananda (KA, 2026-09-09: "sw. sivananda, sw. satyananda,
    sw. niranjanananda, sw. satyasangananda is the official order")."""
    by_kind: dict[str, list[int]] = {}
    for d in DECKS["decks"]:
        rank = next((i for i, s in enumerate(OFFICIAL) if d["short"].startswith(s)), None)
        if rank is not None:
            by_kind.setdefault(d["kind"], []).append(rank)
    assert by_kind, "no swami-named decks found"
    for kind, ranks in by_kind.items():
        assert ranks == sorted(ranks), f"{kind}: {[OFFICIAL[r] for r in ranks]}"


def test_built_page_carries_no_internal_source_path(tmp_path):
    """#299 (KA, 2026-09-09): "Don't show kg txt file source path ... I don't want this accidentally
    publicly visible even in beta demos." Hiding the Reference row was not enough — the path sat in
    the embedded payload of every card and in the flag / feedback report lines. The build strips it.

    The prefix is derived from decks.json, never written here: this file is itself published
    (#302), and a guard that must name the private tree in order to defend it leaks the very
    thing it guards. Deriving it also survives a rename of the corpus root."""
    html = _load_build().build(tmp_path / "r.html").read_text("utf-8")
    assert _corpus_prefix() not in html
    assert '"source_file"' not in html
