import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

# Mengatur konfigurasi halaman web
st.set_page_config(page_title="Rekomendasi Diet AI", page_icon="🥗", layout="wide")

# ==============================================================================
# 1. LOAD DATA DAN SCALER (PAKAI PAKET MENU)
# ==============================================================================
@st.cache_data
def load_data_dan_scaler():
    # Load dataset
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
    
    return df_hasil.head(1)

# ==============================================================================
# 4. TAMPILAN USER INTERFACE (UI) STREAMLIT
# ==============================================================================
st.title("🍽️ Sistem Rekomendasi Menu Makanan Diet")
st.markdown("Masukkan data profil fisik Anda di bawah ini untuk mendapatkan rekomendasi paket menu makanan harian yang paling sesuai dengan kebutuhan gizi dan kalori Anda.")
st.write("---")

# Load Data di Latar Belakang
df_paket, scaler, vektor_database = load_data_dan_scaler()

# Membuka Form Input User
with st.form("form_input_user"):
    st.subheader("Data Profil Fisik")
    col1, col2 = st.columns(2)
    
    with col1:
        usia = st.number_input("Usia (Tahun)", min_value=18, max_value=40, value=22, step=1)
        gender = st.selectbox("Jenis Kelamin", ["Perempuan", "Laki-laki"])
        bb = st.number_input("Berat Badan (Kg)", min_value=30.0, max_value=150.0, value=55.0, step=0.1)
        
    with col2:
        tb = st.number_input("Tinggi Badan (Cm)", min_value=100.0, max_value=220.0, value=160.0, step=0.1)
        aktivitas = st.selectbox("Tingkat Aktivitas Fisik", ["Sangat Ringan", "Ringan", "Sedang", "Berat", "Sangat Berat"])
        goal = st.selectbox("Tujuan Program Diet", ["Defisit Kalori (Turun Berat Badan)", "Maintenance (Jaga Berat Badan)", "Surplus Kalori (Naik Berat Badan)"])
    
    # Tombol Submit Form
    submit_button = st.form_submit_button("Analisis dan Berikan Rekomendasi 🚀")

# ==============================================================================
# 5. EKSEKUSI SETELAH TOMBOL DITEKAN
# ==============================================================================
if submit_button:
    # Proses Perhitungan
    bmr, tdee, target_kalori, target_protein, target_karbo, target_lemak = hitung_kebutuhan_user(bb, tb, usia, gender, aktivitas, goal)
    rekomendasi = dapatkan_rekomendasi_web(target_kalori, target_protein, target_karbo, target_lemak, goal, df_paket, scaler, vektor_database)
    paket_terpilih = rekomendasi.iloc[0]
    
    st.success("🎉 Berhasil! Berikut adalah rekomendasi terbaik untuk Anda.")
    
    # Menampilkan Target Gizi
    st.markdown("### 📊 Target Kebutuhan Gizi Harian Anda")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Kalori", f"{target_kalori:.1f} Kkal")
    k2.metric("Protein", f"{target_protein:.1f} g")
    k3.metric("Karbohidrat", f"{target_karbo:.1f} g")
    k4.metric("Lemak", f"{target_lemak:.1f} g")
    st.caption(f"*Catatan: Nilai BMR Anda adalah {bmr:.1f} Kkal dan TDEE Anda {tdee:.1f} Kkal.*")
    
    st.write("---")
    
    # Menampilkan Paket Rekomendasi
    st.markdown(f"### 🍱 Rekomendasi Menu: {paket_terpilih['Id Paket']} - {paket_terpilih['Paket']}")
    skor_persen = paket_terpilih['Similarity_Score'] * 100
    st.info(f"🎯 **Akurasi Sistem (Cosine Similarity): {paket_terpilih['Similarity_Score']:.4f} ({skor_persen:.2f}%)**")
    
    st.markdown("#### 📋 Rincian Menu Makan")
    with st.expander("🌅 Menu Sarapan Pagi", expanded=True):
        st.write(paket_terpilih['Sarapan'])
    with st.expander("☀️ Menu Makan Siang", expanded=True):
        st.write(paket_terpilih['Makan Siang'])
    with st.expander("🌌 Menu Makan Malam", expanded=True):
        st.write(paket_terpilih['Makan Malam'])
        
    st.write("---")
    
    # Menampilkan Total Kandungan Paket
    st.markdown("#### 📈 Kandungan Gizi dalam Paket Menu Ini")
    p1, p2, p3, p4 = st.columns(4)
    p1.warning(f"🔥 Kalori: {paket_terpilih['Total Kalori']} Kkal")
    p2.warning(f"🍗 Protein: {paket_terpilih['Total Protein']} g")
    p3.warning(f"🍞 Karbo: {paket_terpilih['Total Karbo']} g")
    p4.warning(f"🥑 Lemak: {paket_terpilih['Total Lemak']} g")
