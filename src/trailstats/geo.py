"""Geographic calculations on sequences of GPS coordinates."""

import numpy as np

from trailstats.models import Track

EARTH_RADIUS_KM = 6371.0088


def haversine(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> float | np.ndarray:
    """Great-circle distance between two points

    Args:
        lat1: Latitude of the first point
        lon1: Longitude of the first point
        lat2: Latitude of the second point
        lon2: Longitude of the second point
        
        Distance in km
    """
    phi1, lam1, phi2, lam2 = np.radians([lat1, lon1, lat2, lon2])
    a = np.sin((phi2 - phi1) / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin((lam2 - lam1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def step_distances(track: Track) -> np.ndarray:
    """
    Distance in kilometres between each point and the previous one.
    """
    if len(track) < 2:
        return np.zeros(len(track))

    lat = np.array([p.lat for p in track.points])
    lon = np.array([p.lon for p in track.points])
    steps = haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])
    return np.concatenate([[0.0], steps])


def cumulative_distance(track: Track) -> np.ndarray:
    """Cumulative distance from the start of the track in km"""
    return np.cumsum(step_distances(track))


def total_distance(track: Track) -> float:
    """Total length of the track in km
    """
    return float(step_distances(track).sum())
