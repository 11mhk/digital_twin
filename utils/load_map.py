import osmnx as ox
import logging

logging.basicConfig(level=logging.INFO)
#ox.config(use_cache=True, log_console=False)

def load_city_graph(place_name: str):
    """
    Load driving road graph for the given city name using OSMnx.
    """
    try:
        logging.info(f"Loading OSM data for {place_name} ...")
        graph = ox.graph_from_place(place_name, network_type="drive")
        logging.info("OSM data loaded successfully.")
        return graph
    except Exception as e:
        logging.error("Error loading OSM data:")
        raise e
