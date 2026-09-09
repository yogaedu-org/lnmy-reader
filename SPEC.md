# Yajna Reader — design spec

**Spec version: round-5, 2026-09-09.** The `version` field in `config.json` carries the same string and
is embedded in every build (`CONFIG.version`), so a built page can always be matched to the spec that
describes it. Every round of the owner's feedback is a numbered entry in §12; the sections above it
always describe the CURRENT page.

The reader is a single self-contained HTML page that puts one verbatim reading at a time in front of a
room: a projector, a shared screen, or a phone held up in a waiting hall. Everything in this spec is what
`template.html` implements; `config.json` decides the values, `decks.json` the content, and `build.py`
assembles them. **Recreatable means:** the three files plus this spec are enough to rebuild the page
byte-for-byte (`python build.py`); nothing about its look lives anywhere else.

Versioning of a live programme: the build a room actually used is tagged
`yajna-reader/<event-slug>-<date>` (PROTOCOL.md → "Tag a programme").

## 1. Structure of the page

| region | what it is | hidden in Live | hidden in Auto/fit |
|---|---|---|---|
| top bar | left: **Edit** switch. Right, in this order: ⚑ flag · ⓘ about · 🔗 parameters · ◐ theme · **Live** switch · pipe · **Auto** switch + seconds + "sec" | no | yes |
| credit line | "Made with … by YogicApproach · Yajna Reader · repo", shown by ⓘ | no | yes |
| parameters panel | field + Apply + Copy link, shown by 🔗 (§7) | no | yes |
| header | occasion (eyebrow, ember), title (light serif), dates + total count | dates | yes |
| tabs | one per reading type (`config.tabs`), count badge per tab | counts | yes |
| deck pills | one per deck inside the tab; hidden when a tab has one deck | no | yes |
| progress | segmented bar + "n of N"; picked cells outlined when `cards=` restricts | no | yes |
| deck editor | Edit mode's list (§8) | yes | yes |
| card | the reading: eyebrow, title, credit, source line, body, attribution | no | no |
| reference strip | metadata grid + "why it lands" + caveats + feedback box, on the card's ash panel | yes | yes |
| controls | Previous / Next + keyboard hint (bottom only since round 3) | hint | yes |
| footer | the verbatim promise | yes | yes |

Rule: **the card carries only what is read or spoken.** Provenance notes, attribution method and
editorial remarks belong in the reference strip, which Live mode removes.

**Deck order on every tab is the official order of the swamis:** Swami Sivananda · Swami Satyananda ·
Swami Niranjanananda · Swami Satyasangananda. Decks are shown in `decks.json` order, so a new deck is
inserted at its place, never appended (guard: `tests/test_yajna_reader_build.py`).

## 2. Navigation

- **Previous / Next** buttons below the card, `←` `→`, `space` (next).
- **Progress bar = slider.** Every segment is a reading (up to 60 segments; beyond that one segment
  spans several). Click a segment to jump; press and drag to scrub; the counter follows live. Hit area
  is 24 px tall while the drawn bar stays 6 px. `Home`/`End` jump to the first/last reading. The bar is
  a `role=slider` with `aria-valuenow`, keyboard-focusable. Config: `features.progressScrub`.
- **Tabs and decks remember position**: leaving a deck and coming back returns to the same reading.
- Moving to a reading while Auto is on restarts the timer from that reading.
- Keys are ignored while typing in any field (seconds, parameters, editor, feedback).

## 3. Card layouts

