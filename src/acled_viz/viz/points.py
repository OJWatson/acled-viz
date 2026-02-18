"""Point map, animation, and interactive widget helpers."""

from __future__ import annotations

import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pandas as pd
from matplotlib import dates as mdates
from matplotlib import pyplot as plt

from acled_viz.viz.styling import apply_style
from acled_viz.viz.transforms import add_deterministic_jitter, normalize_event_frame


def _frame_from_figure(fig: plt.Figure) -> np.ndarray:
    fig.canvas.draw()
    buffer = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    width, height = fig.canvas.get_width_height()
    return buffer.reshape((height, width, 4))[..., :3]


def _build_frame_days(events: pd.DataFrame, by: str) -> pd.DatetimeIndex:
    if events.empty:
        return pd.DatetimeIndex([])

    first_day = events["event_day"].min()
    last_day = events["event_day"].max()

    if by == "week":
        weekly = pd.date_range(first_day, last_day, freq="7D")
        if len(weekly) == 0 or weekly[-1] != last_day:
            weekly = weekly.append(pd.DatetimeIndex([last_day]))
        return weekly

    return pd.date_range(first_day, last_day, freq="D")


def _window_subset(events: pd.DataFrame, frame_day: pd.Timestamp, tail_days: int) -> pd.DataFrame:
    ages = (frame_day - events["event_day"]).dt.days
    return events[(ages >= 0) & (ages < tail_days)].copy()


def _size_from_fatalities(fatalities: pd.Series) -> np.ndarray:
    base = np.sqrt(np.clip(fatalities.to_numpy(dtype=float), 0.0, None)) * 2.6
    return 7.0 + np.minimum(26.0, base)


def _rgba_colors(ages: np.ndarray, fatalities: np.ndarray, tail_days: int) -> np.ndarray:
    if len(ages) == 0:
        return np.zeros((0, 4))

    age_alpha = np.clip(1.0 - (ages / max(float(tail_days), 1.0)), 0.08, 0.98)
    fatal_mask = fatalities > 0

    colors = np.zeros((len(ages), 4), dtype=float)
    colors[~fatal_mask, 0] = 89 / 255
    colors[~fatal_mask, 1] = 112 / 255
    colors[~fatal_mask, 2] = 136 / 255
    colors[~fatal_mask, 3] = age_alpha[~fatal_mask] * 0.3

    colors[fatal_mask, 0] = 226 / 255
    colors[fatal_mask, 1] = 88 / 255
    colors[fatal_mask, 2] = 64 / 255
    colors[fatal_mask, 3] = age_alpha[fatal_mask] * 0.9
    return colors


def _plot_activity_context(
    *,
    ax: plt.Axes,
    daily_counts: pd.Series,
    frame_day: pd.Timestamp,
    tail_days: int,
) -> None:
    rolling = daily_counts.rolling(window=14, min_periods=1).mean()

    ax.fill_between(
        daily_counts.index,
        daily_counts.values,
        color="#9cb0c6",
        alpha=0.22,
        linewidth=0,
    )
    ax.plot(
        daily_counts.index,
        daily_counts.values,
        color="#607c99",
        linewidth=0.9,
        alpha=0.8,
    )
    ax.plot(
        rolling.index,
        rolling.values,
        color="#a4483f",
        linewidth=2.0,
        label="14-day mean",
    )

    tail_start = frame_day - pd.Timedelta(days=max(1, tail_days) - 1)
    ax.axvspan(tail_start, frame_day, color="#c95c4d", alpha=0.12, lw=0)
    ax.axvline(frame_day, color="#264f7f", linewidth=1.2)

    ax.set_ylabel("events/day")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))


