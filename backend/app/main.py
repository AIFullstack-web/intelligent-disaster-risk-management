from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import RiskRecord
from .services.risk import calculate_demo_risk
from .store import RISK_RECORDS

app = FastAPI(
    title="Intelligent Disaster Risk Management API",
    version="0.2.0",
    description="Backend API for disaster risk assessment and emergency response support.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "disaster-risk-management-api",
        "version": "0.2.0",
    }


@app.get("/api/metadata")
def metadata():
    return {
        "project": "INFRAguard AI",
        "hazard_focus": "Flood-related / extreme rainfall conditions",
        "engine": "demo-rule-based",
        "production_model": False,
    }


@app.get("/api/risks", response_model=list[RiskRecord])
def list_risks():
    return RISK_RECORDS


@app.get("/api/risks/{risk_id}", response_model=RiskRecord)
def get_risk(risk_id: str):
    for record in RISK_RECORDS:
        if record.id == risk_id:
            return record
    raise HTTPException(status_code=404, detail="Risk record not found")


@app.get("/api/priorities", response_model=list[RiskRecord])
def priorities():
    return sorted(
        RISK_RECORDS,
        key=lambda record: record.priority_score,
        reverse=True,
    )


@app.get("/api/alerts")
def alerts():
    critical = [
        record for record in RISK_RECORDS if record.risk_level == "CRITICAL"
    ]
    high = [record for record in RISK_RECORDS if record.risk_level == "HIGH"]

    return [
        {
            "id": "ALERT-001",
            "severity": "CRITICAL",
            "title": "Critical flood exposure",
            "message": f"{len(critical)} asset(s) require priority inspection.",
        },
        {
            "id": "ALERT-002",
            "severity": "HIGH",
            "title": "Heavy rainfall detected",
            "message": f"{len(high)} high-risk asset(s) are under elevated rainfall exposure.",
        },
        {
            "id": "ALERT-003",
            "severity": "INFO",
            "title": "Inspection queue updated",
            "message": "Priority rankings were recalculated from the current scenario.",
        },
    ]


@app.get("/api/summary")
def summary():
    return {
        "total_assets": len(RISK_RECORDS),
        "critical": sum(record.risk_level == "CRITICAL" for record in RISK_RECORDS),
        "high": sum(record.risk_level == "HIGH" for record in RISK_RECORDS),
        "moderate": sum(record.risk_level == "MODERATE" for record in RISK_RECORDS),
        "low": sum(record.risk_level == "LOW" for record in RISK_RECORDS),
        "open_alerts": 3,
    }


@app.post("/api/assessment")
def assessment(
    rainfall_24h_mm: float,
    elevation_m: float,
    water_distance_km: float,
    exposure: float,
):
    return calculate_demo_risk(
        rainfall_24h_mm=rainfall_24h_mm,
        elevation_m=elevation_m,
        water_distance_km=water_distance_km,
        exposure=exposure,
    )
