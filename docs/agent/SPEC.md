# Gaza Conflict Visualisation + Forecast Gallery (Python) — Package + Website Spec
Date: 2026-02-16

This spec defines a new Python package and static website that:
1) pulls ACLED Gaza conflict events via `trace` (reusing existing ingestion functions);
2) produces high-quality spatio-temporal visualisations (animated points, KDE/heatmaps, summaries);
3) ingests and visualises **motac** conflict forecasts over time (including accuracy metrics);
4) builds a visually-led landing site plus full technical documentation (Sphinx).

It is written for low-noise, milestone-based execution by an agentic coding system.

---

## 1) Overview / Objective

Problem: We have modelling packages (`trace`, `motac`) but no dedicated, high-quality, reproducible “front-end” to (a) curate Gaza conflict event data, (b) generate compelling spatio-temporal visualisations, and (c) track and communicate forecast performance over time.

Target end-state:
- A new repo/package (working name: **`acled-viz`**, Python import: `acled_viz`) that provides:
  - data ingestion + caching for Gaza ACLED events (via `trace`);
  - a visualisation toolkit producing both **website-ready assets** (MP4/GIF/PNG/HTML) and reusable plotting APIs;
  - a forecast registry (database-backed) to ingest forecast runs (from `motac`) and compute/visualise accuracy.
- A static website (GitHub Pages compatible) where:
  - the **landing page** is a visually-dominant “storyboard” of Gaza conflict evolution over time (video/interactive);
  - a “Gallery” page shows additional visualisation types (points, KDE, heatmaps, summary charts);
  - a “Forecasts” page shows forecast maps and performance metrics across time;
  - a separate documentation section covers package API, CLI, configs, and reproducibility.

Definition of done (one sentence):
- Done when `uv run acled-viz site build --mode demo` produces a complete Sphinx site (HTML) with a hero animation, gallery, and forecasts pages, and `uv run pytest -q` passes, without requiring ACLED credentials.

---

## 2) Scope

### In scope
- A new Python package (MIT licensed) focused on Gaza conflict **visualisation + forecast tracking**.
- ACLED ingestion via `trace` functions with robust caching and provenance.
- A local forecast registry (DuckDB preferred) for storing forecast runs and evaluation outputs.
- Visual products:
  - point animations (time-lapse) over roads/POIs (optional) and region boundary;
  - KDE/heatmap animations (daily/weekly aggregation options);
  - summary time series (event counts, marks breakdown);
  - forecast maps and forecast-vs-actual comparison visuals;
  - forecast performance visuals (rolling metrics).
- A static website with a visually-driven landing page and separate docs section.
- High documentation standard: rendered tutorials/vignettes, reproducible commands, CI builds docs.

### Out of scope
- Implementing new conflict models (that is `motac`’s job).
- Operational deployment with a live backend (no always-on server, no authentication system).
- Publishing or redistributing raw ACLED data in-repo (raw data must remain local/private).
- Any MSF/private datasets (this repo is Gaza ACLED + forecasts only).
- Real-time streaming infrastructure (Kafka etc).

---

## 3) Repo Targets

- repo_id: acled-viz
  repo_path: /home/oai/.openclaw/workspace/repos/acled-viz
  branch: main

Notes:
- This repo *depends on* `trace-conflict` and `motac` as Python dependencies (pinned versions). We do not edit those repos in this spec.

---

## 4) Architecture (what will be built)

### 4.1 Package layout (strict)

```
acled-viz/
  pyproject.toml
  src/acled_viz/
    __init__.py

    core/
      config.py          # dataclasses/pydantic models for configs
      paths.py           # standard directory layout + run IDs
      provenance.py      # dataset provenance (query/hash/date)

    data/
      acled.py           # wrappers around trace ACLED functions
      demo.py            # small synthetic/demo dataset for docs/tests
      region.py          # Gaza bbox/polygon helpers (config-driven)
      cache.py           # parquet caches + manifests

    spatial/
      osm.py             # roads/POIs extraction (optional) + caching
      grid.py            # optional grid surfaces for heatmaps
      geometry.py        # boundary polygons, clipping, plotting helpers

    viz/
      points.py          # point maps + animations
      kde.py             # KDE/heatmap surfaces + animations
      summaries.py       # time series, breakdowns
      styling.py         # central style config (fonts, sizes, legends)

    forecasts/
      schema.py          # forecast bundle contracts
      registry.py        # DuckDB registry (runs, artefacts, metrics)
      ingest_motac.py    # import from motac outputs or run motac workflows
      eval.py            # accuracy metrics + hotspot metrics
      viz.py             # forecast maps + comparisons

    site/
      build.py           # “site build” orchestration: assets + docs
      assets.py          # paths + asset builders (hero video, gallery tiles)

    cli.py               # Typer CLI entrypoint
  docs/
    conf.py
    index.md             # visually-led landing page (hero)
    gallery.md
    forecasts.md
    installation.md
    api/...
    tutorials/...
  notebooks/             # vignettes (rendered by nbsphinx)
  scripts/
    ci.sh
    test.sh
  tests/
```

