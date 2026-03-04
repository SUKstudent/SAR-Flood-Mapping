import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import tifffile

# ---------- App Title ----------
st.title("SAR Flood Mapping System (No Rasterio)")
st.success("App loaded successfully 🚀")

# ---------- File Upload ----------
before_file = st.file_uploader("Upload Before-Flood SAR Image (GeoTIFF)", type=["tif", "tiff"])
after_file = st.file_uploader("Upload After-Flood SAR Image (GeoTIFF)", type=["tif", "tiff"])
ground_truth_file = st.file_uploader("Upload Ground Truth Flood Map (Optional)", type=["tif", "tiff"])

# ---------- Flood Detection Function ----------
def detect_flood(before, after, threshold=1.25):
    ratio = after / (before + 1e-6)
    flood_map = ratio > threshold
    return flood_map.astype(np.uint8)

# ---------- Metrics Function ----------
def calculate_metrics(actual, predicted):
    actual_flat = actual.flatten()
    predicted_flat = predicted.flatten()
    
    if np.sum(actual_flat) == 0:
        return pd.DataFrame({"Warning": ["Ground truth has no flooded pixels"]})
    
    accuracy = accuracy_score(actual_flat, predicted_flat)
    precision = precision_score(actual_flat, predicted_flat)
    recall = recall_score(actual_flat, predicted_flat)
    f1 = f1_score(actual_flat, predicted_flat)
    
    return pd.DataFrame({
        "Accuracy": [accuracy],
        "Precision": [precision],
        "Recall": [recall],
        "F1-Score": [f1]
    })

# ---------- Main Processing ----------
if before_file and after_file:
    # Read GeoTIFFs as NumPy arrays
    before_img = tifffile.imread(before_file)
    after_img = tifffile.imread(after_file)

    # Detect flood
    flood_map = detect_flood(before_img, after_img)

    # Visualization
    fig, ax = plt.subplots(1, 3, figsize=(18, 6))
    ax[0].imshow(before_img, cmap="gray")
    ax[0].set_title("Before Flood")
    ax[0].axis("off")

    ax[1].imshow(after_img, cmap="gray")
    ax[1].set_title("After Flood")
    ax[1].axis("off")

    ax[2].imshow(flood_map, cmap="Blues")
    ax[2].set_title("Detected Flood")
    ax[2].axis("off")

    st.pyplot(fig)

    # Flood area estimation
    pixel_resolution = 10  # meters
    flooded_pixels = np.sum(flood_map)
    flooded_area_km2 = (flooded_pixels * pixel_resolution**2) / 1e6
    st.subheader("Flood Area Estimation")
    st.write(f"Estimated Flooded Area: **{flooded_area_km2:.2f} sq.km**")

    # Optional ground truth metrics
    if ground_truth_file:
        ground_truth = tifffile.imread(ground_truth_file)
        metrics_df = calculate_metrics(ground_truth, flood_map)
        st.subheader("Flood Detection Metrics")
        st.dataframe(metrics_df)
