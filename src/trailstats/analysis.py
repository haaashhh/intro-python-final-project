"""Metrics derived from a track: elevation, moving time, pace."""

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from trailstats.geo import cumulative_distance, step_distances
from trailstats.models import Track

DEFAULT_SMOOTH_WINDOW = 7
DEFAULT_ELEVATION_THRESHOLD_M = 3.0
DEFAULT_STOP_SPEED_MS = 0.5
DEFAULT_GAP_SECONDS = 30.0


def to_dataframe(track: Track) -> pd.DataFrame:
    """Return a DataFrame with one row per track point.

    Columns: lat, lon, ele, time, step_km, dist_km, dt_s, speed_ms.
    """
    frame = pd.DataFrame(
        {
            "lat": [p.lat for p in track.points],
            "lon": [p.lon for p in track.points],
            "ele": [p.ele for p in track.points],
            "time": [p.time for p in track.points],
        }
    )
    frame["step_km"] = step_distances(track)
    frame["dist_km"] = cumulative_distance(track)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame["dt_s"] = frame["time"].diff().dt.total_seconds().fillna(0.0)
    frame["speed_ms"] = np.where(
        frame["dt_s"] > 0,
        frame["step_km"] * 1000 / frame["dt_s"].replace(0, np.nan),
        0.0,
    )
    return frame


def smooth_elevation(
    frame: pd.DataFrame, window: int = DEFAULT_SMOOTH_WINDOW
) -> pd.Series:
    """Smooth raw GPS elevation with a centred rolling median."""
    return frame["ele"].rolling(window, center=True, min_periods=1).median()


def elevation_gain(
    elevation: pd.Series, threshold_m: float = DEFAULT_ELEVATION_THRESHOLD_M
) -> tuple[float, float]:
    """Total ascent and descent in metres, ignoring changes below a threshold.

    A climb is only counted once it rises ``threshold_m`` above the last
    confirmed level, which removes the metre-by-metre jitter of GPS altitude.
    """
    values = elevation.dropna().to_numpy()
    if values.size < 2:
        return 0.0, 0.0

    gain = loss = 0.0
    reference = values[0]
    for value in values[1:]:
        change = value - reference
        if abs(change) < threshold_m:
            continue
        if change > 0:
            gain += change
        else:
            loss -= change
        reference = value
    return gain, loss


def moving_mask(
    frame: pd.DataFrame,
    stop_speed_ms: float = DEFAULT_STOP_SPEED_MS,
    gap_s: float = DEFAULT_GAP_SECONDS,
) -> pd.Series:
    """True for points recorded while actually moving."""
    return (frame["speed_ms"] >= stop_speed_ms) & (frame["dt_s"] <= gap_s)


@dataclass(frozen=True)
class ActivityStats:
    """Summary metrics for one activity."""

    distance_km: float
    duration: timedelta | None
    moving_time: timedelta | None
    elevation_gain_m: float
    elevation_loss_m: float
    raw_elevation_gain_m: float
    min_elevation_m: float | None
    max_elevation_m: float | None

    @property
    def average_pace(self) -> timedelta | None:
        """Pace over the whole recording, per kilometre."""
        return self._pace(self.duration)

    @property
    def moving_pace(self) -> timedelta | None:
        """Pace excluding stops, per kilometre."""
        return self._pace(self.moving_time)

    def _pace(self, elapsed: timedelta | None) -> timedelta | None:
        if elapsed is None or self.distance_km <= 0:
            return None
        return elapsed / self.distance_km


