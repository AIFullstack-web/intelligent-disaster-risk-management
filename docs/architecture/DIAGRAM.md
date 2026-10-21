# INFRAguard AI Architecture

## Current demo path

```mermaid
flowchart LR
    U[Operator] --> UI[React Risk Command Center]
    UI --> API[FastAPI REST API]
    API --> DATA[Risk Records]
    API --> ENGINE[Demo Risk Engine]
    DATA --> UI
    ENGINE --> API
    UI --> MAP[Interactive GIS Map]
    UI --> PRI[Priority Queue]
    UI --> ALT[Alert Center]
```

## Target research path

```mermaid
flowchart LR
    R[Rainfall / Weather] --> P[Data Processing]
    T[Terrain / Elevation] --> P
    G[Geospatial / Land Data] --> P
    I[Infrastructure Data] --> P
    H[Historical Events] --> P

    P --> F[Feature Engineering]
    F --> M[ML Model]
    M --> X[Explainability + Calibration]
    X --> D[Vulnerability / Risk]
    D --> Q[Inspection Priority Engine]
    Q --> API[FastAPI]
    API --> GIS[React GIS Dashboard]
    API --> ALERT[Alerts]
    API --> RESP[Response Support]
```

## Demo boundary

The present dashboard intentionally uses deterministic demo records and a transparent rule-based risk engine. It is a software integration milestone, not the final trained research model.
