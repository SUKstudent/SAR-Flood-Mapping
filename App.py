import streamlit as st
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# ---------- App Title ----------
st.title("SAR Flood Mapping System")
st.success("App loaded successfully 🚀")

# ---------- File Upload ----------
before_file = st.file_uploader("Upload Before-Flood SAR Image (GeoTIFF)", type=["tif"])
after_file = st.file_uploader("Upload After-Flood SAR Image (GeoTIFF)", type=["tif"])
ground_truth_file = st.file_uploader("Upload Ground Truth Flood Map (Optional)", type=["tif"])

# ---------- Flood Detection ----------
def detect_flood(before, after, threshold=1.25):
    # Prevent division by zero
    ratio = after / (before + 1e-6)
    flood_map = ratio > threshold
    return flood_map.astype(np.uint8)

# ---------- Metrics ----------
def calculate_metrics(actual, predicted):
    # Flatten arrays for sklearn metrics
    actual_flat = actual.flatten()
    predicted_flat = predicted.flatten()
    # Avoid errors if actual has only 0s
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

# ---------- Processing ----------
if before_file and after_file:
    # Read SAR images safely
    with rasterio.open(before_file) as src:
        before_img = src.read(1).astype(np.float32)
    with rasterio.open(after_file) as src:
        after_img = src.read(1).astype(np.float32)

    # Detect flooded areas
    flood_map = detect_flood(before_img, after_img)

    # ---------- Visualization ----------
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
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

    # ---------- Flood Area Estimation ----------
    pixel_resolution = 10  # meters (adjust to your SAR data)
    flooded_pixels = np.sum(flood_map)
    flooded_area_km2 = (flooded_pixels * pixel_resolution**2) / 1e6
    st.subheader("Flood Area Estimation")
    st.write(f"Estimated Flooded Area: **{flooded_area_km2:.2f} sq.km**")

    # ---------- Optional Metrics ----------
    if ground_truth_file:
        with rasterio.open(ground_truth_file) as src:
            ground_truth = src.read(1).astype(np.uint8)

        metrics_df = calculate_metrics(ground_truth, flood_map)
        st.subheader("Flood Detection Metrics")
        st.dataframe(metrics_df)