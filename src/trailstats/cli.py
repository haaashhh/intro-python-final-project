"""Command-line interface for trailstats"""

import argparse
from collections.abc import Sequence

from trailstats.gpx import load_gpx


def _format_bounds(bounds: tuple[float, float, float, float]) -> str:
    min_lat, min_lon, max_lat, max_lon = bounds
    return f"{min_lat:.5f}, {min_lon:.5f} to {max_lat:.5f}, {max_lon:.5f}"


def summary_command(args: argparse.Namespace) -> int:
    """Print an overview of a single activity file"""
    track = load_gpx(args.path)

    print(f"{track.name}")
    print(f"  file           {args.path}")
    print(f"  points         {len(track)}")
    print(f"  elevation      {'yes' if track.has_elevation else 'incomplete'}")
    print(f"  timestamps     {'yes' if track.has_time else 'incomplete'}")
    if track.start_time is not None:
        print(f"  start          {track.start_time:%Y-%m-%d %H:%M:%S %Z}")
    if track.duration is not None:
        print(f"  duration       {track.duration}")
    print(f"  bounds         {_format_bounds(track.bounds)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trailstats",
        description="Analyze GPS activity recordings (GPX files) offline.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    summary = subcommands.add_parser(
        "summary",
        help="print an overview of one activity",
        description="Print an overview of one activity file.",
    )
    summary.add_argument("path", help="path to a .gpx file")
    summary.set_defaults(handler=summary_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
