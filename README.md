# Lakshmi-Narayana Mahayajna Reader

One reading at a time, on a screen a room can follow.

**Read it: https://yogaedu-org.github.io/lnmy-reader/**

The page is a single self-contained HTML file. No build step to view it, no network calls,
no tracking. Open `index.html` from disk and it works.

## What this is

Passages, stories and quotes drawn from the published books of Swami Sivananda Saraswati,
Swami Satyananda Saraswati, Swami Niranjanananda Saraswati and Swami Satyasangananda
Saraswati, curated for reading aloud during a yajna. Every card carries its book, page and a
link to the source edition. Nothing here replaces the books -- it points at them.

## Rebuilding it

The page is generated, and everything needed to generate it is in this repo:

```
decks.json  +  config.json  +  template.html
        |   build.py
        v
   index.html
```

```sh
python build.py --out index.html
python -m pytest tests/ -q          # needs playwright for the browser guards
```

`build.py` stamps the page with the commit it was built from, so the footer always says which
build you are looking at.

## The files

| file | what it is |
|---|---|
| `index.html` | the built reader -- this is what GitHub Pages serves |
| `decks.json` | the readings: 13 decks, every card with its citation |
| `config.json` | occasion, tabs, theme, typography, auto-advance, feedback link |
| `template.html` | the whole page -- CSS, markup and JS, with three build placeholders |
| `build.py` | decks + config + template -> `index.html` |
| `tests/` | the guards -- each test names the failure it catches |

## How it got here

Every card is a verbatim excerpt, checked against the source text before it ships. That
checking, and the curation that chooses a passage in the first place, happen in a private
working repo that holds the corpus; they are not part of this one. What this repo has is the
reader and everything needed to rebuild it.

## What changed

| round | what changed on the page |
|---|---|
| 1 | one reading per screen; scrubbable progress bar; Live; Auto + fit; deep links |
| 2 | hostable single deck with audio; PPTX export |
| 3 | title + page linked with the arrow last; fit scales only reading + citation; stable card ids |
| 4 | one 34 em measure in every mode; quote bounds 24-52 px; URL parameters |
| 5 | official swami order on every tab; theme toggle; no internal source path anywhere |
| 6 | slideshow opens at 15 s; feedback link to a prefilled issue form; build stamp; flag on the card |

## Feedback## Feedback

Something wrong on a card? Click the flag at its top right: the issue form opens with the
card already filled in. Or open an issue directly.

## Provenance

Built and maintained from a private working repo that holds the corpus and the extraction
machinery; this repo carries the reader and everything needed to rebuild it. Exported by
`export_lnmy_reader.py` under an allowlist -- nothing crosses that is not named there.

## Licence

MIT for the code (see `LICENSE`). The quoted passages remain the property of their
publishers and are reproduced here for study, with citation.
