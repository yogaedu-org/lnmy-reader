# Curation protocol — adding a person's stories or quotes to the reader

Owner rule (KA, 2026-09-09, #296): *"I hope you have a reusable prompt, protocol, and/or scripts for
that. We need that documented and committed for determinism and evolution."* This is it. Two halves:
a deterministic scan (`curate.py candidates`) and a judged selection (a person or a model, using the
prompt below), joined by files that are committed so any deck can be re-derived or extended.

```
candidates/<person>-<kind>.json   ←  curate.py candidates   (pure scan; same corpus → same file)
selections/<person>-<kind>.json   ←  the selector's judgement (ids, titles, trims, credits, why)
decks.json                        ←  curate.py add           (verbatim cards; validate.py runs on the deck)
```

## 1. Mine candidates (deterministic, no model)

```
python curate.py candidates --person "Swami Niranjanananda Saraswati" --kind quotes  --alias Niranjan --per-book 16 --max 160 --out candidates/niranjanananda-quotes.json
python curate.py candidates --person "Swami Niranjanananda Saraswati" --kind stories --alias Niranjan \
    --book "Bihar School of Yoga: The Vision of a Sage" --book "Satyam, Krishna and Niranjan" --book "My Inheritance of Sannyasa" --out candidates/niranjanananda-stories.json
```

- **Quotes** come from books whose `author` in `data/books.json` contains `--alias` (or the person's
  second name). The first 3 % of each book (copyright, dedication, contents) is skipped. A sentence
  qualifies when it is 10–38 words, starts with a capital, ends with a stop, names none of the
  institutions, is not deictic ("This…", "Today…", "As I said…"), and scores ≥ 3 on the theme
  keywords + "you / one / life / mind / heart" + a copula. The top `--per-book` by score are kept.
- **Stories** come from `--book` titles (or, without them, books whose title names the person, and
  the person's own memoir/satsang titles). Windows of consecutive paragraphs, 150–650 words, are
  scored on narrative markers ("once", "one day", "he said", "in 19xx"…), name mentions and
  first-person pronouns; overlapping windows are dropped; the top `--per-book` are kept.
- Every candidate carries: book, author (from books.json — sometimes wrong, override in the
  selection), year (from the stem), **printed page = the nearest bare page-number line above the
  text** (the header rule the earlier hand-curated cards used; page lines that look like years are
  ignored), `source_file`, deep link (`deeplink_base/<page + offset>` when the page map's offset
  has confidence ≥ 0.8, else the bare book link), and a theme guess.

Re-running on the same corpus gives the same candidates. Change the corpus, the aliases or the
book list and the file changes with them: commit both.

## 2. Select (judgement) — the prompt

Read the candidates with `python curate.py show --candidates <file>` (previews) and
`--ids S03,S07` (full text). Then write `selections/<person>-<kind>.json`:

```json
{"_this_is": "Yajna Reader curation selection — <repo> <project> — feed to curate.py add",
 "made": "<date> (<who>)",
 "candidates": ["candidates/a.json", "candidates/b.json"],
 "deck": {"id": "stories-<person>-stories", "kind": "stories", "short": "Swami X", "label": "Remembrance of Swami X", "attributed": "Swami X Saraswati"},
 "picks": [
   {"id": "S014", "from": "candidates/b.json", "title": "…", "trim": {"start": "first words", "end": "last words"},
    "speaker": "who is telling it, in a listener's words", "why": "one line", "note": "provenance remarks", "author": "", "page": "50–51"}
 ]}
```

**The prompt for the selector (a person or a model):**

> You are choosing readings for a room. From these candidates keep only text that is (a) verbatim
> — you may cut a window at a sentence boundary with `trim`, never rewrite or bridge; (b) a story
> with a scene, people and something that happens (for stories) or a sentence that stands alone
> without its paragraph (for quotes); (c) actually in the person's voice or about the person —
> compilations with several speakers (Glimpses, country volumes) need the chapter byline, so
> prefer the person's own books; when the voice is uncertain, leave it out. Give each pick a title a
> listener would understand, a `speaker` line that says who is telling it, and a one-line `why`. Put
> provenance ("the passage opens mid-conversation", "author on the record is a subtitle") in
> `note`, never in the text. Group quotes under 4–8 theme titles. Do not invent pages, dates or
> occasions: the candidate's page is the header rule's answer; correct it only from the folio.

## 3. Add, validate, build

```
python curate.py add --selection selections/<person>-<kind>.json   # appends to decks.json, validates that deck
python validate.py && python build.py
```

`add` refuses an unknown id, a `trim` that is not verbatim, and never repairs text. A card that
fails validation stays in `decks.json` for the diff to be read, and the run exits 1 — do not build
until it passes or is parked.

## 4. Record

Commit `candidates/`, `selections/`, `decks.json`, the built page and this file's changes in one
commit named for the deck ("feat(#N): reader — Swami X stories (9) and quotes (21) via curate.py").
The round's issue gets a line: how many candidates, how many kept, from which books.

## Known limits (2026-09-09)

- Story mining favours the narrator's voice in a book; a memoir about person A inside a book by
  person B surfaces under B's alias. Reading the candidates is what catches it.
- The header page rule is right for the fulltexts checked so far; a book that prints its folio at
  the foot of the page will be one page off — the deep link is the check.
- Books whose fulltext is one paragraph per line (no blank lines) yield no story windows.
