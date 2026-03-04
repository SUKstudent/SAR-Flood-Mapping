# src/utils.py
import streamlit as st

def add_logo(path):
    st.sidebar.image(path, use_column_width=True)

def add_about():
    st.sidebar.markdown("This app estimates flood extent using Sentinel-1 SAR data.")

def set_home_page_style():
    st.markdown("<style>body {background-color: #f0f2f6;}</style>", unsafe_allow_html=True)

def toggle_menu_button():
    # Example: hide menu in deployed version
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )