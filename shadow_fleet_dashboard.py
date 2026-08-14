# shadow_fleet_dashboard.py
# ─────────────────────────────────────────────────────────────────────────────
# SHADOW — Stealthy Hub for Advanced Detection & Operational Watch
# HCSS Dashboard Concept — Visual prototype
# Run: streamlit run shadow_fleet_dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import random
import time
import os
from datetime import datetime, timedelta

# ── MAPBOX TOKEN CONFIGURATION ────────────────────────────────────────────────
# Set Mapbox token from Streamlit secrets or environment variable
try:
    mapbox_token = st.secrets.get("MAPBOX_TOKEN", os.getenv("MAPBOX_TOKEN", ""))
    if mapbox_token:
        os.environ["MAPBOX_API_KEY"] = mapbox_token
except:
    pass

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SHADOW Dashboard — HCSS Concept",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── GLOBAL STYLE ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0a0f1e; color: #e0e6f0; }
  section[data-testid="stSidebar"] { background-color: #0d1526; }

  div[data-testid="metric-container"] {
    background: linear-gradient(135deg,#0d2040,#0a3060);
    border: 1px solid #1e5080;
    border-radius: 10px;
    padding: 14px 18px;
  }
  div[data-testid="metric-container"] label { color: #6ab0f5 !important; font-size:0.78rem; }
  div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #ffffff; font-size:1.8rem; font-weight:700;
  }

  .section-header {
    background: linear-gradient(90deg,#0d3060,#0a1830);
    border-left: 4px solid #2a9df4;
    border-radius: 6px;
    padding: 8px 16px;
    margin: 18px 0 10px 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: #7ecfff;
    letter-spacing: 0.05em;
  }

  .db-badge {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:0.72rem; font-weight:700; margin:2px 3px; letter-spacing:0.04em;
  }
  .db-ais   { background:#0a3a6a; color:#5bb8ff; border:1px solid #1a6aaa; }
  .db-sat   { background:#2a1a4a; color:#b98aff; border:1px solid #6a3aaa; }
  .db-sanc  { background:#3a1a0a; color:#ff9955; border:1px solid #aa5a1a; }
  .db-insur { background:#0a3a1a; color:#55dd88; border:1px solid #1aaa4a; }

  .alert-box {
    background:#1a0a0a; border:1px solid #cc2222;
    border-radius:8px; padding:10px 16px; margin:6px 0;
    font-size:0.83rem; color:#ff9999;
  }
  .alert-box span { color:#ff4444; font-weight:700; }
  h1,h2,h3 { color:#7ecfff !important; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
SANCTIONED_FLAGS = ["IR","RU","KP","SY","VE","CU","MM"]
ALL_FLAGS = SANCTIONED_FLAGS + ["PA","LR","MH","SG","BS","CY","GR","MT","GB","NO","CN","AE"]
VESSEL_TYPES = ["Crude Tanker","Product Tanker","LNG Carrier","Bulk Carrier","Container","VLCC","Aframax","Suezmax"]
RISK_LEVELS  = ["CRITICAL","HIGH","MEDIUM","LOW"]
RISK_WEIGHTS = [0.10, 0.25, 0.35, 0.30]

HOTSPOTS = [
    ("Persian Gulf",      26.5,  54.0, 3.0),
    ("Strait of Hormuz",  26.0,  57.0, 1.5),
    ("Black Sea",         43.0,  33.0, 3.5),
    ("Suez Corridor",     30.0,  33.0, 2.0),
    ("Baltic Sea",        57.0,  20.0, 3.0),
    ("SE Asia Straits",    1.5, 104.0, 2.5),
    ("Arabian Sea",       18.0,  63.0, 4.0),
    ("Mediterranean",     35.0,  20.0, 5.0),
    ("North Sea",         56.0,   3.0, 3.5),
    ("Caspian Sea",       41.5,  51.5, 2.0),
    ("Red Sea",           20.0,  38.5, 3.0),
    ("Gulf of Guinea",     3.0,   3.0, 3.5),
]

# ── DATA GENERATORS ───────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def generate_vessels(n=120, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        hs       = HOTSPOTS[i % len(HOTSPOTS)]
        lat      = float(rng.normal(hs[1], hs[3] * 0.5))
        lon      = float(rng.normal(hs[2], hs[3] * 0.5))
        flag     = rng.choice(ALL_FLAGS)
        risk     = rng.choice(RISK_LEVELS, p=RISK_WEIGHTS)
        ais_dark = bool(rng.random() < (0.85 if flag in SANCTIONED_FLAGS else 0.25))
        spoofed  = bool(rng.random() < (0.70 if flag in SANCTIONED_FLAGS else 0.15))
        sts      = bool(rng.random() < 0.35)
        rows.append({
            "vessel_id":    f"V-{10000+i}",
            "mmsi":         f"4{rng.integers(10000000,99999999)}",
            "imo":          f"IMO{rng.integers(1000000,9999999)}",
            "vessel_name":  f"{rng.choice(['GHOST','PHANTOM','SHADOW','DARK','SILENT','ROGUE'])} "
                            f"{rng.choice(['MARINER','VOYAGER','TRADER','CARRIER','SPIRIT','RUNNER'])} "
                            f"{rng.integers(1,99)}",
            "type":         rng.choice(VESSEL_TYPES),
            "flag":         flag,
            "lat":          round(lat, 5),
            "lon":          round(lon, 5),
            "risk":         risk,
            "ais_dark":     ais_dark,
            "spoofed":      spoofed,
            "sts_detected": sts,
            "speed_kn":     round(float(rng.uniform(0.2, 15.5)), 1),
            "heading":      round(float(rng.uniform(0, 360)), 1),
            "last_port":    rng.choice(["Bandar Abbas","Novorossiysk","Vladivostok","Latakia",
                                        "Kharg Island","Singapore","Dubai","Fujairah",
                                        "Rotterdam","Shanghai","Odessa"]),
            "region":       hs[0],
            "db_ais":       bool(rng.random() < 0.75),
            "db_satellite": bool(rng.random() < 0.85),
            "db_sanctions": bool(flag in SANCTIONED_FLAGS and rng.random() < 0.65),
            "db_insurance": bool(rng.random() < 0.45),
            "cargo_est_kbd":round(float(rng.uniform(100, 2000)), 0) if flag in SANCTIONED_FLAGS else 0,
            "last_seen":    datetime.utcnow() - timedelta(minutes=int(rng.integers(1,240))),
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=30)
def generate_satellite_pings(vessels_df, seed=0):
    rng   = np.random.default_rng(seed + 2)
    pings = vessels_df.sample(frac=0.7, random_state=seed).copy()
    pings["sat_confidence"] = [round(float(rng.uniform(0.55, 0.99)), 2) for _ in range(len(pings))]
    pings["image_source"]   = rng.choice(["Sentinel-1 SAR","Planet Labs","Maxar","Capella Space",
                                           "ICEYE SAR","Airbus DS"], size=len(pings))
    pings["ais_match"]      = [bool(rng.random() < 0.5) for _ in range(len(pings))]
    pings["sat_lat"]        = pings["lat"] + rng.normal(0, 0.05, len(pings))
    pings["sat_lon"]        = pings["lon"] + rng.normal(0, 0.05, len(pings))
    return pings

@st.cache_data(ttl=30)
def generate_sts_events(vessels_df, seed=0):
    rng = np.random.default_rng(seed + 1)
    sts = vessels_df[vessels_df["sts_detected"]].copy()
    sts["pair_vessel"]      = [f"V-{rng.integers(10000,19999)}" for _ in range(len(sts))]
    sts["transfer_vol_kbd"] = [round(float(rng.uniform(50,500)),0) for _ in range(len(sts))]
    sts["duration_hrs"]     = [round(float(rng.uniform(2,18)),1) for _ in range(len(sts))]
    return sts[["vessel_id","vessel_name","region","lat","lon",
                "pair_vessel","transfer_vol_kbd","duration_hrs","risk"]]

@st.cache_data(ttl=30)
def generate_sanctions_data(seed=0):
    rng      = np.random.default_rng(seed + 3)
    entities = ["PJSC Sovcomflot","NIOC Shipping","Feodosia Tankers","Korea Songi","PDVSA Marine",
                "Iran LNG Co","Black Sea Tankers","Sytrans LLC","Kimura Bulk","Palmali Group"]
    return pd.DataFrame([{
        "entity":         e,
        "listed_by":      rng.choice(["OFAC","EU","UKFCO","UN","OFSI"]),
        "sanction_date":  str(datetime(2020,1,1) + timedelta(days=int(rng.integers(0,1500)))),
        "vessels_linked": int(rng.integers(2, 22)),
        "status":         rng.choice(["ACTIVE","REVIEW","DELISTED"]),
    } for e in entities])

@st.cache_data(ttl=30)
def generate_alerts(vessels_df, seed=0):
    rng       = np.random.default_rng(seed + 4)
    critical  = vessels_df[vessels_df["risk"]=="CRITICAL"].head(8)
    templates = [
        "AIS signal lost - dark vessel detected via SAR imagery",
        "GPS spoofing signature confirmed - position offset greater than 12nm",
        "Ship-to-ship transfer in progress at declared anchorage",
        "Vessel entered sanctioned port without IMO notification",
        "Cargo manifest mismatch - declared ballast, satellite shows laden",
        "Flag-of-convenience change within 72h of port departure",
        "AIS transponder toggled 3 times in 6h - evasion pattern detected",
        "Vessel linked to OFAC-listed entity via ownership chain",
    ]
    return [{
        "time":   (datetime.utcnow() - timedelta(minutes=int(rng.integers(1,120)))).strftime("%H:%M UTC"),
        "vessel": row["vessel_name"],
        "region": row["region"],
        "alert":  rng.choice(templates),
    } for _, row in critical.iterrows()]

# ── HELPERS ───────────────────────────────────────────────────────────────────
RISK_COLOR = {
    "CRITICAL": [255, 40,  40,  220],
    "HIGH":     [255, 140,  0,  200],
    "MEDIUM":   [255, 210,  0,  180],
    "LOW":      [60,  220, 100, 140],
}
RISK_HEX   = {"CRITICAL":"#ff2828","HIGH":"#ff8c00","MEDIUM":"#ffd200","LOW":"#3cdc64"}
RISK_EMOJI = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}

def db_badges(row):
    out = ""
    if row["db_ais"]:       out += '<span class="db-badge db-ais">AIS</span>'
    if row["db_satellite"]: out += '<span class="db-badge db-sat">SAT</span>'
    if row["db_sanctions"]: out += '<span class="db-badge db-sanc">SANC</span>'
    if row["db_insurance"]: out += '<span class="db-badge db-insur">INS</span>'
    return out

PORT_COORDS = {
    "Bandar Abbas": (27.18, 56.27), "Novorossiysk": (44.72, 37.77),
    "Vladivostok":  (43.11,131.87), "Latakia":      (35.52, 35.77),
    "Kharg Island": (29.24, 50.33), "Singapore":    (1.29,  103.85),
    "Dubai":        (25.20, 55.27), "Fujairah":     (25.12, 56.34),
    "Rotterdam":    (51.92,  4.48), "Shanghai":     (31.23, 121.47),
    "Odessa":       (46.48, 30.73),
}

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚢 SHADOW")
    st.markdown(
        "<span style='font-size:0.72rem;color:#3a7aaa;'>"
        "Stealthy Hub for Advanced Detection and Operational Watch"
        "</span>",
        unsafe_allow_html=True
    )
    st.markdown("**v0.9 — HCSS Concept Build**")
    st.markdown("---")

    st.markdown("### Map Layers")
    show_vessels   = st.toggle("Vessel Positions",     value=True)
    show_sts       = st.toggle("STS Transfer Events",  value=True)
    show_sat_pings = st.toggle("Satellite Detections", value=True)
    show_heat      = st.toggle("Risk Heatmap",         value=False)
    show_arcs      = st.toggle("Last-Port Arc Lines",  value=False)

    st.markdown("### Filters")
    risk_filter = st.multiselect("Risk Level",
        ["CRITICAL","HIGH","MEDIUM","LOW"],
        default=["CRITICAL","HIGH","MEDIUM","LOW"])
    flag_filter = st.multiselect("Flag State", ALL_FLAGS, default=ALL_FLAGS)
    db_filter   = st.multiselect("Must Appear In DB",
        ["AIS","Satellite","Sanctions","Insurance"], default=[])
    ais_dark_only = st.checkbox("AIS-Dark Vessels Only", False)
    spoofed_only  = st.checkbox("GPS-Spoofed Only",      False)
    sts_only      = st.checkbox("STS Events Only",       False)

    st.markdown("### Map Style")
    map_style = st.selectbox("Basemap", ["dark","satellite","road","light"])
    MAP_STYLES = {
        "dark":      "mapbox://styles/mapbox/dark-v10",
        "satellite": "mapbox://styles/mapbox/satellite-streets-v11",
        "road":      "mapbox://styles/mapbox/streets-v11",
        "light":     "mapbox://styles/mapbox/light-v10",
    }

    st.markdown("### Live Refresh")
    auto_refresh = st.checkbox("Auto-refresh every 30s", True)
    st.caption("Replace simulated data with live API endpoints.")

    st.markdown("---")
    st.markdown("**Databases Active:**")
    st.markdown("""
<span class="db-badge db-ais">AIS LIVE</span>
<span class="db-badge db-sat">SAT IMG</span>
<span class="db-badge db-sanc">SANCTIONS</span>
<span class="db-badge db-insur">INSURANCE</span>
""", unsafe_allow_html=True)

    if st.button("Force Refresh"):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOAD
# ══════════════════════════════════════════════════════════════════════════════
seed_val    = int(time.time()) // 30 if auto_refresh else 42
vessels_df  = generate_vessels(n=120, seed=seed_val)
sat_df      = generate_satellite_pings(vessels_df, seed=seed_val)
sts_df      = generate_sts_events(vessels_df, seed=seed_val)
sanction_df = generate_sanctions_data(seed=seed_val)
alerts      = generate_alerts(vessels_df, seed=seed_val)

# ── APPLY FILTERS ─────────────────────────────────────────────────────────────
filtered = vessels_df[
    vessels_df["risk"].isin(risk_filter) &
    vessels_df["flag"].isin(flag_filter)
].copy()

if ais_dark_only: filtered = filtered[filtered["ais_dark"]]
if spoofed_only:  filtered = filtered[filtered["spoofed"]]
if sts_only:      filtered = filtered[filtered["sts_detected"]]
if "AIS"       in db_filter: filtered = filtered[filtered["db_ais"]]
if "Satellite" in db_filter: filtered = filtered[filtered["db_satellite"]]
if "Sanctions" in db_filter: filtered = filtered[filtered["db_sanctions"]]
if "Insurance" in db_filter: filtered = filtered[filtered["db_insurance"]]

filtered["color"] = filtered["risk"].map(RISK_COLOR)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_logo, col_title, col_time = st.columns([1, 6, 2])
with col_logo:
    st.markdown("# 🚢")
with col_title:
    st.markdown(
        "<div style='margin-bottom:2px;'>"
        "<span style='font-size:0.78rem;font-weight:600;letter-spacing:0.18em;"
        "color:#2a9df4;text-transform:uppercase;'>HCSS Dashboard Concept</span>"
        "</div>"
        "<div style='font-size:2rem;font-weight:800;color:#7ecfff;"
        "letter-spacing:0.06em;line-height:1.15;margin-bottom:2px;'>"
        "<span style='color:#ffffff;'>SHADOW</span>"
        "</div>"
        "<div style='font-size:0.88rem;color:#5a9fd4;font-style:italic;font-weight:500;"
        "letter-spacing:0.03em;'>"
        "Stealthy Hub for Advanced Detection and Operational Watch"
        "</div>"
        "<div style='margin-top:5px;font-size:0.75rem;color:#3a7aaa;'>"
        "AIS - Satellite Imagery - Sanctions Lists - Insurance Records"
        "</div>",
        unsafe_allow_html=True
    )
with col_time:
    st.markdown(
        f"<br>🕐 **{datetime.utcnow().strftime('%Y-%m-%d  %H:%M:%S UTC')}**",
        unsafe_allow_html=True
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# KPI METRICS
# ══════════════════════════════════════════════════════════════════════════════
k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
k1.metric("🚢 Tracked Vessels", len(filtered),                           f"+{random.randint(1,5)} 1h")
k2.metric("🔴 Critical Risk",   (filtered["risk"]=="CRITICAL").sum(),    f"+{random.randint(0,3)}")
k3.metric("🌑 AIS Dark",        filtered["ais_dark"].sum(),              f"+{random.randint(0,4)}")
k4.metric("📡 GPS Spoofed",     filtered["spoofed"].sum(),               f"+{random.randint(0,3)}")
k5.metric("⚓ STS Detected",    filtered["sts_detected"].sum(),          f"+{random.randint(0,2)}")
k6.metric("🚫 Sanctioned",      filtered["db_sanctions"].sum(),          "+-0")
k7.metric("🔗 Multi-DB Match",
    ((filtered["db_ais"].astype(int)+filtered["db_satellite"].astype(int)+
      filtered["db_sanctions"].astype(int)+filtered["db_insurance"].astype(int))>=3).sum(),
    f"+{random.randint(0,4)}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ALERT TICKER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">LIVE INTELLIGENCE ALERTS</div>', unsafe_allow_html=True)
for a in alerts[:5]:
    st.markdown(
        f'<div class="alert-box"><span>[{a["time"]}]</span> '
        f'<b>{a["vessel"]}</b> — {a["region"]} | {a["alert"]}</div>',
        unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">GLOBAL VESSEL INTELLIGENCE MAP</div>', unsafe_allow_html=True)

layers = []

if show_vessels and not filtered.empty:
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=filtered,
        get_position=["lon","lat"], get_color="color",
        get_radius=35000, radius_min_pixels=4, radius_max_pixels=18,
        pickable=True, opacity=0.85, stroked=True,
        line_width_min_pixels=1, get_line_color=[255,255,255,120],
    ))

if show_sat_pings and not sat_df.empty:
    sat_f = sat_df[sat_df["vessel_id"].isin(filtered["vessel_id"])]
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=sat_f,
        get_position=["sat_lon","sat_lat"], get_color=[180,100,255,160],
        get_radius=25000, radius_min_pixels=3, radius_max_pixels=10,
        pickable=True, opacity=0.7, stroked=True,
        line_width_min_pixels=1, get_line_color=[220,180,255,200],
    ))

if show_sts and not sts_df.empty:
    sts_f = sts_df[sts_df["vessel_id"].isin(filtered["vessel_id"])].copy()
    sts_f["target_lat"] = sts_f["lat"] + np.random.normal(0, 0.3, len(sts_f))
    sts_f["target_lon"] = sts_f["lon"] + np.random.normal(0, 0.3, len(sts_f))
    sts_f["sc"] = [[255,140,0,200]]*len(sts_f)
    sts_f["tc"] = [[255,60,60,200]]*len(sts_f)
    layers.append(pdk.Layer(
        "ArcLayer", data=sts_f,
        get_source_position=["lon","lat"],
        get_target_position=["target_lon","target_lat"],
        get_source_color="sc", get_target_color="tc",
        get_width=2, pickable=True, auto_highlight=True,
    ))
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=sts_f,
        get_position=["lon","lat"], get_color=[255,140,0,220],
        get_radius=60000, radius_min_pixels=6, radius_max_pixels=22,
        pickable=True, stroked=True, line_width_min_pixels=2,
        get_line_color=[255,200,0,255],
    ))

if show_heat and not filtered.empty:
    layers.append(pdk.Layer(
        "HeatmapLayer", data=filtered,
        get_position=["lon","lat"],
        get_weight=filtered["risk"].map({"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1}).tolist(),
        radiusPixels=60, intensity=1.2, threshold=0.05, opacity=0.6,
    ))

if show_arcs and not filtered.empty:
    arc_df = filtered.copy()
    arc_df["port_lat"] = arc_df["last_port"].map(lambda p: PORT_COORDS.get(p,(0,0))[0])
    arc_df["port_lon"] = arc_df["last_port"].map(lambda p: PORT_COORDS.get(p,(0,0))[1])
    layers.append(pdk.Layer(
        "ArcLayer", data=arc_df,
        get_source_position=["port_lon","port_lat"],
        get_target_position=["lon","lat"],
        get_source_color=[100,200,255,100], get_target_color="color",
        get_width=1, pickable=False, opacity=0.4,
    ))

tooltip = {
    "html": (
        "<div style='background:#0d1a2e;border:1px solid #2a9df4;border-radius:8px;"
        "padding:12px 16px;font-family:monospace;font-size:13px;color:#e0f0ff;min-width:240px;'>"
        "<b style='color:#7ecfff;font-size:15px;'>{vessel_name}</b><br/>"
        "<span style='color:#aaa;'>IMO:</span> {imo} "
        "<span style='color:#aaa;'>MMSI:</span> {mmsi}<br/>"
        "<span style='color:#aaa;'>Flag:</span> <b>{flag}</b> "
        "<span style='color:#aaa;'>Type:</span> {type}<br/>"
        "<span style='color:#aaa;'>Speed:</span> {speed_kn} kn "
        "<span style='color:#aaa;'>Hdg:</span> {heading} degrees<br/>"
        "<span style='color:#aaa;'>Region:</span> {region}<br/>"
        "<span style='color:#aaa;'>Last Port:</span> {last_port}<br/>"
        "<hr style='border-color:#1e5080;margin:6px 0;'>"
        "<span style='color:#aaa;'>AIS Dark:</span> <b>{ais_dark}</b> "
        "<span style='color:#aaa;'>Spoofed:</span> <b>{spoofed}</b><br/>"
        "<span style='color:#aaa;'>STS:</span> <b>{sts_detected}</b> "
        "<span style='color:#aaa;'>Sanctions:</span> <b>{db_sanctions}</b>"
        "</div>"
    ),
    "style": {"backgroundColor":"transparent","border":"none"}
}

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=pdk.ViewState(latitude=27.0, longitude=45.0, zoom=2.8, pitch=35),
    map_style=MAP_STYLES.get(map_style, MAP_STYLES["dark"]),
    tooltip=tooltip,
), use_container_width=True)

st.caption("Purple = Satellite Detection   Red = Critical   Orange = High or STS   Yellow = Medium   Green = Low")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Vessel Intel", "Satellite Log", "STS Events", "Sanctions DB", "Analytics"
])

# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">AIS + SATELLITE + SANCTIONS + INSURANCE CROSS-MATCH</div>',
                unsafe_allow_html=True)
    vsearch = st.text_input("Search Vessel / IMO / MMSI")
    disp    = filtered.copy()
    if vsearch:
        disp = disp[disp["vessel_name"].str.contains(vsearch, case=False) |
                    disp["imo"].str.contains(vsearch, case=False) |
                    disp["mmsi"].str.contains(vsearch, case=False)]
    disp["_r"] = disp["risk"].map({"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3})
    disp = disp.sort_values("_r")
    for _, row in disp.head(25).iterrows():
        with st.expander(
            f"{RISK_EMOJI[row['risk']]}  {row['vessel_name']}  "
            f"{row['flag']}  {row['type']}  {row['region']}"
        ):
            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(
                f"**IMO:** {row['imo']}\n\n"
                f"**MMSI:** {row['mmsi']}\n\n"
                f"**Flag:** {row['flag']}\n\n"
                f"**Type:** {row['type']}"
            )
            c2.markdown(
                f"**Speed:** {row['speed_kn']} kn\n\n"
                f"**Heading:** {row['heading']} degrees\n\n"
                f"**Last Port:** {row['last_port']}\n\n"
                f"**Region:** {row['region']}"
            )
            c3.markdown(
                f"**AIS Dark:** {'YES' if row['ais_dark'] else 'No'}\n\n"
                f"**GPS Spoofed:** {'YES' if row['spoofed'] else 'No'}\n\n"
                f"**STS Detected:** {'YES' if row['sts_detected'] else 'No'}\n\n"
                f"**Cargo Est.:** {int(row['cargo_est_kbd'])} kbd"
            )
            c4.markdown(f"**Last Seen:** {row['last_seen'].strftime('%H:%M UTC')}\n\n**Databases:**")
            c4.markdown(db_badges(row), unsafe_allow_html=True)

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">SATELLITE DETECTION LOG</div>', unsafe_allow_html=True)
    sat_show = sat_df[sat_df["vessel_id"].isin(filtered["vessel_id"])].copy()
    sat_show["AIS Match"]  = sat_show["ais_match"].map({True:"Matched", False:"Dark / No Match"})
    sat_show["Confidence"] = sat_show["sat_confidence"].apply(lambda x: f"{x:.0%}")
    st.dataframe(
        sat_show[["vessel_name","flag","type","region","image_source","Confidence","AIS Match","risk"]].rename(
            columns={"vessel_name":"Vessel","flag":"Flag","type":"Type",
                     "image_source":"Sat Source","risk":"Risk"}),
        use_container_width=True, height=480)

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">SHIP-TO-SHIP TRANSFER EVENTS</div>', unsafe_allow_html=True)
    sts_show = sts_df[sts_df["vessel_id"].isin(filtered["vessel_id"])].copy()
    if not sts_show.empty:
        sts_show["Vol (kbd)"]   = sts_show["transfer_vol_kbd"].astype(int)
        sts_show["Duration"]    = sts_show["duration_hrs"].apply(lambda x: f"{x}h")
        sts_show["Coordinates"] = sts_show.apply(
            lambda r: f"{r['lat']:.3f}, {r['lon']:.3f}", axis=1)
        st.dataframe(
            sts_show[["vessel_name","pair_vessel","region","Coordinates",
                      "Vol (kbd)","Duration","risk"]].rename(
                columns={"vessel_name":"Primary Vessel","pair_vessel":"Transfer Pair","risk":"Risk"}),
            use_container_width=True, height=420)
        st.info(
            f"{len(sts_show)} STS events detected. "
            f"Estimated total undocumented cargo: {int(sts_show['transfer_vol_kbd'].sum()):,} kbd"
        )
    else:
        st.info("No STS events match current filters.")

# ── TAB 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">SANCTIONS ENTITY DATABASE</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3,1])
    with c1:
        st.dataframe(sanction_df, use_container_width=True, height=380)
    with c2:
        st.metric("Active Sanctions",     (sanction_df["status"]=="ACTIVE").sum())
        st.metric("Total Entities",       len(sanction_df))
        st.metric("Total Vessels Linked",
            sanction_df[sanction_df["status"]=="ACTIVE"]["vessels_linked"].sum())
        st.markdown("**Listed By:**")
        for lb, cnt in sanction_df["listed_by"].value_counts().items():
            st.markdown(f"- **{lb}**: {cnt}")

# ── TAB 5 ─────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">THREAT ANALYTICS</div>', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Risk Distribution**")
        st.bar_chart(filtered["risk"].value_counts().reindex(
            ["CRITICAL","HIGH","MEDIUM","LOW"], fill_value=0), color="#2a9df4")
        st.markdown("**AIS Dark Vessels by Flag**")
        st.bar_chart(
            filtered.groupby("flag")["ais_dark"].sum().sort_values(ascending=False).head(10),
            color="#ff4444")
    with a2:
        st.markdown("**Detections by Region**")
        st.bar_chart(filtered["region"].value_counts().head(10), color="#ffaa00")
        st.markdown("**Database Coverage Overlap**")
        db_overlap = pd.DataFrame({
            "Database": ["AIS Only","SAT Only","SANC Only","INS Only",
                         "AIS+SAT","AIS+SAT+SANC","All 4 DBs"],
            "Vessels": [
                int((filtered["db_ais"] & ~filtered["db_satellite"] & ~filtered["db_sanctions"] & ~filtered["db_insurance"]).sum()),
                int((~filtered["db_ais"] & filtered["db_satellite"] & ~filtered["db_sanctions"] & ~filtered["db_insurance"]).sum()),
                int((~filtered["db_ais"] & ~filtered["db_satellite"] & filtered["db_sanctions"] & ~filtered["db_insurance"]).sum()),
                int((~filtered["db_ais"] & ~filtered["db_satellite"] & ~filtered["db_sanctions"] & filtered["db_insurance"]).sum()),
                int((filtered["db_ais"] & filtered["db_satellite"] & ~filtered["db_sanctions"] & ~filtered["db_insurance"]).sum()),
                int((filtered["db_ais"] & filtered["db_satellite"] & filtered["db_sanctions"] & ~filtered["db_insurance"]).sum()),
                int((filtered["db_ais"] & filtered["db_satellite"] & filtered["db_sanctions"] & filtered["db_insurance"]).sum()),
            ]
        })
        st.bar_chart(db_overlap.set_index("Database")["Vessels"], color="#aa44ff")
    st.markdown("---")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Avg Speed (kn)", f"{filtered['speed_kn'].mean():.1f}")
    s2.metric("AIS Dark Rate",  f"{filtered['ais_dark'].mean():.0%}")
    s3.metric("Spoofing Rate",  f"{filtered['spoofed'].mean():.0%}")
    s4.metric("STS Rate",       f"{filtered['sts_detected'].mean():.0%}")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3a6090;font-size:0.78rem;padding:10px 0;'>"
    "SHADOW — Stealthy Hub for Advanced Detection and Operational Watch<br/>"
    "HCSS Dashboard Concept — Prototype Build — All data simulated for demonstration<br/>"
    "Live integration targets: MarineTraffic AIS — Sentinel-1 SAR / Planet Labs "
    "— OFAC / EU / UN Sanctions — Lloyds Insurance Registry"
    "</div>",
    unsafe_allow_html=True
)
