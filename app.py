import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import os
import json
import tempfile

# ==== EARTH ENGINE AUTHENTICATION (Service Account) ====
# Load service account from Streamlit secrets
service_account_info = json.loads(st.secrets["EE_SERVICE_ACCOUNT"])
service_account_file = os.path.join(tempfile.gettempdir(), "service_account.json")
with open(service_account_file, "w") as f:
    json.dump(service_account_info, f)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file
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
    by comparing radar backscatter before and after an event.
    """)
    st.markdown("""
    **How to use:**  
    - In the sidebar, choose **Flood Analysis**.  
    - Draw a small Area of Interest (AOI) for faster results.  
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
        # Warn user if AOI is too large
        if (maxx - minx) * (maxy - miny) > 1.0:
            st.warning("AOI is large! Consider using a smaller area for faster results.")
        aoi_geom = ee.Geometry.Rectangle([minx, miny, maxx, maxy])
        st.success(f"AOI set: {minx:.2f}, {miny:.2f} to {maxx:.2f}, {maxy:.2f}")

    # Cached function to fetch median Sentinel-1 collection
    @st.cache_data
    def fetch_s1_median(aoi, start, end):
        return (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(aoi)
                .filterDate(str(start), str(end))
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
                .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
                .median())

    # Run flood mapping
    if st.button("Run Flood Mapping") and aoi_geom:
        progress = st.progress(0)
        st.info("Fetching pre-flood data…")
        s1_pre = fetch_s1_median(aoi_geom, pre_start, pre_end)
        progress.progress(30)

        st.info("Fetching post-flood data…")
        s1_post = fetch_s1_median(aoi_geom, post_start, post_end)
        progress.progress(60)

        st.info("Calculating flood mask…")
        ratio = s1_post.select("VV").divide(s1_pre.select("VV"))
        flood_mask = ratio.gt(threshold)
        progress.progress(90)

        # Visualization parameters
        vis_params = {"min": 1, "max": 3, "palette": ["white", "blue"]}

        st.info("Rendering map…")
        flood_map = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=8)
        flood_map.add_ee_layer(flood_mask.selfMask(), vis_params, "Flood Extent")
        progress.progress(100)

        st.subheader("Flood Extent Map")
        st_folium(flood_map, width=700, height=500)
        st.success("Flood mapping complete!")
