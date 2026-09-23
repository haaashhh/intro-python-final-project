"""Matplotlib figures for activity tracks."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from trailstats.analysis import moving_mask, smooth_elevation, to_dataframe
from trailstats.models import Track

LINE_COLOR = "#2a78d6"
FILL_COLOR = "#2a78d6"
GRID_COLOR = "#d9d9d6"
TEXT_COLOR = "#52514e"
ELEVATION_CMAP = "viridis"


def _style_axes(axes: plt.Axes) -> None:
    """Apply the recessive grid and spine style used by all figures."""
    axes.grid(True, color=GRID_COLOR, linewidth=0.6, alpha=0.8)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(GRID_COLOR)
    axes.tick_params(colors=TEXT_COLOR, labelsize=9)
    axes.xaxis.label.set_color(TEXT_COLOR)
    axes.yaxis.label.set_color(TEXT_COLOR)


def _padded(low: float, high: float, fraction: float = 0.05) -> tuple[float, float]:
    """Widen a range by a fraction of its span on both sides."""
    pad = (high - low) * fraction or 1e-4
    return low - pad, high + pad


def _at_least(low: float, high: float, span: float) -> tuple[float, float]:
    """Widen a range around its centre so that it covers at least ``span``."""
    if high - low >= span:
        return low, high
    middle = (low + high) / 2
    return middle - span / 2, middle + span / 2


def _pace_formatter(minutes: float, _pos: int) -> str:
    """Format a pace in minutes per kilometre as m:ss."""
    if not np.isfinite(minutes):
        return ""
    return f"{int(minutes)}:{round((minutes % 1) * 60):02d}"


def plot_elevation(track: Track, axes: plt.Axes | None = None) -> plt.Axes:
    """Draw the elevation profile of a track against distance."""
    if axes is None:
        _, axes = plt.subplots(figsize=(9, 3.2))

    frame = to_dataframe(track)
    elevation = smooth_elevation(frame)

    axes.fill_between(
        frame["dist_km"], elevation, elevation.min(), color=FILL_COLOR, alpha=0.15
    )
    axes.plot(frame["dist_km"], elevation, color=LINE_COLOR, linewidth=2)
    axes.set_xlabel("distance (km)")
    axes.set_ylabel("elevation (m)")
    axes.set_title(f"{track.name} - elevation profile", color=TEXT_COLOR, loc="left")
    axes.set_xlim(0, frame["dist_km"].iloc[-1])
    _style_axes(axes)
    return axes


def plot_pace(track: Track, window: int = 30, axes: plt.Axes | None = None) -> plt.Axes:
    """Draw smoothed pace against distance, fastest at the top."""
    if axes is None:
        _, axes = plt.subplots(figsize=(9, 3.2))

    frame = to_dataframe(track)
    speed = frame["speed_ms"].where(moving_mask(frame))
    speed = speed.rolling(window, center=True, min_periods=1).mean()
    pace = (1000 / (speed * 60)).replace([np.inf, -np.inf], np.nan)
    # Stops and GPS drift produce paces of many minutes per kilometre; they
    # would flatten the whole curve, so keep the axis near the typical pace.
    pace = pace.where(pace < pace.median() * 2.5)

    axes.plot(frame["dist_km"], pace, color=LINE_COLOR, linewidth=2)
    axes.invert_yaxis()
    axes.yaxis.set_major_formatter(_pace_formatter)
    axes.set_xlabel("distance (km)")
    axes.set_ylabel("pace (min/km)")
    axes.set_title(f"{track.name} - pace", color=TEXT_COLOR, loc="left")
    axes.set_xlim(0, frame["dist_km"].iloc[-1])
    _style_axes(axes)
    return axes


def plot_map(track: Track, axes: plt.Axes | None = None) -> plt.Axes:
    """Draw the route from above, coloured by elevation."""
    if axes is None:
        _, axes = plt.subplots(figsize=(6, 6))

    frame = to_dataframe(track)
    points = np.column_stack([frame["lon"], frame["lat"]])
    segments = np.stack([points[:-1], points[1:]], axis=1)
    elevation = smooth_elevation(frame).to_numpy()

    if np.isfinite(elevation).any():
        lines = LineCollection(segments, cmap=ELEVATION_CMAP, linewidth=2.5)
        lines.set_array(elevation[:-1])
        axes.add_collection(lines)
        bar = axes.figure.colorbar(lines, ax=axes, shrink=0.75, pad=0.02)
        bar.set_label("elevation (m)", color=TEXT_COLOR, fontsize=9)
        bar.ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    else:
        axes.plot(frame["lon"], frame["lat"], color=LINE_COLOR, linewidth=2.5)

    axes.scatter(
        points[0, 0], points[0, 1], s=45, color="#1baf7a", zorder=3, label="start"
    )
    axes.scatter(
        points[-1, 0], points[-1, 1], s=45, color="#e34948", zorder=3, label="finish"
    )
    axes.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=TEXT_COLOR)

    # One degree of longitude is shorter than one of latitude away from the
    # equator; scaling by cos(latitude) keeps the route free of distortion.
    shrink = float(np.cos(np.radians(frame["lat"].mean())))
    lon_min, lon_max = _padded(frame["lon"].min(), frame["lon"].max())
    lat_min, lat_max = _padded(frame["lat"].min(), frame["lat"].max())
    lon_min, lon_max = _at_least(lon_min, lon_max, (lat_max - lat_min) / shrink)
    lat_min, lat_max = _at_least(lat_min, lat_max, (lon_max - lon_min) * shrink)
    axes.set_xlim(lon_min, lon_max)
    axes.set_ylim(lat_min, lat_max)
    axes.set_aspect(1 / shrink)
    axes.ticklabel_format(useOffset=False, style="plain")
    axes.set_xlabel("longitude")
    axes.set_ylabel("latitude")
    axes.set_title(f"{track.name} - route", color=TEXT_COLOR, loc="left", pad=12)
    _style_axes(axes)
    return axes


def plot_overview(track: Track) -> Figure:
    """Combine the route, elevation profile and pace into one figure."""
    figure = plt.figure(figsize=(11, 8))
    grid = figure.add_gridspec(2, 2, height_ratios=[1.6, 1], hspace=0.45, wspace=0.25)

    plot_map(track, figure.add_subplot(grid[0, 0]))
    plot_elevation(track, figure.add_subplot(grid[0, 1]))
    plot_pace(track, axes=figure.add_subplot(grid[1, :]))
    return figure
