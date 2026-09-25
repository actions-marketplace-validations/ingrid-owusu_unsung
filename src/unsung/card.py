"""Render a Stats object into a self-contained SVG card.

No external assets or fonts (uses the viewer's system UI font), so the SVG
renders identically on GitHub's camo proxy, which strips scripts and blocks
remote references.
"""
from __future__ import annotations

from .api import Stats

THEMES = {
    "light": {
        "bg": "#fffefe", "border": "#e4e2e2", "title": "#2f80ed",
        "text": "#434d58", "num": "#2f80ed", "muted": "#858585", "accent": "#2f80ed",
    },
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "title": "#58a6ff",
        "text": "#c9d1d9", "num": "#58a6ff", "muted": "#8b949e", "accent": "#58a6ff",
    },
    "dracula": {
        "bg": "#282a36", "border": "#44475a", "title": "#ff79c6",
        "text": "#f8f8f2", "num": "#bd93f9", "muted": "#6272a4", "accent": "#ff79c6",
    },
    "gruvbox": {
        "bg": "#282828", "border": "#3c3836", "title": "#fabd2f",
        "text": "#ebdbb2", "num": "#8ec07c", "muted": "#928374", "accent": "#fabd2f",
    },
}

# Detail rows below the hero. ``projects_helped`` is surfaced in the hero
# headline instead, so the breakdown stays to the three "invisible" actions.
_ROWS = [
    ("reviews_given", "Reviews given", "\U0001F50D"),
    ("prs_to_others", "PRs to others' projects", "\U0001F500"),
    ("issues_for_others", "Issues opened for others", "\U0001F41B"),
]


# Footer text is font-size 11; this is a conservative average glyph width (px)
# for the default sans-serif stack, used to keep the "most helped" line inside
# the card instead of overflowing past the border for long owner/repo names.
_FOOTER_CHAR_W = 6.2
_FOOTER_PREFIX = "\u2764 most helped: "

# Title is font-size 18; conservative average glyph width (px) for the default
# sans stack, used to keep the header inside the card for long display names.
_TITLE_CHAR_W = 9.8
_TITLE_SUFFIX = "'s unsung open-source work"


def _fit_title(display: str, inner_width: int) -> str:
    """Build the auto title, truncating a long display name so it fits."""
    budget = int(inner_width / _TITLE_CHAR_W)
    full = display + _TITLE_SUFFIX
    if len(full) <= budget:
        return full
    name_budget = budget - len(_TITLE_SUFFIX) - 1  # -1 for the ellipsis
    if name_budget < 1:
        name_budget = 1
    return display[:name_budget].rstrip() + "\u2026" + _TITLE_SUFFIX


def _fit_generic(text: str, inner_width: int) -> str:
    """Hard-cut an arbitrary (e.g. custom) title so it fits the card."""
    budget = int(inner_width / _TITLE_CHAR_W)
    if len(text) <= budget:
        return text
    return text[: max(1, budget - 1)].rstrip() + "\u2026"


def _fmt_stars(n: int) -> str:
    """Compact star count: 90000 -> '90k', 1500 -> '1.5k', 234 -> '234'."""
    if n >= 1000:
        v = n / 1000.0
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "k"
    return str(n)


def _footer_entries(top: list) -> list[str]:
    """Format ``top_helped`` rows as 'owner/repo \u2605Nk', dropping the star
    badge for repos with no stars. Accepts (name, count) or (name, count, stars).
    """
    out = []
    for row in top:
        name = row[0]
        stars = row[2] if len(row) > 2 else 0
        if stars and stars > 0:
            out.append(f"{name} \u2605{_fmt_stars(stars)}")
        else:
            out.append(name)
    return out


def _fit_names(names: list[str], inner_width: int) -> str:
    """Join repo names to fit within ``inner_width`` px, ellipsizing if needed.

    Drops whole trailing names first (adding an ellipsis), and only hard-cuts a
    single over-long name as a last resort. Returns the raw (unescaped) string.
    """
    budget = int(inner_width / _FOOTER_CHAR_W) - len(_FOOTER_PREFIX)
    if budget < 1:
        budget = 1
    full = ", ".join(names)
    if len(full) <= budget:
        return full
    kept = list(names)
    while kept:
        candidate = ", ".join(kept) + ", \u2026"
        if len(candidate) <= budget:
            return candidate
        kept.pop()
    # A single name alone is too long: hard-cut with an ellipsis.
    first = names[0]
    return first[: max(1, budget - 1)] + "\u2026"


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# Hero number is font-size 34; conservative average digit width (px).
_HERO_DIGIT_W = 21.0


