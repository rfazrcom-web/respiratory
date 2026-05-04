"""Rule-based asthma risk analyzer.

Returns a status (Normal / Risk / Danger), a risk score (0-100), and a list
of human-readable reasons explaining the score.

This is a health monitoring SUPPORT tool, not a medical diagnostic device.
"""

from typing import Any


def _age_adjusted_resp_rate(age: int) -> tuple[int, int]:
    """Approximate normal resting breathing rate range (breaths/min)."""
    if age < 6:
        return (20, 30)
    if age < 12:
        return (18, 25)
    if age < 18:
        return (12, 20)
    return (12, 20)


def _age_adjusted_heart_rate(age: int) -> tuple[int, int]:
    """Approximate normal resting heart rate range (bpm)."""
    if age < 6:
        return (75, 130)
    if age < 12:
        return (70, 120)
    if age < 18:
        return (60, 110)
    return (60, 100)


SEVERITY_WEIGHT = {"mild": 1.0, "moderate": 1.2, "severe": 1.5}


def analyze_reading(
    reading: dict[str, Any],
    patient: dict[str, Any] | None,
) -> dict[str, Any]:
    """Score a sensor reading and produce a status with reasons."""

    age = patient["age"] if patient else 25
    severity = patient.get("severity", "moderate") if patient else "moderate"
    known_triggers = set(patient.get("triggers", [])) if patient else set()
    weight = SEVERITY_WEIGHT.get(severity, 1.0)

    score = 0.0
    reasons: list[str] = []

    spo2 = reading["spo2"]
    if spo2 < 90:
        score += 45
        reasons.append(f"Critical oxygen saturation ({spo2:.0f}%)")
    elif spo2 < 92:
        score += 30
        reasons.append(f"Low oxygen saturation ({spo2:.0f}%)")
    elif spo2 < 95:
        score += 15
        reasons.append(f"Slightly low oxygen ({spo2:.0f}%)")

    br_low, br_high = _age_adjusted_resp_rate(age)
    br = reading["breathing_rate"]
    if br > br_high + 10:
        score += 30
        reasons.append(f"Very high breathing rate ({br}/min)")
    elif br > br_high + 4:
        score += 18
        reasons.append(f"Elevated breathing rate ({br}/min)")
    elif br < br_low - 4:
        score += 10
        reasons.append(f"Unusually low breathing rate ({br}/min)")

    hr_low, hr_high = _age_adjusted_heart_rate(age)
    hr = reading["heart_rate"]
    if hr > hr_high + 25:
        score += 18
        reasons.append(f"Very high heart rate ({hr} bpm)")
    elif hr > hr_high + 10:
        score += 10
        reasons.append(f"Elevated heart rate ({hr} bpm)")

    aqi = reading["aqi"]
    if aqi >= 200:
        score += 18
        reasons.append(f"Very unhealthy air quality (AQI {aqi})")
    elif aqi >= 150:
        score += 12
        reasons.append(f"Unhealthy air quality (AQI {aqi})")
    elif aqi >= 100:
        score += 6
        reasons.append(f"Moderate air quality (AQI {aqi})")

    active_triggers = set(reading.get("active_triggers", []))
    matched = active_triggers & known_triggers
    if matched:
        score += 6 * len(matched)
        reasons.append(
            "Exposure to known trigger(s): " + ", ".join(sorted(matched))
        )

    if reading.get("physical_stress"):
        score += 6
        reasons.append("Currently under physical exertion")

        if matched:
            score += 8
            reasons.append("Combined trigger exposure + exertion")

    score *= weight
    score = max(0, min(100, round(score)))

    if score >= 55:
        status = "Danger"
    elif score >= 25:
        status = "Risk"
    else:
        status = "Normal"
        if not reasons:
            reasons.append("All vitals within typical ranges")

    return {"status": status, "risk_score": int(score), "reasons": reasons}


SUGGESTED_ACTIONS = {
    "Danger": [
        "Use your rescue inhaler now (e.g., albuterol) as prescribed",
        "Sit upright and focus on slow, controlled breathing",
        "Move to clean, fresh air immediately",
        "Call emergency services if symptoms do not improve in 10–15 minutes",
        "Notify a family member or caregiver",
    ],
    "Risk": [
        "Pause activity and sit down to rest",
        "Have your inhaler within reach",
        "Practice slow pursed-lip breathing",
        "Move away from triggers (smoke, dust, pets, cold air)",
        "Re-check your readings in a few minutes",
    ],
    "Normal": [
        "Vitals look good — keep going",
        "Stay hydrated and avoid known triggers",
        "Continue any prescribed daily controller medication",
    ],
}
