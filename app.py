import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN HALAMAN & CSS
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

st.markdown("""
    <style>
    div[data-testid="InputInstructions"] { display: none !important; }
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05); 
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px); 
        background-color: rgba(255, 255, 255, 0.08);
    }
    [data-testid="stMetricLabel"] p {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #00d4ff !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🥗 Sistem Rekomendasi Paket Menu Harian Sehat")
st.write("Mulai Hidup Sehat Dengan Menentukan Makanan Harian yang Sehat.")
st.markdown("---")

# ==========================================
# 2. FUNGSI PEMBANTU
# ==========================================
def format_menu_menyamping(sarapan, siang, malam):
    data_tabel = []
    waktu_makan = [("🌅 Sarapan", sarapan), ("☀️ Makan Siang", siang), ("🌙 Makan Malam", malam)]
    
    for waktu, menu_str in waktu_makan:
        items = menu_str.split(',')
        nama_list = []
        berat_list = []
        
        for item in items:
            gram_match = re.search(r'\((.*?)\)', item)
            berat = gram_match.group(1) if gram_match else "-"
            nama_menu = re.sub(r'\(.*?\)', '', item).strip()
            
            nama_list.append(nama_menu)
            berat_list.append(berat)
            
        data_tabel.append({
            "Waktu Makan": waktu,
            "Daftar Menu": ", ".join(nama_list),
            "Total Porsi/Gram": ", ".join(berat_list)
        })
    return pd.DataFrame(data_tabel)

# ==========================================
# 3. FORM INPUT DATA PENGGUNA (SIDEBAR)
# ==========================================
with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama = st.text_input("Nama Lengkap")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        
        # Usia dibiarkan bisa diisi bebas (untuk mengetes validasi)
        usia = st.number_input("Usia (Tahun)", min_value=1, value=None, placeholder="Ketik Usia Anda...", step=1)
        
        bb = st.number_input("Berat Badan (kg)", min_value=10, value=None, placeholder="Ketik BB...", step=1) 
        tb = st.number_input("Tinggi Badan (cm)", min_value=50, value=None, placeholder="Ketik TB...", step=1)
        
        aktivitas = st.selectbox("Tingkat Aktivitas", [
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)",
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)",
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)",
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)",
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)"
        ])
        
        goal = st.selectbox("Tujuan Diet (Goal)", [
            "Defisit (Menurunkan Berat Badan)", 
            "Maintenance (Menjaga Berat Badan)", 
            "Surplus (Menambah Massa Otot)"
        ])

        # FITUR BARU: PERTANYAAN ALERGI
        alergi = st.selectbox("Riwayat Alergi Makanan", [
            "Tidak Ada", 
            "Ada Alergi (Seafood, Kacang, Susu, dll)"
        ])
        
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

# ==========================================
# 4. PROSES PERHITUNGAN & VALIDASI
# ==========================================
if submitted:
    # --- GERBANG VALIDASI 1: Form Kosong ---
    if not nama or bb is None or tb is None or usia is None:
        st.warning("⚠️ Mohon lengkapi Nama, Usia, Berat Badan, dan Tinggi Badan Anda di form samping!")
        
    # --- GERBANG VALIDASI 2: Batasan Usia (18 - 40 Tahun) ---
    elif usia < 18 or usia > 40:
        st.error(f"🛑 MAAF! Rekomendasi hanya dapat memproses rentang usia dewasa sehat (18 - 40 Tahun). Usia yang Anda masukkan: {usia} Tahun.")
        
    # --- GERBANG VALIDASI 3: Batasan Alergi Makanan ---
    elif alergi != "Tidak Ada":
        st.error("🛑 MAAF! Untuk mencegah risiko medis, saat ini sistem tidak dapat memproses rekomendasi bagi pengguna yang memiliki riwayat alergi makanan.")
        
    # --- JIKA LOLOS SEMUA VALIDASI, SISTEM DIJALANKAN ---
    else:
        # A. Perhitungan BMR & TDEE
        if gender == "Laki-laki":
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
        else:
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
            
        pal_dict = {
            "Sangat Ringan (Duduk bekerja/belajar, hampir tidak pernah olahraga)": 1.2,
            "Ringan (Aktivitas sehari-hari + Olahraga ringan 1-3 hari/minggu)": 1.375,
            "Sedang (Aktivitas cukup padat + Olahraga kardio/gym 3-5 hari/minggu)": 1.55,
            "Berat (Pekerjaan fisik/Olahraga berat 6-7 hari/minggu)": 1.725,
            "Sangat Berat (Atlet profesional atau pekerjaan fisik sangat berat setiap hari)": 1.9
        }
        tdee = bmr * pal_dict[aktivitas]
        
        target_kalori = tdee
        if "Defisit" in goal: target_kalori -= 500
        elif "Surplus" in goal: target_kalori += 500
        
        t_protein = (target_kalori * 0.20) / 4
        t_karbo = (target_kalori * 0.50) / 4
        t_lemak = (target_kalori * 0.30) / 9

        # --- DISPLAY TARGET KALORI ---
        st.subheader(f"📊 Hasil Analisis Kebutuhan Energi: {nama.upper()}")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Target Kalori", f"{target_kalori:.0f} (Kkal)")
        with col_m2:
            st.metric("Protein", f"{t_protein:.1f} (g)")
        with col_m3:
            st.metric("Karbohidrat", f"{t_karbo:.1f} (g)")
        with col_m4:
            st.metric("Lemak", f"{t_lemak:.1f} (g)")
        
        st.markdown("---")

        # C. Modelling Cosine Similarity
        file_paket = 'datasetpaketmenu.csv' 
        if os.path.exists(file_paket):
            df_paket = pd.read_csv(file_paket, sep=';')
            df_paket.columns = df_paket.columns.str.strip()
            
            scaler = MinMaxScaler()
            fitur = ['Total Kalori', 'Total Protein', 'Total Karbohidrat', 'Total Lemak']
            vektor_db = scaler.fit_transform(df_paket[fitur])
            
            target_vec = pd.DataFrame([[target_kalori, t_protein, t_karbo, t_lemak]], columns=fitur)
            vektor_user = scaler.transform(target_vec)
            
            skor = cosine_similarity(vektor_user, vektor_db)[0]
            df_paket['Score'] = skor
            
            if "Defisit" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('D')]
            elif "Surplus" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('S')]
            else: df_h = df_paket[df_paket['Paket'].str.startswith('M')]
            
            top_1 = df_h.sort_values('Score', ascending=False).iloc[0]
            
            # --- DISPLAY HASIL REKOMENDASI ---
            st.success(f"🏆 Rekomendasi Terbaik: Paket {top_1['Id Paket']} (Kategori: {top_1['Paket']}) (Skor Kemiripan: {top_1['Score']:.4f})")
            
            st.write("### 🍱 Rincian Menu Harian")
            df_menu_rapi = format_menu_menyamping(top_1['Sarapan'], top_1['Makan Siang'], top_1['Makan Malam'])
            st.table(df_menu_rapi.assign(hack='').set_index('hack'))
            
            st.info(f"💡 **Informasi Gizi Paket:** Menu ini mengandung total **{top_1['Total Kalori']} (Kkal)**. "
                    f"Selisih dengan target Anda adalah **{abs(top_1['Total Kalori'] - target_kalori):.1f} (Kkal)**.")
        else:
            st.error("File 'datasetpaketmenu.csv' tidak ditemukan.")
else:
    st.info("👈 Silakan isi form data diri Anda pada sidebar di sebelah kiri lalu klik 'Cari Rekomendasi'.")
