# Gaza Events Quickstart

```bash
acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
acled-viz viz build-gallery --mode demo
```

This creates:

- `data/acled/gaza/events.parquet`
- `data/acled/gaza/meta.json`
- `docs/_static/gallery/hero_points.mp4`
- `docs/_static/gallery/kde_weekly.mp4`
- `docs/_static/gallery/summary_counts.png`
