# Changelog

## 0.4.0 — 2026-09-24
- New `unsung init` command: scaffolds `.github/workflows/unsung.yml` and prints
  the README embed line to paste, so setup is one command instead of copying two
  blocks by hand. Accepts `--theme`, `--since`, `--cron`, `--output`, and
  `--force` (refuses to overwrite an existing workflow unless forced). Try it
  with `pipx run unsung-card init`.

## 0.3.0 — 2026-09-24
- Redesigned card: it now **leads with a positive headline** — your total
  contributions across the projects you don't own (e.g. *"139 contributions
  across 21 projects you don't own — the invisible half of open source"*) — so
  the card celebrates a single flattering number instead of reading like a
  scorecard. A zero metric (e.g. no reviews yet) now renders **muted** rather
  than as a bright `0`, so a modest contributor's card still looks good and is
  worth embedding. The `projects helped` count moved into the headline.

## 0.2.0 — 2026-09-23
- The "most helped" footer now ranks by repository **prominence** (stargazers)
  instead of raw contribution count, and shows a compact star badge, e.g.
  `♥ most helped: facebook/react ★220k`. Surfacing the most recognizable repo you
  touched is a flex even at a single PR, so the card is worth sharing for the
  median contributor — not only for heavy ones. Ties break on contribution count.
- Repos with no stars still render (without a badge); private repos stay excluded.

## 0.1.2 — 2026-09-23
- Fix: the card title now truncates long display names (e.g.
  `Alexander Christopher Montgomery-Wellington`) with an ellipsis so the header
  stays inside the card border, matching the footer's width-aware fitting.

## 0.1.1 — 2026-09-23
- Fix: the "most helped" footer now ellipsizes long `owner/repo` names so it
  always stays inside the card border (previously long names could overflow for
  heavy contributors to projects with long repo names).

## 0.1.0 — 2026-09-23
- Initial release. Generates an SVG "unsung" card: reviews given, and PRs/issues
  opened on repositories you don't own, plus the projects you helped most.
- Ships as a GitHub composite Action and a zero-dependency Python CLI
  (`pip install unsung-card`). Themes: dark, light, dracula, gruvbox.
