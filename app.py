import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import os
import json
import tempfile
from datetime import date, timedelta

# ==== EARTH ENGINE AUTHENTICATION (Service Account) ====
service_account_info = json.loads(st.secrets["EE_SERVICE_ACCOUNT"])
service_account_file = os.path.join(tempfile.gettempdir(), "service_account.json")
with open(service_account_file, "w") as f:
    json.dump(service_account_info, f)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file
ee.Initialize()

# ==== FOLIUM LAYER SUPPORT ====
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
    - Go to **Flood Analysis**.  
    - Default small AOI is set for fast testing.  
    - Pre/post flood dates are short by default.  
    - Click **Run Flood Mapping** to see fast results.  
    """)

# ==== FLOOD ANALYSIS PAGE ====
elif page == "Flood Analysis":
    st.title("Flood Extent Analysis")

    # Default small AOI
    default_aoi = ee.Geometry.Rectangle([77.5, 28.5, 77.6, 28.6])
    st.info("Default small AOI is set for instant results.")

    # Short default dates (last week)
    today = date.today()
    default_pre_start = today - timedelta(days=14)
    default_pre_end = today - timedelta(days=8)
    default_post_start = today - timedelta(days=7)
    default_post_end = today - timedelta(days=1)

    st.sidebar.subheader("Select Dates & Threshold")
    pre_start = st.sidebar.date_input("Pre‑flood Start", default_pre_start)
    pre_end = st.sidebar.date_input("Pre‑flood End", default_pre_end)
    post_start = st.sidebar.date_input("Post‑flood Start", default_post_start)
    post_end = st.sidebar.date_input("Post‑flood End", default_post_end)
    threshold = st.sidebar.slider("Backscatter Threshold", 0.5, 5.0, 1.25)

    # AOI map (just for display)
    st.subheader("Area of Interest (AOI)")
    m = folium.Map(location=[28.55, 77.55], zoom_start=12)
    st_folium(m, width=700, height=400)

    # Cached function for fast repeated runs
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
    if st.button("Run Flood Mapping"):
        progress = st.progress(0)
        st.info("Fetching pre-flood data…")
        s1_pre = fetch_s1_median(default_aoi, pre_start, pre_end)
        progress.progress(30)

        st.info("Fetching post-flood data…")
        s1_post = fetch_s1_median(default_aoi, post_start, post_end)
        progress.progress(60)

        st.info("Calculating flood mask…")
        ratio = s1_post.select("VV").divide(s1_pre.select("VV"))
        flood_mask = ratio.gt(threshold)
        progress.progress(90)

        st.info("Rendering map…")
        vis_params = {"min": 1, "max": 3, "palette": ["white", "blue"]}
        flood_map = folium.Map(location=[28.55, 77.55], zoom_start=12)
        flood_map.add_ee_layer(flood_mask.selfMask(), vis_params, "Flood Extent")
        progress.progress(100)

        st.subheader("Flood Extent Map")
        st_folium(flood_map, width=700, height=500)
        st.success("Flood mapping complete! ✅")
