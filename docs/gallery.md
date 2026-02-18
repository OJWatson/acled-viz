# Gallery

`acled-viz` builds a full gallery of spatio-temporal assets from ACLED Gaza events.

## Hero Points Animation

Points fade out after a configurable trailing window (`--tail-days`), so motion reflects
recent conflict activity rather than only cumulative buildup.

```{raw} html
<video controls muted loop playsinline width="100%">
  <source src="_static/gallery/hero_points.mp4" type="video/mp4" />
</video>
```

## Weekly KDE Animation

```{raw} html
<video controls muted loop playsinline width="100%">
  <source src="_static/gallery/kde_weekly.mp4" type="video/mp4" />
</video>
```

## Summary Counts

![Summary counts](_static/gallery/summary_counts.png)

## Fatalities Facet Grid

This view bins events across the full cached horizon into evenly spaced time slices,
with point size scaling by fatalities and color separating `fatalities > 0`.

![Fatalities facet grid](_static/gallery/fatalities_facets.png)

## Interactive Trailing Window Explorer

Use the slider to control how many days points persist after appearing.

```{raw} html
<iframe src="_static/gallery/points_windowed.html" style="width:100%;height:860px;border:0;border-radius:10px;"></iframe>
```
