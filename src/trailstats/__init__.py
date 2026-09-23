"""trailstats: offline analysis of GPX activity recordings."""

from trailstats.analysis import (
    ActivityStats,
    BestEffort,
    Split,
    best_effort,
    splits,
    summarize,
    to_dataframe,
)
from trailstats.gpx import load_gpx
from trailstats.log import build_log, personal_bests, weekly_totals
from trailstats.models import Track, TrackPoint

__all__ = [
    "ActivityStats",
    "BestEffort",
    "Split",
    "Track",
    "TrackPoint",
    "best_effort",
    "build_log",
    "load_gpx",
    "personal_bests",
    "splits",
    "summarize",
    "to_dataframe",
    "weekly_totals",
]
