from app.services.risk import calculate_demo_risk


def test_high_risk_demo_record():
    result = calculate_demo_risk(
        rainfall_24h_mm=182,
        elevation_m=12,
        water_distance_km=0.35,
        exposure=0.92,
    )

    assert result["risk_level"] == "CRITICAL"
    assert 0 <= result["risk_score"] <= 1
    assert 0 <= result["priority_score"] <= 1


def test_low_risk_demo_record():
    result = calculate_demo_risk(
        rainfall_24h_mm=41,
        elevation_m=64,
        water_distance_km=3.10,
        exposure=0.28,
    )

    assert result["risk_level"] == "LOW"
