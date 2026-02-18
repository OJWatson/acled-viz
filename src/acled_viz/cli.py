"""Typer CLI for acled-viz."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import typer

from acled_viz import __version__
from acled_viz.core.paths import forecasts_dir
from acled_viz.data.acled import cache_paths, fetch_gaza_events
from acled_viz.forecasts.ingest_motac import ingest_demo, ingest_run_dir
from acled_viz.forecasts.registry import init_registry, list_runs
from acled_viz.site.assets import build_gallery_assets
from acled_viz.site.build import build_forecast_report, build_site, ensure_event_cache

app = typer.Typer(help="ACLED visualisation and forecast gallery toolkit")
data_app = typer.Typer(help="Data commands")
viz_app = typer.Typer(help="Visualisation commands")
forecasts_app = typer.Typer(help="Forecast commands")
site_app = typer.Typer(help="Site commands")

app.add_typer(data_app, name="data")
app.add_typer(viz_app, name="viz")
app.add_typer(forecasts_app, name="forecasts")
app.add_typer(site_app, name="site")


@app.command("version")
def version() -> None:
    """Print version."""
    typer.echo(__version__)


@data_app.command("fetch-acled")
def data_fetch_acled(
    region: str = typer.Option("gaza", help="Region id, e.g. gaza"),
    start: str = typer.Option(..., help="Start date YYYY-MM-DD"),
    end: str = typer.Option(..., help="End date YYYY-MM-DD"),
    mode: str = typer.Option("demo", help="demo or full"),
) -> None:
    """Fetch and cache ACLED events.

    Example:
    acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as exc:
        raise typer.BadParameter("start/end must be YYYY-MM-DD") from exc

    result = fetch_gaza_events(start=start_date, end=end_date, mode=mode, region=region)
    typer.echo(f"Wrote {result.events_path}")
    typer.echo(f"Wrote {result.meta_path}")


@data_app.command("show-cache")
def data_show_cache(region: str = typer.Option("gaza")) -> None:
    """Show cache paths."""
    cache = cache_paths(region=region)
    typer.echo(str(cache.events_path))
    typer.echo(str(cache.meta_path))


@viz_app.command("build-gallery")
def viz_build_gallery(
    mode: str = typer.Option("demo", help="demo or full"),
    fps: int = typer.Option(8, help="Frames per second"),
    by: str = typer.Option("week", help="day or week aggregation"),
    tail_days: int = typer.Option(30, help="Point lifetime in days for point animation"),
    start: str | None = typer.Option(None, help="Optional start YYYY-MM-DD"),
    end: str | None = typer.Option(None, help="Optional end YYYY-MM-DD"),
) -> None:
    """Build point/KDE/summary gallery assets."""
    if (start is None) != (end is None):
        raise typer.BadParameter("Provide both --start and --end, or neither")

    if start and end:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except ValueError as exc:
            raise typer.BadParameter("start/end must be YYYY-MM-DD") from exc
        fetch_gaza_events(start=start_date, end=end_date, mode=mode)
    else:
        ensure_event_cache(mode=mode)

    assets = build_gallery_assets(fps=fps, by=by, tail_days=tail_days)
    typer.echo(f"Wrote {assets.hero_points_mp4}")
    typer.echo(f"Wrote {assets.kde_weekly_mp4}")
    typer.echo(f"Wrote {assets.summary_counts_png}")
    typer.echo(f"Wrote {assets.fatalities_facets_png}")
    typer.echo(f"Wrote {assets.points_windowed_html}")


@forecasts_app.command("init-db")
def forecasts_init_db() -> None:
    """Initialise forecast registry database."""
    paths = init_registry(forecasts_dir())
    typer.echo(str(paths.db_path))


@forecasts_app.command("ingest-motac")
def forecasts_ingest_motac(
    mode: str = typer.Option("demo", help="demo or full"),
    run_dir: Path | None = typer.Option(None, help="Existing motac output directory"),
) -> None:
    """Ingest motac predictions.

    Example:
    acled-viz forecasts ingest-motac --mode demo
    """
    if mode == "demo":
        run_id = ingest_demo(forecasts_dir())
    else:
        if run_dir is None:
            raise typer.BadParameter("--run-dir is required when --mode full")
        run_id = ingest_run_dir(forecasts_dir(), run_dir=run_dir)
    typer.echo(run_id)


@forecasts_app.command("list-runs")
def forecasts_list_runs() -> None:
    """List registered forecast runs."""
    db_path = init_registry(forecasts_dir()).db_path
    runs = list_runs(db_path)
    if runs.empty:
        typer.echo("No runs found")
        return
    typer.echo(runs.to_string(index=False))


@forecasts_app.command("build-report")
def forecasts_build_report(run_id: str = typer.Option(..., help="Run id to evaluate")) -> None:
    """Build forecast report assets."""
    out_dir = build_forecast_report(run_id)
    typer.echo(str(out_dir / "perf_timeseries.png"))
    typer.echo(str(out_dir / "map_compare_h1.png"))
    typer.echo(str(out_dir / "metrics.json"))


@site_app.command("build")
def site_build(
    mode: str = typer.Option("demo", help="demo or full"),
    start: str | None = typer.Option(None, help="Optional start YYYY-MM-DD"),
    end: str | None = typer.Option(None, help="Optional end YYYY-MM-DD"),
    tail_days: int = typer.Option(30, help="Point lifetime in days for point animation"),
) -> None:
    """Build full site end-to-end. Example: acled-viz site build --mode demo"""
    if (start is None) != (end is None):
        raise typer.BadParameter("Provide both --start and --end, or neither")

    start_date: date | None = None
    end_date: date | None = None
    if start and end:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except ValueError as exc:
            raise typer.BadParameter("start/end must be YYYY-MM-DD") from exc

    result = build_site(mode=mode, start=start_date, end=end_date, tail_days=tail_days)
    typer.echo(json.dumps({"run_id": result.run_id, "index": str(result.docs_index)}))


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
