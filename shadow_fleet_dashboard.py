# shadow_fleet_dashboard.py
# ─────────────────────────────────────────────────────────────────────────────
# SHADOW — Stealthy Hub for Advanced Detection & Operational Watch
# Professional Intelligence-Grade Dashboard
# Run: streamlit run shadow_fleet_dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import random
import time
from datetime import datetime, timedelta

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SHADOW Dashboard",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── PROFESSIONAL COLOR PALETTE ────────────────────────────────────────────────
PRIMARY_BG = "#0B1929"      # Deep navy blue
PANEL_BG = "#112240"        # Lighter panel navy
ACCENT_BLUE = "#1A6EBD"     # Accent blue
HIGHLIGHT_BLUE = "#2E9BDA"  # Highlight blue
TEXT_PRIMARY = "#FFFFFF"    # White text
TEXT_SECONDARY = "#A8B8CC"  # Light grey text
BORDER_COLOR = "#1E3A5F"    # Dark border
CRITICAL_RED = "#CC2936"    # Critical red
AMBER_WARNING = "#E8A020"   # High priority amber
SUCCESS_GREEN = "#2ECC71"   # Low risk green

# ── PROFESSIONAL STYLING ──────────────────────────────────────────────────────
st.markdown(f"""
<style>
  body {{ background-color: {PRIMARY_BG}; }}
  .stApp {{ background-color: {PRIMARY_BG}; color: {TEXT_PRIMARY}; }}
  section[data-testid="stSidebar"] {{ background-color: {PANEL_BG}; }}
  
  /* Metric cards */
  div[data-testid="metric-container"] {{
    background: {PANEL_BG};
    border: 1px solid {BORDER_COLOR};
    border-top: 3px solid {ACCENT_BLUE};
    border-radius: 6px;
    padding: 16px;
  }}
  div[data-testid="metric-container"] label {{ 
    color: {TEXT_SECONDARY} !important; 
    font-size: 0.75rem;
    font-weight: 500;
  }}
  div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY};
    font-size: 1.8rem;
    font-weight: 700;
  }}

  /* Section headers */
  .section-header {{
    background: {PANEL_BG};
    border-left: 4px solid {ACCENT_BLUE};
    border-radius: 4px;
    padding: 12px 16px;
    margin: 20px 0 12px 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    letter-spacing: 0.05em;
  }}

  /* Risk badges */
  .risk-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.70rem;
    font-weight: 700;
    margin: 2px 4px;
  }}
  .risk-critical {{ background: {CRITICAL_RED}; color: white; }}
  .risk-high {{ background: {AMBER_WARNING}; color: white; }}
  .risk-medium {{ background: {ACCENT_BLUE}; color: white; }}
  .risk-low {{ background: {SUCCESS_GREEN}; color: white; }}

  /* Notification bars */
  .notification {{
    display: flex;
    align-items: center;
    background: {PANEL_BG};
    border-left: 4px solid;
    border-radius: 4px;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.85rem;
  }}
  .notification-critical {{ border-left-color: {CRITICAL_RED}; }}
  .notification-high {{ border-left-color: {AMBER_WARNING}; }}
  .notification-medium {{ border-left-color: {ACCENT_BLUE}; }}

  /* Tab styling */
  .stTabs [data-baseweb="tab-list"] {{
    background: transparent;
    border-bottom: 1px solid {BORDER_COLOR};
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {TEXT_SECONDARY};
    font-weight: 500;
  }}
  .stTabs [aria-selected="true"] {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT_BLUE};
  }}

  /* Footer */
  .footer {{
    background: {PANEL_BG};
    border-top: 1px solid {BORDER_COLOR};
    padding: 16px;
    margin-top: 32px;
    text-align: center;
    color: {TEXT_SECONDARY};
    font-size: 0.75rem;
  }}

  h1, h2, h3 {{ color: {TEXT_PRIMARY} !important; }}
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
        "risk":   row["risk"],
        "alert":  rng.choice(templates),
    } for _, row in critical.iterrows()]

# ── RISK COLOR MAPPING ────────────────────────────────────────────────────────
RISK_COLOR = {
    "CRITICAL": [204, 41,  54,  220],
    "HIGH":     [232, 160,  32,  200],
    "MEDIUM":   [26,  110, 189,  180],
    "LOW":      [46,  204, 113, 140],
}

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<div style='font-size:2rem;font-weight:800;color:#FFFFFF;letter-spacing:0.1em;'>SHADOW</div>", 
                unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.70rem;color:{TEXT_SECONDARY};font-style:italic;margin-bottom:12px;'>"
                "Stealthy Hub for Advanced Detection and Operational Watch</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.85rem;color:{ACCENT_BLUE};font-weight:600;margin-bottom:20px;'>"
                "HCSS Dashboard Concept</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### Map Layers")
    show_vessels   = st.toggle("Vessel Positions",     value=True)
    show_sat_pings = st.toggle("Satellite Detections", value=False)
    show_heat      = st.toggle("Risk Heatmap",         value=False)

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

    st.markdown("### Live Updates")
    auto_refresh = st.checkbox("Auto-refresh every 30s", True)

    st.markdown("---")
    st.markdown("### Top Risk Vessels")

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOAD & FILTERS
# ══════════════════════════════════════════════════════════════════════════════
seed_val    = int(time.time()) // 30 if auto_refresh else 42
vessels_df  = generate_vessels(n=120, seed=seed_val)
sat_df      = generate_satellite_pings(vessels_df, seed=seed_val)
sts_df      = generate_sts_events(vessels_df, seed=seed_val)
sanction_df = generate_sanctions_data(seed=seed_val)
alerts      = generate_alerts(vessels_df, seed=seed_val)

# Apply filters
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

# Get top 5 high risk vessels for sidebar
top_risk = filtered.sort_values("risk", 
    key=lambda x: x.map({"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3})).head(5)

# ── POPULATE SIDEBAR LIVE TRACKER ─────────────────────────────────────────────
with st.sidebar:
    for _, vessel in top_risk.iterrows():
        risk_badge = f'<span class="risk-badge risk-{vessel["risk"].lower()}">{vessel["risk"]}</span>'
        st.markdown(
            f"<div style='background:{PANEL_BG};border:1px solid {BORDER_COLOR};border-radius:4px;padding:10px;margin:6px 0;'>"
            f"<div style='font-weight:600;color:{TEXT_PRIMARY};font-size:0.85rem;'>{vessel['vessel_name']}</div>"
            f"<div style='font-size:0.70rem;color:{TEXT_SECONDARY};margin:4px 0;'>{vessel['flag']} • {vessel['region']}</div>"
            f"{risk_badge}"
            f"<div style='font-size:0.65rem;color:{TEXT_SECONDARY};margin-top:6px;'>Last seen: {vessel['last_seen'].strftime('%H:%M UTC')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT AREA
# ══════════════════════════════════════════════════════════════════════════════

# Header
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(f"<div style='font-size:2.2rem;font-weight:800;color:{TEXT_PRIMARY};margin-bottom:2px;'>"
                "SHADOW Vessel Intelligence Platform</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.85rem;color:{TEXT_SECONDARY};'>Global maritime domain awareness and threat assessment</div>",
                unsafe_allow_html=True)
with col2:
    st.markdown(f"<div style='text-align:right;font-size:0.75rem;color:{TEXT_SECONDARY};'>"
                f"Last updated:<br/>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>", 
                unsafe_allow_html=True)

st.markdown("---")

# Notifications
st.markdown('<div class="section-header">ACTIVE ALERTS</div>', unsafe_allow_html=True)
alert_count = 0
for a in alerts[:4]:
    risk_border = {"CRITICAL": CRITICAL_RED, "HIGH": AMBER_WARNING, "MEDIUM": ACCENT_BLUE}
    risk_color = risk_border.get(a["risk"], ACCENT_BLUE)
    severity_text = a["risk"]
    st.markdown(
        f'<div class="notification notification-{a["risk"].lower()}" style="border-left-color:{risk_color};">'
        f'<div style="font-weight:700;color:{risk_color};min-width:70px;">{severity_text}</div>'
        f'<div style="margin:0 12px;color:{TEXT_PRIMARY};font-weight:600;">{a["vessel"]}</div>'
        f'<div style="margin-left:auto;color:{TEXT_SECONDARY};font-size:0.75rem;">{a["region"]} • {a["time"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    alert_count += 1

if alert_count == 0:
    st.markdown(f'<div style="padding:12px;color:{TEXT_SECONDARY};font-size:0.85rem;">No active alerts</div>', 
                unsafe_allow_html=True)

st.markdown("---")

# KPI Metrics
st.markdown('<div class="section-header">FLEET STATISTICS</div>', unsafe_allow_html=True)
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Tracked Vessels", len(filtered), f"+{random.randint(1,5)}")
m2.metric("Critical Risk",   (filtered["risk"]=="CRITICAL").sum(), f"+{random.randint(0,3)}")
m3.metric("AIS Dark",        filtered["ais_dark"].sum(), f"+{random.randint(0,4)}")
m4.metric("GPS Spoofed",     filtered["spoofed"].sum(), f"+{random.randint(0,3)}")
m5.metric("STS Detected",    filtered["sts_detected"].sum(), f"+{random.randint(0,2)}")
m6.metric("Sanctioned",      filtered["db_sanctions"].sum(), "+-0")
m7.metric("Multi-DB Match",
    ((filtered["db_ais"].astype(int)+filtered["db_satellite"].astype(int)+
      filtered["db_sanctions"].astype(int)+filtered["db_insurance"].astype(int))>=3).sum(),
    f"+{random.randint(0,4)}")

st.markdown("---")

# Map
st.markdown('<div class="section-header">GLOBAL VESSEL POSITIONS</div>', unsafe_allow_html=True)

if not filtered.empty:
    # Build map layers
    layers = []
    
    if show_vessels and not filtered.empty:
        # Scale radius by risk level
        vessel_data = filtered.copy()
        vessel_data["radius"] = vessel_data["risk"].map({"CRITICAL": 80000, "HIGH": 60000, "MEDIUM": 40000, "LOW": 30000})
        
        layers.append(pdk.Layer(
            "ScatterplotLayer", data=vessel_data,
            get_position=["lon","lat"], get_color="color",
            get_radius="radius",
            radius_min_pixels=5, radius_max_pixels=20,
            pickable=True, opacity=0.85, stroked=True,
            line_width_min_pixels=1, get_line_color=[255,255,255,120],
        ))
        
        # Label top 20 highest risk vessels
        top_20 = filtered.sort_values("risk", 
            key=lambda x: x.map({"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3})).head(20)
        
        layers.append(pdk.Layer(
            "TextLayer", data=top_20,
            get_position=["lon","lat"],
            get_text="vessel_name",
            get_size=12,
            get_color=[255, 255, 255, 200],
            get_angle=0,
            get_text_anchor="middle",
            get_alignment_baseline="center",
            pickable=False,
        ))
    
    if show_heat and not filtered.empty:
        heat_data = filtered.copy()
        heat_data["weight"] = heat_data["risk"].map({"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1})
        
        layers.append(pdk.Layer(
            "HeatmapLayer", data=heat_data,
            get_position=["lon","lat"],
            get_weight="weight",
            radiusPixels=60, intensity=1.2, threshold=0.05, opacity=0.5,
        ))
    
    tooltip = {
        "html": "<b>{vessel_name}</b><br/>IMO: {imo}<br/>MMSI: {mmsi}<br/>Flag: {flag}<br/>Risk: {risk}",
        "style": {"backgroundColor": "#0B1929", "color": "#FFFFFF", "font-size": "12px"}
    }
    
    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=25.0, longitude=45.0, zoom=2.5, pitch=40),
        map_style="mapbox://styles/mapbox/dark-v10",
        tooltip=tooltip,
    ), use_container_width=True, height=600)
else:
    st.info("No vessels match current filters")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Vessel Intelligence", "Satellite Log", "STS Events", "Sanctions Database", "Analytics"
])

# ── TAB 1: VESSEL INTELLIGENCE ────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">VESSEL INTELLIGENCE QUERY</div>', unsafe_allow_html=True)
    
    search_term = st.text_input("Search by vessel name, IMO, or MMSI", "")
    
    disp = filtered.copy()
    if search_term:
        disp = disp[disp["vessel_name"].str.contains(search_term, case=False) |
                    disp["imo"].str.contains(search_term, case=False) |
                    disp["mmsi"].str.contains(search_term, case=False)]
    
    disp = disp.sort_values("risk", key=lambda x: x.map({"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}))
    
    # Create display dataframe
    display_df = disp[["vessel_name", "risk", "flag", "type", "speed_kn", "imo", "mmsi", "region"]].copy()
    display_df.columns = ["Vessel", "Risk", "Flag", "Type", "Speed (kn)", "IMO", "MMSI", "Region"]
    
    # Add databases column
    db_cols = []
    for _, row in disp.iterrows():
        dbs = []
        if row["db_ais"]: dbs.append("AIS")
        if row["db_satellite"]: dbs.append("SAT")
        if row["db_sanctions"]: dbs.append("SANC")
        if row["db_insurance"]: dbs.append("INS")
        db_cols.append(", ".join(dbs) if dbs else "None")
    
    display_df["Databases"] = db_cols
    
    # Display table
    st.dataframe(display_df, use_container_width=True, height=500)

# ── TAB 2: SATELLITE LOG ──────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">SATELLITE DETECTION LOG</div>', unsafe_allow_html=True)
    
    sat_show = sat_df[sat_df["vessel_id"].isin(filtered["vessel_id"])].copy()
    if not sat_show.empty:
        sat_show["AIS Match"]  = sat_show["ais_match"].map({True:"Matched", False:"Dark / No Match"})
        sat_show["Confidence"] = sat_show["sat_confidence"].apply(lambda x: f"{x:.0%}")
        
        display_sat = sat_show[["vessel_name","flag","type","region","image_source","Confidence","AIS Match"]].copy()
        display_sat.columns = ["Vessel", "Flag", "Type", "Region", "Satellite Source", "Confidence", "AIS Match"]
        
        st.dataframe(display_sat, use_container_width=True, height=400)
    else:
        st.info("No satellite data for filtered vessels")

# ── TAB 3: STS EVENTS ─────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">SHIP-TO-SHIP TRANSFER EVENTS</div>', unsafe_allow_html=True)
    
    sts_show = sts_df[sts_df["vessel_id"].isin(filtered["vessel_id"])].copy()
    if not sts_show.empty:
        sts_show["Volume"] = sts_show["transfer_vol_kbd"].astype(int).astype(str) + " kbd"
        sts_show["Duration"] = sts_show["duration_hrs"].apply(lambda x: f"{x}h")
        
        display_sts = sts_show[["vessel_name","pair_vessel","region","Volume","Duration","risk"]].copy()
        display_sts.columns = ["Primary Vessel", "Transfer Pair", "Region", "Volume", "Duration", "Risk"]
        
        st.dataframe(display_sts, use_container_width=True, height=400)
        st.info(f"Total undocumented cargo: {int(sts_show['transfer_vol_kbd'].sum()):,} kbd")
    else:
        st.info("No STS events match current filters")

# ── TAB 4: SANCTIONS DATABASE ─────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">SANCTIONS ENTITY DATABASE</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.dataframe(sanction_df, use_container_width=True, height=400)
    with col2:
        st.metric("Active Sanctions",     (sanction_df["status"]=="ACTIVE").sum())
        st.metric("Total Entities",       len(sanction_df))
        st.metric("Vessels Linked",
            sanction_df[sanction_df["status"]=="ACTIVE"]["vessels_linked"].sum())

# ── TAB 5: ANALYTICS ──────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">THREAT ANALYTICS</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        dark_rate = filtered["ais_dark"].mean()
        st.metric("AIS Dark Rate", f"{dark_rate:.0%}")
        st.progress(dark_rate)
    with col2:
        spoof_rate = filtered["spoofed"].mean()
        st.metric("Spoofing Rate", f"{spoof_rate:.0%}")
        st.progress(spoof_rate)
    with col3:
        sts_rate = filtered["sts_detected"].mean()
        st.metric("STS Rate", f"{sts_rate:.0%}")
        st.progress(sts_rate)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Risk Distribution**")
        risk_dist = filtered["risk"].value_counts().reindex(["CRITICAL","HIGH","MEDIUM","LOW"], fill_value=0)
        st.bar_chart(risk_dist, color=["#CC2936", "#E8A020", "#1A6EBD", "#2ECC71"])
    with col2:
        st.markdown("**Detections by Region**")
        st.bar_chart(filtered["region"].value_counts().head(10))

st.markdown("---")

# Footer
st.markdown(f"""
<div class="footer">
SHADOW — Stealthy Hub for Advanced Detection and Operational Watch | Version 1.0.0<br>
Data Sources: AIS Live Feed • Satellite Imagery • Sanctions Lists • Insurance Registry<br>
Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
</div>
""", unsafe_allow_html=True)
