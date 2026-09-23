"""Reading GPX files into Track objects."""

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from trailstats.models import Track, TrackPoint

# Precision beyond microseconds is not supported by datetime; some devices
# write 7 fractional digits (e.g. "12:00:04.2073437Z").
_FRACTION = re.compile(r"(\.\d{6})\d+")


def _parse_time(text: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp as found in GPX files.

    Returns None for missing or malformed values instead of raising, because a
    single bad timestamp should not make the whole file unreadable.
    """
    if not text:
        return None
    text = _FRACTION.sub(r"\1", text.strip())
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _parse_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _namespace(root: ET.Element) -> str:
    """Return the XML namespace of the root element, e.g. '{http://...}'."""
    match = re.match(r"(\{.*\})", root.tag)
    return match.group(1) if match else ""


def load_gpx(path: str | Path) -> Track:
    """Read a GPX file and return a single Track.

    All track segments in the file are concatenated in document order.
    Waypoints and routes are ignored.

    Raises:
        ValueError: if the file is not a GPX document or contains no track points.
    """
    path = Path(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"{path} is not well-formed XML: {exc}") from exc

    ns = _namespace(root)
    if not root.tag.endswith("gpx"):
        raise ValueError(f"{path} is not a GPX file (root element is {root.tag!r})")

    name = root.findtext(f"{ns}trk/{ns}name") or path.stem
    points = [
        TrackPoint(
            lat=float(trkpt.get("lat")),
            lon=float(trkpt.get("lon")),
            ele=_parse_float(trkpt.findtext(f"{ns}ele")),
            time=_parse_time(trkpt.findtext(f"{ns}time")),
        )
        for trkpt in root.iter(f"{ns}trkpt")
    ]
    if not points:
        raise ValueError(f"{path} contains no track points")

    return Track(name=name, points=points)
