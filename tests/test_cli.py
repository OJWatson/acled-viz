from typer.testing import CliRunner

from acled_viz.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ACLED visualisation" in result.stdout


def test_site_build_demo() -> None:
    result = runner.invoke(app, ["site", "build", "--mode", "demo"])
    assert result.exit_code == 0
    assert "index" in result.stdout
