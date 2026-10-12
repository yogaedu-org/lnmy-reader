"""#1 -- the committed index.html must be what build.py makes from the committed inputs.

Failure caught: decks.json / config.json / template.html edited, `python build.py --out index.html`
forgotten; GitHub Pages then serves a page that no longer matches the repo.

The one thing allowed to differ is the build stamp (the commit the page was built from): a page
built from commit X is committed in commit X+1, so the stamp can never equal HEAD.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUTS = ("build.py", "decks.json", "config.json", "template.html")
STAMP = re.compile(r'"build":\{[^}]*\}')


def _built(root: pathlib.Path, out: pathlib.Path) -> str:
    spec = importlib.util.spec_from_file_location("sync_build", root / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build(out, here=root)
    return STAMP.sub('"build":{}', out.read_text("utf-8"))


def _drifts(root: pathlib.Path, committed: pathlib.Path, tmp: pathlib.Path) -> bool:
    return _built(root, tmp / "rebuilt.html") != STAMP.sub('"build":{}', committed.read_text("utf-8"))


def test_committed_index_matches_a_fresh_build(tmp_path):
    assert not _drifts(ROOT, ROOT / "index.html", tmp_path), (
        "index.html is stale against decks.json/config.json/template.html -- "
        "run: python build.py --out index.html")


def test_the_guard_notices_an_input_edited_without_a_rebuild(tmp_path):
    """Guards the guard: a comparison that ignored more than the stamp would pass forever."""
    work = tmp_path / "copy"
    work.mkdir()
    for name in INPUTS:
        shutil.copy(ROOT / name, work / name)
    shutil.copy(ROOT / "index.html", work / "index.html")
    tpl = work / "template.html"
    tpl.write_text(tpl.read_text("utf-8").replace("<title>", "<title>EDITED ", 1), "utf-8")
    assert _drifts(work, work / "index.html", tmp_path)