**Passage / story** (left-aligned): eyebrow (theme, or the deck's `label`, or its `short`), title, credit
line (speaker · event · date), source line (§4), body at `--read` size with `--lead` leading, in ONE
reading measure: `--measure` em (`config.type.measureEm`, 34) — the same measure and size in every mode,
so nothing rescales between the page and the fit view; a long reading scrolls inside the card.

**Quote** (centred): a large, light opening mark in ember at 30 % opacity above the text; body at
1.55–2.2 rem, weight 300, max width 23 em; then the source line, then the attribution in italic serif
("— Swami Sivananda Saraswati"). The credit line is suppressed when it would only repeat the attribution.
In the fit view the two meta lines stay pinned at the top, the mark is a fixed ornament, and only the
quote and its attribution scale, between `config.fit.quoteMinPx` and `quoteMaxPx` (24–52 px).

**Source line.** Book title and page are links in the text's own colour and weight, no underline until
hover; a small `↗` sits at the far right of the line at 45 % opacity in the sans face. Opens in a new tab.
Config: `features.sourceLinks`.

## 4. Type and colour

- Faces: **Spectral** (reading, titles; 300/400/600 + italics) and **IBM Plex Sans** (UI, metadata;
  400/500/600), from Google Fonts with system fallbacks. The page is fully readable if the fonts never
  load.
- Sizes: body `--read` (`config.type.readSize`, 1.5 rem; 1.25 rem under 640 px), leading `--lead`
  (`config.type.leading`, 1.62); fit-view reading size `--room` (`config.type.roomSize`, 1.7 rem);
  h1 clamp 1.9–2.9 rem; h2 clamp 1.5–2.1 rem.
- Palette: `config.theme.light` / `config.theme.dark` are the single source; `build.py` writes them as
  CSS custom properties (`__THEME_CSS__`), and the table below is a copy for reading, not a second source.

| token | role | light | dark |
|---|---|---|---|
| ash | page ground | #EFEEE9 | #141310 |
| ash-2 | reference panel, idle segments | #E4E2DB | #1B1A16 |
| surface | card | #FBFAF7 | #1E1D19 |
| ink / ink-2 | text / body text | #191816 / #3B3833 | #EFEBE1 / #D3CDC0 |
| muted | metadata, hints | #6C675E | #9A9487 |
| line | borders | #D8D4C9 | #33302A |
| ember / ember-soft | accent: occasion, active tab, current / done segments | #7A2E1E / #9C4A33 | #E08663 / #C96E4D |
| leaf | eyebrow on cards | #1F4D46 | #7FB5AA |

**Theme (round 5).** The page follows the device (`prefers-color-scheme`) unless a theme is chosen with
the ◐ button: ◐ follows the device · ○ light · ● dark, cycling in that order; the choice is remembered
per browser (`localStorage`, key `<storageKey>-theme`). The CSS keys on `data-theme="light|dark"` on the
root element; "follows the device" hands back whatever the host page had stamped there at load, so an
embedding host's own theme setting is honoured, never wiped. Reduced-motion users get no transitions.

## 5. Live mode (`L`)

Removes counts, the reference strip, footer, dates and the keyboard hint; centres the card in at least
56 vh. For screen-sharing to a room. Remembered per browser. `config.features.liveDefault`.

## 6. Auto-advance + fit-to-window (`A`, `Esc` stops)

The waiting-room view. Turning Auto on: switches Live on, hides every control, makes the card fill the
window, and advances every N seconds (`config.auto.defaultSeconds`, bounds `minSeconds` … `maxSeconds`,
remembered per browser). **N = 0 is manual**: the full-window view without advancing (same as `?fit=1`).
It loops by default (`config.auto.loop`). A hidden tab pauses the timer; returning resumes without a
catch-up jump. Each new reading starts scrolled to its top. A status line bottom-right ("n / N · 5 s ·
Esc stops · F full screen") fades after `config.auto.hudFadeSeconds` of idleness and wakes on any input.
Background audio (`config.audio`, or a hosted deck's own) plays only while Auto is on.

## 7. URL parameters and the 🔗 panel (rounds 4–5)

`tab`, `deck`, `cards` (ranges / indices / ids; restricts Prev / Next / Auto and outlines the picked
cells), `card`, `auto`, `fit`, `live` — full table in PROTOCOL.md → "URL parameters". Parameters are read
from the query string and from the `#` fragment; a fragment value wins. The 🔗 button opens a field holding
the current view's parameter string; **Apply** (Enter) shows that view without a reload, **Copy link**
copies a full link (or just the parameters when the reader is embedded). Esc closes.

## 8. Edit mode (`E`, round 3)

The Edit switch opens the deck editor under the progress bar: tick to select, drag to reorder, eye to
hide, pencil to edit title / credit / theme / notes / text. Everything is local to the browser until
"Copy selection JSON" or "Copy full patch" hands it to `build.py --select` / `--apply` (PROTOCOL.md).
Hidden and reordered cards are honoured by the reading view at once.

## 9. Flag and feedback (round 3)

⚑ copies a one-line report for the current card (tab / deck / card id · title · book · page · SYP URL)
and opens `config.feedback.docUrl` when set. The reference strip's feedback box stores a per-card note;
"Copy as JSON" / "Copy all pending" emit self-identifying JSON for `curate.py`. Neither line carries an
internal file path (§10).

## 10. What the page must NOT contain (round 5)

**No internal source path.** `decks.json` keeps `source_file` (the corpus text each card was verified
against — `validate.py` needs it), but `build.py` strips it from the embedded payload unless
`config.features.showSourceFile` is true (it is false), and the flag / feedback lines never include it.
The SYP link on the card is the authoritative source and is sufficient. Guard: the built page contains
no `kb/corpus` (`tests/test_yajna_reader_build.py`). The path can always be recovered from `decks.json`
by card id.

## 11. Content rules the page relies on

Every card is verbatim from its source (`validate.py`, PROTOCOL.md, CURATION.md). Metadata never sits on
the card; where the source does not state a speaker, edition or page, the reference strip says "not
stated in the text". Page links open the book at the PDF page matching the printed page via the per-book
offset in `data/reports/printed_page_map.json`; titles with no reliable offset link to the book and say
so in the caveat line. Attribution that cannot be established is left out, not guessed.

## 12. Change log (owner's rounds)

| round | date | issues | what changed on the page |
|---|---|---|---|
| 1 | 2026-09-09 | #259 #279 | one reading per screen; scrubbable progress bar; Live; Auto + fit; deep links; metadata off the card |
| 2 | 2026-09-09 | #280 #281 #282 | Edit mode (select / reorder / hide / edit → JSON); hostable single deck with audio; PPTX export |
| 3 | 2026-09-09 | #283–#288 #295 | top nav dropped; title + page linked unstyled with the arrow last; fit scales only reading + citation; HUD fade; per-card feedback JSON; flag button; stable card ids; 92 vw fit columns |
| 4 | 2026-09-09 | #296 | Edit switch top-left, ⚑ ⓘ Live \| Auto right; one 34 em measure in every mode; quote bounds 24–52 px; scroll in Auto; Auto 0 = manual; URL parameters; Niranjanananda + Satyasangananda decks |
| 4b | 2026-09-09 | #297 | parameters from the `#` fragment; 🔗 panel (Apply / Copy link) |
| 5 | 2026-09-09 | #299 | official swami order on every tab; ◐ theme toggle; no internal source path anywhere in the artifact; this spec versioned |
| 5a | 2026-09-09 | #298 | top bar wraps at phone width — the page no longer scrolls sideways at 320/400 px |
| 6 | 2026-09-09 | #301 | slideshow opens at 15 s; the info line drops the repo, says “Created with” and ends with a feedback link to a per-app issue template; git-derived build stamp; ⚑ moved onto the card with a confirmation you can see |
| 6b | 2026-09-09 | #301 | the info line links the word “Feedback” and closes with the ↗ indicator; ⚑ opens the issue form already filled in with the card |

## 13. Non-goals

No search, no server, no analytics, no network calls beyond the two font stylesheets and the markdown
library. It must open from a file.
