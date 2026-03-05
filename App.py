import streamlit as st
import rasterio
import numpy as np
from scipy.ndimage import median_filter
import matplotlib.pyplot as plt

st.title("SAR Flood Mapping using Sentinel-1")

# Upload SAR images
pre_file = st.file_uploader("Upload Pre-Flood SAR Image (.tif)", type=["tif"])
post_file = st.file_uploader("Upload Post-Flood SAR Image (.tif)", type=["tif"])

if pre_file and post_file:

    with rasterio.open(pre_file) as src:
        pre = src.read(1)

    with rasterio.open(post_file) as src:
        post = src.read(1)

    # Speckle filtering
    pre_filtered = median_filter(pre, size=5)
    post_filtered = median_filter(post, size=5)

    # Difference
    difference = pre_filtered - post_filtered

    # Threshold slider
    threshold = st.slider("Flood Detection Threshold", -5.0, 0.0, -1.5)

    flood_mask = difference < threshold

    st.subheader("Pre-Flood SAR Image")
    st.image(pre_filtered, clamp=True)

    st.subheader("Post-Flood SAR Image")
    st.image(post_filtered, clamp=True)

    st.subheader("Detected Flood Area")
    st.image(flood_mask.astype(int), clamp=True)
