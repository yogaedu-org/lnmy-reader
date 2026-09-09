"""Yajna Reader URL parameters (#296) and the in-page parameters panel (#297) — browser guards.

KA, 2026-09-09: "no links working. no way to test parameters feature." The parameters worked, but
only through 127.0.0.1 links that reach nothing off this machine, and the artifact URL carries no
query string into the page. Each test names the failure it catches:
  * the `#tab=...` fragment form is silently dropped (the only form a query-stripping host can pass);
  * a fragment loses to the query string, against what PROTOCOL.md documents;
  * the panel's Apply does not change the view (dead wiring — the one thing that lets him test
    parameters from inside the artifact);
  * keystrokes typed into the field fire the page shortcuts (space advances, A starts Auto, L flips
    Live, E opens Edit) — the arrow/space handler only skips buttons;
  * the field misreports the view it was opened on, so a copied link points elsewhere.
Runs headless Chromium on the built file (file://); no network, no server.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
from urllib.parse import parse_qs, urlparse

import pytest

pw = pytest.importorskip("playwright.sync_api")

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
DECKS = {d["id"]: d for d in json.loads((READER / "decks.json").read_text("utf-8"))["decks"]}
QUOTES = "quotes-sivananda-quotes"
STORIES = "stories-niranjanananda-stories"


@pytest.fixture(scope="module")
def page_url(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("yr_build_params", READER / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.build(tmp_path_factory.mktemp("reader") / "yajna-reader.html")
    return out.resolve().as_uri()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    # clipboard granted: the flag button's confirmation depends on the copy actually succeeding,
    # and a denied clipboard makes it report "copy blocked" instead of what the room would see.
    ctx = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    yield ctx.new_page()
    ctx.close()


def _count(page) -> str:
    return page.locator("#count").inner_text().strip()


def test_hash_form_opens_the_view(page, page_url):
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=3")
    assert "is-quote" in page.evaluate("document.body.className")
    assert _count(page) == f"3 of {len(DECKS[QUOTES]['items'])}"


def test_hash_wins_over_query(page, page_url):
    page.goto(page_url + f"?tab=stories&deck={STORIES}#tab=quotes&deck={QUOTES}")
    assert "is-quote" in page.evaluate("document.body.className")


def test_panel_apply_changes_the_view_without_reload(page, page_url):
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=3")
    page.click("#linkBtn")
    page.fill("#linkIn", f"tab=stories&deck={STORIES}&cards=1-3,7&card=2")
    page.click("#linkApply")
    assert "is-quote" not in page.evaluate("document.body.className")
    assert _count(page) == f"2 of {len(DECKS[STORIES]['items'])}"
    assert page.input_value("#linkIn") == f"tab=stories&deck={STORIES}&cards=1,2,3,7&card=2"
    assert page.locator("#linkMsg").inner_text() == "applied"


def test_typing_in_the_field_fires_no_page_shortcut(page, page_url):
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=3")
    live_before = page.get_attribute("#live", "aria-pressed")
    page.click("#linkBtn")
    page.type("#linkIn", " a l e f")
    assert page.get_attribute("#auto", "aria-pressed") == "false"
    assert page.get_attribute("#live", "aria-pressed") == live_before
    assert "edit-on" not in page.evaluate("document.body.className")
    assert _count(page) == f"3 of {len(DECKS[QUOTES]['items'])}"


def test_field_reports_the_loaded_view(page, page_url):
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=3")
    page.click("#linkBtn")
    assert page.input_value("#linkIn").startswith(f"tab=quotes&deck={QUOTES}&card=3")


def _theme(page):
    return page.evaluate("document.documentElement.getAttribute('data-theme')")


def test_theme_toggle_cycles_device_light_dark_and_persists(page, page_url):
    """#299: the toggle must stamp data-theme (the CSS keys on it), remember the choice per browser,
    and return to the device setting — an attribute left behind would pin one theme for good."""
    page.goto(page_url)
    assert _theme(page) is None
    page.click("#themeBtn"); assert _theme(page) == "light"
    page.click("#themeBtn"); assert _theme(page) == "dark"
    page.reload(); assert _theme(page) == "dark"
    assert page.locator("#themeBtn").inner_text() == "\u25cf"
    page.click("#themeBtn"); assert _theme(page) is None
    assert page.locator("#themeBtn").inner_text() == "\u25d0"


def test_theme_device_mode_restores_the_hosts_own_stamp(browser, page_url):
    """#299: the artifact host stamps data-theme on the root for an explicit viewer choice. "Follows
    your device" must hand that stamp back, not wipe it."""
    ctx = browser.new_context()
    # at document start <html> does not exist yet; stamp it the moment it appears, before body scripts
    ctx.add_init_script("new MutationObserver(function(m, o){ if (document.documentElement){"
                        " document.documentElement.setAttribute('data-theme','light'); o.disconnect(); } })"
                        ".observe(document, {childList: true});")
    pg = ctx.new_page(); pg.goto(page_url)
    assert _theme(pg) == "light"
    pg.click("#themeBtn"); pg.click("#themeBtn"); assert _theme(pg) == "dark"
    pg.click("#themeBtn"); assert _theme(pg) == "light"
    ctx.close()


