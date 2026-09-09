# lnmy-reader -- notes for Claude

This repo is the PUBLIC face of the Lakshmi-Narayana Mahayajna Reader. It is exported from a
private working repo; `export_lnmy_reader.py` there copies an allowlist of paths into here.

## Two rules that matter more than the rest

1. **Nothing from the corpus may ever land here.** No fulltexts, no knowledge-graph output, no
   response bank, no extraction reports. If a change seems to need one of those, it belongs
   upstream, not here.
2. **`index.html` is generated.** Never hand-edit it. Change `template.html`, `decks.json` or
   `config.json` and re-run `python build.py --out index.html`. A hand edit is lost on the next
   export.

## Working here

- Test: `python -m pytest tests/ -q` (the browser guards need playwright).
- Every test names the failure it catches. Do not add a test that cannot name one.
- `build.py` stamps the commit into the page; two builds of the same commit are identical.

## Upstream

Issues about the READINGS (a wrong page, a differing word, an attribution) belong here.
Issues about how the passages were extracted from the books belong upstream.
