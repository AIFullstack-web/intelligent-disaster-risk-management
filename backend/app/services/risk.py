from .__init__ import *  # noqa: F401,F403

def calculate_demo_risk(
    rainfall_24h_mm: float,
    elevation_m: float,
    water_distance_km: float,
    exposure: float,
) -> dict[str, float | str]:
    """Deterministic demo engine used until the trained ML model is integrated."""
    rainfall_component = min(rainfall_24h_mm / 200.0, 1.0)
    elevation_component = 1.0 - min(max(elevation_m, 0.0) / 100.0, 1.0)
    water_component = 1.0 - min(max(water_distance_km, 0.0) / 5.0, 1.0)

    score = max(
        0.0,
        min(
            1.0,
            (
                0.40 * rainfall_component
                + 0.20 * elevation_component
                + 0.20 * water_component
                + 0.20 * exposure
            ),
        ),
    )

    if score >= 0.85:
        level = "CRITICAL"
    elif score >= 0.65:
        level = "HIGH"
    elif score >= 0.35:
        level = "MODERATE"
    else:
        level = "LOW"

    priority = min(1.0, 0.85 * score + 0.15 * exposure)

    return {
        "risk_score": round(score, 3),
        "risk_level": level,
        "priority_score": round(priority, 3),
    }