def test_space_in_the_feedback_box_types_a_space_and_stays_on_the_card(page, page_url):
    """#300: the arrow/space handler skipped only buttons, so a space in the feedback textarea advanced
    the card and was swallowed (2 of 119 -> 3 of 119 on one keystroke, 2026-09-09).

    The box is stripped from the public build (#302), where this failure cannot occur -- so there
    the test asserts the box really is gone rather than passing vacuously. The same handler is
    still exercised against a field that exists in BOTH builds by
    test_typing_in_the_field_fires_no_page_shortcut.
    """
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=2")
    has_box = json.loads((READER / "config.json").read_text("utf-8")).get(
        "features", {}).get("cardFeedback", True)
    if has_box is False:
        assert page.locator("#fbText").count() == 0
        return
    page.click("#fbText")
    page.keyboard.type("a b")
    assert page.input_value("#fbText") == "a b"
    assert _count(page) == f"2 of {len(DECKS[QUOTES]['items'])}"


# ---- #298: the top bar overflows at phone width -------------------------------------------------
# KA reads on a phone during the yajna. At 320 px the top bar's right group (4 icons + Live + Auto +
# the seconds field) is a no-wrap inline-flex row, so the PAGE scrolls sideways and the reading text
# sits off-screen. Named failure: document.scrollWidth > window.innerWidth at phone widths.
@pytest.mark.parametrize("width", [320, 400])
def test_topbar_does_not_scroll_the_page_sideways(page, page_url, width):
    page.set_viewport_size({"width": width, "height": 720})
    page.goto(page_url)
    scroll_w, inner_w = page.evaluate(
        "() => [document.documentElement.scrollWidth, window.innerWidth]"
    )
    assert scroll_w <= inner_w, f"page scrolls sideways at {width}px: {scroll_w} > {inner_w}"


# ---- #301 item 1: "Make slideshow default to 15 seconds" -- the field opened on 5.
def test_auto_opens_at_fifteen_seconds(page, page_url):
    page.goto(page_url)
    assert page.input_value("#autoSecs") == "15"


# ---- #301 item 2: KA, "Don't include this info in the info line: <the repo slug>".
#      The line read "... Yajna Reader . <owner>/<repo> . round-5a 2026-09-09". Asserted against
#      config.repo rather than a literal, so the guard travels with the export and never has to
#      name a private repo to defend it.
def test_info_line_does_not_name_the_repo(page, page_url):
    page.goto(page_url)
    page.click("#infoBtn")
    line = page.locator("#siteCredit").inner_text()
    repo = json.loads((READER / "config.json").read_text("utf-8")).get("repo", "")
    assert repo, "config.repo must be set for this guard to mean anything"
    assert repo not in line, line
    assert repo.split("/")[-1] not in line, line
    assert "Yajna Reader" in line, line


# ---- #301 item 3: "Flag button isn't doing anything. I was expecting it at the top right of a card."
#      It DID copy the reference, but its only confirmation (#fbStatus) lives in the card's reference
#      strip: is_visible False, never scrolled into view, display:none under Live. Measured 2026-09-09.
def test_flag_sits_on_the_card_not_in_the_topbar(page, page_url):
    page.goto(page_url)
    assert page.evaluate("!!document.querySelector('article#card #flagBtn')")
    assert not page.evaluate("!!document.querySelector('.topbar #flagBtn')")


