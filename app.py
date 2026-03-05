import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
import json

# ==============================
# EARTH ENGINE INITIALIZATION (Corrected for Service Account)
# ==============================

# Removed ee.Authenticate() completely
@st.cache_resource
def init_ee():
    """
    Initialize Google Earth Engine using Service Account credentials stored in Streamlit secrets.
    """
    service_account_info = json.loads(st.secrets["EE_SERVICE_ACCOUNT"])

    credentials = ee.ServiceAccountCredentials(
        service_account_info["client_email"],
        key_data=json.dumps(service_account_info)
    )

    ee.Initialize(credentials)
    return True

init_ee()

# ==============================
# FOLIUM + EARTH ENGINE LAYER
# ==============================

def add_ee_layer(self, ee_image, vis_params, name):
    map_id = ee.Image(ee_image).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True
    ).add_to(self)

folium.Map.add_ee_layer = add_ee_layer

# ==============================
# STREAMLIT PAGE CONFIG
# ==============================

st.set_page_config(layout="wide", page_title="SAR Flood Mapping Tool")

page = st.sidebar.selectbox("Navigation", ["Home", "Flood Analysis"])

# ==============================
# HOME PAGE
# ==============================

if page == "Home":
    st.title("SAR Flood Mapping Tool")

    st.markdown(
        """
This tool estimates **flood extent using Sentinel-1 SAR imagery**
through the **Google Earth Engine API**.

Flood areas are detected by comparing radar backscatter
**before and after a flood event**.

### How to use

1. Go to **Flood Analysis**
2. Select **Pre-Flood and Post-Flood dates**
3. Adjust the **threshold if needed**
4. Click **Run Flood Mapping**

A flood extent map will appear automatically.
"""
    )

# ==============================
# FLOOD ANALYSIS PAGE
# ==============================

elif page == "Flood Analysis":
    st.title("Flood Extent Analysis")

    # Default AOI (small for fast testing)
    default_aoi = ee.Geometry.Rectangle([77.5, 28.5, 77.6, 28.6])
    st.info("Default AOI is set for quick testing.")

    # Default dates
    today = date.today()
    default_pre_start = today - timedelta(days=14)
    default_pre_end = today - timedelta(days=8)
    default_post_start = today - timedelta(days=7)
    default_post_end = today - timedelta(days=1)

    # Sidebar inputs
    st.sidebar.subheader("Select Dates")
    pre_start = st.sidebar.date_input("Pre-Flood Start", default_pre_start)
    pre_end = st.sidebar.date_input("Pre-Flood End", default_pre_end)
    post_start = st.sidebar.date_input("Post-Flood Start", default_post_start)
    post_end = st.sidebar.date_input("Post-Flood End", default_post_end)
    threshold = st.sidebar.slider("Flood Threshold", 0.5, 5.0, 1.25)

    # AOI Map
    st.subheader("Area of Interest")
    m = folium.Map(location=[28.55, 77.55], zoom_start=12)
    st_folium(m, width=700, height=400)

    # Fetch Sentinel-1 Data
    @st.cache_data
    def fetch_s1(aoi, start, end):
        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi)
            .filterDate(str(start), str(end))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
            .select("VV")
        )
        return collection.median()

    # Run Flood Analysis
    if st.button("Run Flood Mapping"):
        progress = st.progress(0)

        st.info("Fetching pre-flood imagery...")
        s1_pre = fetch_s1(default_aoi, pre_start, pre_end)
        progress.progress(30)

        st.info("Fetching post-flood imagery...")
        s1_post = fetch_s1(default_aoi, post_start, post_end)
        progress.progress(60)

        st.info("Calculating flood mask...")
        ratio = s1_post.divide(s1_pre)
        flood_mask = ratio.gt(threshold)
        progress.progress(85)

        st.info("Rendering flood map...")
        flood_map = folium.Map(location=[28.55, 77.55], zoom_start=12)
        vis = {"min": 1, "max": 3, "palette": ["white", "blue"]}
        flood_map.add_ee_layer(flood_mask.selfMask(), vis, "Flood Extent")
        progress.progress(100)

        st.subheader("Flood Extent Map")
        st_folium(flood_map, width=700, height=500)
        st.success("Flood mapping completed successfully!")
