# Changelog

## 0.1.1 — 2026-09-23
- Fix: the "most helped" footer now ellipsizes long `owner/repo` names so it
  always stays inside the card border (previously long names could overflow for
  heavy contributors to projects with long repo names).

## 0.1.0 — 2026-09-23
- Initial release. Generates an SVG "unsung" card: reviews given, and PRs/issues
  opened on repositories you don't own, plus the projects you helped most.
- Ships as a GitHub composite Action and a zero-dependency Python CLI
  (`pip install unsung-card`). Themes: dark, light, dracula, gruvbox.