def animate_points(
    events: pd.DataFrame,
    output_path: Path,
    fps: int = 8,
    by: str = "week",
    tail_days: int = 30,
) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clean = add_deterministic_jitter(normalize_event_frame(events), scale=0.0034)
    frame_days = _build_frame_days(clean, by=by)
    frames: list[np.ndarray] = []

    if clean.empty or len(frame_days) == 0:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=128)
        ax.set_facecolor("#f7f3ea")
        ax.set_title("Gaza ACLED Events (No Data)")
        ax.set_xlabel("latitude")
        ax.set_ylabel("longitude")
        frames.append(_frame_from_figure(fig))
        plt.close(fig)
        imageio.mimsave(output_path, frames, fps=fps)
        return output_path

    x_min = float(clean["latitude_jitter"].min())
    x_max = float(clean["latitude_jitter"].max())
    y_min = float(clean["longitude_jitter"].min())
    y_max = float(clean["longitude_jitter"].max())
    x_margin = max((x_max - x_min) * 0.06, 0.02)
    y_margin = max((y_max - y_min) * 0.06, 0.02)

    daily_counts = (
        clean.groupby("event_day", observed=True)
        .size()
        .reindex(
            pd.date_range(clean["event_day"].min(), clean["event_day"].max(), freq="D"),
            fill_value=0,
        )
    )

    for frame_day in frame_days:
        subset = _window_subset(clean, frame_day, tail_days=max(1, tail_days))

        fig = plt.figure(figsize=(9, 6), dpi=128)
        gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.9, 1.35], hspace=0.12)
        ax_map = fig.add_subplot(gs[0])
        ax_ts = fig.add_subplot(gs[1])

        ax_map.set_facecolor("#f7f3ea")
        ax_map.grid(alpha=0.16)

        ax_map.scatter(
            clean["latitude_jitter"],
            clean["longitude_jitter"],
            s=7,
            c="#c9d2dc",
            alpha=0.16,
            linewidths=0,
            zorder=1,
        )

        if not subset.empty:
            ages = (frame_day - subset["event_day"]).dt.days.to_numpy(dtype=float)
            fatalities = subset["fatalities"].to_numpy(dtype=float)
            ax_map.scatter(
                subset["latitude_jitter"],
                subset["longitude_jitter"],
                s=_size_from_fatalities(subset["fatalities"]),
                c=_rgba_colors(ages=ages, fatalities=fatalities, tail_days=max(1, tail_days)),
                linewidths=0,
                zorder=3,
            )

        ax_map.set_xlim(x_min - x_margin, x_max + x_margin)
        ax_map.set_ylim(y_min - y_margin, y_max + y_margin)
        ax_map.set_xlabel("latitude")
        ax_map.set_ylabel("longitude")
        ax_map.set_title(
            f"Gaza ACLED conflict events through {frame_day.date().isoformat()}"
            f" (trailing {tail_days} days)",
            fontsize=12,
            pad=9,
        )

        shown = len(subset)
        cum = int((clean["event_day"] <= frame_day).sum())
        ax_map.text(
            0.012,
            0.985,
            f"shown={shown:,} | cumulative={cum:,} | total={len(clean):,}",
            transform=ax_map.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            color="#3f5468",
        )

        _plot_activity_context(
            ax=ax_ts,
            daily_counts=daily_counts,
            frame_day=frame_day,
            tail_days=tail_days,
        )
        fig.autofmt_xdate(rotation=0)

        frames.append(_frame_from_figure(fig))
        plt.close(fig)

    imageio.mimsave(output_path, frames, fps=fps)
    return output_path


