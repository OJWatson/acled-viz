# PLAN

## Now

- [x] Milestone `M6.OSM`: finish OSM enrichment so all core visuals can optionally overlay
  cached road networks and places of interest (POIs), with simple on/off controls.
- [x] Milestone `M0.REALIGN`: package/docs/tooling scaffold with demo-safe docs build.
- [x] Milestone `M1`: ACLED ingestion wrappers and cache/provenance.
- [x] Milestone `M2`: point/KDE/summary visual products.
- [x] Milestone `M3`: DuckDB forecast registry + demo motac ingestion.
- [x] Milestone `M4`: forecast evaluation metrics + report visuals.
- [x] Milestone `M5`: visual-first Sphinx site integration with gallery/forecasts/docs pages.
- [x] Visual rework pass (2026-02-18):
  - eliminate demo overwrite in docs CI
  - rebuild gallery from full cached ACLED fixture horizon
  - improve point/KDE/summary visual quality
  - add full-horizon daily interactive widget with controllable point lifetime

## Next

- [ ] Milestone `M7.END`: hardening, data policy, CLI help consistency, local gates.

## Later

- [ ] Optional full-mode integration against live `trace`/`motac` repo outputs.
- [ ] Additional interactive Plotly embeds if needed.
