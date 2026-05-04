"""Simulate sensor readings from a wearable device.

Three modes:
- "normal" — typical resting vitals, clean air
- "elevated" — mild abnormalities, possible early warning
- "attack" — clear signs of an asthma episode
"""

import random
from datetime import datetime
from typing import Any

ALL_TRIGGERS = [
    "dust",
    "smoke",
    "cold air",
    "pollen",
    "exercise",
    "pets",
    "stress",
    "strong odors",
]


def _round(value: float, ndigits: int = 0) -> float:
    return round(value, ndigits)


def simulate_reading(mode: str = "normal", age: int = 25) -> dict[str, Any]:
    """Generate a synthetic reading. mode: normal | elevated | attack."""

    if mode == "attack":
        hr = random.randint(115, 145)
        br = random.randint(28, 36)
        spo2 = round(random.uniform(86.0, 91.5), 1)
        aqi = random.randint(140, 230)
        triggers = random.sample(
            ["dust", "smoke", "cold air", "pets"], k=random.randint(1, 3)
        )
        physical_stress = random.random() < 0.6
    elif mode == "elevated":
        hr = random.randint(90, 115)
        br = random.randint(20, 26)
        spo2 = round(random.uniform(92.0, 95.0), 1)
        aqi = random.randint(80, 140)
        triggers = random.sample(ALL_TRIGGERS, k=random.randint(0, 2))
        physical_stress = random.random() < 0.4
    else:
        hr = random.randint(62, 88)
        br = random.randint(13, 18)
        spo2 = round(random.uniform(96.5, 99.0), 1)
        aqi = random.randint(15, 70)
        triggers = []
        physical_stress = False

    if age < 12:
        hr += random.randint(8, 18)
        br += random.randint(2, 5)

    return {
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "heart_rate": int(hr),
        "breathing_rate": int(br),
        "spo2": float(spo2),
        "aqi": int(aqi),
        "active_triggers": triggers,
        "physical_stress": bool(physical_stress),
    }
