# INFRAguard AI Dashboard

React + Vite dashboard for the Intelligent Disaster Risk Management system.

## Run

```bash
npm install
npm run dev
```

The dashboard expects the FastAPI service at:

```
http://127.0.0.1:8000
```

Override it with:

```
VITE_API_URL=http://127.0.0.1:8000
```

## Current interaction

- Dashboard / Risk Map / Priority Assets / Alerts / Response Teams navigation
- Interactive Leaflet map with selectable assets
- Risk-level filtering
- Asset-level risk evidence and recommended action
- Priority queue selection
- Alert center
- API health/metadata connection indicator
- Demo fallback data when the backend is unavailable

The current risk records are clearly marked as demo data. The production ML model is a later integration boundary.
