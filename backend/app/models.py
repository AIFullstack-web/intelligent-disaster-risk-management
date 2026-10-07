from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


class RiskRecord(BaseModel):
    id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    risk_score: float = Field(ge=0, le=1)
    risk_level: RiskLevel
    priority_score: float = Field(ge=0, le=1)
    rainfall_24h_mm: float = Field(ge=0)
    elevation_m: float
    water_distance_km: float = Field(ge=0)
    exposure: float = Field(ge=0, le=1)
    recommended_action: str