def test_flag_confirms_where_you_can_see_it(page, page_url):
    page.goto(page_url)
    page.click("#flagBtn")
    page.wait_for_selector("#flagMsg.show")          # the copy is a promise; wait for the callback
    msg = page.locator("#flagMsg")
    assert msg.is_visible(), "the flag's confirmation must be visible"
    assert "filled in" in msg.inner_text().lower(), msg.inner_text()
    assert page.evaluate(
        "()=>{const r=document.getElementById('flagMsg').getBoundingClientRect();"
        "return r.top>=0 && r.top<window.innerHeight}"
    ), "the confirmation must be on screen, not buried down the page"


def test_flag_confirms_in_live_mode_too(page, page_url):
    """Live hides the whole reference strip -- the old #fbStatus could never be seen there."""
    page.goto(page_url)
    page.click("#live")
    page.click("#flagBtn")
    page.wait_for_selector("#flagMsg.show")
    assert page.locator("#flagMsg").is_visible()


# ---- #301 item 4: "where is the Share Feedback link. I was expecting it in the info line; at end of
#      it for example." There was none -- config.feedback carried only an empty docUrl.
def test_info_line_ends_with_the_feedback_note_and_link(page, page_url):
    page.goto(page_url)
    page.click("#infoBtn")
    line = page.locator("#siteCredit").inner_text()
    assert line.startswith("Created with"), line
    assert "Feedback is welcome." in line, line
    assert line.rstrip().endswith("↗"), line            # our ext arrow closes the line
    assert page.locator("#feedbackLink").inner_text().strip() == "Feedback"
    href = page.get_attribute("#feedbackLink", "href")
    assert "issues/new?template=yajna-reader-feedback.yml" in href, href
    assert page.get_attribute("#feedbackArrow", "href") == href
    # KA, 2026-09-10: "feedback needs to go to the lnmy repo, not ajna's." Reader feedback belongs
    # with the reader's own repo -- and the working repo is PRIVATE, so a link there 404s for
    # everyone but the owner. Asserted in BOTH builds: this file ships to the public repo too.
    assert href.startswith("https://github.com/yogaedu-org/lnmy-reader/"), href


def test_build_stamp_names_the_commit_the_page_was_built_from(page, page_url):
    """After the yogaedu.org study tool: a reader must be able to say which build they see."""
    page.goto(page_url)
    page.click("#infoBtn")
    assert page.locator("#buildStamp").is_visible()
    assert re.fullmatch(r"[0-9a-f]{7,40}", page.locator("#buildCommit").inner_text().strip())
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} \(NST\)", page.locator("#buildWhen").inner_text().strip())


# ---- #301 round 6b: "The flag click would pre-populate the issue ... it would make it so smooth to
#      know the card, tab, source." It did not -- the flag opened a blank form and left the reference
#      on the clipboard, so every report needed a paste that is easy to forget.
def test_flag_opens_a_prefilled_issue_form(page, page_url):
    page.goto(page_url + f"#tab=quotes&deck={QUOTES}&card=3")
    # Capture what the page ASKS for. Following the popup would assert on where GitHub sends an
    # anonymous visitor (login?return_to=...), which tests GitHub's auth, not this code -- and it
    # differs between the private working repo and the public export this file also ships to.
    page.evaluate("window.__opened = null; window.open = function(u){ window.__opened = u; return null; };")
    page.click("#flagBtn")
    url = page.evaluate("window.__opened")
    assert url, "the flag must open the feedback form"
    assert "template=yajna-reader-feedback.yml" in url, url
    q = parse_qs(urlparse(url).query)
    assert q["card"][0].startswith("[Yajna Reader flag]"), q["card"][0]
    assert QUOTES in q["card"][0], q["card"][0]            # tab, deck and the stable card id travel
    third = DECKS[QUOTES]["items"][2]
    assert third["id"] in q["card"][0], q["card"][0]
    assert third["title"] in q["card"][0], q["card"][0]
    assert third["book"] in q["card"][0], q["card"][0]     # the source travels too
    assert q["title"][0].startswith("[reader] "), q["title"][0]
    assert third["title"] in q["title"][0], q["title"][0]


