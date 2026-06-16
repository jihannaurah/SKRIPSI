import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import base64
import time
import pickle  # <--- INI TAMBAHAN UNTUK MEMBACA FILE .PKL
import streamlit.components.v1 as components
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN & CSS (ADAPTIVE & CLEAN)
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

st.markdown("""
    <style>
    /* HAPUS TULISAN PRESS ENTER & INSTRUKSI INPUT */
    [data-testid="InputInstructions"] { 
        display: none !important; 
        visibility: hidden !important;
    }
    
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 5rem !important;
    }

    /* KOTAK METRIC ADAPTIF */
    [data-testid="stMetric"] {
        background-color: rgba(0, 212, 255, 0.05); 
        border: 1px solid rgba(0, 212, 255, 0.2);
        padding: 15px 5px;
        border-radius: 15px;
        text-align: center;
    }
    
    [data-testid="stMetricLabel"] p {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #00b4d8 !important; 
    }

    /* KOTAK DESKRIPSI (TANPA WARNA TEKS STATIS AGAR AMAN DI MODE GELAP) */
    .desc-box {
        background-color: rgba(0, 212, 255, 0.08); 
        border-left: 5px solid #00d4ff; 
        padding: 20px; 
        border-radius: 10px; 
        margin-top: 15px;
        margin-bottom: 30px;
        font-size: 16px;
        line-height: 1.7;
        border: 1px solid rgba(0, 212, 255, 0.1);
    }

    /* RESPONSIVE JUDUL */
    @media (max-width: 640px) {
        h1 { font-size: 20px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNGSI PEMBANTU
# ==========================================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def format_menu_ke_tabel(sarapan, siang, malam):
    data_tabel = []
    waktu_makan = [("🌅 Sarapan", sarapan), ("☀️ Makan Siang", siang), ("🌙 Makan Malam", malam)]
    for waktu, menu_str in waktu_makan:
        items = menu_str.split('+') if '+' in menu_str else menu_str.split(',')
        nama_list, porsi_list = [], []
        for item in items:
            match = re.search(r'\((.*?)\)', item)
            porsi_list.append(match.group(1) if match else "-")
            nama_list.append(re.sub(r'\(.*?\)', '', item).strip())
        data_tabel.append({
            "Waktu Makan": waktu,
            "Bahan Makanan": ", ".join(nama_list),
            "Porsi (Gram)": ", ".join(porsi_list)
        })
    return pd.DataFrame(data_tabel)

# HEADER: LOGO & JUDUL
img_file = 'Macronutrients.png' 
if os.path.exists(img_file):
    img_base64 = get_base64_of_bin_file(img_file)
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; border-bottom: 2px solid rgba(128,128,128,0.2); padding-bottom: 20px; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid rgba(0,212,255,0.2);">
            <h1 style="margin: 0; font-size: 32px; font-weight: 800; letter-spacing: -1px;">Sistem Rekomendasi Paket Menu Harian Sehat</h1>
        </div>
        """, unsafe_allow_html=True)

# TAGLINE
st.markdown("""
    <div style="text-align: center; font-style: italic; font-size: 16px; margin-top: -10px; margin-bottom: 10px;">
