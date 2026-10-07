from fastapi import FastAPI

app = FastAPI(
    title="Intelligent Disaster Risk Management API",
    version="0.1.0",
    description="Backend API for disaster risk assessment and emergency response support.",
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "disaster-risk-management-api",
        "version": "0.1.0",
    }