### 4.2 Core data contracts

#### Events table (canonical)
All Gaza event data are stored as a canonical events table:

- Columns (required):
  - `event_id` (str)
  - `event_date` (datetime64[ns])
  - `latitude` (float)
  - `longitude` (float)
  - `event_type` (str)
  - `sub_event_type` (optional str)
  - `fatalities` (optional float/int)
  - `source` (str; always `"ACLED"`)
- Columns (derived, optional):
  - `day_index` (int; relative to chosen start date)
  - `mark` (int; stable mapping for `event_type`)
  - `week_index` (int)
  - `geometry` (optional; geopandas)

Storage:
- `data/acled/gaza/events.parquet`
- `data/acled/gaza/meta.json` (provenance, filters, hashes)

#### Forecast bundle (registry contract)
We store forecast runs as:

1) **metadata** (DuckDB table `forecast_runs`)
2) **predictions** (partitioned parquet)
3) **evaluation** (DuckDB + parquet for time-indexed metrics)

Predictions parquet schema (minimum viable):
- `run_id` (str)
- `issue_date` (date)
- `target_date` (date)
- `horizon` (int)
- `cell_id` (int) or `lat`/`lon` (if point forecast)
- `pred_mean` (float)
- optional: `pred_q05`, `pred_q50`, `pred_q95` (floats)
- optional: `pred_samples_path` (str; if storing samples separately)

Evaluation schema:
- by (run_id, issue_date, horizon):
  - `nll_poisson` (float) or other proper score depending on available distribution
  - `mae` (float)
  - `rmse` (float)
  - `hotspot_hitrate_k` (float; with k configured)
  - `runtime_s` (float; optional)

---

## 5) Technology choices (defaults)

### Dependencies (core)
- `trace-conflict` (for ACLED fetch/prepare; must be importable)
- `motac` (for running/reading road-constrained Hawkes forecasts)
- `pandas`, `numpy`, `pyarrow` (storage)
- `requests` (network fetch)
- `duckdb` (forecast registry)
- `matplotlib` (static plots; also used to render frames reliably)
- `plotly` (interactive HTML embeds; optional but recommended)
- `geopandas`, `shapely`, `pyproj` (geometry, optional roads/boundaries)
- `osmnx` (roads/POIs extraction; cached)
- `imageio` + `imageio-ffmpeg` OR system `ffmpeg` (for MP4)

### Documentation/site
- `sphinx`, `myst-parser`, `nbsphinx`, `sphinx-autodoc-typehints`
- Theme: `pydata-sphinx-theme` (preferred for modern landing pages)
- Optional: `sphinx-design` for gallery grids/cards

### Packaging / tooling
- Use `uv` with dependency groups (`dev`, `docs`) and a lockfile for reproducibility (match motac style).
- Code quality: `ruff`, `pytest`, (optional) `mypy`.
- CLI: `typer`.

---

## 6) Milestones (ordered, single-purpose slices)

### milestone_id: M0.REALIGN
Objective:
- Create repo skeleton, toolchain, CI, and a “demo-only” pipeline that can build docs without credentials.

Boundaries:
- No real ACLED fetch. Use only demo data.
- No forecast registry yet.

Outputs:
- Packaging scaffold (`pyproject.toml`, `src/acled_viz`)
- `scripts/ci.sh` and `scripts/test.sh`
- Sphinx docs skeleton with placeholder landing/gallery/forecasts pages
- `docs/agent/PLAN.md` (Now/Next/Later)

