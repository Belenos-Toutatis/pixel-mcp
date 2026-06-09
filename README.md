# pixel-mcp

MCP server for the [Google Health API](https://developers.google.com/health) (v4) — access Pixel Watch, Fitbit, and Google Health data from Claude or any MCP client.

Built with Python + [FastMCP](https://github.com/jlowin/fastmcp). Replaces the deprecated Fitbit Web API.

## Features

### Health data (31 convenience tools)
- **Activity** — steps, distance, active energy burned, active zone minutes, activity level, sedentary periods, floors
- **Heart** — heart rate, resting heart rate, heart rate zones, HRV, HRV intraday
- **Sleep** — sleep sessions, sleep temperature
- **Body** — weight, body fat, height, core body temperature
- **Breathing** — respiratory rate, daily respiratory rate, SpO2, daily SpO2
- **Exercise** — exercise sessions with export to TCX
- **Nutrition** — nutrition log, hydration log
- **Medical** — ECG, IRN alerts, IRN profile
- **Other** — VO2 max, run VO2 max

### Write tools
- **Log weight** — record a weigh-in (kg)
- **Log body fat** — record body fat percentage
- **Log height** — record height (cm)
- **Log hydration** — record water intake (ml)
- **Delete data point** — remove any data point by ID

### Generic CRUD
- List, get, create, patch, delete any data point
- Rollup and daily rollup aggregations
- Reconcile data points
- List all supported data types

### Profile & devices
- User identity, profile, settings
- List paired devices, device details

### 50+ tools total

## Setup

### 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable the **Google Health API**
4. Go to **OAuth consent screen** > add all `googlehealth.*` scopes (15 scopes)
5. Create an **OAuth 2.0 Client ID** (Web application) with redirect URI: `http://127.0.0.1:8733/callback`

> **Tip:** Publish your app (OAuth consent screen > Audience > Publish) to avoid refresh token expiry every 7 days in "Testing" mode.

### 2. Configure credentials

```bash
cd pixel-mcp
cp .env.example .env
# Edit .env with your GOOGLE_HEALTH_CLIENT_ID and GOOGLE_HEALTH_CLIENT_SECRET
```

### 3. Install and run

```bash
uv sync
uv run python -m pixel_mcp.server

# First run opens your browser for Google OAuth authorization
```

### 4. Add to Claude Desktop

```json
{
  "mcpServers": {
    "pixel": {
      "command": "uv",
      "args": ["--directory", "/path/to/pixel-mcp", "run", "python", "-m", "pixel_mcp.server"]
    }
  }
}
```

## Authentication

OAuth 2.0 with loopback redirect on `http://127.0.0.1:8733/callback`. Tokens persisted in `~/.config/pixel-mcp/tokens.json`. Auto-refresh with automatic re-auth on `invalid_grant`.

## Google Health API filter quirks

This server handles several undocumented filter syntax quirks:
- Exercise and nutrition use `civil_start_time` (not `start_time`)
- Sleep is indexed by `end_time` (wake-up time)
- ECG only supports single `>=` bound (no upper bound)
- Floors require `dailyRollUp` (list not supported)
- respiratory-rate-sleep-summary is a sample type, not interval

## Logging

JSON-lines logs in `~/.config/pixel-mcp/logs/pixel-mcp.log`. Set `PIXEL_MCP_LOG_LEVEL=DEBUG` in `.env`.

## License

MIT
