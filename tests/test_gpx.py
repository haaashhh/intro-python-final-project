"""Tests for the GPX parser."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trailstats.gpx import load_gpx

DATA = Path(__file__).parent / "data"

MINIMAL_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Morning run</name>
    <trkseg>
      <trkpt lat="49.60" lon="6.13"><ele>280.0</ele><time>2026-09-14T06:12:33Z</time></trkpt>
      <trkpt lat="49.61" lon="6.14"><ele>285.5</ele><time>2026-09-14T06:12:43Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def write_gpx(tmp_path: Path, content: str, name: str = "test.gpx") -> Path:
    """Write GPX content to a temporary file and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parses_points_and_name(tmp_path):
    track = load_gpx(write_gpx(tmp_path, MINIMAL_GPX))

    assert track.name == "Morning run"
    assert len(track) == 2
    assert track.points[0].lat == pytest.approx(49.60)
    assert track.points[0].lon == pytest.approx(6.13)
    assert track.points[0].ele == pytest.approx(280.0)
    assert track.points[0].time == datetime(2026, 9, 14, 6, 12, 33, tzinfo=UTC)


def test_falls_back_to_filename_when_track_has_no_name(tmp_path):
    content = MINIMAL_GPX.replace("<name>Morning run</name>", "")
    track = load_gpx(write_gpx(tmp_path, content, name="evening_walk.gpx"))

    assert track.name == "evening_walk"


def test_concatenates_all_segments_and_tracks(tmp_path):
    content = MINIMAL_GPX.replace(
        "</trkseg>",
        """</trkseg>
    <trkseg></trkseg>
    <trkseg>
      <trkpt lat="49.62" lon="6.15"></trkpt>
    </trkseg>""",
    )
    track = load_gpx(write_gpx(tmp_path, content))

    assert len(track) == 3


def test_missing_elevation_and_time_become_none(tmp_path):
    content = MINIMAL_GPX.replace(
        "<ele>280.0</ele><time>2026-09-14T06:12:33Z</time>", ""
    )
    track = load_gpx(write_gpx(tmp_path, content))

    assert track.points[0].ele is None
    assert track.points[0].time is None
    assert track.has_elevation is False
    assert track.has_time is False


def test_malformed_values_do_not_raise(tmp_path):
    content = MINIMAL_GPX.replace("<ele>280.0</ele>", "<ele>n/a</ele>").replace(
        "<time>2026-09-14T06:12:33Z</time>", "<time>not a date</time>"
    )
    track = load_gpx(write_gpx(tmp_path, content))

    assert track.points[0].ele is None
    assert track.points[0].time is None
    assert track.points[1].ele == pytest.approx(285.5)


def test_naive_timestamps_are_assumed_utc(tmp_path):
    content = MINIMAL_GPX.replace("2026-09-14T06:12:33Z", "2026-09-14T06:12:33")
    track = load_gpx(write_gpx(tmp_path, content))

    assert track.points[0].time == datetime(2026, 9, 14, 6, 12, 33, tzinfo=UTC)


def test_rejects_non_gpx_xml(tmp_path):
    path = write_gpx(tmp_path, "<html><body>not a track</body></html>")

    with pytest.raises(ValueError, match="not a GPX file"):
        load_gpx(path)


def test_rejects_broken_xml(tmp_path):
    path = write_gpx(tmp_path, "<gpx><trk>")

    with pytest.raises(ValueError, match="not well-formed"):
        load_gpx(path)


def test_rejects_gpx_without_track_points(tmp_path):
    content = """<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
      <wpt lat="49.6" lon="6.1"><name>a waypoint</name></wpt>
    </gpx>"""

    with pytest.raises(ValueError, match="no track points"):
        load_gpx(write_gpx(tmp_path, content))


def test_reads_gpx_1_0_files():
    """The parser detects the namespace, so GPX 1.0 needs no special case."""
    track = load_gpx(DATA / "Mojstrovka.gpx")

    assert len(track) == 184
    assert track.has_elevation


def test_handles_seven_digit_fractional_seconds():
    """Mojstrovka.gpx has timestamps like 20:45:52.2073437Z (7 digits)."""
    track = load_gpx(DATA / "Mojstrovka.gpx")

    assert track.points[0].time is not None
    assert track.points[0].time.microsecond == 207343


def test_partial_timestamps_are_reported_honestly():
    """korita-zbevnica.gpx has times on only some of its points."""
    track = load_gpx(DATA / "korita-zbevnica.gpx")

    assert track.has_time is False
    assert track.duration is None
