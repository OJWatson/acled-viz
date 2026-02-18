"""Forecast evaluation metrics."""

from __future__ import annotations

import math

import pandas as pd


def poisson_nll(observed: float, pred_mean: float) -> float:
    lam = max(pred_mean, 1e-9)
    return lam - observed * math.log(lam) + math.lgamma(observed + 1.0)


def evaluate_predictions(
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    merged = predictions.merge(actuals, on=["target_date", "horizon", "cell_id"], how="left")
    merged["observed"] = merged["observed"].fillna(0.0)
    merged["abs_err"] = (merged["pred_mean"] - merged["observed"]).abs()
    merged["sq_err"] = (merged["pred_mean"] - merged["observed"]) ** 2
    merged["nll_poisson_row"] = [
        poisson_nll(float(obs), float(pred))
        for obs, pred in zip(merged["observed"], merged["pred_mean"], strict=True)
    ]

    summary = (
        merged.groupby(["run_id", "issue_date", "horizon"], as_index=False)
        .agg(
            nll_poisson=("nll_poisson_row", "mean"),
            mae=("abs_err", "mean"),
            rmse=("sq_err", lambda s: float(s.mean() ** 0.5)),
        )
        .sort_values(["issue_date", "horizon"])
    )

    hit_rates = []
    for (run_id, issue_date, horizon), frame in merged.groupby(["run_id", "issue_date", "horizon"]):
        pred_top = set(frame.nlargest(top_k, columns=["pred_mean"])["cell_id"])
        obs_top = set(frame.nlargest(top_k, columns=["observed"])["cell_id"])
        hit = len(pred_top.intersection(obs_top)) / float(top_k)
        hit_rates.append(
            {
                "run_id": run_id,
                "issue_date": issue_date,
                "horizon": horizon,
                "hotspot_hitrate_k": hit,
                "runtime_s": 0.0,
            }
        )

    hits = pd.DataFrame(hit_rates)
    return summary.merge(hits, on=["run_id", "issue_date", "horizon"], how="left")
