import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import os
import json

# ==== EARTH ENGINE AUTHENTICATION (Service Account) ====
# Store your service account JSON in Streamlit Secrets as EE_SERVICE_ACCOUNT
service_account_info = json.loads(st.secrets["EE_SERVICE_ACCOUNT"])
service_account_file = "/tmp/service_account.json"
with open(service_account_file, "w") as f:
    json.dump(service_account_info, f)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file

# Initialize Earth Engine
ee.Initialize()

# ==== FOLIUM EARTH ENGINE LAYER SUPPORT ====
def add_ee_layer(self, ee_image, vis_params, name):
    map_id = ee.Image(ee_image).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True
    ).add_to(self)

folium.Map.add_ee_layer = add_ee_layer

# ==== STREAMLIT PAGE CONFIG ====
st.set_page_config(layout="wide", page_title="SAR Flood Mapping")

# Sidebar navigation
page = st.sidebar.selectbox("Navigation", ["Home", "Flood Analysis"])

# ==== HOME PAGE ====
if page == "Home":
    st.title("SAR Flood Mapping Tool")
    st.markdown("""
    This tool estimates flood extent using Sentinel‑1 SAR imagery and the
    Google Earth Engine Python API (EE API). Flood extent is calculated
    by comparing radar backscatter before and after an event and applying
    a threshold.
    """)
    st.markdown("""
    **How to use:**  
    - In the sidebar, choose **Flood Analysis**.  
    - Draw an area of interest (AOI) on the map.  
    - Select pre‑ and post‑flood dates.  
    - Adjust the threshold if necessary.  
    - Click **Run Flood Mapping** to generate flood map.  
    """)

# ==== FLOOD ANALYSIS PAGE ====
elif page == "Flood Analysis":
    st.title("Flood Extent Analysis")

    # Sidebar inputs
    st.sidebar.subheader("Select Dates & Threshold")
    pre_start = st.sidebar.date_input("Pre‑flood Start")
    pre_end = st.sidebar.date_input("Pre‑flood End")
    post_start = st.sidebar.date_input("Post‑flood Start")
    post_end = st.sidebar.date_input("Post‑flood End")
    threshold = st.sidebar.slider("Backscatter Threshold", 0.5, 5.0, 1.25)

    # AOI drawing map
    st.subheader("Draw Area of Interest (AOI)")
    m = folium.Map(location=[0, 0], zoom_start=2)
    map_data = st_folium(m, width=700, height=400, returned_objects=['last_active_drawing'])

    aoi_geom = None
    if map_data.get("last_active_drawing"):
        coords = map_data["last_active_drawing"]["geometry"]["coordinates"][0]
        minx, miny = min(p[0] for p in coords), min(p[1] for p in coords)
        maxx, maxy = max(p[0] for p in coords), max(p[1] for p in coords)
        aoi_geom = ee.Geometry.Rectangle([minx, miny, maxx, maxy])
        st.success(f"AOI set: {minx:.2f}, {miny:.2f} to {maxx:.2f}, {maxy:.2f}")

    # Run flood mapping
    if st.button("Run Flood Mapping") and aoi_geom:
        st.info("Fetching and processing data…")

        # Sentinel‑1 collection before flood
        s1_pre = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi_geom)
            .filterDate(str(pre_start), str(pre_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
            .median()
        )

        # Sentinel‑1 collection after flood
        s1_post = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi_geom)
            .filterDate(str(post_start), str(post_end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
            .median()
        )

        # Flood mask using ratio and threshold
        ratio = s1_post.select("VV").divide(s1_pre.select("VV"))
        flood_mask = ratio.gt(threshold)

        # Visualization parameters
        vis_params = {"min": 1, "max": 3, "palette": ["white", "blue"]}

        # Map for displaying flood
        flood_map = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=8)
        flood_map.add_ee_layer(flood_mask.selfMask(), vis_params, "Flood Extent")

        st.subheader("Flood Extent Map")
        st_folium(flood_map, width=700, height=500)