def summarize(
    track: Track,
    *,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
    elevation_threshold_m: float = DEFAULT_ELEVATION_THRESHOLD_M,
    stop_speed_ms: float = DEFAULT_STOP_SPEED_MS,
) -> ActivityStats:
    """Compute the summary metrics of a track."""
    frame = to_dataframe(track)
    smoothed = smooth_elevation(frame, smooth_window)
    gain, loss = elevation_gain(smoothed, elevation_threshold_m)
    raw_gain, _ = elevation_gain(frame["ele"], threshold_m=0.0)

    moving = moving_mask(frame, stop_speed_ms=stop_speed_ms)
    moving_seconds = float(frame.loc[moving, "dt_s"].sum())
    has_elevation = frame["ele"].notna().any()

    return ActivityStats(
        distance_km=float(frame["dist_km"].iloc[-1]) if len(frame) else 0.0,
        duration=track.duration,
        moving_time=timedelta(seconds=moving_seconds) if track.has_time else None,
        elevation_gain_m=gain,
        elevation_loss_m=loss,
        raw_elevation_gain_m=raw_gain,
        min_elevation_m=float(frame["ele"].min()) if has_elevation else None,
        max_elevation_m=float(frame["ele"].max()) if has_elevation else None,
    )


@dataclass(frozen=True)
class Split:
    """One fixed-distance section of an activity."""

    index: int
    distance_km: float
    duration: timedelta | None
    elevation_gain_m: float

    @property
    def pace(self) -> timedelta | None:
        """Pace of this split, per kilometre."""
        if self.duration is None or self.distance_km <= 0:
            return None
        return self.duration / self.distance_km


def splits(
    track: Track,
    split_km: float = 1.0,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
    elevation_threshold_m: float = DEFAULT_ELEVATION_THRESHOLD_M,
) -> list[Split]:
    """Break a track into sections of ``split_km`` kilometres each.

    The last split is usually shorter than the others; its pace is still
    reported per kilometre so that it stays comparable to the rest.
    """
    frame = to_dataframe(track)
    if frame.empty:
        return []

    frame = frame.assign(
        smoothed=smooth_elevation(frame, smooth_window),
        split=(frame["dist_km"] // split_km).astype(int),
    )

    result = []
    previous_km = 0.0
    previous_time = frame["time"].iloc[0]
    for index, section in frame.groupby("split", sort=True):
        end_km = float(section["dist_km"].iloc[-1])
        end_time = section["time"].iloc[-1]
        duration = None
        if pd.notna(end_time) and pd.notna(previous_time):
            duration = (end_time - previous_time).to_pytimedelta()
        gain, _ = elevation_gain(section["smoothed"], elevation_threshold_m)

        result.append(
            Split(
                index=int(index) + 1,
                distance_km=end_km - previous_km,
                duration=duration,
                elevation_gain_m=gain,
            )
        )
        previous_km, previous_time = end_km, end_time
    return result


@dataclass(frozen=True)
class BestEffort:
    """The fastest section of a given distance within an activity."""

    distance_km: float
    duration: timedelta
    start_km: float

    @property
    def pace(self) -> timedelta:
        """Pace of the effort, per kilometre."""
        return self.duration / self.distance_km


def best_effort(track: Track, distance_km: float) -> BestEffort | None:
    """Find the fastest continuous section covering ``distance_km``.

    Uses a sliding window over the cumulative distance, so the search costs
    one pass over the track regardless of how long it is.

    returns fastest effort, or None if the track is shorter than the requested
        distance or has no usable timestamps.
    """
    frame = to_dataframe(track)
    if frame.empty or not track.has_time:
        return None

    cumulative = frame["dist_km"].to_numpy()
    seconds = (frame["time"] - frame["time"].iloc[0]).dt.total_seconds().to_numpy()
    if cumulative[-1] < distance_km:
        return None

    best: BestEffort | None = None
    end = 0
    for start in range(len(cumulative)):
        while (
            end < len(cumulative) and cumulative[end] - cumulative[start] < distance_km
        ):
            end += 1
        if end >= len(cumulative):
            break
        elapsed = timedelta(seconds=float(seconds[end] - seconds[start]))
        if best is None or elapsed < best.duration:
            best = BestEffort(
                distance_km=distance_km,
                duration=elapsed,
                start_km=float(cumulative[start]),
            )
    return best
