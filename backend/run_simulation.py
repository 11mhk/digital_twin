from utils.load_map import load_city_graph
from utils.emission_model import compute_emissions, export_points, make_grid
import osmnx as ox

def run_simulation(city="Bangalore, India"):
    print("Loading OSM...")
    G = load_city_graph(city)

    print("Converting to GeoDataFrame...")
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

    print("Computing emissions...")
    gdf_edges = compute_emissions(gdf_edges)

    print("Exporting emission points...")
    export_points(gdf_edges)

    print("Generating grid...")
    make_grid(gdf_edges)

    print("Simulation completed successfully!")

if __name__ == "__main__":
    run_simulation()
