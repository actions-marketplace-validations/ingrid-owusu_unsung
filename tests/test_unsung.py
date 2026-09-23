"""Tests for unsung. No network: api._post is monkeypatched."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unsung.api as api  # noqa: E402
from unsung.api import Stats, collect  # noqa: E402
from unsung.card import THEMES, render  # noqa: E402


def _fake_payload(login="octo", created="2020-01-01T00:00:00Z"):
    def repo(nwo, priv=False):
        owner = nwo.split("/")[0]
        return {"nameWithOwner": nwo, "isPrivate": priv, "owner": {"login": owner}}

    return {
        "login": login,
        "name": "Octo Cat",
        "createdAt": created,
        "contributionsCollection": {
            "totalPullRequestReviewContributions": 5,
            "totalPullRequestContributions": 3,
            "totalIssueContributions": 2,
            "pullRequestReviewContributionsByRepository": [
                {"repository": repo("acme/widget"), "contributions": {"totalCount": 4}},
                {"repository": repo("octo/mine"), "contributions": {"totalCount": 9}},  # own -> excluded
                {"repository": repo("secret/x", priv=True), "contributions": {"totalCount": 7}},  # private
            ],
            "pullRequestContributionsByRepository": [
                {"repository": repo("acme/widget"), "contributions": {"totalCount": 2}},
                {"repository": repo("beta/tool"), "contributions": {"totalCount": 1}},
            ],
            "issueContributionsByRepository": [
                {"repository": repo("beta/tool"), "contributions": {"totalCount": 3}},
            ],
        },
    }


def test_collect_excludes_own_and_private(monkeypatch):
    monkeypatch.setattr(api, "_post", lambda token, variables: _fake_payload())
    s = collect("octo", token="x", since="year")
    assert s.reviews_given == 4          # own repo + private excluded
    assert s.prs_to_others == 3          # 2 + 1
    assert s.issues_for_others == 3
    assert s.projects_helped == 2        # acme/widget, beta/tool
    assert s.total_help == 10
    assert s.since_label == "the last year"


def test_top_helped_sorted(monkeypatch):
    monkeypatch.setattr(api, "_post", lambda token, variables: _fake_payload())
    s = collect("octo", token="x")
    # acme/widget: 4 review + 2 pr = 6 ; beta/tool: 1 pr + 3 issue = 4
    assert s.top_helped[0] == ("acme/widget", 6)
    assert s.top_helped[1] == ("beta/tool", 4)


def test_collect_requires_token():
    try:
        collect("octo", token="")
    except api.ApiError as e:
        assert "token" in str(e)
    else:
        raise AssertionError("expected ApiError")


def test_collect_case_insensitive_owner(monkeypatch):
    def payload(token, variables):
        p = _fake_payload(login="Octo")
        p["contributionsCollection"]["pullRequestContributionsByRepository"] = [
            {"repository": {"nameWithOwner": "OCTO/mine", "isPrivate": False,
                            "owner": {"login": "OCTO"}}, "contributions": {"totalCount": 5}},
        ]
        return p
    monkeypatch.setattr(api, "_post", payload)
    s = collect("Octo", token="x")
    assert s.prs_to_others == 0  # OCTO/mine is own repo despite case


def test_render_all_themes_valid_svg():
    s = Stats(login="octo", name="Octo", reviews_given=201, prs_to_others=126,
              issues_for_others=14, projects_helped=18,
              top_helped=[("a/b", 9), ("c/d", 5)])
    for theme in THEMES:
        svg = render(s, theme=theme)
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "201" in svg
        assert "Octo" in svg
        assert "unsung open-source work" in svg


def test_render_escapes_and_number_format():
    s = Stats(login="a<b", name='Ev&il "<x>"', reviews_given=12345,
              prs_to_others=0, issues_for_others=0, projects_helped=0)
    svg = render(s, animate=False)
    assert "12,345" in svg
    assert "&amp;" in svg and "&lt;" in svg
    assert "<x>" not in svg  # raw angle brackets escaped


def test_render_no_animate_has_no_animate_tag():
    s = Stats(login="o", name=None, reviews_given=1, prs_to_others=1,
              issues_for_others=1, projects_helped=1)
    assert "<animate" not in render(s, animate=False)
    assert "<animate" in render(s, animate=True)


def test_footer_names_fit_within_card():
    """Long owner/repo names must be ellipsized so the footer stays in the card."""
    from unsung.card import _fit_names, _FOOTER_CHAR_W, _FOOTER_PREFIX

    inner = 470 - 2 * 25
    budget = int(inner / _FOOTER_CHAR_W) - len(_FOOTER_PREFIX)
    long_names = [
        "kubernetes-sigs/aws-load-balancer-controller",
        "prometheus-operator/prometheus-operator",
        "opentelemetry/opentelemetry-collector-contrib",
    ]
    out = _fit_names(long_names, inner)
    assert len(out) <= budget
    assert out.endswith("\u2026")
    # short names are left untouched
    short = ["a/b", "c/d", "e/f"]
    assert _fit_names(short, inner) == "a/b, c/d, e/f"
    # a single over-long name is hard-cut with an ellipsis
    solo = _fit_names(["x" * 200], inner)
    assert len(solo) <= budget and solo.endswith("\u2026")


def test_title_fits_within_card():
    """A long display name must be truncated so the header stays in the card."""
    from unsung.card import _fit_title, _fit_generic, _TITLE_CHAR_W, _TITLE_SUFFIX

    inner = 470 - 2 * 25
    budget = int(inner / _TITLE_CHAR_W)
    # long display name -> ellipsized name, suffix preserved, fits budget
    out = _fit_title("Alexander Christopher Montgomery-Wellington", inner)
    assert len(out) <= budget
    assert out.endswith(_TITLE_SUFFIX)
    assert "\u2026" in out
    # short name is left untouched
    assert _fit_title("dan", inner) == "dan" + _TITLE_SUFFIX
    # custom title is hard-cut generically
    long_custom = "A very very very very very very very long custom title here"
    cut = _fit_generic(long_custom, inner)
    assert len(cut) <= budget and cut.endswith("\u2026")
    assert _fit_generic("short", inner) == "short"


def test_render_long_name_title_in_svg():
    s = Stats(login="x", name="Alexander Christopher Montgomery-Wellington")
    svg = render(s)
    import re

    t = re.search(r'font-size="18"[^>]*>([^<]*)<', svg).group(1)
    assert t.endswith("'s unsung open-source work")
    assert "\u2026" in t
