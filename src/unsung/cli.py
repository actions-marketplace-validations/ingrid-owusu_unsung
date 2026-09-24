"""Command-line entry point for unsung."""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .api import ApiError, collect
from .card import THEMES, render

WORKFLOW_PATH = ".github/workflows/unsung.yml"

_WORKFLOW_TEMPLATE = """\
name: unsung
on:
  schedule:
    - cron: "{cron}"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  card:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ingrid-owusu/unsung@v1
        with:
          theme: {theme}        # dark | light | dracula | gruvbox
          since: {since}        # year | all
"""


def _build_init_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unsung init",
        description="Scaffold the GitHub Action workflow that keeps your unsung "
        "card up to date, and print the README embed snippet to paste.",
    )
    p.add_argument("--theme", default="dark", choices=sorted(THEMES),
                   help="card theme to write into the workflow (default: dark)")
    p.add_argument("--since", default="year", choices=["year", "all"],
                   help="'year' (trailing 365 days, default) or 'all' (lifetime)")
    p.add_argument("--cron", default="0 3 * * *",
                   help="schedule cron for the workflow (default: '0 3 * * *')")
    p.add_argument("-o", "--output", default="unsung.svg",
                   help="SVG path the card is written to (default: unsung.svg)")
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing workflow file")
    return p


def init(argv: list[str] | None = None) -> int:
    args = _build_init_parser().parse_args(argv)
    path = WORKFLOW_PATH
    if os.path.exists(path) and not args.force:
        print(
            f"unsung: {path} already exists (use --force to overwrite)",
            file=sys.stderr,
        )
        return 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = _WORKFLOW_TEMPLATE.format(cron=args.cron, theme=args.theme, since=args.since)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    embed = f"![My unsung open-source work]({args.output})"
    print(f"unsung: wrote {path}", file=sys.stderr)
    print(
        "\nNext: add this line to your profile README.md "
        "(the repo named after your username):\n",
        file=sys.stderr,
    )
    print(embed)
    print(
        "\nThen commit both files. The Action runs on the schedule (and on demand "
        "via 'Run workflow') using the built-in GITHUB_TOKEN \u2014 no secrets to set.",
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unsung",
        description="Generate an SVG card of your unsung open-source work: "
        "reviews given, and PRs/issues opened on repositories you don't own.",
    )
    p.add_argument("user", nargs="?", help="GitHub login (default: $GITHUB_ACTOR or token owner)")
    p.add_argument("-o", "--output", default="unsung.svg", help="output SVG path (default: unsung.svg)")
    p.add_argument("--theme", default="dark", choices=sorted(THEMES), help="color theme")
    p.add_argument("--since", default="year", choices=["year", "all"],
                   help="'year' (trailing 365 days, default) or 'all' (lifetime)")
    p.add_argument("--title", default=None, help="custom card title")
    p.add_argument("--hide-border", action="store_true", help="draw no border")
    p.add_argument("--no-animate", action="store_true", help="disable fade-in animation")
    p.add_argument("--token", default=None, help="GitHub token (default: $GITHUB_TOKEN or $GH_TOKEN)")
    p.add_argument("--version", action="version", version=f"unsung {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "init":
        return init(argv[1:])
    args = build_parser().parse_args(argv)
    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("error: no GitHub token; set GITHUB_TOKEN or pass --token", file=sys.stderr)
        return 2
    user = args.user or os.environ.get("GITHUB_ACTOR")
    if not user:
        print("error: no user; pass a login or set GITHUB_ACTOR", file=sys.stderr)
        return 2
    try:
        stats = collect(user, token, since=args.since)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    svg = render(
        stats, theme=args.theme, title=args.title,
        hide_border=args.hide_border, animate=not args.no_animate,
    )
    if args.output == "-":
        sys.stdout.write(svg)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(
            f"unsung: wrote {args.output} \u2014 {stats.reviews_given} reviews, "
            f"{stats.prs_to_others} PRs & {stats.issues_for_others} issues for "
            f"{stats.projects_helped} projects you don't own ({stats.since_label}).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
