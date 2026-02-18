"""Synthetic demo datasets used for tests/docs builds."""

from datetime import date, datetime, timedelta

import pandas as pd

EVENT_TYPES = ["Battles", "Explosions/Remote violence", "Violence against civilians"]


def demo_events(start: date, end: date) -> pd.DataFrame:
    if end < start:
        raise ValueError("end must be on or after start")

    rows = []
    start_dt = datetime.combine(start, datetime.min.time())
    num_days = (end - start).days + 1
    for day in range(num_days):
        for idx in range(6):
            event_type = EVENT_TYPES[(day + idx) % len(EVENT_TYPES)]
            rows.append(
                {
                    "event_id": f"DEMO-{day:02d}-{idx}",
                    "event_date": start_dt + timedelta(days=day),
                    "latitude": 31.30 + 0.03 * (idx % 5) + 0.002 * day,
                    "longitude": 34.28 + 0.04 * ((day + idx) % 6),
                    "event_type": event_type,
                    "sub_event_type": "Synthetic",
                    "fatalities": (day + idx) % 4,
                    "source": "ACLED",
                }
            )
    frame = pd.DataFrame(rows)
    frame["event_date"] = pd.to_datetime(frame["event_date"])
    return frame


def demo_forecast_predictions(run_id: str) -> pd.DataFrame:
    issue = datetime(2023, 10, 8)
    rows = []
    for horizon in (1, 2, 3):
        for cell_id in range(1, 13):
            pred = 1.0 + (cell_id % 4) * 0.4 + horizon * 0.2
            rows.append(
                {
                    "run_id": run_id,
                    "issue_date": issue.date().isoformat(),
                    "target_date": (issue + timedelta(days=horizon)).date().isoformat(),
                    "horizon": horizon,
                    "cell_id": cell_id,
                    "pred_mean": round(pred, 4),
                    "pred_q05": max(0.0, round(pred - 0.7, 4)),
                    "pred_q50": round(pred, 4),
                    "pred_q95": round(pred + 0.9, 4),
                }
            )
    return pd.DataFrame(rows)


def demo_actual_counts() -> pd.DataFrame:
    issue = datetime(2023, 10, 8)
    rows = []
    for horizon in (1, 2, 3):
        target = (issue + timedelta(days=horizon)).date().isoformat()
        for cell_id in range(1, 13):
            observed = (cell_id * horizon) % 6 + 1
            rows.append(
                {
                    "target_date": target,
                    "horizon": horizon,
                    "cell_id": cell_id,
                    "observed": observed,
                }
            )
    return pd.DataFrame(rows)
