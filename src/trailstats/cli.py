"""Command-line interface for trailstats"""

import argparse
from collections.abc import Sequence
from datetime import timedelta

import pandas as pd

from trailstats.analysis import (
    DEFAULT_SMOOTH_WINDOW,
    DEFAULT_STOP_SPEED_MS,
    best_effort,
    splits,
    summarize,
)
from trailstats.gpx import load_gpx
from trailstats.log import build_log, weekly_totals


def _format_bounds(bounds: tuple[float, float, float, float]) -> str:
    min_lat, min_lon, max_lat, max_lon = bounds
    return f"{min_lat:.5f}, {min_lon:.5f} to {max_lat:.5f}, {max_lon:.5f}"


def _format_pace(pace: timedelta | None) -> str:
    if pace is None:
        return "n/a"
    total = int(pace.total_seconds())
    return f"{total // 60}:{total % 60:02d} /km"


def _format_duration(value: timedelta | None) -> str:
    if value is None:
        return "n/a"
    total = int(value.total_seconds())
    return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"


def summary_command(args: argparse.Namespace) -> int:
    """Print an overview of a single activity file."""
    track = load_gpx(args.path)
    stats = summarize(
        track,
        smooth_window=args.smooth,
        stop_speed_ms=args.stop_speed,
    )

    print(track.name)
    print(f"  points         {len(track)}")
    if track.start_time is not None:
        print(f"  start          {track.start_time:%Y-%m-%d %H:%M:%S %Z}")
    print(f"  distance       {stats.distance_km:.2f} km")
    print(f"  duration       {_format_duration(stats.duration)}")
    print(f"  moving time    {_format_duration(stats.moving_time)}")
    print(f"  average pace   {_format_pace(stats.average_pace)}")
    print(f"  moving pace    {_format_pace(stats.moving_pace)}")
    if stats.max_elevation_m is not None:
        print(
            f"  elevation      {stats.min_elevation_m:.0f} - {stats.max_elevation_m:.0f} m"
        )
        print(
            f"  ascent         {stats.elevation_gain_m:.0f} m (raw GPS: {stats.raw_elevation_gain_m:.0f} m)"
        )
        print(f"  descent        {stats.elevation_loss_m:.0f} m")
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
    summary.add_argument(
        "--smooth",
        type=int,
        default=DEFAULT_SMOOTH_WINDOW,
        metavar="N",
        help="rolling median window for elevation (default: %(default)s)",
    )
    summary.add_argument(
        "--stop-speed",
        type=float,
        default=DEFAULT_STOP_SPEED_MS,
        metavar="MS",
        help="speed below which a point counts as stopped, m/s (default: %(default)s)",
    )
    summary.set_defaults(handler=summary_command)

    plot = subcommands.add_parser("plot", help="draw figures for one activity")
    plot.add_argument("path", help="path to a .gpx file")
    plot.add_argument(
        "--kind",
        choices=["all", "map", "elevation", "pace"],
        default="all",
        help="which figure to draw (default: %(default)s)",
    )
    plot.add_argument(
        "--out", metavar="FILE", help="save to a file instead of opening a window"
    )
    plot.set_defaults(handler=plot_command)

    split_parser = subcommands.add_parser("splits", help="show per-kilometre splits")
    split_parser.add_argument("path", help="path to a .gpx file")
    split_parser.add_argument(
        "--km",
        type=float,
        default=1.0,
        metavar="KM",
        help="split length in kilometres (default: %(default)s)",
    )
    split_parser.set_defaults(handler=splits_command)

    best = subcommands.add_parser("best", help="find the fastest sections")
    best.add_argument("path", help="path to a .gpx file")
    best.add_argument(
        "--distance",
        type=float,
        nargs="+",
        default=[1.0, 5.0, 10.0],
        metavar="KM",
        help="distances to search for (default: 1 5 10)",
    )
    best.set_defaults(handler=best_command)

    log_parser = subcommands.add_parser("log", help="summarize a folder of activities")
    log_parser.add_argument("folder", help="folder containing .gpx files")
    log_parser.add_argument(
        "--pattern", default="*.gpx", help="filename pattern (default: %(default)s)"
    )
    log_parser.add_argument(
        "--weekly", action="store_true", help="also print weekly totals"
    )
    log_parser.add_argument(
        "--csv", metavar="FILE", help="write the activity table to a CSV file"
    )
    log_parser.add_argument(
        "--plot", metavar="FILE", help="save a weekly distance chart"
    )
    log_parser.set_defaults(handler=log_command)

    compare = subcommands.add_parser("compare", help="compare several activities")
    compare.add_argument("paths", nargs="+", help="two or more .gpx files")
    compare.add_argument("--out", metavar="FILE", help="save the comparison chart")
    compare.add_argument(
        "--absolute",
        action="store_true",
        help="plot absolute elevation instead of change from the start",
    )
    compare.set_defaults(handler=compare_command)

    return parser