# ---- #302 follow-up: KA's public-build review -----------------------------------------------
def test_credit_names_who_it_was_made_for(page, page_url):
    """KA: "Created with ... by YogicApproach -> ... by YogicApproach for yogaedu.org"."""
    page.goto(page_url)
    page.click("#infoBtn")
    line = page.locator("#siteCredit").inner_text()
    assert "by YogicApproach for yogaedu.org" in line, line
    # The label is the domain; the href is where the domain will eventually forward. yogaedu.org
    # does NOT resolve today -- registered, delegated to Cloudflare, zone never activated, so its
    # nameservers REFUSE every query (verified against Google and Cloudflare resolvers 2026-09-09).
    # A credit link that 404s on a public page is worse than an indirect one, so it points at the
    # org until the domain answers. Flip this one href then; the label never changes.
    href = page.get_attribute("#siteCredit a:has-text('yogaedu.org')", "href")
    assert href == "https://github.com/yogaedu-org", href


def test_the_dates_line_says_excerpts_from_the_syp_corpus(page, page_url):
    """KA: "342 verbatim readings from the corpus -> 342 verbatim excerpts from the SYP corpus".
    "readings" collided with the Readings tab, and "the corpus" named nothing a visitor knows."""
    page.goto(page_url)
    line = page.locator("#dates").inner_text()
    assert "verbatim excerpts from the SYP corpus" in line, line
    assert "verbatim readings from the corpus" not in line, line


def test_edit_matches_what_this_build_declares(page, page_url):
    """Edit is on in our working build and off in the public export (#302), and this file ships
    with BOTH -- so the guard asserts the page agrees with its own config rather than with one
    repo's answer. A page that declares edit and does not offer it, or offers it while declaring
    it off, is the failure either way."""
    page.goto(page_url)
    want = json.loads((READER / "config.json").read_text("utf-8")).get("features", {}).get("edit", True)
    if want is False:
        assert page.locator("#editBtn").count() == 0
        assert page.locator("#editor").count() == 0
        return
    assert page.locator("#editBtn").is_visible()
    page.click("#editBtn")
    assert "edit-on" in page.evaluate("document.body.className")


def test_edit_removed_entirely_when_the_feature_is_off(browser, tmp_path_factory):
    """Off must mean gone, not hidden: a hidden Edit button still answers the E shortcut, and a
    reader who trips it lands in a curation UI whose output nothing can validate."""
    import json as _json
    src = READER
    out = tmp_path_factory.mktemp("noedit")
    for name in ("decks.json", "template.html", "build.py"):
        (out / name).write_bytes((src / name).read_bytes())
    cfg = _json.loads((src / "config.json").read_text("utf-8"))
    cfg.setdefault("features", {})["edit"] = False
    (out / "config.json").write_text(_json.dumps(cfg, ensure_ascii=False), "utf-8")
    import importlib.util as _iu
    spec = _iu.spec_from_file_location("yr_noedit", out / "build.py")
    mod = _iu.module_from_spec(spec); spec.loader.exec_module(mod)
    built = mod.build(out / "r.html", here=out)

    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(built.resolve().as_uri())
    assert pg.locator("#editBtn").count() == 0, "the Edit button must be removed, not hidden"
    assert pg.locator("#editor").count() == 0, "the editor panel must be removed, not hidden"
    pg.keyboard.press("e")
    assert "edit-on" not in pg.evaluate("document.body.className"), "E must not open a removed UI"
    ctx.close()


def test_topbar_controls_stay_right_with_or_without_edit(page, page_url):
    """KA, 2026-09-09: "The header UI seems to all be on the left side now. I didn't ask for any
    changes." A regression I introduced with the Edit feature flag: .topbar is space-between with
    two children, so removing the Edit button left ONE child and space-between parked it on the
    left. Measured before the fix: the right group spanned 120..599 in a 1160-wide bar.

    Asserted in this build AND in a build with Edit off, because the bug only appears in the
    second -- a guard that checks only our own build would never have caught it.
    """
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(page_url)
    edge = page.evaluate(
        "() => {const b=document.querySelector('.topbar').getBoundingClientRect(),"
        "r=document.querySelector('.topbar .right').getBoundingClientRect();"
        "return Math.round(b.right - r.right);}")
    assert edge < 3, f"the controls are not against the right edge (gap {edge}px)"


