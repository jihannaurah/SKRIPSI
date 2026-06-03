import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

# ==============================================================================
# 1. LOAD DATA DAN SCALER (PAKAI PAKET MENU)
# ==============================================================================
@st.cache_data
def load_data_dan_scaler():
    # Pastikan path file ini sesuai dengan lokasi file CSV di folder Streamlit-mu
    df_paket = pd.read_csv('datasetpaketmenu.csv', sep=';')
    df_paket.columns = df_paket.columns.str.strip()
    
    # Bikin Scaler
    scaler = MinMaxScaler()
    kolom_gizi = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
    
    # Timbangan dikunci pakai Paket Menu
    scaler.fit(df_paket[kolom_gizi])
    
    # Bikin Vektor Database Paket
    vektor_database = scaler.transform(df_paket[kolom_gizi])
    
    return df_paket, scaler, vektor_database

# ==============================================================================
# 2. FUNGSI HITUNG ENERGI & MAKRONUTRISI (DENGAN SAFETY THRESHOLD)
# ==============================================================================
def hitung_kebutuhan_user(bb, tb, usia, gender, aktivitas, goal):
    # A. Multiplier Aktivitas
    akt = str(aktivitas).strip().lower()
    if "sangat berat" in akt or "sangat aktif" in akt: pal = 1.900
    elif "sangat ringan" in akt: pal = 1.200
    elif "berat" in akt: pal = 1.725
    elif "sedang" in akt: pal = 1.550
    elif "ringan" in akt: pal = 1.375
    else: pal = 1.200

    # B. BMR Mifflin
    if 'laki' in str(gender).lower(): 
        bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
    else: 
        bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161

    # C. TDEE
    tdee = bmr * pal
    target_kalori = tdee
    goal_str = str(goal).lower()

    # D. SAFETY THRESHOLD (Sama persis dengan Laporan Bab 4)
    if ('turun' in goal_str or 'defisit' in goal_str) and tdee > 1500:
        target_kalori -= 500
    elif ('naik' in goal_str or 'surplus' in goal_str) and tdee < 2500:
        target_kalori += 500

    # E. Makronutrisi
    target_protein = (target_kalori * 0.20) / 4
    target_karbo = (target_kalori * 0.50) / 4
    target_lemak = (target_kalori * 0.30) / 9
    
    return bmr, tdee, target_kalori, target_protein, target_karbo, target_lemak

# ==============================================================================
# 3. FUNGSI REKOMENDASI COSINE SIMILARITY
# ==============================================================================
def dapatkan_rekomendasi_web(target_kalori, target_protein, target_karbo, target_lemak, goal, df_paket, scaler, vektor_database):
    
    kolom_gizi = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
    
    # Vektorisasi target user
    df_target = pd.DataFrame([[target_kalori, target_protein, target_karbo, target_lemak]], columns=kolom_gizi)
    vektor_user = scaler.transform(df_target)
    
    # Hitung Cosine Similarity
    skor_kemiripan = cosine_similarity(vektor_user, vektor_database)[0]
    
    df_hasil = df_paket.copy()
    df_hasil['Similarity_Score'] = skor_kemiripan
    
    # Filter berdasarkan Goal (D/M/S)
    goal_str = str(goal).lower()
    if 'turun' in goal_str or 'defisit' in goal_str:
        df_hasil = df_hasil[df_hasil['Paket'].str.startswith('D', na=False)]
    elif 'naik' in goal_str or 'surplus' in goal_str:
        df_hasil = df_hasil[df_hasil['Paket'].str.startswith('S', na=False)]
    else:
        df_hasil = df_hasil[df_hasil['Paket'].str.startswith('M', na=False)]
        
    # Urutkan dari yang paling mirip
    df_hasil = df_hasil.sort_values(by='Similarity_Score', ascending=False)
    
    return df_hasil.head(1) # Ambil 1 rekomendasi terbaik