def plot_command(args: argparse.Namespace) -> int:
    """Render figures for one activity."""
    from trailstats import plotting

    track = load_gpx(args.path)
    builders = {
        "map": plotting.plot_map,
        "elevation": plotting.plot_elevation,
        "pace": plotting.plot_pace,
    }
    if args.kind == "all":
        figure = plotting.plot_overview(track)
    else:
        figure = builders[args.kind](track).figure

    if args.out:
        figure.savefig(args.out, dpi=150, bbox_inches="tight")
        print(f"wrote {args.out}")
    else:
        plotting.plt.show()
    return 0


def splits_command(args: argparse.Namespace) -> int:
    """Print per-kilometre splits for one activity."""
    track = load_gpx(args.path)

    print(f"{track.name}")
    print(f"  {'#':>3}  {'distance':>8}  {'time':>8}  {'pace':>9}  {'ascent':>6}")
    for split in splits(track, split_km=args.km):
        print(
            f"  {split.index:>3}  {split.distance_km:>7.2f}km"
            f"  {_format_duration(split.duration):>8}"
            f"  {_format_pace(split.pace):>9}"
            f"  {split.elevation_gain_m:>5.0f}m"
        )
    return 0


def best_command(args: argparse.Namespace) -> int:
    """Print the fastest section of one or more distances."""
    track = load_gpx(args.path)

    print(f"{track.name}")
    for distance in args.distance:
        effort = best_effort(track, distance)
        if effort is None:
            print(f"  {distance:>5}km  not reached")
        else:
            print(
                f"  {distance:>5}km  {_format_duration(effort.duration):>8}"
                f"  {_format_pace(effort.pace):>9}  starting at {effort.start_km:.2f} km"
            )
    return 0


def log_command(args: argparse.Namespace) -> int:
    """Summarize every activity in a folder."""
    activities = build_log(args.folder, pattern=args.pattern)
    if activities.empty:
        print(f"no readable activities in {args.folder}")
        return 1

    print(
        f"{'date':<12} {'activity':<34} {'dist':>7} {'time':>8} {'pace':>9} {'ascent':>7}"
    )
    for row in activities.itertuples():
        start = row.start.strftime("%Y-%m-%d") if pd.notna(row.start) else "unknown"
        pace = (
            timedelta(seconds=row.pace_s_per_km)
            if pd.notna(row.pace_s_per_km)
            else None
        )
        moving = (
            timedelta(seconds=row.moving_time_s)
            if pd.notna(row.moving_time_s)
            else None
        )
        print(
            f"{start:<12} {row.name[:34]:<34} {row.distance_km:>6.2f}km"
            f" {_format_duration(moving):>8} {_format_pace(pace):>9}"
            f" {row.elevation_gain_m:>6.0f}m"
        )

    total = activities["distance_km"].sum()
    print(f"\n{len(activities)} activities, {total:.1f} km total")

    if args.weekly:
        print()
        weekly = weekly_totals(activities)
        print(
            f"{'week of':<12} {'runs':>5} {'distance':>10} {'hours':>7} {'ascent':>8}"
        )
        for row in weekly.itertuples():
            print(
                f"{row.week:%Y-%m-%d}   {row.activities:>5}"
                f" {row.distance_km:>8.1f}km {row.hours:>7.1f} {row.elevation_gain_m:>7.0f}m"
            )

    if args.csv:
        activities.to_csv(args.csv, index=False)
        print(f"\nwrote {args.csv}")

    if args.plot:
        from trailstats.plotting import plot_weekly, plt

        axes = plot_weekly(weekly_totals(activities))
        axes.figure.savefig(args.plot, dpi=150, bbox_inches="tight")
        plt.close(axes.figure)
        print(f"wrote {args.plot}")

    return 0


def compare_command(args: argparse.Namespace) -> int:
    """Compare several activities side by side."""
    tracks = [load_gpx(path) for path in args.paths]

    print(f"{'activity':<32} {'dist':>8} {'time':>9} {'pace':>10} {'ascent':>7}")
    for track in tracks:
        stats = summarize(track)
        print(
            f"{track.name[:32]:<32} {stats.distance_km:>6.2f}km"
            f" {_format_duration(stats.moving_time):>9}"
            f" {_format_pace(stats.moving_pace):>10}"
            f" {stats.elevation_gain_m:>6.0f}m"
        )

    if args.out:
        from trailstats.plotting import plot_comparison, plt

        figure = plot_comparison(tracks, relative_elevation=not args.absolute)
        figure.savefig(args.out, dpi=150, bbox_inches="tight")
        plt.close(figure)
        print(f"\nwrote {args.out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
