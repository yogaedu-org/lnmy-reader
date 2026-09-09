# Yajna Reader — card protocol

How a card gets in, changes, moves, or leaves. The page is never edited by hand: **`decks.json` is
the source of truth, `build.py` writes the page, `validate.py` proves the words.**

```
decks.json  +  config.json  +  template.html   --build.py-->   yajna-reader.html
decks.json  +  kb/corpus/fulltext/*.txt        --validate.py-> validation.md / validation.html
```

## The shape of a card

```json
{
  "title":       "Why he was named Kuppuswamy",
  "md":          "Swami Sivanandaji’s life was divided into two chapters ...",   // markdown; paragraphs = blank line
  "attributed":  "Swami Sivananda Saraswati",      // whose words / whose life — shown under a quote, in the strip otherwise
  "speaker":     "Swami Niranjanananda, telling the story of Swami Sivananda's life.",  // credit line on the card; "" = none
  "event": "", "date": "",                          // credit line, after the speaker
  "book": "Guru Charitra", "author": "Swami Niranjanananda Saraswati", "year": "2024", "edition": "2024",
  "page": "50–51",                                  // PRINTED page(s), as the book prints them
  "url": "https://www.satyamyogaprasad.net/ebooks/<id>/62", "exact": true,   // pdf page = printed + offset; exact=false → book link only
  "theme": "",                                      // eyebrow on the card; "" → the deck's label
  "why": "...", "note": "",                         // reference strip only ("Why it lands"; caveats/provenance)
  "source_file": "kb/corpus/fulltext/Guru Charitra.txt",   // the text validate.py checks against
  "words": 258                                      // recomputed by build.py; never edit
}
```

Deck fields: `id` (stable, kebab), `kind` (matches a tab's `kinds`), `short` (pill text),
`label` (eyebrow on cards without a theme, e.g. "Remembrance of Swami Sivananda"), `attributed`
(deck default, informational), `items`.

## Add a card

1. Find the passage in `kb/corpus/fulltext/<book>.txt` (or the stemmed file — `validate.py --resolve`
   finds the right one by content). Copy it **verbatim**; reflow line breaks into paragraphs; drop
   page-number lines. Do not fix typos, do not shorten with an ellipsis, do not merge two places.
2. Printed page: read the folio the fulltext preserves around the passage. PDF page = printed page +
   the book's `offset` in `data/reports/printed_page_map.json` (`books.<stem>.offset`; use
   `deeplink_base` + `/` + pdf page). If the book has no map entry or `confidence` < 0.8, use the
   bare book URL and `"exact": false`.
