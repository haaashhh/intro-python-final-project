"""Building a training log from a folder of activity files."""

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from trailstats.analysis import best_effort, summarize
from trailstats.gpx import load_gpx

ACTIVITY_COLUMNS = [
    "name",
    "file",
    "start",
    "distance_km",
    "duration_s",
    "moving_time_s",
    "pace_s_per_km",
    "elevation_gain_m",
]


def find_activities(folder: str | Path, pattern: str = "*.gpx") -> list[Path]:
    """Return the activity files in a folder, sorted by name."""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory")
    return sorted(folder.glob(pattern))


def _rows(paths: list[Path]) -> Iterator[dict]:
    """Summarize each file, skipping the ones that cannot be read."""
    for path in paths:
        try:
            track = load_gpx(path)
        except ValueError:
            continue
        stats = summarize(track)
        yield {
            "name": track.name,
            "file": path.name,
            "start": track.start_time,
            "distance_km": stats.distance_km,
            "duration_s": stats.duration.total_seconds() if stats.duration else None,
            "moving_time_s": stats.moving_time.total_seconds()
            if stats.moving_time
            else None,
            "pace_s_per_km": stats.moving_pace.total_seconds()
            if stats.moving_pace
            else None,
            "elevation_gain_m": stats.elevation_gain_m,
        }


def build_log(folder: str | Path, pattern: str = "*.gpx") -> pd.DataFrame:
    """Summarize every activity in a folder into one DataFrame.

    Files that cannot be parsed are skipped rather than aborting the scan.
    The result is sorted by start time, oldest first.
    """
    frame = pd.DataFrame(
        list(_rows(find_activities(folder, pattern))), columns=ACTIVITY_COLUMNS
    )
    if frame.empty:
        return frame
    frame["start"] = pd.to_datetime(frame["start"], utc=True)
    return frame.sort_values("start", na_position="last").reset_index(drop=True)


def weekly_totals(activities: pd.DataFrame) -> pd.DataFrame:
    """Aggregate an activity log into weekly distance, time and ascent."""
    if activities.empty or activities["start"].isna().all():
        return pd.DataFrame(
            columns=["week", "activities", "distance_km", "hours", "elevation_gain_m"]
        )

    weeks = activities.dropna(subset=["start"]).copy()
    # Periods carry no timezone, so drop it explicitly rather than let pandas warn.
    weeks["week"] = weeks["start"].dt.tz_convert(None).dt.to_period("W").dt.start_time
    grouped = weeks.groupby("week").agg(
        activities=("file", "count"),
        distance_km=("distance_km", "sum"),
        hours=("moving_time_s", lambda values: values.sum() / 3600),
        elevation_gain_m=("elevation_gain_m", "sum"),
    )
    return grouped.reset_index()


def personal_bests(
    folder: str | Path,
    distances_km: tuple[float, ...] = (1.0, 5.0, 10.0),
    pattern: str = "*.gpx",
) -> pd.DataFrame:
    """Find the fastest effort at each distance across all activities.

    Pass a narrower ``pattern`` to compare like with like: a bike ride will
    otherwise take every record away from the runs.
    """
    records = []
    for path in find_activities(folder, pattern):
        try:
            track = load_gpx(path)
        except ValueError:
            continue
        for distance in distances_km:
            effort = best_effort(track, distance)
            if effort is not None:
                records.append(
                    {
                        "distance_km": distance,
                        "duration_s": effort.duration.total_seconds(),
                        "file": path.name,
                        "name": track.name,
                    }
                )

    frame = pd.DataFrame(records, columns=["distance_km", "duration_s", "file", "name"])
    if frame.empty:
        return frame
    fastest = frame.loc[frame.groupby("distance_km")["duration_s"].idxmin()]
    return fastest.sort_values("distance_km").reset_index(drop=True)
