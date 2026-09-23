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

_ROWS = [
    ("reviews_given", "Reviews given", "\U0001F50D"),
    ("prs_to_others", "PRs to others' projects", "\U0001F500"),
    ("issues_for_others", "Issues opened for others", "\U0001F41B"),
    ("projects_helped", "Projects helped", "\U0001F30D"),
]


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render(stats: Stats, theme: str = "dark", title: str | None = None,
           hide_border: bool = False, animate: bool = True) -> str:
    c = THEMES.get(theme, THEMES["dark"])
    display = stats.name or stats.login
    if title is None:
        title = f"{display}'s unsung open-source work"

    width, height = 470, 200
    pad = 25
    header_y = 40
    row_start = 78
    row_gap = 27

    def anim(delay: float) -> str:
        if not animate:
            return ""
        return (
            f'<animate attributeName="opacity" from="0" to="1" '
            f'dur="0.5s" begin="{delay:.2f}s" fill="freeze"/>'
        )

    rows = []
    for i, (attr, label, icon) in enumerate(_ROWS):
        y = row_start + i * row_gap
        val = getattr(stats, attr)
        op = "0" if animate else "1"
        rows.append(
            f'<g transform="translate({pad}, {y})" opacity="{op}">{anim(0.3 + i * 0.15)}'
            f'<text x="0" y="0" font-size="15">{icon}</text>'
            f'<text x="28" y="0" fill="{c["text"]}" font-size="14">{_esc(label)}</text>'
            f'<text x="{width - 2 * pad}" y="0" fill="{c["num"]}" font-size="15" '
            f'font-weight="700" text-anchor="end">{val:,}</text>'
            f"</g>"
        )

    # Footer: top projects helped.
    footer = ""
    if stats.top_helped:
        names = ", ".join(_esc(n) for n, _ in stats.top_helped)
        op = "0" if animate else "1"
        footer = (
            f'<g transform="translate({pad}, {row_start + len(_ROWS) * row_gap + 4})" '
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
{''.join(rows)}
{footer}
</svg>"""