3. Fill `speaker` only with what a listener needs ("Swami Chidananda, on Kuppuswami's childhood.").
   Provenance and framing ("told inside the book's satsang frame", "attribution inferred from the
   title page") go in `note`.
4. Insert into the deck's `items` at the position it should be read. Order in the file is the order
   on screen.
5. `python validate.py` — the card must be PASS. Then `python build.py`. Open the page, check the
   card in the tab, in Live, and in Auto (fit).
6. Commit `decks.json` + `yajna-reader.html` together: `feat(#<issue>): reader — add "<title>"`.

## Edit a card

Text: never — replace it with the correct verbatim text instead (validate will refuse a paraphrase).
Metadata (title, speaker, theme, why, note, page/url): edit in `decks.json`, build, commit.

## Move a card

Within a deck: reorder in `items`. To another deck: cut and paste the object; the deck's `kind`
decides which tab shows it. Position and tab memory in the browser are by index, so a big reorder
resets where viewers were — fine between programmes, avoid during one.

## Remove a card

Delete the object. For "hide for this programme but keep", move it to a deck whose `kind` is not in
any tab (e.g. `"kind": "parked"`) — it stays validated and versioned without being shown.

## Add a deck or a tab

Deck: append to `decks` with a new `id`; its `kind` must appear in one of `config.tabs[].kinds` or it
is parked. Tab: add to `config.tabs`; tabs with zero cards are not rendered.

## Build, validate, publish

```
python events/lakshmi-narayana-mahayajna-2026-09/reader/validate.py [--resolve]
python events/lakshmi-narayana-mahayajna-2026-09/reader/build.py
python -m pytest tests/test_yajna_reader_build.py -q
```

Publishing is a republish of the same artifact URL (Claude Code → Artifact tool with the existing
`url`, or the hosted copy per #282). Never change the favicon or title on a redeploy.

## Tag a programme

After the last build that a room actually saw:

```
git tag -a yajna-reader/lakshmi-narayana-2026-09 -m "Yajna Reader as used 8–12 Sep 2026, Sri Lakshmi-Narayana Mahayajna"
git push origin yajna-reader/lakshmi-narayana-2026-09
```

`git checkout yajna-reader/<tag> -- events/<event>/reader/` brings that exact page back later.

## What validate.py guarantees, and what it does not

Guarantees: every card's text is a contiguous substring of its `source_file` at the EXACT or
NORMALISED tier of `scripts/_common/grounding.py` (whitespace, hyphenation at line ends, quote
glyphs and case are neutral; page-number-only lines are ignored). A FUZZY or ABSENT card is listed
with a side-by-side word diff against the closest window of the source in `validation.html`.

Does not: check the printed page, the speaker, or the year — those are read by a person from the
folio and the title page. UNCHECKED means the source text is not on this machine, never a pass.

## Edit mode, selections, hosted decks, PowerPoint (round 3: #280 #281 #282)

**Edit** (top-left toggle, or `E`) opens the deck editor above the card: drag rows to reorder,
tick to select, eye to hide, pencil to edit title / credit / theme / why / note / text. Every change
is local to the browser (localStorage) and previews live in the reading view. Nothing reaches the
repo until you copy JSON:

| button | JSON | what to do with it |
|---|---|---|
| Copy selection JSON | `{selection:[ids…], hidden, edits, deck:{title, occasion, audio}}` | `python build.py --select sel.json --out deck.html` → one hostable page with only those cards, in that order; `deck.audio.src` (an MP3/OGG URL or a relative file) plays while Auto runs |
| Copy full patch | `{order:{deck:[ids…]}, hidden:[ids…], edits:{id:{…}}}` | `python build.py --apply patch.json` writes it into `decks.json` permanently (text edits are listed loudly: run `validate.py` before building) |

Both JSONs open with a `_this_is` line naming this repo and project; `build.py` refuses a JSON
made for another repo or project.

**PowerPoint / Google Slides:** `python export_pptx.py --select sel.json --out deck.pptx`
(or `--deck <id>`, `--all`). One 16:9 slide per card in the reader's palette and faces; the
reference strip goes to the speaker notes. Upload the `.pptx` to Google Drive and open with
Slides. Cards over ~420 words are listed for a human to split.

**Hosting a deck:** `deck.html` is self-contained (fonts and the markdown library from CDNs).
Publish it as an Artifact (keep the same URL for the same programme) or drop it on any static
host; the tag rule above applies to the build the room used.

**Feedback and flags** (reference strip, non-live): type on any card, *Copy as JSON* clears the
box and marks it sent; edit again to send an update; *Copy all pending* gathers every unsent
draft across tabs. *Flag ↗* copies a one-line report and opens `config.feedback.docUrl` when set.
*ⓘ* shows the credit line.

## URL parameters (round 4: #296)

Every parameter is optional and combinable. Indices are 1-based within the deck; card ids are the
`id` values in `decks.json` (the part after the colon is enough).

| parameter | values | effect |
|---|---|---|
| `tab` | `yajna` · `passages` · `stories` · `quotes` | opens that tab |
| `deck` | a deck id, e.g. `stories-niranjanananda-stories` | opens that deck inside the tab |
| `cards` | `1-5,9,12` or ids `why-he-was-named-kuppuswamy,the-new-dhoti` | shows only those cards, in deck order; their cells are outlined in the bar; Prev / Next / Auto move only among them |
| `card` | one index or id | starts on that card (no restriction) |
| `auto` | seconds; `0` = manual | starts Auto (full-window) at that pace |
| `fit` | `1` | full-window view without advancing (same as `auto=0`) |
| `live` | `1` | Live mode on (counts and reference strip hidden) |

Local forms: `file:///…/reader/yajna-reader.html?…` (works from disk in Chrome/Edge) or
`http://127.0.0.1:8010/events/lakshmi-narayana-mahayajna-2026-09/reader/yajna-reader.html?…`
after `python archive/offline-replica/serve.py 8010`.

### Testing and sharing parameters from inside the reader (#297)

The 🔗 button in the top bar opens a field holding the parameter string of the view you are on
(`tab=…&deck=…&cards=…&card=…`, plus `auto=` / `live=1` when those are on). Edit it and press
**Apply** (or Enter) — the reader shows that view at once, exactly as if it had been loaded with those
parameters, no reload and no link needed. **Copy link** copies a full link to the view when the reader
runs on its own address, and just the parameter string when it runs inside a host page (paste it after
the reader address's `?` or `#`). Esc closes the field; the page shortcuts do not fire while typing in it.

Parameters are also read from the `#` fragment — `yajna-reader.html#tab=quotes&deck=quotes-sivananda-quotes&card=3`
— and a fragment value wins over the same query value. Use the `#` form on any host that strips
query strings from the page it embeds.

Which link reaches which device:

| link | reaches |
|---|---|
| the claude.ai artifact URL | any device, but the host does not pass `?…` into the page — use 🔗 → Apply, or a `#` form if the host keeps fragments |
| `http://127.0.0.1:8010/…?…` | only this machine, only while `serve.py 8010` runs |
| `file:///…/reader/yajna-reader.html?…` | only a machine that has the repo |
| a hosted copy (#282) `…/yajna-reader.html?…` or `#…` | any device |
