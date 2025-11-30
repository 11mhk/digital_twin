# pages/map.py
# Full map page combining:
# - emissions.json heatmap + CO2 grid (data/grid.csv)
# - sample Pune points (clustered)
# - optional Vehicular CO2 layer loaded from data/pune_traffic_synthetic.csv when checked
# - sidebar controls and LayerControl
#
# Drop this file into pages/map.py (overwrites existing). Restart Streamlit.

import os
import json
import streamlit as st
import pandas as pd
import folium
import branca.colormap as cm
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

import streamlit as st

st.markdown(
    """
    <div class="page-title-pill">
        🌍 Map · CO₂ Intensity
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("Map View")
st.caption("Interactive spatial view of CO₂ intensity and simulation layers.")


st.set_page_config(layout="wide", page_title="CO₂ Map — Pune")
st.title("CO₂ Map — Pune (Heatmap · Grid · Vehicular)")

# ---------------------------
# Paths
# ---------------------------
EM_PATH = os.path.join("data", "emissions.json")
GRID_PATH = os.path.join("data", "grid.csv")
VEH_CSV = os.path.join("data", "pune_traffic_synthetic.csv")

# ---------------------------
# Sidebar controls
# ---------------------------
st.sidebar.header("Map controls")

# Heatmap (emissions.json)
show_heat = st.sidebar.checkbox("Emissions Heatmap", True)
heat_radius = st.sidebar.slider("Heatmap radius", 4, 40, 12)
heat_blur = st.sidebar.slider("Heatmap blur", 4, 30, 14)
min_opacity = st.sidebar.slider("Heatmap min opacity", 0.05, 0.6, 0.25)
heat_gradient = st.sidebar.selectbox("Heatmap gradient", ["default", "blue->red"], index=1)

# Grid
show_grid = st.sidebar.checkbox("CO₂ Grid", True)
grid_opacity = st.sidebar.slider("Grid opacity", 0.1, 1.0, 0.6)
colormap_name = st.sidebar.selectbox("Grid colormap", ["YlOrRd", "Viridis", "Plasma"], index=0)

# Pune points
show_points = st.sidebar.checkbox("Pune Points", True)

# Vehicular CSV layer (only load when checked)
show_veh = st.sidebar.checkbox("Vehicular CO₂ emissions (pune_traffic_synthetic)", False)
veh_splat = st.sidebar.checkbox("Splat veh points (increase visibility)", False)
veh_splat_count = st.sidebar.slider("Veh splat count (per point)", 1, 25, 8) if veh_splat else 1

# Map view
zoom = st.sidebar.slider("Initial zoom", 10, 14, 12)

# ---------------------------
# Prepare map center
# ---------------------------
def center_from_emissions(emissions):
    if not emissions:
        return [18.5204, 73.8567]  # Pune fallback
    avg_lat = sum(p["lat"] for p in emissions) / len(emissions)
    avg_lon = sum(p["lon"] for p in emissions) / len(emissions)
    return [avg_lat, avg_lon]

# ---------------------------
# Load emissions.json (if present)
# ---------------------------
emissions = []
if os.path.exists(EM_PATH):
    try:
        with open(EM_PATH) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            for r in raw:
                lat = r.get("lat") or r.get("latitude") or r.get("y")
                lon = r.get("lon") or r.get("longitude") or r.get("x")
                v = r.get("co2") or r.get("value") or r.get("intensity") or 1.0
                if lat is None or lon is None:
                    continue
                emissions.append({"lat": float(lat), "lon": float(lon), "co2": float(v)})
    except Exception as e:
        st.sidebar.error(f"Failed to read {EM_PATH}: {e}")

# ---------------------------
# Create base map
# ---------------------------
m = folium.Map(location=center_from_emissions(emissions), zoom_start=zoom, tiles="CartoDB positron")

# ---------------------------
# Emissions HeatMap (from emissions.json)
# ---------------------------
if show_heat and emissions:
    # prepare heat points with normalized weights 0..1
    vals = [p["co2"] for p in emissions]
    maxv = max(vals) if vals else 1.0
    heat_pts = [[p["lat"], p["lon"], (p["co2"] / maxv) if maxv > 0 else 1.0] for p in emissions]

    # choose gradient
    if heat_gradient == "blue->red":
        gradient = {0.0: "navy", 0.25: "cyan", 0.5: "lime", 0.75: "orange", 1.0: "red"}
    else:
        gradient = None

    HeatMap(
        heat_pts,
        radius=heat_radius,
        blur=heat_blur,
        min_opacity=min_opacity,
        gradient=gradient,
        max_zoom=17
    ).add_to(folium.FeatureGroup(name="Emissions Heatmap").add_to(m))

# ---------------------------
# CO2 Grid (from data/grid.csv)
# ---------------------------
if show_grid and os.path.exists(GRID_PATH):
    try:
        grid_df = pd.read_csv(GRID_PATH)
        lower_cols = [c.lower() for c in grid_df.columns]
        # detect value column
        val_col = None
        for cand in ("co2", "value", "intensity", "emission"):
            if cand in lower_cols:
                val_col = [c for c in grid_df.columns if c.lower() == cand][0]
                break
        if val_col is None:
            val_col = grid_df.columns[-1]

        vals = pd.to_numeric(grid_df[val_col], errors="coerce")
        vmin, vmax = float(vals.min()), float(vals.max())
        if vmin == vmax:
            vmin = 0.0

        cmap = getattr(cm.linear, f"{colormap_name}_09")
        colormap = cmap.scale(vmin, vmax)
        colormap.caption = "CO₂ intensity"

        gf = folium.FeatureGroup(name="CO₂ Grid").add_to(m)

        if set(["lat_min", "lon_min", "lat_max", "lon_max"]).issubset(lower_cols):
            df = grid_df.rename(columns={c: c.lower() for c in grid_df.columns})
            for _, row in df.iterrows():
                try:
                    lat1, lon1, lat2, lon2 = float(row["lat_min"]), float(row["lon_min"]), float(row["lat_max"]), float(row["lon_max"])
                    value = float(row[val_col])
                except Exception:
                    continue
                color = colormap(value) if vmax > vmin else colormap(vmin)
                folium.Rectangle(
                    bounds=[[lat1, lon1], [lat2, lon2]],
                    color=None,
                    fill=True,
                    fill_opacity=grid_opacity,
                    fill_color=color,
                    tooltip=f"CO₂: {value:.2f}"
                ).add_to(gf)
        else:
            # centroid fallback
            lat_col = next(c for c in grid_df.columns if c.lower().startswith("lat"))
            lon_col = next(c for c in grid_df.columns if c.lower().startswith("lon"))
            lats = grid_df[lat_col].astype(float)
            lons = grid_df[lon_col].astype(float)
            if len(lats) > 1:
                lat_diff = abs(lats.diff().dropna().median()) or 0.001
                lon_diff = abs(lons.diff().dropna().median()) or 0.001
            else:
                lat_diff = lon_diff = 0.001
            hlat, hlon = lat_diff / 2.2, lon_diff / 2.2
            for _, row in grid_df.iterrows():
                try:
                    lat, lon = float(row[lat_col]), float(row[lon_col])
                    v = float(row[val_col])
                except Exception:
                    continue
                color = colormap(v) if vmax > vmin else colormap(vmin)
                folium.Rectangle(
                    bounds=[[lat - hlat, lon - hlon], [lat + hlat, lon + hlon]],
                    color=None,
                    fill=True,
                    fill_opacity=grid_opacity,
                    fill_color=color,
                    tooltip=f"CO₂: {v:.2f}"
                ).add_to(gf)

        colormap.add_to(m)
    except Exception as e:
        st.sidebar.error(f"Failed to read {GRID_PATH}: {e}")
elif show_grid:
    st.sidebar.info(f"{GRID_PATH} not found. create it (conversion script) to show grid.")

# ---------------------------
# Pune Sample Points (cluster)
# ---------------------------
if show_points:
    pune_points = [
        ("Shivaji Nagar", 18.5309, 73.8478, 12.3),
        ("Viman Nagar",   18.5679, 73.9143, 18.1),
        ("Hinjawadi",     18.5913, 73.7389, 8.2),
        ("Kothrud",       18.5074, 73.8077, 9.5),
        ("Swargate",      18.5018, 73.8640, 11.0),
    ]
    pc = MarkerCluster(name="Pune Points").add_to(m)
    for name, lat, lon, co2 in pune_points:
        html = f"<div style='font-size:13px'><b>{name}</b><br/>CO₂: {co2:.2f}</div>"
        folium.Marker([lat, lon], popup=folium.Popup(html, max_width=250),
                      tooltip=name, icon=folium.Icon(color="darkgreen", icon="info-sign")).add_to(pc)

# ---------------------------
# Vehicular CO2 layer (loaded only when checkbox is checked)
# ---------------------------
if show_veh:
    veh_fg = folium.FeatureGroup(name="Vehicular CO₂ emissions")
    try:
        if not os.path.exists(VEH_CSV):
            raise FileNotFoundError(VEH_CSV)
        dfv = pd.read_csv(VEH_CSV)
        # detect lat/lon and co2 columns
        cols = [c.lower() for c in dfv.columns]
        lat_col = next((c for c in dfv.columns if c.lower() in ("lat", "latitude", "y")), None)
        lon_col = next((c for c in dfv.columns if c.lower() in ("lon", "longitude", "long", "x")), None)
        if not lat_col or not lon_col:
            # try fuzzy match
            lat_col = next((c for c in dfv.columns if "lat" in c.lower()), dfv.columns[0])
            lon_col = next((c for c in dfv.columns if "lon" in c.lower() or "long" in c.lower()), dfv.columns[1] if len(dfv.columns) > 1 else dfv.columns[0])

        co2_col = next((c for c in dfv.columns if "co2" in c.lower() or "emission" in c.lower()), None)
        if co2_col is None:
            # fallback numeric column
            for c in dfv.columns:
                if c not in (lat_col, lon_col) and pd.api.types.is_numeric_dtype(dfv[c]):
                    co2_col = c
                    break

        # build heat points and markers
        pts = []
        vals = []
        for _, r in dfv.iterrows():
            try:
                lat = float(r[lat_col]); lon = float(r[lon_col])
            except Exception:
                continue
            w = float(r[co2_col]) if co2_col and pd.notna(r[co2_col]) else 1.0
            pts.append([lat, lon, w])
            vals.append(w)

        maxv = max(vals) if vals else 1.0
        # optionally splat points to increase visibility for sparse data
        import random
        heat_pts = []
        for lat, lon, w in pts:
            norm_w = (w / maxv) if maxv > 0 else 1.0
            if veh_splat and veh_splat_count > 1:
                for _ in range(veh_splat_count):
                    jitter = (random.random() - 0.5) * 0.0008
                    jitter2 = (random.random() - 0.5) * 0.0008
                    heat_pts.append([lat + jitter, lon + jitter2, norm_w])
            else:
                heat_pts.append([lat, lon, norm_w])

        # add heatmap to veh_fg
        HeatMap(
            heat_pts,
            radius=heat_radius,
            blur=heat_blur,
            min_opacity=min_opacity,
            max_zoom=17
        ).add_to(veh_fg)

        # add clustered circle markers with popup
        cluster = MarkerCluster(name="Vehicular markers").add_to(veh_fg)
        for _, r in dfv.iterrows():
            try:
                lat = float(r[lat_col]); lon = float(r[lon_col])
            except Exception:
                continue
            w = float(r[co2_col]) if co2_col and pd.notna(r[co2_col]) else None
            # optional fields
            veh_count = None
            cong = None
            for c in dfv.columns:
                if "veh" in c.lower():
                    veh_count = r[c]
                if "cong" in c.lower():
                    cong = r[c]
            popup = "<div style='font-size:13px'>"
            if w is not None:
                popup += f"<b>CO₂:</b> {w:.2f}<br/>"
            if pd.notna(veh_count):
                try:
                    popup += f"<b>Vehicles:</b> {int(veh_count)}<br/>"
                except Exception:
                    popup += f"<b>Vehicles:</b> {veh_count}<br/>"
            if pd.notna(cong):
                popup += f"<b>Congestion:</b> {cong}<br/>"
            popup += "</div>"
            folium.CircleMarker(
                [lat, lon],
                radius=5,
                fill=True,
                fill_opacity=0.9,
                color=None,
                popup=folium.Popup(popup, max_width=320)
            ).add_to(cluster)

        veh_fg.add_to(m)

    except FileNotFoundError:
        st.sidebar.error(f"{VEH_CSV} not found on disk.")
    except Exception as e:
        st.sidebar.error(f"Failed to load veh data: {e}")

# ---------------------------
# Finalize: Layer control & render
# ---------------------------
folium.LayerControl(collapsed=False).add_to(m)
st.markdown("#### Map")
st.write("Use the sidebar to toggle layers and adjust appearance. LayerControl (top-right) also toggles layers.")
st_data = st_folium(m, width=1100, height=700)
