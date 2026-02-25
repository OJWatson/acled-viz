# Installation

## Install

```bash
uv sync --extra dev --extra docs
uv sync --extra dev --extra docs --extra osm
```

Full mode uses a built-in lightweight ACLED OAuth wrapper (no `trace` install required).
Set `ACLED_EMAIL` and `ACLED_PASSWORD`, or set `ACLED_CREDENTIALS_FILE` to a file containing
email/password (JSON or 2-line plaintext). If credentials are unavailable, full mode can fall back
to a local ACLED snapshot (for example, `acled_example.csv` in repo root).
OSM overlays require `osmnx` and network access on first fetch, then reuse local cache files in `data/osm/`.

## GitHub Actions secrets (for full-mode CI)

Never commit ACLED credentials to git. If you need full-mode API calls in CI, add repo secrets:

- `ACLED_EMAIL`
- `ACLED_PASSWORD`

Setup path in GitHub:

1. Repository **Settings**
2. **Secrets and variables** → **Actions**
3. **New repository secret**
4. Add `ACLED_EMAIL` and `ACLED_PASSWORD`

The CI workflow includes an optional full-mode smoke step that runs only when both secrets are set.

For GitHub Pages in this repo, gallery assets are expected to be generated and committed first; CI then builds Sphinx HTML without regenerating demo visuals.

## Local gates

```bash
./scripts/ci.sh
./scripts/test.sh
```

## CLI examples

```bash
acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
acled-viz viz build-gallery --mode demo --tail-days 30
acled-viz viz build-gallery --mode full --start 2023-09-04 --end 2026-02-18 --by week --tail-days 45
acled-viz viz build-gallery --mode full --show-roads --show-poi --tail-days 45
acled-viz site build --mode full --start 2023-09-04 --end 2026-02-18 --tail-days 45
acled-viz site build --mode full --show-roads --show-poi --tail-days 45
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <id>
```