Acceptance criteria (testable):
- [ ] `uv run python -c "import acled_viz; print(acled_viz.__version__)"` prints a version
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest -q` passes (even if only trivial tests)
- [ ] `cd docs && uv run make html` succeeds using demo assets

---

### milestone_id: M1
Objective:
- Implement ACLED ingestion wrappers (via `trace`) with caching + provenance and a Gaza region config.

Boundaries:
- No visualisations yet beyond minimal sanity plot.
- No forecast ingestion yet.

Outputs:
- `acled_viz.data.acled.fetch_gaza_events(...)`
- local cache write/read: `events.parquet` + `meta.json`
- demo dataset remains for CI/docs

Acceptance criteria:
- [ ] `uv run acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo` creates:
  - `data/acled/gaza/events.parquet`
  - `data/acled/gaza/meta.json`
- [ ] Unit tests validate:
  - canonical columns exist
  - meta includes query parameters and a content hash

---

### milestone_id: M2
Objective:
- Implement the core visualisation generators and export routines (MP4/GIF/HTML), operating on the cached events table.

Boundaries:
- Forecast visuals not included (that is M4).
- Focus on “conflict evolution over time” visual products.

Outputs:
- `acled_viz.viz.points.animate_points(...)`
- `acled_viz.viz.kde.animate_kde(...)`
- `acled_viz.viz.summaries.plot_timeseries(...)`
- export utilities to:
  - MP4 (hero + gallery)
  - PNG (thumbnail tiles)
  - HTML (plotly interactive; optional)

Acceptance criteria:
- [ ] `uv run acled-viz viz build-gallery --mode demo` writes:
  - `docs/_static/gallery/hero_points.mp4`
  - `docs/_static/gallery/kde_weekly.mp4`
  - `docs/_static/gallery/summary_counts.png`
- [ ] Each artefact is non-empty and renderable (file size > threshold checked in tests)

---

### milestone_id: M3
Objective:
- Add forecast registry database + forecast bundle schema.

Boundaries:
- Do not implement rich forecast visuals yet (M4).
- Focus on durable storage, ingestion and retrieval.

Outputs:
- `acled_viz.forecasts.registry` using DuckDB:
  - initialise DB
  - register runs
  - list runs
  - attach artefact paths
- `acled_viz.forecasts.schema` dataclasses for run metadata + predictions
- `acled_viz.forecasts.ingest_motac` minimal ingestion path:
  - (A) run motac workflow for a given dataset + substrate and persist predictions
  - (B) ingest an existing motac output directory if provided (best-effort)

Acceptance criteria:
- [ ] `uv run acled-viz forecasts init-db` creates `data/forecasts/registry.duckdb`
- [ ] `uv run acled-viz forecasts ingest-motac --mode demo` registers 1 demo run with predictions parquet
- [ ] `uv run acled-viz forecasts list-runs` prints that run

---

### milestone_id: M4
Objective:
- Implement forecast evaluation + forecast visualisation products for the website.

Boundaries:
- This milestone must not redesign DB schema (only additive fields/tables).

Outputs:
- Metrics:
  - Poisson NLL (given mean forecasts)
  - MAE/RMSE
  - hotspot hit rate (top-k cells)
- Visualisations:
  - forecast vs actual time series
  - “issue date” summary plots
  - map comparison tiles (predicted surface vs observed counts)
  - rolling performance charts

Acceptance criteria:
- [ ] `uv run acled-viz forecasts build-report --run-id <demo_run_id>` writes:
  - `docs/_static/forecasts/<run_id>/perf_timeseries.png`
  - `docs/_static/forecasts/<run_id>/map_compare_h1.png`
  - `docs/_static/forecasts/<run_id>/metrics.json`
- [ ] Tests verify metrics keys exist and plots are produced

---

### milestone_id: M5
Objective:
- Build the actual “two-purpose” website: visual-first landing + gallery + forecasts + package docs.

Boundaries:
- No new modelling, no new DB features.
- This is integration + presentation.

Outputs:
- Sphinx site with:
  - `index.md` landing page: hero video + minimal text + nav
  - `gallery.md`: grid of visual types and embedded videos/tiles
  - `forecasts.md`: run selector (static list) + embedded forecast performance visuals
  - docs pages: installation, CLI, API reference, tutorials/vignettes
- At least 2 vignettes rendered:
  - “Gaza events quickstart”
  - “Forecast ingestion and evaluation quickstart”

Acceptance criteria:
- [ ] `cd docs && uv run make html` produces:
  - landing page with embedded MP4
  - gallery page with ≥ 3 embedded assets
  - forecasts page with ≥ 1 run shown in demo mode
- [ ] GitHub Actions workflow builds docs on PR and deploys on main push

---

### milestone_id: M6.OSM
Objective:
- Complete OSM enrichment so existing visuals can optionally include roads and places of interest (POIs).

Boundaries:
- No changes to model logic or forecast schema.
- OSM overlays must be optional and cache-backed.

Outputs:
- `acled_viz.spatial.osm` implemented with:
  - region-scoped OSM fetch and local cache
  - roads and POI extraction helpers
- Visual overlays available in core views:
  - points animation
  - KDE/heatmap animation
  - interactive trailing-window widget
- CLI options for overlay toggles, for example:
  - `--show-roads`
  - `--show-poi`
- Docs updates:
  - gallery examples with and without overlays
  - clear note on optional network dependency and local caching

Acceptance criteria:
- [ ] `uv run acled-viz viz build-gallery --mode full --show-roads --show-poi` produces overlay-enabled assets without breaking non-overlay mode.
- [ ] Unit tests cover OSM cache read/write and no-network fallback behavior.
- [ ] `docs/gallery.md` includes at least one overlay-enabled example and explains toggles.

---

### milestone_id: M7.END
Objective:
- Harden and finalise for public release: reproducibility, guardrails, licensing, and “no sensitive data” guarantees.

Boundaries:
- Bugfixes + documentation only. No new features.

Outputs:
- Clear “data policy” documentation:
  - raw ACLED not redistributed
  - demo data synthetic
  - how to build full site locally with credentials
- CLI help polished + consistent
- Release checklist + version bump

Acceptance criteria:
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest -q` passes
- [ ] `cd docs && uv run make html` passes (demo mode)
- [ ] `uv run acled-viz site build --mode demo` completes end-to-end and writes `docs/_build/html/index.html`

