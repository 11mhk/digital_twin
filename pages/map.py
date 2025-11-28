import streamlit as st
import json
import pandas as pd
import folium
from folium.plugins import HeatMap
import branca.colormap as cm
from streamlit_folium import st_folium
import os

st.set_page_config(layout="wide", page_title="CO₂ Map")

st.title("Geo-Visualization — CO₂ Heatmap & Grid")

# paths
EM_PATH = os.path.join("data", "emissions.json")
GRID_PATH = os.path.join("data", "grid.csv")

# Sidebar controls
show_heat = st.sidebar.checkbox("Show heatmap", True)
show_grid = st.sidebar.checkbox("Show grid", True)
opacity = st.sidebar.slider("Grid opacity", 0.1, 1.0, 0.6)
radius = st.sidebar.slider("Heatmap radius", 6, 30, 12)
blur = st.sidebar.slider("Heatmap blur", 8, 30, 15)
zoom = st.sidebar.slider("Initial zoom", 10, 16, 13)

# load emissions
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
                emissions.append({"lat": float(lat), "lon": float(lon), "value": float(v)})
    except Exception as e:
        st.error(f"Failed to read {EM_PATH}: {e}")
else:
    st.warning(f"{EM_PATH} not found. Create or restore it.")

# load grid
grid_df = None
if os.path.exists(GRID_PATH):
    try:
        grid_df = pd.read_csv(GRID_PATH)
    except Exception as e:
        st.error(f"Failed to read {GRID_PATH}: {e}")
else:
    st.warning(f"{GRID_PATH} not found. Create or restore it.")

# quick data info
col1, col2 = st.columns([1,3])
with col1:
    st.markdown("**Data summary**")
    st.write("Emissions points:", len(emissions))
    st.write("Grid rows:", len(grid_df) if grid_df is not None else 0)

# determine center
if emissions:
    avg_lat = sum(p["lat"] for p in emissions)/len(emissions)
    avg_lon = sum(p["lon"] for p in emissions)/len(emissions)
elif grid_df is not None and {"lat_min","lat_max","lon_min","lon_max"}.issubset(set(c.lower() for c in grid_df.columns)):
    df = grid_df.rename(columns={c:c.lower() for c in grid_df.columns})
    avg_lat = (df["lat_min"].mean() + df["lat_max"].mean())/2
    avg_lon = (df["lon_min"].mean() + df["lon_max"].mean())/2
else:
    avg_lat, avg_lon = 28.7041, 77.1025  # fallback (Delhi)

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=zoom, tiles="CartoDB positron")

# add heatmap
if show_heat and emissions:
    heat_points = [[p["lat"], p["lon"], p["value"]] for p in emissions]
    HeatMap(heat_points, radius=radius, blur=blur, max_zoom=17).add_to(m)

# prepare colormap & value column for grid
val_col = None
if grid_df is not None:
    lower = [c.lower() for c in grid_df.columns]
    for candidate in ("co2","value","intensity","emission"):
        if candidate in lower:
            val_col = [c for c in grid_df.columns if c.lower()==candidate][0]
            break
    if val_col is None:
        val_col = grid_df.columns[-1]  # fallback
    vals = pd.to_numeric(grid_df[val_col], errors="coerce")
    vmin, vmax = float(vals.min()), float(vals.max())
    if vmin == vmax:
        vmin = 0.0
    colormap = cm.linear.YlOrRd_09.scale(vmin, vmax)
    colormap.caption = "CO₂ intensity"

# draw grid rectangles
if show_grid and grid_df is not None:
    cols_low = [c.lower() for c in grid_df.columns]
    if set(["lat_min","lon_min","lat_max","lon_max"]).issubset(cols_low):
        df = grid_df.rename(columns={c:c.lower() for c in grid_df.columns})
        for _, row in df.iterrows():
            try:
                lat1, lon1, lat2, lon2 = row["lat_min"], row["lon_min"], row["lat_max"], row["lon_max"]
                value = float(row[val_col])
            except Exception:
                continue
            color = colormap(value) if vmax>vmin else colormap(vmin)
            folium.Rectangle(
                bounds=[[lat1, lon1], [lat2, lon2]],
                color=None,
                fill=True,
                fill_opacity=opacity,
                fill_color=color,
                tooltip=f"CO₂: {value:.2f}"
            ).add_to(m)
    else:
        # centroid case
        lat_col = [c for c in grid_df.columns if c.lower().startswith("lat")][0]
        lon_col = [c for c in grid_df.columns if c.lower().startswith("lon")][0]
        lats = grid_df[lat_col].astype(float)
        lons = grid_df[lon_col].astype(float)
        if len(lats) > 1:
            lat_diff = abs(lats.diff().dropna().median()) or 0.001
            lon_diff = abs(lons.diff().dropna().median()) or 0.001
        else:
            lat_diff = lon_diff = 0.001
        hlat, hlon = lat_diff/2.2, lon_diff/2.2
        for _, row in grid_df.iterrows():
            lat, lon = float(row[lat_col]), float(row[lon_col])
            v = float(row[val_col])
            color = colormap(v) if vmax>vmin else colormap(vmin)
            folium.Rectangle(
                bounds=[[lat-hlat, lon-hlon], [lat+hlat, lon+hlon]],
                color=None,
                fill=True,
                fill_opacity=opacity,
                fill_color=color,
                tooltip=f"CO₂: {v:.2f}"
            ).add_to(m)

# add map controls
if 'colormap' in locals():
    colormap.add_to(m)
folium.LayerControl().add_to(m)

# render in Streamlit
st.markdown("#### Map")
st_folium(m, width=1100, height=700)
