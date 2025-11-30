# pages/map.py
import streamlit as st
import os, json
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import branca.colormap as cm
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Pune — Heatmap & Visuals")
st.title("Pune — Heatmap & CO₂ Grid Visuals")

# paths
EM_PATH = os.path.join("data", "emissions.json")
GRID_PATH = os.path.join("data", "grid.csv")

# Sidebar controls
st.sidebar.header("Map controls")
show_heat = st.sidebar.checkbox("Show heatmap (emissions)", True)
heat_radius = st.sidebar.slider("Heatmap radius", 4, 40, 12)
heat_blur = st.sidebar.slider("Heatmap blur", 4, 30, 14)
show_grid = st.sidebar.checkbox("Show CO₂ grid", True)
grid_opacity = st.sidebar.slider("Grid opacity", 0.1, 1.0, 0.6)
show_points = st.sidebar.checkbox("Show Pune points", True)
colormap_name = st.sidebar.selectbox("Colormap", ["YlOrRd", "Viridis", "Plasma"], index=0)
zoom = st.sidebar.slider("Initial zoom", 10, 14, 12)

# center Pune
center = [18.5204, 73.8567]
m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

# ---------- Load emissions (heatmap) ----------
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
                emissions.append([float(lat), float(lon), float(v)])
    except Exception as e:
        st.sidebar.error(f"Failed to read emissions: {e}")
else:
    st.sidebar.info("No emissions.json found (create or restore it).")

# add HeatMap layer (weighted)
if show_heat and emissions:
    # normalize values for HeatMap weight (optional): use value directly; folium will handle weighting
    HeatMap(emissions, radius=heat_radius, blur=heat_blur, max_zoom=17).add_to(folium.FeatureGroup(name="Emissions Heatmap").add_to(m))

# ---------- Load grid (choropleth-like) ----------
if os.path.exists(GRID_PATH) and show_grid:
    try:
        grid_df = pd.read_csv(GRID_PATH)
        # detect value column
        lower = [c.lower() for c in grid_df.columns]
        val_col = None
        for cand in ("co2","value","intensity","emission"):
            if cand in lower:
                val_col = [c for c in grid_df.columns if c.lower()==cand][0]
                break
        if val_col is None:
            val_col = grid_df.columns[-1]
        vals = pd.to_numeric(grid_df[val_col], errors="coerce")
        vmin, vmax = float(vals.min()), float(vals.max())
        if vmin == vmax:
            vmin = 0.0
        # choose colormap
        cmap = getattr(cm.linear, f"{colormap_name}_09")
        colormap = cmap.scale(vmin, vmax)
        colormap.caption = "CO₂ intensity"
        # draw rectangles (bounding-box format)
        cols_low = [c.lower() for c in grid_df.columns]
        gf = folium.FeatureGroup(name="CO₂ Grid").add_to(m)
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
                    fill_opacity=grid_opacity,
                    fill_color=color,
                    tooltip=f"CO₂: {value:.2f}"
                ).add_to(gf)
        else:
            # centroid fallback: draw small squares
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
                    color=None, fill=True, fill_opacity=grid_opacity, fill_color=color,
                    tooltip=f"CO₂: {v:.2f}"
                ).add_to(gf)
        colormap.add_to(m)
    except Exception as e:
        st.sidebar.error(f"Failed to read grid.csv: {e}")

# ---------- Pune sample points (cluster + popups) ----------
if show_points:
    pune_points = [
        ("Shivaji Nagar", 18.5309, 73.8478, 12.3),
        ("Viman Nagar",   18.5679, 73.9143, 18.1),
        ("Hinjawadi",     18.5913, 73.7389, 8.2),
        ("Kothrud",       18.5074, 73.8077, 9.5),
        ("Swargate",      18.5018, 73.8640, 11.0),
    ]
    cluster = MarkerCluster(name="Pune Points").add_to(m)
    for name, lat, lon, co2 in pune_points:
        html = f"""
        <div style="font-size:13px">
          <b>{name}</b><br/>
          CO₂: {co2:.2f} units<br/>
          <small>Sample point</small>
        </div>
        """
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(html, max_width=250),
            tooltip=name,
            icon=folium.Icon(color="darkgreen", icon="info-sign")
        ).add_to(cluster)

# Layer controls + render
folium.LayerControl(collapsed=False).add_to(m)
st.markdown("#### Map")
st.write("Use the sidebar to toggle layers and adjust heatmap/grid appearance.")
st_data = st_folium(m, width=1100, height=700)
