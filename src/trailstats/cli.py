"""Command-line interface for trailstats"""

import argparse
from collections.abc import Sequence
from trailstats.analysis import DEFAULT_SMOOTH_WINDOW, DEFAULT_STOP_SPEED_MS, summarize
from trailstats.gpx import load_gpx

from datetime import time, timedelta


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
        print(f"  elevation      {stats.min_elevation_m:.0f} - {stats.max_elevation_m:.0f} m")
        print(f"  ascent         {stats.elevation_gain_m:.0f} m (raw GPS: {stats.raw_elevation_gain_m:.0f} m)")
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
    plot.add_argument("--kind", choices=["all", "map", "elevation", "pace"], default="all",
                      help="which figure to draw (default: %(default)s)")
    plot.add_argument("--out", metavar="FILE", help="save to a file instead of opening a window")
    plot.set_defaults(handler=plot_command)


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



def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1