---

## 7) Acceptance Criteria (global, additional)

- [ ] The repo includes `docs/agent/PLAN.md` and it is updated at least once per milestone.
- [ ] Every public CLI command has `--help` with examples.
- [ ] No raw ACLED events are committed to git (enforced by `.gitignore` + a CI check that blocks common cache paths).
- [ ] There is a working “demo mode” that does not require:
  - ACLED credentials
  - internet access
  - large downloads

---

## 8) Local Gates / Commands

Preferred (mirroring motac conventions):
1. `./scripts/ci.sh`
2. `./scripts/test.sh`

If absent/early bootstrapping:
1. `uv run ruff check .`
2. `uv run python -m pytest -q`
3. `cd docs && uv run make html`
4. `uv run acled-viz site build --mode demo`

---

## 9) CI Expectations + CI_GATED

CI workflows required:
- `ci.yml`: lint + tests
- `docs.yml`: build docs; deploy on main

CI_GATED milestones:
- `M7.END` is CI_GATED (must wait for CI green before concluding).

Failure handling:
- smallest hotfix slice; rerun local gates; push; re-wait CI.

---

## 10) Risk Flags / Dependencies

risk_flags:
- `security_sensitive`: conflict-related visualisations; avoid sharing anything beyond public ACLED-derived outputs.
- `operational_risk`: do not imply operational guidance; present forecasts with uncertainty and clear caveats.
- `licensing_sensitive`: ACLED terms; no raw redistribution.

dependencies:
- ACLED credentials (optional; required only for full fetch mode)
- network access for OSMnx fetch (optional; cacheable)
- ffmpeg availability (use `imageio-ffmpeg` fallback if system ffmpeg missing)

mitigations:
- Demo dataset ships with repo for CI/docs.
- Full fetch/build is an opt-in local step with explicit warnings and provenance logs.
- CI checks block committing cache/data directories.

---

## 11) Escalation Points (predeclared decisions)

E0 (Repo name and import name)
- Trigger: if `acled-viz` conflicts with existing internal naming.
- Options:
  A) `acled-viz` (recommended default)
  B) `conflictviz` (more general)
  C) `gaza_atlas` (more narrative)
- Recommended: A

E1 (Interactive mapping)
- Trigger: if plotly HTML embeds are too heavy for the landing page.
- Options:
  A) MP4-first (recommended; robust and lightweight)
  B) Plotly-first (interactive; heavier)
- Recommended: A, with optional Plotly in Gallery page

E2 (Forecast geometry)
- Trigger: if motac forecasts are cell-based but we need lat/lon point surfaces.
- Options:
  A) choropleth over grid (recommended)
  B) rasterised heatmap surface
  C) point-based predictions (future)
- Recommended: A

---

## 12) Deliverables / Artifacts

Commit format:
- `[M0.REALIGN] <summary>`
- `[M1] <summary>` ...
- `[M7.END] <summary>`

Required artefacts:
- `docs/agent/PLAN.md` updated per milestone
- durable logs:
  - `~/.openclaw/workspace/logs/acled-viz/<utc_ts>_<milestone_id>.log`

Outcome fields (record in final summary per milestone):
- repo_id, repo_path, milestone_id, branch, executed, commit_sha, pushed,
  local_gates, ci_gated, ci_status, reason, log_path, spec_sources_used

---

## Appendix A) CLI surface (planned)

```
acled-viz data fetch-acled --region gaza --start YYYY-MM-DD --end YYYY-MM-DD [--api-token ...]
acled-viz data show-cache
acled-viz viz build-gallery [--mode demo|full] [--fps 10] [--by day|week]
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --run-dir <path>  OR  --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <id>
acled-viz site build --mode demo|full
```

---

## Appendix B) Data policy (must appear in docs)

- This repo does not redistribute raw ACLED data.
- Demo data are synthetic and included for testing/docs only.
- Users who have ACLED access may fetch data locally and generate derived visual assets.
- Derived visualisations published to a website should be reviewed for compliance with ACLED terms and any institutional guidance.
