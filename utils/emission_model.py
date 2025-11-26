import pandas as pd
import numpy as np
from shapely.geometry import box
import json
import logging

logging.basicConfig(level=logging.INFO)

# Basic emission factor (kg/km)
EMISSION_FACTOR = 0.12

TRAFFIC_MULTIPLIERS = {
    "motorway": 1.5,
    "primary": 1.3,
    "secondary": 1.2,
    "tertiary": 1.0,
    "residential": 0.8
}

def compute_emissions(gdf_edges):
    gdf_edges["length_km"] = gdf_edges["length"] / 1000
    gdf_edges["traffic"] = gdf_edges["highway"].apply(
        lambda x: TRAFFIC_MULTIPLIERS.get(str(x), 1.0)
    )
    gdf_edges["co2_kg"] = gdf_edges["length_km"] * EMISSION_FACTOR * gdf_edges["traffic"]
    return gdf_edges

def export_points(gdf_edges, out_file="data/emissions.json"):
    points = []
    for _, row in gdf_edges.iterrows():
        centroid = row.geometry.centroid
        points.append({
            "lat": float(centroid.y),
            "lon": float(centroid.x),
            "co2": float(row["co2_kg"])
        })
    with open(out_file, "w") as f:
        json.dump(points, f, indent=2)
    logging.info("Emission points saved.")

def make_grid(gdf_edges, grid_size=10, out_file="data/grid.csv"):
    bounds = gdf_edges.total_bounds
    minx, miny, maxx, maxy = bounds

    x_lines = np.linspace(minx, maxx, grid_size + 1)
    y_lines = np.linspace(miny, maxy, grid_size + 1)

    records = []
    for i in range(grid_size):
        for j in range(grid_size):
            cell = box(x_lines[i], y_lines[j], x_lines[i+1], y_lines[j+1])
            mask = gdf_edges.centroid.within(cell)
            total_co2 = gdf_edges.loc[mask, "co2_kg"].sum()
            records.append({"row": i, "col": j, "co2": total_co2})

    df_grid = pd.DataFrame(records)
    df_grid.to_csv(out_file, index=False)
    logging.info("Grid file saved.")