def _widget_html(payload_json: str, frame_max: int, tail_default: int, tail_max: int) -> str:
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Gaza ACLED Trailing Window Explorer</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {
  --paper: #f8f4ec;
  --ink: #23374f;
  --accent: #264f7f;
  --line: #d8cfbd;
}
body {
  margin: 0;
  font-family: 'Avenir Next', 'Segoe UI', sans-serif;
  background: #efe9dd;
  color: var(--ink);
}
.wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 16px 22px;
}
.controls {
  display: grid;
  gap: 10px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
}
.row {
  display: grid;
  grid-template-columns: 220px 1fr 120px;
  gap: 10px;
  align-items: center;
}
.row label { font-size: 14px; font-weight: 600; }
.row output {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  color: #1d2f44;
}
#plot {
  height: 700px;
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--paper);
}
.meta {
  margin-top: 8px;
  font-size: 13px;
  color: #42576f;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
button {
  width: 100px;
  background: var(--accent);
  color: #fff;
  border: 0;
  border-radius: 6px;
  height: 34px;
  cursor: pointer;
}
button:hover { background: #1d4068; }
@media (max-width: 900px) {
  .row { grid-template-columns: 1fr; }
  .row output { text-align: left; }
  #plot { height: 520px; }
}
</style>
</head>
<body>
<div class="wrap">
  <h2 style="margin:0 0 8px;">Gaza ACLED Trailing Window Explorer</h2>
  <div class="controls">
    <div class="row">
      <label for="frame">Animation Frame</label>
      <input id="frame" type="range" min="0" max="__FRAME_MAX__" step="1" value="__FRAME_MAX__" />
      <output id="frameOut"></output>
    </div>
    <div class="row">
      <label for="tail">Point Lifetime (days)</label>
      <input id="tail" type="range" min="1" max="__TAIL_MAX__" step="1" value="__TAIL_DEFAULT__" />
      <output id="tailOut"></output>
    </div>
    <div class="row">
      <label for="speed">Playback Speed (fps)</label>
      <input id="speed" type="range" min="2" max="30" step="1" value="10" />
      <output id="speedOut"></output>
    </div>
    <div class="row" style="grid-template-columns:220px auto 1fr;">
      <label>Playback</label>
      <button id="play" type="button">Play</button>
      <span style="font-size:13px;color:#54697f;">
        Marker size = fatalities, color = fatalities > 0, alpha fades with age.
      </span>
    </div>
  </div>
  <div id="plot"></div>
  <div class="meta"><span id="dateLabel"></span><span id="countLabel"></span></div>
</div>
<script>
const data = __PAYLOAD_JSON__;
const frameSlider = document.getElementById('frame');
const tailSlider = document.getElementById('tail');
const speedSlider = document.getElementById('speed');
const frameOut = document.getElementById('frameOut');
const tailOut = document.getElementById('tailOut');
const speedOut = document.getElementById('speedOut');
const dateLabel = document.getElementById('dateLabel');
const countLabel = document.getElementById('countLabel');
const playBtn = document.getElementById('play');
let timerId = null;

function updatePlot() {
  const frameIdx = Number(frameSlider.value);
  const tailDays = Number(tailSlider.value);
  const currentDay = data.frame_day_indices[frameIdx];
  const startDay = Math.max(0, currentDay - tailDays + 1);

  const fatalX = [], fatalY = [], fatalS = [], fatalC = [];
  const nonX = [], nonY = [], nonS = [], nonC = [];

  for (let d = startDay; d <= currentDay; d += 1) {
    const dayEvents = data.days[d];
    if (!dayEvents) continue;
    const age = currentDay - d;
    const ageAlpha = Math.max(0.08, 1 - age / Math.max(tailDays, 1));

    for (let i = 0; i < dayEvents.length; i += 1) {
      const ev = dayEvents[i];
      const lat = ev[0];
      const lon = ev[1];
      const fatalities = ev[2];
      const size = ev[3];

      if (fatalities > 0) {
        fatalX.push(lat);
        fatalY.push(lon);
        fatalS.push(size);
        fatalC.push(`rgba(228,87,68,${(ageAlpha * 0.9).toFixed(4)})`);
      } else {
        nonX.push(lat);
        nonY.push(lon);
        nonS.push(Math.max(6, size * 0.75));
        nonC.push(`rgba(79,111,143,${(ageAlpha * 0.35).toFixed(4)})`);
      }
    }
  }

  const traces = [
    {
      type: 'scattergl',
      mode: 'markers',
      name: 'fatalities = 0',
      x: nonX,
      y: nonY,
      marker: { size: nonS, color: nonC, line: {width: 0} },
      hovertemplate: 'lat %{x:.4f}<br>lon %{y:.4f}<br>fatalities 0<extra></extra>'
    },
    {
      type: 'scattergl',
      mode: 'markers',
      name: 'fatalities > 0',
      x: fatalX,
      y: fatalY,
      marker: { size: fatalS, color: fatalC, line: {width: 0} },
      hovertemplate: 'lat %{x:.4f}<br>lon %{y:.4f}<br>fatalities > 0<extra></extra>'
    }
  ];

  const layout = {
    margin: {l: 70, r: 20, t: 58, b: 65},
    paper_bgcolor: '#f8f4ec',
    plot_bgcolor: '#f8f4ec',
    xaxis: {title: 'latitude', range: data.x_range, zeroline: false, gridcolor: '#dcd4c6'},
    yaxis: {title: 'longitude', range: data.y_range, zeroline: false, gridcolor: '#dcd4c6'},
    legend: {orientation: 'h', x: 0.01, y: 1.1},
    title: `Gaza ACLED: trailing ${tailDays} day window`
  };

  Plotly.react('plot', traces, layout, {responsive: true, displaylogo: false});
  frameOut.value = `${frameIdx + 1} / ${data.frame_labels.length}`;
  tailOut.value = `${tailDays} days`;
  speedOut.value = `${Number(speedSlider.value)} fps`;
  dateLabel.textContent = `Frame date: ${data.frame_labels[frameIdx]}`;
  countLabel.textContent = `Points shown: ${fatalX.length + nonX.length}`;
}

function stopPlayback() {
  if (timerId !== null) {
    clearTimeout(timerId);
    timerId = null;
  }
  playBtn.textContent = 'Play';
}

function playTick() {
  if (timerId === null) return;
  const next = Number(frameSlider.value) + 1;
  frameSlider.value = next >= data.frame_labels.length ? '0' : String(next);
  updatePlot();
  const delayMs = Math.max(35, Math.round(1000 / Math.max(2, Number(speedSlider.value))));
  timerId = setTimeout(playTick, delayMs);
}

function startPlayback() {
  if (timerId !== null) return;
  playBtn.textContent = 'Pause';
  timerId = setTimeout(playTick, 10);
}

frameSlider.addEventListener('input', updatePlot);
tailSlider.addEventListener('input', updatePlot);
speedSlider.addEventListener('input', updatePlot);

playBtn.addEventListener('click', () => {
  if (timerId !== null) {
    stopPlayback();
    return;
  }
  startPlayback();
});

window.addEventListener('blur', stopPlayback);
updatePlot();
</script>
</body>
</html>
"""
    html = html.replace("__PAYLOAD_JSON__", payload_json)
    html = html.replace("__FRAME_MAX__", str(frame_max))
    html = html.replace("__TAIL_DEFAULT__", str(tail_default))
    html = html.replace("__TAIL_MAX__", str(tail_max))
    return html


def build_points_tail_widget(
    events: pd.DataFrame,
    output_path: Path,
    *,
    by: str = "day",
    default_tail_days: int = 30,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clean = add_deterministic_jitter(normalize_event_frame(events), scale=0.0034)

    if clean.empty:
        output_path.write_text(
            "<html><body><p>No event data available.</p></body></html>\n",
            encoding="utf-8",
        )
        return output_path

    first_day = clean["event_day"].min()
    max_day = clean["event_day"].max()
    frame_days = _build_frame_days(clean, by=by)
    frame_labels = [day.date().isoformat() for day in frame_days]
    frame_day_indices = [int((day - first_day).days) for day in frame_days]

    horizon_days = int((max_day - first_day).days + 1)
    day_bins: list[list[list[float]]] = [[] for _ in range(horizon_days)]

    for row in clean.itertuples(index=False):
        day_idx = int((row.event_day - first_day).days)
        point_size = float(7.0 + min(26.0, np.sqrt(max(float(row.fatalities), 0.0)) * 2.6))
        day_bins[day_idx].append(
            [
                float(row.latitude_jitter),
                float(row.longitude_jitter),
                float(row.fatalities),
                point_size,
            ]
        )

    x_min = float(clean["latitude_jitter"].min())
    x_max = float(clean["latitude_jitter"].max())
    y_min = float(clean["longitude_jitter"].min())
    y_max = float(clean["longitude_jitter"].max())
    x_margin = max((x_max - x_min) * 0.06, 0.02)
    y_margin = max((y_max - y_min) * 0.06, 0.02)

    payload = {
        "days": day_bins,
        "frame_labels": frame_labels,
        "frame_day_indices": frame_day_indices,
        "x_range": [x_min - x_margin, x_max + x_margin],
        "y_range": [y_min - y_margin, y_max + y_margin],
    }

    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    frame_max = max(0, len(frame_labels) - 1)
    tail_default = max(1, int(default_tail_days))
    tail_max = max(30, horizon_days)

    output_path.write_text(
        _widget_html(
            payload_json=payload_json,
            frame_max=frame_max,
            tail_default=tail_default,
            tail_max=tail_max,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_path
