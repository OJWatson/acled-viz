# ACLED API Wrapper

`acled_viz` includes a lightweight ACLED OAuth wrapper used by `fetch-acled --mode full`.

## What it does

- Resolves credentials from env vars or local credential files.
- Requests an OAuth access token from `https://acleddata.com/oauth/token`.
- Reuses the token in-memory until expiry (with a small refresh buffer).
- Fetches events from `https://acleddata.com/api/acled/read`.
- Returns rows that are normalized/cached by `acled_viz.data.acled`.

## Credential sources (in order)

1. `ACLED_EMAIL` + `ACLED_PASSWORD`
2. `ACLED_CREDENTIALS_FILE`
3. `~/.config/acled/oauth_credentials.json`

## Quick usage

```python
from datetime import date
from acled_viz.data.acled import fetch_gaza_events

result = fetch_gaza_events(
    start=date(2023, 10, 1),
    end=date(2023, 10, 14),
    mode="full",
    region="gaza",
)

print(result.events_path)
print(result.meta_path)
```

## Notes

- If credentials are unavailable in full mode, `acled_viz` attempts local snapshot fallback.
- The wrapper is intentionally lightweight and uses stdlib HTTP (no `requests` dependency).
- The in-memory token cache is process-local and is not persisted to disk.
