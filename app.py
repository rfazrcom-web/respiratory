"""Smart Asthma Monitoring System.

A health-monitoring SUPPORT system (not a medical diagnostic tool) that
collects patient profile + simulated wearable data and warns the user when
risk of an asthma attack is detected.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import database as db
from lib.monitor import SUGGESTED_ACTIONS, analyze_reading
from lib.simulator import ALL_TRIGGERS, simulate_reading

st.set_page_config(
    page_title="Smart Asthma Monitor",
    page_icon="🫁",
    layout="wide",
)

db.init_db()


SEVERITIES = ["mild", "moderate", "severe"]
GENDERS = ["Female", "Male", "Other / Prefer not to say"]


def _status_color(status: str) -> str:
    return {"Normal": "#16a34a", "Risk": "#f59e0b", "Danger": "#dc2626"}.get(
        status, "#475569"
    )


def _status_emoji(status: str) -> str:
    return {"Normal": "🟢", "Risk": "🟡", "Danger": "🔴"}.get(status, "⚪")


def _format_ts(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%b %d, %Y · %H:%M:%S UTC")
    except ValueError:
        return ts


def page_dashboard(patient: dict | None) -> None:
    st.title("🫁 Smart Asthma Monitor")
    st.caption(
        "A health-monitoring support tool — provides early warnings, "
        "not a medical diagnosis."
    )

    if patient is None:
        st.warning(
            "No patient profile yet. Open **Patient Profile** in the sidebar "
            "to get started."
        )
        return

    readings = db.load_readings(limit=1)
    latest = readings[0] if readings else None

    col_status, col_profile = st.columns([2, 1])

    with col_status:
        st.subheader("Current status")
        if latest is None:
            st.info(
                "No readings yet. Open **Live Monitor** to capture a reading "
                "from your wearable (or simulate one)."
            )
        else:
            status = latest["status"]
            score = latest["risk_score"]
            color = _status_color(status)
            st.markdown(
                f"<div style='padding:18px;border-radius:14px;"
                f"background:{color}22;border:1px solid {color}55;'>"
                f"<div style='font-size:36px;font-weight:700;color:{color};'>"
                f"{_status_emoji(status)} {status}</div>"
                f"<div style='color:#475569;margin-top:4px;'>"
                f"Risk score: <b>{score}/100</b> · "
                f"Updated {_format_ts(latest['ts'])}</div></div>",
                unsafe_allow_html=True,
            )

            if status == "Danger":
                st.error("⚠️ Warning: Possible asthma attack detected")
            elif status == "Risk":
                st.warning("Conditions suggest elevated risk — take precautions.")

            st.markdown("**Why:**")
            for reason in latest["reasons"]:
                st.markdown(f"- {reason}")

            st.markdown("**Suggested actions:**")
            for action in SUGGESTED_ACTIONS.get(status, []):
                st.markdown(f"- {action}")

            st.markdown("#### Latest sensor readings")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Heart rate", f"{latest['heart_rate']} bpm")
            m2.metric("Breathing rate", f"{latest['breathing_rate']} /min")
            m3.metric("SpO₂", f"{latest['spo2']:.1f} %")
            m4.metric("Air quality (AQI)", f"{latest['aqi']}")

            extras = []
            if latest["active_triggers"]:
                extras.append(
                    "Triggers detected: " + ", ".join(latest["active_triggers"])
                )
            if latest["physical_stress"]:
                extras.append("Physical exertion: yes")
            if extras:
                st.caption(" · ".join(extras))

    with col_profile:
        st.subheader("Patient profile")
        st.markdown(f"**Name:** {patient['name']}")
        st.markdown(f"**Age:** {patient['age']}")
        st.markdown(f"**Gender:** {patient['gender']}")
        st.markdown(
            f"**Asthma duration:** {patient['duration_years']:g} years"
        )
        st.markdown(f"**Severity:** {patient['severity'].title()}")
        meds = patient["medications"] or "—"
        st.markdown(f"**Medications:** {meds}")
        triggers = ", ".join(patient["triggers"]) if patient["triggers"] else "—"
        st.markdown(f"**Known triggers:** {triggers}")

    history = db.load_readings(limit=50)
    if len(history) >= 2:
        st.markdown("---")
        st.subheader("Recent trend")
        df = pd.DataFrame(history).iloc[::-1]
        df["ts"] = pd.to_datetime(df["ts"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["ts"], y=df["spo2"], mode="lines+markers",
                name="SpO₂ (%)", line=dict(color="#2563eb"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["ts"], y=df["breathing_rate"], mode="lines+markers",
                name="Breathing /min", line=dict(color="#dc2626"), yaxis="y2",
            )
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="SpO₂ (%)", range=[80, 100]),
            yaxis2=dict(title="Breathing /min", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig, use_container_width=True)


def page_profile(patient: dict | None) -> None:
    st.title("Patient profile")
    st.caption(
        "We use this to personalize the risk analysis. "
        "Stored locally on this device only."
    )

    defaults = patient or {
        "name": "",
        "age": 25,
        "gender": GENDERS[0],
        "duration_years": 1.0,
        "medications": "",
        "triggers": [],
        "severity": "moderate",
    }

    with st.form("profile_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name", value=defaults["name"])
            age = st.number_input(
                "Age", min_value=1, max_value=120, value=int(defaults["age"])
            )
            gender_idx = (
                GENDERS.index(defaults["gender"])
                if defaults["gender"] in GENDERS else 0
            )
            gender = st.selectbox("Gender", GENDERS, index=gender_idx)
            duration = st.number_input(
                "Asthma duration (years since diagnosis)",
                min_value=0.0, max_value=100.0,
                value=float(defaults["duration_years"]), step=0.5,
            )
        with c2:
            medications = st.text_area(
                "Current medications",
                value=defaults["medications"],
                placeholder="e.g. Albuterol inhaler (rescue), "
                "Fluticasone (daily controller)",
                height=100,
            )
            triggers = st.multiselect(
                "Known asthma triggers",
                options=ALL_TRIGGERS,
                default=defaults["triggers"],
            )
            sev_idx = (
                SEVERITIES.index(defaults["severity"])
                if defaults["severity"] in SEVERITIES else 1
            )
            severity = st.radio(
                "Severity level", SEVERITIES, index=sev_idx, horizontal=True
            )

        submitted = st.form_submit_button("Save profile", type="primary")

        if submitted:
            if not name.strip():
                st.error("Please enter a name.")
            else:
                db.save_patient(
                    {
                        "name": name.strip(),
                        "age": int(age),
                        "gender": gender,
                        "duration_years": float(duration),
                        "medications": medications.strip(),
                        "triggers": triggers,
                        "severity": severity,
                    }
                )
                st.success("Profile saved.")
                st.rerun()


def page_monitor(patient: dict | None) -> None:
    st.title("Live monitor")
    st.caption(
        "Connect a wearable, enter a manual reading, or simulate one to check "
        "current risk."
    )

    if patient is None:
        st.warning("Set up the patient profile first.")
        return

    sim_col, _ = st.columns([2, 1])
    with sim_col:
        st.subheader("Simulate a reading from a wearable")
        s1, s2, s3, s4 = st.columns(4)
        if s1.button("🟢 Normal sample", use_container_width=True):
            _capture(simulate_reading("normal", patient["age"]), patient)
        if s2.button("🟡 Elevated sample", use_container_width=True):
            _capture(simulate_reading("elevated", patient["age"]), patient)
        if s3.button("🔴 Attack sample", use_container_width=True):
            _capture(simulate_reading("attack", patient["age"]), patient)
        if s4.button("🎲 Random sample", use_container_width=True):
            import random
            mode = random.choices(
                ["normal", "elevated", "attack"], weights=[6, 3, 1]
            )[0]
            _capture(simulate_reading(mode, patient["age"]), patient)

    st.markdown("---")
    st.subheader("Or enter a reading manually")

    with st.form("manual_reading", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        hr = c1.number_input("Heart rate (bpm)", 30, 220, 78)
        br = c2.number_input("Breathing rate (/min)", 5, 60, 16)
        spo2 = c3.number_input("SpO₂ (%)", 70.0, 100.0, 97.5, step=0.5)
        aqi = c4.number_input("Air quality index", 0, 500, 50)

        c5, c6 = st.columns([2, 1])
        active = c5.multiselect(
            "Triggers in environment right now",
            ALL_TRIGGERS,
            default=[],
        )
        stress = c6.checkbox("Currently exerting (exercise, climbing stairs…)")

        if st.form_submit_button("Analyze reading", type="primary"):
            reading = {
                "ts": datetime.utcnow().isoformat(timespec="seconds"),
                "heart_rate": int(hr),
                "breathing_rate": int(br),
                "spo2": float(spo2),
                "aqi": int(aqi),
                "active_triggers": active,
                "physical_stress": bool(stress),
            }
            _capture(reading, patient)

    latest = db.load_readings(limit=1)
    if latest:
        st.markdown("---")
        _show_result(latest[0])


def _capture(reading: dict, patient: dict) -> None:
    result = analyze_reading(reading, patient)
    enriched = {**reading, **result}
    db.save_reading(enriched)
    if result["status"] in ("Risk", "Danger"):
        db.save_alert(enriched)
    st.session_state["_just_captured"] = enriched
    st.rerun()


def _show_result(reading: dict) -> None:
    status = reading["status"]
    color = _status_color(status)

    st.markdown(
        f"<div style='padding:14px;border-radius:12px;"
        f"background:{color}22;border:1px solid {color}55;'>"
        f"<b style='color:{color};font-size:20px;'>"
        f"{_status_emoji(status)} {status}</b> · "
        f"Risk score {reading['risk_score']}/100"
        f"</div>",
        unsafe_allow_html=True,
    )

    if status == "Danger":
        st.error("⚠️ Warning: Possible asthma attack detected")

    a, b, c, d = st.columns(4)
    a.metric("Heart rate", f"{reading['heart_rate']} bpm")
    b.metric("Breathing rate", f"{reading['breathing_rate']} /min")
    c.metric("SpO₂", f"{reading['spo2']:.1f} %")
    d.metric("AQI", f"{reading['aqi']}")

    st.markdown("**Reasons:**")
    for r in reading["reasons"]:
        st.markdown(f"- {r}")

    st.markdown("**Suggested actions:**")
    for action in SUGGESTED_ACTIONS.get(status, []):
        st.markdown(f"- {action}")


def page_history(patient: dict | None) -> None:
    st.title("History")
    st.caption("All saved readings and alerts for this device.")

    readings = db.load_readings(limit=500)
    alerts = db.load_alerts(limit=200)

    tab_r, tab_a = st.tabs(
        [f"Readings ({len(readings)})", f"Alerts ({len(alerts)})"]
    )

    with tab_r:
        if not readings:
            st.info("No readings yet.")
        else:
            df = pd.DataFrame(readings)
            df["active_triggers"] = df["active_triggers"].apply(
                lambda x: ", ".join(x) if x else "—"
            )
            df["reasons"] = df["reasons"].apply(lambda x: " · ".join(x))
            df = df[
                [
                    "ts", "status", "risk_score", "heart_rate",
                    "breathing_rate", "spo2", "aqi", "active_triggers",
                    "physical_stress", "reasons",
                ]
            ].rename(
                columns={
                    "ts": "Time (UTC)",
                    "status": "Status",
                    "risk_score": "Score",
                    "heart_rate": "HR",
                    "breathing_rate": "BR",
                    "spo2": "SpO₂",
                    "aqi": "AQI",
                    "active_triggers": "Triggers",
                    "physical_stress": "Exerting",
                    "reasons": "Reasons",
                }
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_a:
        if not alerts:
            st.info("No alerts logged. Good news.")
        else:
            for a in alerts:
                color = _status_color(a["status"])
                st.markdown(
                    f"<div style='padding:10px;border-radius:10px;"
                    f"margin-bottom:8px;background:{color}1a;"
                    f"border-left:4px solid {color};'>"
                    f"<b style='color:{color}'>"
                    f"{_status_emoji(a['status'])} {a['status']}</b> · "
                    f"{_format_ts(a['ts'])} · score {a['risk_score']}<br/>"
                    f"<span style='color:#475569;font-size:14px;'>"
                    f"{' · '.join(a['reasons'])}</span></div>",
                    unsafe_allow_html=True,
                )

    if readings or alerts:
        st.markdown("---")
        if st.button("Clear all history", type="secondary"):
            db.clear_history()
            st.success("History cleared.")
            st.rerun()


def main() -> None:
    patient = db.load_patient()

    with st.sidebar:
        st.markdown("## 🫁 Asthma Monitor")
        page = st.radio(
            "Navigation",
            ["Dashboard", "Patient Profile", "Live Monitor", "History"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if patient:
            latest = db.load_readings(limit=1)
            if latest:
                status = latest[0]["status"]
                st.markdown(
                    f"**Status:** {_status_emoji(status)} {status}"
                )
            st.caption(f"Patient: {patient['name']}")
        else:
            st.caption("No profile set up yet.")
        st.markdown("---")
        st.caption(
            "ℹ️ Health-monitoring support tool — for early warnings only. "
            "Not a substitute for professional medical advice or emergency care."
        )

    if page == "Dashboard":
        page_dashboard(patient)
    elif page == "Patient Profile":
        page_profile(patient)
    elif page == "Live Monitor":
        page_monitor(patient)
    else:
        page_history(patient)


if __name__ == "__main__":
    main()
