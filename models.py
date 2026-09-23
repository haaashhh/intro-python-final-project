"""Data models for GPS tracks."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class TrackPoint:
    """A single GPS fix.

    Attributes:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        ele: Elevation in metres, or None if the recording has no altitude.
        time: Timestamp of the fix, or None if the recording has no timestamps.
    """

    lat: float
    lon: float
    ele: float | None = None
    time: datetime | None = None


@dataclass
class Track:
    """An ordered sequence of track points, i.e. one recorded activity."""

    name: str
    points: list[TrackPoint] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.points)

    @property
    def has_time(self) -> bool:
        """True if every point carries a timestamp."""
        return bool(self.points) and all(p.time is not None for p in self.points)

    @property
    def has_elevation(self) -> bool:
        """True if every point carries an elevation."""
        return bool(self.points) and all(p.ele is not None for p in self.points)

    @property
    def start_time(self) -> datetime | None:
        return self.points[0].time if self.points else None

    @property
    def end_time(self) -> datetime | None:
        return self.points[-1].time if self.points else None

    @property
    def duration(self) -> timedelta | None:
        """Wall-clock time between the first and last point."""
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Bounding box as (min_lat, min_lon, max_lat, max_lon)."""
        lats = [p.lat for p in self.points]
        lons = [p.lon for p in self.points]
        return min(lats), min(lons), max(lats), max(lons)
