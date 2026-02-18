from pathlib import Path

from typer.testing import CliRunner

from acled_viz.cli import app
from acled_viz.site.build import SiteBuildResult

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ACLED visualisation" in result.stdout


def test_site_build_demo(monkeypatch, tmp_path) -> None:
    def _fake_build_site(
        mode: str = "demo",
        start=None,
        end=None,
        tail_days: int = 30,
        show_roads: bool = False,
        show_poi: bool = False,
        osm_refresh: bool = False,
    ) -> SiteBuildResult:
        _ = (mode, start, end, tail_days, show_roads, show_poi, osm_refresh)
        return SiteBuildResult(docs_index=Path(tmp_path) / "index.html", run_id="demo_test")

    monkeypatch.setattr("acled_viz.cli.build_site", _fake_build_site)
    result = runner.invoke(app, ["site", "build", "--mode", "demo"])
    assert result.exit_code == 0
    assert "index" in result.stdout
