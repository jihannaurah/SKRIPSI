import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. KONFIGURASI TAMPILAN HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Rekomendasi Diet", page_icon="🥗", layout="wide")

# CSS Custom untuk mempercantik tampilan tabel
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🥗 Sistem Rekomendasi Paket Menu Diet")
st.write("Dapatkan rekomendasi menu harian yang dipersonalisasi berdasarkan algoritma AI Cosine Similarity.")
st.markdown("---")

# ==========================================
# 2. FUNGSI PEMBANTU (PARSING MENU)
# ==========================================
def pecah_menu_ke_tabel(sarapan, siang, malam):
    """Fungsi untuk memecah string menu menjadi baris tabel yang rapi"""
    data_tabel = []
    
    waktu_makan = [("🌅 Sarapan", sarapan), ("☀️ Makan Siang", siang), ("🌙 Makan Malam", malam)]
    
    for waktu, menu_str in waktu_makan:
        # Memisahkan berdasarkan koma
        items = menu_str.split(',')
        for item in items:
            # Mencari berat di dalam kurung menggunakan Regex
            gram_match = re.search(r'\((.*?)\)', item)
            berat = gram_match.group(1) if gram_match else "-"
            # Menghapus bagian dalam kurung dari nama menu
            nama_menu = re.sub(r'\(.*?\)', '', item).strip()
            
            data_tabel.append({
                "Waktu Makan": waktu,
                "Nama Menu": nama_menu,
                "Porsi / Berat": berat
            })
    return pd.DataFrame(data_tabel)

# ==========================================
# 3. FORM INPUT DATA PENGGUNA
# ==========================================
with st.sidebar:
    st.header("📝 Form Data Diri")
    with st.form("form_pengguna"):
        nama = st.text_input("Nama Lengkap")
        gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        usia = st.number_input("Usia (Tahun)", min_value=18, max_value=40, value=22, step=1)
        bb = st.number_input("Berat Badan (kg)", min_value=30, value=50, step=1) # Tanpa koma
        tb = st.number_input("Tinggi Badan (cm)", min_value=100, value=160, step=1) # Tanpa koma
        
        aktivitas = st.selectbox("Tingkat Aktivitas", [
            "Ringan (Jarang olahraga)", 
            "Sedang (Olahraga 1-3x seminggu)", 
            "Berat (Olahraga 3-5x seminggu)", 
            "Sangat Berat (Olahraga tiap hari)"
        ])
        goal = st.selectbox("Tujuan Diet (Goal)", [
            "Defisit (Menurunkan Berat Badan)", 
            "Maintenance (Menjaga Berat Badan)", 
            "Surplus (Menambah Massa Otot)"
        ])
        
        submitted = st.form_submit_button("Cari Rekomendasi 🚀")

# ==========================================
# 4. PROSES PERHITUNGAN & MODELLING
# ==========================================
if submitted:
    if not nama:
        st.warning("⚠️ Mohon isi Nama Anda di sidebar!")
    else:
        # A. Perhitungan BMR & TDEE
        if gender == "Laki-laki":
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) + 5
        else:
            bmr = (10 * bb) + (6.25 * tb) - (5 * usia) - 161
            
        pal = {"Ringan": 1.375, "Sedang": 1.55, "Berat": 1.725, "Sangat Berat": 1.9}
        key_pal = [k for k in pal.keys() if k in aktivitas][0]
        tdee = bmr * pal[key_pal]
        
        # B. Target Gizi
        target_kalori = tdee
        if "Defisit" in goal: target_kalori -= 500
        elif "Surplus" in goal: target_kalori += 500
        
        t_protein = (target_kalori * 0.20) / 4
        t_karbo = (target_kalori * 0.50) / 4
        t_lemak = (target_kalori * 0.30) / 9

        # --- DISPLAY TARGET KALORI (DIPERJELAS) ---
        st.subheader(f"📊 Hasil Analisis Kebutuhan Energi: {nama}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Target Kalori", f"{target_kalori:.0f} Kkal")
        c2.metric("Protein", f"{t_protein:.1f}g")
        c3.metric("Karbohidrat", f"{t_karbo:.1f}g")
        c4.metric("Lemak", f"{t_lemak:.1f}g")
        
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
            
            # Hybrid Filtering
            if "Defisit" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('D')]
            elif "Surplus" in goal: df_h = df_paket[df_paket['Paket'].str.startswith('S')]
            else: df_h = df_paket[df_paket['Paket'].str.startswith('M')]
            
            top_1 = df_h.sort_values('Score', ascending=False).iloc[0]
            
            # --- DISPLAY HASIL REKOMENDASI ---
            st.success(f"🏆 Rekomendasi Terbaik: Paket {top_1['Id Paket']} (Skor Kemiripan: {top_1['Score']:.4f})")
            
            st.write("### 🍱 Rincian Menu Harian (Gramasi Terperinci)")
            
            # Memanggil fungsi pemecah tabel
            df_menu_rapi = pecah_menu_ke_tabel(top_1['Sarapan'], top_1['Makan Siang'], top_1['Makan Malam'])
            
            # Menampilkan tabel statis agar rapi
            st.table(df_menu_rapi)
            
            # Detail Info Bawah
            st.info(f"💡 **Informasi Gizi Paket:** Menu ini mengandung total **{top_1['Total Kalori']} Kkal**. "
                    f"Selisih dengan target Anda adalah **{abs(top_1['Total Kalori'] - target_kalori):.1f} Kkal**.")
            
        else:
            st.error("File 'datasetpaketmenu.csv' tidak ditemukan.")
else:
    # Tampilan awal saat belum submit
    st.info("👈 Silakan masukkan data diri Anda pada sidebar di sebelah kiri untuk melihat rekomendasi.")