def test_topbar_controls_stay_right_when_edit_is_off(browser, tmp_path_factory):
    """The same failure, in the configuration that actually exhibited it."""
    import json as _json, importlib.util as _iu
    out = tmp_path_factory.mktemp("noedit_bar")
    for n in ("decks.json", "template.html", "build.py"):
        (out / n).write_bytes((READER / n).read_bytes())
    cfg = _json.loads((READER / "config.json").read_text("utf-8"))
    cfg.setdefault("features", {})["edit"] = False
    (out / "config.json").write_text(_json.dumps(cfg, ensure_ascii=False), "utf-8")
    spec = _iu.spec_from_file_location("yr_bar", out / "build.py")
    mod = _iu.module_from_spec(spec); spec.loader.exec_module(mod)
    built = mod.build(out / "r.html", here=out)

    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.goto(built.resolve().as_uri())
    assert pg.locator("#editBtn").count() == 0
    edge = pg.evaluate(
        "() => {const b=document.querySelector('.topbar').getBoundingClientRect(),"
        "r=document.querySelector('.topbar .right').getBoundingClientRect();"
        "return Math.round(b.right - r.right);}")
    ctx.close()
    assert edge < 3, f"with Edit off the controls drifted left (gap {edge}px)"


def test_feedback_never_points_at_a_private_repo(page, page_url):
    """The named failure: a feedback link into a private tracker looks fine to the one person who
    can see it and is a dead end for everyone else. Checked on every affordance that opens the
    form -- the info-line word, its arrow, and the card's flag."""
    page.goto(page_url)
    page.evaluate("window.__o=null; window.open=function(u){window.__o=u;};")
    page.click("#flagBtn")
    page.wait_for_selector("#flagMsg.show")
    flag_url = page.evaluate("window.__o")
    page.click("#infoBtn")
    urls = [page.get_attribute("#feedbackLink", "href"),
            page.get_attribute("#feedbackArrow", "href"),
            flag_url]
    for u in urls:
        assert u, "every feedback affordance must have a destination"
        # Positive assertion only. Naming the private repo here would put it in a file that ships
        # to the public one -- the export's content scan refuses exactly that, and refused this
        # test's first draft. Pinning the destination excludes every other repo anyway.
        assert u.startswith("https://github.com/yogaedu-org/lnmy-reader/"), u


def test_card_feedback_box_matches_what_this_build_declares(page, page_url):
    """Our build keeps the box (it is how KA hands Claude a card); the public export strips it.
    This file ships to both, so it asserts the page against its own config -- the lesson of the
    top-bar regression, where a flag was added and only the on-configuration was ever tested."""
    page.goto(page_url)
    want = json.loads((READER / "config.json").read_text("utf-8")).get("features", {}).get("cardFeedback", True)
    if want is False:
        assert page.locator("#fb").count() == 0, "the box must be removed, not hidden"
        assert page.locator("#fbText").count() == 0
    else:
        assert page.locator("#fb").count() == 1
        assert page.locator("#fbText").is_visible()


def test_the_flag_still_works_when_the_feedback_box_is_gone(browser, tmp_path_factory):
    """The named failure: the box holds #fbStatus, which the flag used to write into. Removing the
    box could have left the flag throwing on a null element -- silently, since a JS error stops the
    handler and the page looks merely unresponsive."""
    import json as _json, importlib.util as _iu
    out = tmp_path_factory.mktemp("nofb")
    for n in ("decks.json", "template.html", "build.py"):
        (out / n).write_bytes((READER / n).read_bytes())
    cfg = _json.loads((READER / "config.json").read_text("utf-8"))
    cfg.setdefault("features", {})["cardFeedback"] = False
    (out / "config.json").write_text(_json.dumps(cfg, ensure_ascii=False), "utf-8")
    spec = _iu.spec_from_file_location("yr_nofb", out / "build.py")
    mod = _iu.module_from_spec(spec); spec.loader.exec_module(mod)
    built = mod.build(out / "r.html", here=out)

    ctx = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(built.resolve().as_uri())
    assert pg.locator("#fb").count() == 0
    pg.evaluate("window.open=function(u){window.__o=u;};")
    pg.click("#flagBtn")
    pg.wait_for_selector("#flagMsg.show")
    assert "filled in" in pg.locator("#flagMsg").inner_text().lower()
    assert errors == [], errors
    ctx.close()