def render(stats: Stats, theme: str = "dark", title: str | None = None,
           hide_border: bool = False, animate: bool = True) -> str:
    c = THEMES.get(theme, THEMES["dark"])
    display = stats.name or stats.login
    width, height = 470, 232
    pad = 25
    if title is None:
        title = _fit_title(display, width - 2 * pad)
    else:
        title = _fit_generic(title, width - 2 * pad)
    header_y = 40
    hero_y = 108          # baseline of the big total number
    row_start = 148
    row_gap = 24

    def anim(delay: float) -> str:
        if not animate:
            return ""
        return (
            f'<animate attributeName="opacity" from="0" to="1" '
            f'dur="0.5s" begin="{delay:.2f}s" fill="freeze"/>'
        )

    # Hero: lead with a positive aggregate so the card celebrates a single
    # flattering number instead of reading like a scorecard with 0-rows. Any
    # contributor who touched one else's repo has a non-trivial headline here.
    total = stats.total_help
    projects = stats.projects_helped
    hero_num = f"{total:,}"
    label_x = pad + len(hero_num) * _HERO_DIGIT_W + 14
    proj_word = "project" if projects == 1 else "projects"
    op_hero = "0" if animate else "1"
    hero = (
        f'<g opacity="{op_hero}">{anim(0.25)}'
        f'<text x="{pad}" y="{hero_y}" fill="{c["num"]}" font-size="34" '
        f'font-weight="800">{hero_num}</text>'
        f'<text x="{label_x:.0f}" y="{hero_y - 9}" fill="{c["text"]}" '
        f'font-size="13.5">contributions across {projects:,} {proj_word}</text>'
        f'<text x="{label_x:.0f}" y="{hero_y + 9}" fill="{c["muted"]}" '
        f'font-size="12.5">you don\u2019t own \u2014 the invisible half of open source</text>'
        f"</g>"
    )

    rows = []
    for i, (attr, label, icon) in enumerate(_ROWS):
        y = row_start + i * row_gap
        val = getattr(stats, attr)
        op = "0" if animate else "1"
        # De-emphasize a zero row (mute label + number) so an empty metric
        # reads as "n/a" rather than a bright failing grade.
        num_fill = c["num"] if val else c["muted"]
        txt_fill = c["text"] if val else c["muted"]
        rows.append(
            f'<g transform="translate({pad}, {y})" opacity="{op}">{anim(0.45 + i * 0.15)}'
            f'<text x="0" y="0" font-size="15">{icon}</text>'
            f'<text x="28" y="0" fill="{txt_fill}" font-size="14">{_esc(label)}</text>'
            f'<text x="{width - 2 * pad}" y="0" fill="{num_fill}" font-size="15" '
            f'font-weight="700" text-anchor="end">{val:,}</text>'
            f"</g>"
        )

    # Footer: top projects helped, ranked by prominence.
    footer = ""
    if stats.top_helped:
        names = _esc(_fit_names(_footer_entries(stats.top_helped), width - 2 * pad))
        op = "0" if animate else "1"
        footer = (
            f'<g transform="translate({pad}, {row_start + len(_ROWS) * row_gap + 6})" '
            f'opacity="{op}">{anim(1.1)}'
            f'<text x="0" y="0" fill="{c["muted"]}" font-size="11">'
            f'\u2764 most helped: {names}</text></g>'
        )

    border = (
        "" if hide_border
        else f'stroke="{c["border"]}" stroke-width="1"'
    )
    op_h = "0" if animate else "1"
    op_s = "0" if animate else "1"

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" role="img" \
aria-label="{_esc(title)}">
<style>text{{font-family:'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif;}}</style>
<rect x="0.5" y="0.5" rx="6" width="{width - 1}" height="{height - 1}" \
fill="{c["bg"]}" {border}/>
<g transform="translate({pad}, {header_y})" opacity="{op_h}">{anim(0.1)}
<text x="0" y="0" fill="{c["title"]}" font-size="18" font-weight="700">\
{_esc(title)}</text>
<text x="0" y="19" fill="{c["muted"]}" font-size="11">\
the work that doesn't show up on your contribution graph \u00b7 {_esc(stats.since_label)}</text>
</g>
<g opacity="{op_s}">{anim(0.2)}<line x1="{pad}" y1="{header_y + 26}" \
x2="{width - pad}" y2="{header_y + 26}" stroke="{c["border"]}" stroke-width="1"/></g>
{hero}
{''.join(rows)}
{footer}
</svg>"""
